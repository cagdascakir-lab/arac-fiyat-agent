from datetime import date

from src.data.matcher import eslestir, hacim_bul, marka_norm
from src.data.models import SifirKayit


def k(model, yil, motor, hacim, yakit, paket, fiyat, marka="Volkswagen"):
    return SifirKayit(marka=marka, model=model, model_yili=yil, motor=motor, motor_hacmi=hacim,
                      yakit=yakit, vites="otomatik", paket=paket, liste_fiyat=fiyat,
                      kaynak="test", guncelleme_tarihi=date(2026, 11, 1))


VERI = [
    k("Golf", 2025, "1.5 eTSI", 1.5, "Benzin", "Style", 1_900_000),
    k("Golf", 2026, "1.5 eTSI 116 PS", 1.5, "Benzin", "Life", 1_800_000),
    k("Golf", 2026, "1.5 eTSI 150 PS", 1.5, "Benzin", "Style", 2_000_000),
    k("Golf", 2026, "2.0 TDI", 2.0, "Dizel", "Style", 2_200_000),
    k("Passat", 2026, "1.5 eTSI", 1.5, "Benzin", "Business", 3_000_000),
]


def test_yardimcilar():
    assert hacim_bul("1,6 TDI") == 1.6
    assert hacim_bul("eTSI") is None
    assert marka_norm("VW") == marka_norm("Volkswagen")
    assert marka_norm("Mercedes") == marka_norm("Mercedes-Benz")


def test_birebir_en_guncel_yil():
    e = eslestir(VERI, marka="VW", model="Golf", motor="1.5 eTSI", paket="Style", yakit="Benzin")
    assert e.tip == "birebir"
    assert e.kayit.model_yili == 2026 and e.kayit.liste_fiyat == 2_000_000


def test_eski_motor_en_yakin():
    # 2020 Golf 1.6 TDI Comfortline -> 2.0 TDI (aynı yakıt, en yakın hacim)
    e = eslestir(VERI, marka="Volkswagen", model="Golf", motor="1.6 TDI", paket="Comfortline", yakit="Dizel")
    assert e.tip == "en_yakin"
    assert e.kayit.motor == "2.0 TDI"
    assert "1.6 TDI" in e.mesaj and "Comfortline" in e.mesaj


def test_motor_bilinmiyor_en_yakin():
    e = eslestir(VERI, marka="Volkswagen", model="Golf", motor=None, paket="Style", yakit=None)
    assert e.tip == "en_yakin"
    assert len(e.adaylar) == 3


def test_bulunamadi():
    e = eslestir(VERI, marka="Fiat", model="Egea", motor="1.4", paket="Easy")
    assert e.tip == "bulunamadi" and e.kayit is None
