"""Uçtan uca akış senaryoları (LLM ve ağ sahte)."""
from datetime import date

import pytest

from src.agent.flow import analiz_et
from src.agent.parca_girdi import ParcaGirdiHatasi, parcalari_coz
from src.data.loader import kurallari_yukle
from src.extract.schema import IlanBilgisi, ParcaCikti
from tests.test_matcher import VERI

K = kurallari_yukle()
BUGUN = date(2026, 11, 16)


class SahteIO:
    def __init__(self, cevaplar):
        self.cevaplar = list(cevaplar)
        self.cikti = []
        self.sorular = []

    def yaz(self, m):
        self.cikti.append(m)

    def sor(self, s):
        self.sorular.append(s)
        return self.cevaplar.pop(0)

    def metin_iste(self, s):
        self.sorular.append(s)
        return self.cevaplar.pop(0)

    @property
    def metin(self):
        return "\n".join(self.cikti)


def ilan(**ek):
    v = dict(marka="Volkswagen", model="Golf", motor="1.5 eTSI", paket="Style", yil=2020, km=90_000,
             yakit="Benzin", vites="Otomatik", fiyat=1_300_000, parcalar=[], diger_parcalar=[],
             parca_bilgisi_var=True, agir_hasar=False, tramer_tutari=None, satici_tipi="sahibinden",
             belirsiz_alanlar=[], celiskiler=[])
    v.update(ek)
    return IlanBilgisi(**v)


def calistir(b, cevaplar=(), girdi="yapıştırılmış ilan metni"):
    io = SahteIO(cevaplar)
    a = analiz_et(girdi, io, VERI, K, cikarici=lambda _: b, yorumlayici=lambda _: "yorum", bugun=BUGUN)
    return a, io


def test_hatasiz_birebir_uygun():
    a, io = calistir(ilan())
    assert a.sonuc.karar == "uygun"
    assert io.sorular == []
    assert "UYGUN" in io.metin and "Kaynak: test" in io.metin


def test_boyali_degisen_pazarlik():
    b = ilan(parcalar=[ParcaCikti(tip="kaput", durum="degisen", konum=""),
                       ParcaCikti(tip="kapi", durum="boyali", konum="sol ön")], fiyat=1_350_000)
    a, io = calistir(b)
    assert a.sonuc.tahmin == pytest.approx(2_000_000 * 0.88 * 0.94**5 * (1 - 0.05))
    assert a.sonuc.karar == "pazarlik"


def test_agir_hasar_soru_sorar():
    a, io = calistir(ilan(agir_hasar=True, fiyat=1_000_000), cevaplar=["2023", "ön"])
    assert len(io.sorular) == 2
    assert any("tarih 2023, yer ön" in n for n in a.notlar)
    assert "yüksek belirsizlik" in io.metin


def test_eski_paket_kullanici_secer():
    b = ilan(motor="1.6 TDI", paket="Comfortline", yakit="Dizel")
    a, io = calistir(b, cevaplar=[""])
    assert a.kayit.motor == "2.0 TDI"
    assert any("kullanıcı onayı" in n for n in a.notlar)


def test_eski_paket_vazgec():
    a, io = calistir(ilan(motor="1.6 TDI", paket="Comfortline", yakit="Dizel"), cevaplar=["0"])
    assert a is None


def test_celiski_duzeltme():
    b = ilan(celiskiler=["Başlık 'hatasız' ama açıklamada 'kaput boyalı'"])
    a, io = calistir(b, cevaplar=["h", "kaput:boyalı"])
    assert [(p.tip, p.durum) for p in a.parcalar] == [("kaput", "boyali")]


def test_veri_yok():
    a, io = calistir(ilan(marka="Fiat", model="Egea"))
    assert a is None and "VERİ YOK" in io.metin


def test_eksik_alan_sorulur_ve_tramer_beyan():
    b = ilan(km=None, fiyat=None, tramer_tutari=0)
    a, io = calistir(b, cevaplar=["90.000", "1.300.000 TL"])
    assert a.ilan.km == 90_000 and a.ilan.fiyat == 1_300_000
    assert "beyan" in io.metin


def test_link_okunamazsa_metin_istenir():
    b = ilan()
    a, io = calistir(b, cevaplar=["yapıştırılan metin"], girdi="https://ornek.com/ilan/1")
    assert "okunamadı" in io.metin and a is not None


def test_parca_girdi_cozumu():
    p = parcalari_coz("kaput:değişen, sol ön kapı:boyalı, arka tampon:lokal")
    assert [(x.tip, x.durum, x.konum) for x in p] == [
        ("kaput", "degisen", ""), ("kapi", "boyali", "sol ön"), ("tampon", "lokal_boyali", "arka")]
    assert parcalari_coz("") == []
    with pytest.raises(ParcaGirdiHatasi):
        parcalari_coz("ayna:boyalı")
