"""Agent akışı: oku -> çıkar -> eksik/çelişkiyi sor -> eşleştir -> hesapla -> yorumla.

Hesap tamamen src.pricing'de; burası sadece sıralama ve kullanıcıya soru sorma.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Optional, Protocol

from src.data.matcher import Eslesme, eslestir
from src.data.models import Kurallar, SifirKayit
from src.extract.fetch import LinkOkunamadi, girdiyi_metne_cevir
from src.extract.schema import IlanBilgisi
from src.pricing.engine import Parca, Sonuc, hesapla

from .parca_girdi import ParcaGirdiHatasi, parcalari_coz

KARAR_METNI = {
    "uygun": "UYGUN, ALINABİLİR",
    "pazarlik": "PAZARLIK YAP",
    "pahali": "PAHALI",
}
DURUM_METNI = {"degisen": "değişen", "boyali": "boyalı", "lokal_boyali": "lokal boyalı"}


class IO(Protocol):
    def yaz(self, metin: str) -> None: ...
    def sor(self, soru: str) -> str: ...
    def metin_iste(self, soru: str) -> str: ...


def tl(x: float) -> str:
    return f"{round(x):,} TL".replace(",", ".")


def yuzde(x: float) -> str:
    return f"%{x*100:+.1f}".replace(".", ",")


@dataclass
class Analiz:
    ilan: IlanBilgisi
    kayit: SifirKayit
    sonuc: Sonuc
    parcalar: list[Parca]
    notlar: list[str] = field(default_factory=list)
    yorum: Optional[str] = None


def _evet_mi(cevap: str) -> bool:
    return cevap.strip().lower() in ("e", "evet", "y", "yes")


def _sayi_sor(io: IO, soru: str) -> int:
    while True:
        cevap = io.sor(soru).replace(".", "").replace(",", "").replace("TL", "").replace("km", "").strip()
        if cevap.isdigit():
            return int(cevap)
        io.yaz("Lütfen sadece sayı yaz.")


def _metin_sor(io: IO, soru: str) -> str:
    while True:
        cevap = io.sor(soru).strip()
        if cevap:
            return cevap


def _parca_sor(io: IO, soru: str) -> list[Parca]:
    while True:
        cevap = io.sor(soru + "\n  Biçim: 'kaput:değişen, sol ön kapı:boyalı, arka tampon:lokal' (yoksa boş bırak)")
        try:
            return parcalari_coz(cevap)
        except ParcaGirdiHatasi as e:
            io.yaz(f"  {e}")


def _parcalar_metni(parcalar: list[Parca]) -> str:
    if not parcalar:
        return "yok"
    return ", ".join(f"{(p.konum + ' ') if p.konum else ''}{p.tip} ({DURUM_METNI[p.durum]})" for p in parcalar)


def _metni_al(girdi: str, io: IO) -> str:
    try:
        return girdiyi_metne_cevir(girdi)
    except LinkOkunamadi as e:
        io.yaz(f"İlan linki okunamadı: {e}")
        return io.metin_iste(
            "İlan sayfasındaki metni (başlık, ilan bilgileri, açıklama, boya/değişen bölümü) kopyalayıp yapıştır."
        )


def _eksikleri_tamamla(b: IlanBilgisi, io: IO) -> None:
    if not b.marka:
        b.marka = _metin_sor(io, "Marka ilandan anlaşılamadı. Marka nedir?")
    if not b.model:
        b.model = _metin_sor(io, "Model ilandan anlaşılamadı. Model nedir? (ör. Golf, 3 Serisi)")
    if not b.yil:
        b.yil = _sayi_sor(io, "Model yılı ilandan anlaşılamadı. Model yılı?")
    if b.km is None:
        b.km = _sayi_sor(io, "Kilometre ilandan anlaşılamadı. Kaç km?")
    if not b.fiyat:
        b.fiyat = _sayi_sor(io, "İlan fiyatı anlaşılamadı. Fiyat kaç TL?")


def _parcalari_netlestir(b: IlanBilgisi, io: IO, notlar: list[str]) -> list[Parca]:
    parcalar = [Parca(p.tip, p.durum, p.konum) for p in b.parcalar]
    if b.celiskiler:
        io.yaz("İlanda çelişen bilgiler var:")
        for c in b.celiskiler:
            io.yaz(f"  - {c}")
        io.yaz(f"İlandan çıkarılan parça listesi: {_parcalar_metni(parcalar)}")
        if not _evet_mi(io.sor("Bu parça listesiyle devam edilsin mi? (e/h)")):
            parcalar = _parca_sor(io, "Doğru parça listesini yaz.")
            notlar.append("Parça listesi kullanıcı tarafından düzeltildi.")
    elif not b.parca_bilgisi_var:
        parcalar = _parca_sor(io, "İlanda boya/değişen bilgisi yok. Bildiğin boyalı/değişen parça var mı?")
        if not parcalar:
            notlar.append("Boya/değişen bilgisi ilanda yok; hatasız varsayıldı. Ekspertiz yaptır.")
    if b.diger_parcalar:
        notlar.append(f"Hesaba katılmayan hasarlı parçalar: {', '.join(b.diger_parcalar)} (ekspertizde incelet).")
    return parcalar


def _agir_hasari_netlestir(b: IlanBilgisi, io: IO, notlar: list[str]) -> bool:
    if b.agir_hasar is None:
        c = io.sor("İlanda ağır hasar kaydı bilgisi yok. Ağır hasar kaydı var mı? (e/h/bilmiyorum)").strip().lower()
        if c.startswith("b"):
            notlar.append("Ağır hasar kaydı bilinmiyor; yok varsayıldı. e-Devlet/TRAMER'den sorgula.")
            return False
        b.agir_hasar = _evet_mi(c)
    if b.agir_hasar:
        tarih = io.sor("Ağır hasar kaydı var. Kaydın tarihi nedir? (bilmiyorsan boş bırak)").strip()
        yer = io.sor("Hasar aracın neresinde? (ör. ön, arka, yan, sel/yangın; bilmiyorsan boş bırak)").strip()
        notlar.append(f"Ağır hasar kaydı: tarih {tarih or 'bilinmiyor'}, yer {yer or 'bilinmiyor'}.")
    return bool(b.agir_hasar)


def _kayit_sec(e: Eslesme, b: IlanBilgisi, io: IO, notlar: list[str]) -> Optional[SifirKayit]:
    if e.tip == "birebir":
        return e.kayit
    io.yaz(e.mesaj)
    io.yaz(f"{e.kayit.model_yili} {e.kayit.marka} güncel seçenekleri:")
    adaylar = e.adaylar[:10]
    for i, k in enumerate(adaylar, 1):
        io.yaz(f"  {i}) {k.model} {k.motor} | {k.paket} | {k.yakit}, {k.vites} | {tl(k.liste_fiyat)}")
    while True:
        c = io.sor(f"Referans olarak hangisi kullanılsın? (1-{len(adaylar)}, Enter = 1, 0 = vazgeç)").strip()
        if c == "":
            secim = 1
        elif c.isdigit() and 0 <= int(c) <= len(adaylar):
            secim = int(c)
        else:
            io.yaz("Geçersiz seçim.")
            continue
        if secim == 0:
            return None
        k = adaylar[secim - 1]
        notlar.append(f"İlandaki '{b.motor or '?'} {b.paket or '?'}' yerine güncel '{k.motor} {k.paket}' referans alındı (kullanıcı onayı).")
        return k


def rapor(a: Analiz) -> str:
    b, k, s = a.ilan, a.kayit, a.sonuc
    sat = [
        "=" * 60,
        f"İLAN: {b.yil} {b.marka} {b.model} {b.motor or ''} {b.paket or ''}".rstrip(),
        f"  {b.km:,} km".replace(",", ".") + f" | İlan fiyatı: {tl(s.ilan_fiyati)}",
        f"  Parçalar: {_parcalar_metni(a.parcalar)}",
        f"  Ağır hasar: {'VAR' if b.agir_hasar else 'yok'}"
        + (" | Tramer: yok (satıcı beyanı, doğrulanmadı)" if b.tramer_tutari == 0 else
           f" | Tramer: {tl(b.tramer_tutari)}" if b.tramer_tutari else ""),
        "",
        f"REFERANS: {k.model_yili} {k.marka} {k.model} {k.motor} {k.paket} liste fiyatı {tl(k.liste_fiyat)}",
        f"  Kaynak: {k.kaynak} ({k.guncelleme_tarihi:%d.%m.%Y})"
        + (f" | Kampanyalı: {tl(k.kampanyali_fiyat)} (bilgi)" if k.kampanyali_fiyat else ""),
        "",
        "HESAP:",
        f"  {'Başlangıç (sıfır liste fiyatı)':<56} {tl(s.referans):>14}",
    ]
    for d in s.dokum:
        sat.append(f"  {d.aciklama + ' ' + yuzde(d.oran):<56} {tl(d.sonra):>14}")
    sat += [
        "",
        f"TAHMİNİ DEĞER: {tl(s.tahmin)}",
        f"İlan fiyatı tahmine göre: {yuzde(s.fark_yuzde)}",
        f"ÖNERİ: {KARAR_METNI[s.karar]}",
        f"Teklif aralığı: {tl(s.teklif_alt)} - {tl(s.teklif_ust)}",
    ]
    uyarilar = s.uyarilar + a.notlar
    if uyarilar:
        sat += ["", "UYARILAR / NOTLAR:"] + [f"  - {u}" for u in uyarilar]
    sat.append("=" * 60)
    return "\n".join(sat)


def analiz_et(
    girdi: str,
    io: IO,
    kayitlar: list[SifirKayit],
    kurallar: Kurallar,
    cikarici: Callable[[str], IlanBilgisi],
    yorumlayici: Optional[Callable[[str], Optional[str]]] = None,
    bugun: Optional[date] = None,
) -> Optional[Analiz]:
    bugun = bugun or date.today()
    metin = _metni_al(girdi, io)
    if not metin.strip():
        io.yaz("İlan metni boş, analiz yapılamadı.")
        return None

    io.yaz("İlan okunuyor...")
    b = cikarici(metin)
    _eksikleri_tamamla(b, io)
    notlar: list[str] = []

    parcalar = _parcalari_netlestir(b, io, notlar)
    agir = _agir_hasari_netlestir(b, io, notlar)
    if b.tramer_tutari == 0:
        notlar.append("'Tramer yok' satıcı beyanıdır; e-Devlet/TRAMER'den doğrula.")

    e = eslestir(kayitlar, marka=b.marka, model=b.model, motor=b.motor, paket=b.paket, yakit=b.yakit, vites=b.vites)
    if e.tip == "bulunamadi":
        io.yaz(f"VERİ YOK: {e.mesaj} Tahmin üretilmedi.")
        return None
    kayit = _kayit_sec(e, b, io, notlar)
    if kayit is None:
        io.yaz("Referans seçilmedi, analiz iptal edildi.")
        return None

    sonuc = hesapla(
        referans_fiyat=kayit.liste_fiyat,
        referans_model_yili=kayit.model_yili,
        ilan_yili=b.yil,
        km=b.km,
        marka=kayit.marka,
        parcalar=parcalar,
        agir_hasar=agir,
        ilan_fiyati=b.fiyat,
        k=kurallar,
        tramer_tutari=b.tramer_tutari,
        veri_tarihi=kayit.guncelleme_tarihi,
        bugun=bugun,
    )
    a = Analiz(b, kayit, sonuc, parcalar, notlar)
    metin_rapor = rapor(a)
    io.yaz(metin_rapor)
    if yorumlayici:
        a.yorum = yorumlayici(metin_rapor)
        if a.yorum:
            io.yaz("\nYORUM:\n" + a.yorum)
    return a
