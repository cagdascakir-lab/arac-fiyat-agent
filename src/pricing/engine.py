"""Saf hesap fonksiyonları. LLM yok, ağ yok, yan etki yok."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Optional

from src.data.models import Kurallar, ParcaDurumu, ParcaTipi

Karar = Literal["uygun", "pazarlik", "pahali"]


@dataclass(frozen=True)
class Parca:
    tip: ParcaTipi
    durum: ParcaDurumu
    konum: str = ""  # ör. "sol ön"; sadece gösterim için


@dataclass
class DokumSatiri:
    aciklama: str
    oran: float      # çarpan değişimi; ör. -0.06 (%6 düşüş) veya +0.01
    sonra: float     # bu adımdan sonraki tahmin (TL)


@dataclass
class Sonuc:
    referans: float
    tahmin: float
    dokum: list[DokumSatiri]
    ilan_fiyati: float
    fark_yuzde: float
    karar: Karar
    teklif_alt: float
    teklif_ust: float
    uyarilar: list[str] = field(default_factory=list)


def yas_carpani(yas: int, k: Kurallar, marka: str = "") -> float:
    """Azalan bakiye: her yıl bir önceki değerin yüzdesi kadar düşüş."""
    if yas <= 0:
        return 1.0
    marka_c = k.yas.marka_yas_carpani.get(marka, 1.0)
    carpan = 1.0
    for yil in range(1, yas + 1):
        if yil == 1:
            oran = k.yas.ilk_yil
        elif yil <= 10:
            oran = k.yas.yil_2_10
        else:
            oran = k.yas.yil_11_ve_sonrasi
        carpan *= 1 - oran * marka_c
    return carpan


def km_carpani(km: int, yas: int, k: Kurallar) -> float:
    """Beklenen km'den her 10.000 km sapma için ±oran, toplam ±maksimum_etki."""
    beklenen = max(yas, 0) * k.km.yillik_normal_km
    etki = -(km - beklenen) / 10_000 * k.km.her_10000_km_orani
    etki = max(-k.km.maksimum_etki, min(k.km.maksimum_etki, etki))
    return 1 + etki


def parca_dususu(parcalar: list[Parca], k: Kurallar) -> float:
    """Parça düşüşlerinin toplamı, tavanla sınırlı (0-1 arası kesir)."""
    toplam = sum(getattr(k.parca[p.tip], p.durum) for p in parcalar)
    return min(toplam, k.parca_toplam_tavan)


def karar_ver(fark_yuzde: float, k: Kurallar) -> Karar:
    if fark_yuzde <= k.karar.uygun_ust_sinir:
        return "uygun"
    if fark_yuzde <= k.karar.pazarlik_ust_sinir:
        return "pazarlik"
    return "pahali"


def hesapla(
    *,
    referans_fiyat: float,
    referans_model_yili: int,
    ilan_yili: int,
    km: int,
    marka: str,
    parcalar: list[Parca],
    agir_hasar: bool,
    ilan_fiyati: float,
    k: Kurallar,
    tramer_tutari: Optional[float] = None,
    veri_tarihi: Optional[date] = None,
    bugun: Optional[date] = None,
) -> Sonuc:
    if referans_fiyat <= 0 or ilan_fiyati <= 0:
        raise ValueError("fiyatlar pozitif olmalı")
    if km < 0:
        raise ValueError("km negatif olamaz")

    yas = max(referans_model_yili - ilan_yili, 0)
    tahmin = float(referans_fiyat)
    dokum: list[DokumSatiri] = []

    yc = yas_carpani(yas, k, marka)
    tahmin *= yc
    dokum.append(DokumSatiri(f"Yaş düşüşü ({yas} yıl)", yc - 1, tahmin))

    kc = km_carpani(km, yas, k)
    tahmin *= kc
    beklenen = yas * k.km.yillik_normal_km
    km_t, bek_t = f"{km:,}".replace(",", "."), f"{beklenen:,}".replace(",", ".")
    dokum.append(DokumSatiri(f"Km düzeltmesi ({km_t} km; beklenen {bek_t} km)", kc - 1, tahmin))

    if parcalar:
        ham = sum(getattr(k.parca[p.tip], p.durum) for p in parcalar)
        pd = parca_dususu(parcalar, k)
        tahmin *= 1 - pd
        ek = " (tavan uygulandı)" if ham > pd else ""
        dokum.append(DokumSatiri(f"Değişen/boyalı parçalar ({len(parcalar)} parça){ek}", -pd, tahmin))

    if agir_hasar:
        tahmin *= 1 - k.agir_hasar
        dokum.append(DokumSatiri("Ağır hasar kaydı", -k.agir_hasar, tahmin))

    fark = (ilan_fiyati - tahmin) / tahmin
    uyarilar: list[str] = []
    if fark < k.karar.supheli_ucuz_alt_sinir:
        uyarilar.append("İlan tahminin %20'den fazla altında: şüpheli derecede ucuz, ekspertiz ve tramer kontrolü yaptır.")
    if agir_hasar:
        uyarilar.append("Ağır hasar kaydı var: tahmin yüksek belirsizlik içerir.")
    if tramer_tutari is not None and tramer_tutari > tahmin * k.tramer_uyari_orani:
        uyarilar.append(f"Tramer tutarı tahminin %{k.tramer_uyari_orani*100:.0f}'undan fazla; hasar geçmişini ayrıntılı incele.")
    if veri_tarihi and bugun and (bugun - veri_tarihi).days > k.veri_eskime_gun:
        uyarilar.append(f"Sıfır fiyat verisi {(bugun - veri_tarihi).days} gün önce güncellenmiş; güncel olmayabilir.")
    if bugun and (bugun - k.kalibrasyon_tarihi).days > 180:
        uyarilar.append("Düşüş oranları 6 aydan uzun süredir kalibre edilmedi.")

    return Sonuc(
        referans=float(referans_fiyat),
        tahmin=tahmin,
        dokum=dokum,
        ilan_fiyati=float(ilan_fiyati),
        fark_yuzde=fark,
        karar=karar_ver(fark, k),
        # Teklif ilan fiyatını asla aşmaz
        teklif_alt=min(tahmin * k.teklif.alt, ilan_fiyati),
        teklif_ust=min(tahmin * k.teklif.ust, ilan_fiyati),
        uyarilar=uyarilar,
    )
