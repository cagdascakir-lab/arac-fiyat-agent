"""İlandaki marka/model/motor/paketi en güncel model yılı sıfır kaydına eşler.

Eşleşme tipleri:
- birebir: aynı model, aynı yakıt, aynı motor (ad veya hacim), aynı paket ve tek aday
- en_yakin: model var ama motor/paket birebir yok ya da birden fazla eşit aday var; kullanıcı seçer
- bulunamadi: marka/model veri tabanında yok -> tahmin üretilmez
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, Optional

from .models import SifirKayit

MARKA_TAKMA = {
    "vw": "volkswagen",
    "mercedes": "mercedesbenz",
    "mercedesbenz": "mercedesbenz",
    "benz": "mercedesbenz",
}

_TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
BILINMEYEN_MOTOR = 9.0


def norm(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.translate(_TR).lower()
    return re.sub(r"[^a-z0-9.]", "", s)


def _n(s: Optional[str]) -> str:
    return norm(s).replace(".", "")


def marka_norm(s: Optional[str]) -> str:
    n = _n(s)
    return MARKA_TAKMA.get(n, n)


def hacim_bul(motor: Optional[str]) -> Optional[float]:
    if not motor:
        return None
    m = re.search(r"(\d)[.,](\d)", motor)
    return float(f"{m.group(1)}.{m.group(2)}") if m else None


def yakit_norm(s: Optional[str]) -> str:
    n = norm(s)
    if not n:
        return ""
    if "elektr" in n:
        return "elektrik"
    if "hibrit" in n or "hybrid" in n:
        return "hibrit"
    if "dizel" in n or "diesel" in n:
        return "dizel"
    if "benzin" in n or "lpg" in n:
        return "benzin"
    return n


def vites_norm(s: Optional[str]) -> str:
    n = norm(s)
    if not n:
        return ""
    return "manuel" if "manuel" in n or "duz" in n else "otomatik"


@dataclass
class Eslesme:
    tip: Literal["birebir", "en_yakin", "bulunamadi"]
    kayit: Optional[SifirKayit] = None
    adaylar: list[SifirKayit] = field(default_factory=list)
    mesaj: str = ""


def _model_filtrele(kayitlar: list[SifirKayit], marka: str, model: str) -> list[SifirKayit]:
    ayni_marka = [k for k in kayitlar if marka_norm(k.marka) == marka_norm(marka)]
    m = _n(model)
    if not m:
        return []
    tam = [k for k in ayni_marka if _n(k.model) == m]
    if tam:
        return tam
    # İlan modeli daha uzunsa ("Golf 8") -> veri tabanında ön eki olan en uzun model
    on_ek = [k for k in ayni_marka if m.startswith(_n(k.model))]
    if on_ek:
        en_uzun = max(len(_n(k.model)) for k in on_ek)
        return [k for k in on_ek if len(_n(k.model)) == en_uzun]
    # İlan modeli daha kısaysa ("Egea") -> tüm alt modeller aday ("Egea Sedan", "Egea Cross")
    return [k for k in ayni_marka if _n(k.model).startswith(m)]


def _motor_farki(k: SifirKayit, motor: Optional[str], hacim: Optional[float]) -> float:
    nm, nk = _n(motor), _n(k.motor)
    if nm and nk and (nm == nk or (len(nk) >= 3 and nk in nm) or (len(nm) >= 3 and nm in nk)):
        return 0.0
    if hacim is not None and k.motor_hacmi is not None:
        return abs(k.motor_hacmi - hacim)
    return BILINMEYEN_MOTOR


def eslestir(
    kayitlar: list[SifirKayit],
    *,
    marka: str,
    model: str,
    motor: Optional[str] = None,
    paket: Optional[str] = None,
    yakit: Optional[str] = None,
    vites: Optional[str] = None,
) -> Eslesme:
    ayni_model = _model_filtrele(kayitlar, marka, model)
    if not ayni_model:
        return Eslesme("bulunamadi", mesaj=f"Veri tabanında '{marka} {model}' için sıfır fiyat kaydı yok.")

    son_yil = max(k.model_yili for k in ayni_model)
    guncel = [k for k in ayni_model if k.model_yili == son_yil]

    hacim = hacim_bul(motor)
    yk, vt, pk = yakit_norm(yakit), vites_norm(vites), _n(paket)

    def skor(k: SifirKayit):
        yakit_farki = 0 if not yk or yakit_norm(k.yakit) == yk else 1
        motor_f = _motor_farki(k, motor, hacim)
        paket_farki = 0 if pk and (_n(k.paket) == pk) else 1
        vites_farki = 0 if not vt or vites_norm(k.vites) == vt else 1
        return (yakit_farki, motor_f, paket_farki, vites_farki)

    adaylar = sorted(guncel, key=lambda k: (*skor(k), k.liste_fiyat))
    en_iyi = adaylar[0]
    s = skor(en_iyi)
    yf, mf, pf, _ = s
    esit = [k for k in adaylar if skor(k) == s]
    if yf == 0 and mf < 0.05 and pf == 0 and len(esit) == 1:
        return Eslesme("birebir", en_iyi, adaylar)

    sebep = []
    if mf >= BILINMEYEN_MOTOR:
        sebep.append("motor ilandan anlaşılamadı veya listede yok" if motor else "motor ilandan anlaşılamadı")
    elif yf or mf >= 0.05:
        sebep.append(f"'{motor}' motoru {son_yil} listesinde yok")
    if pf:
        sebep.append(f"'{paket}' paketi {son_yil} listesinde yok" if paket else "paket ilandan anlaşılamadı")
    if not sebep and len(esit) > 1:
        sebep.append("birden fazla uygun seçenek var")
    metin = "; ".join(sebep)
    return Eslesme(
        "en_yakin", en_iyi, adaylar,
        mesaj=metin[:1].upper() + metin[1:] + f". En yakın güncel karşılık: {en_iyi.model} {en_iyi.motor} {en_iyi.paket}.",
    )
