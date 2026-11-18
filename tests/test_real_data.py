"""Gerçek data/zero_km.json ile eşleştirme kontrolleri."""
from src.data.loader import sifir_fiyatlari_yukle
from src.data.matcher import eslestir

D = sifir_fiyatlari_yukle()


def test_alti_marka_var():
    assert {k.marka for k in D} == {"BMW", "Mercedes-Benz", "Volkswagen", "Porsche", "Opel", "Fiat"}


def test_bmw_motor_adla_birebir():
    e = eslestir(D, marka="BMW", model="3 Serisi", motor="320i", paket="M Sport", yakit="Benzin", vites="Otomatik")
    assert e.tip == "birebir" and e.kayit.liste_fiyat == 6_378_000


def test_mercedes_seri_yazimi():
    e = eslestir(D, marka="Mercedes", model="C Serisi", motor="C 200 4MATIC", paket="AMG", yakit="Benzin")
    assert e.tip == "birebir"


def test_cayenne_electric_karismaz():
    e = eslestir(D, marka="Porsche", model="Cayenne", motor="GTS", paket="Standart", yakit="Benzin")
    assert e.tip == "birebir" and e.kayit.model == "Cayenne"


def test_egea_alt_modelleri_aday():
    e = eslestir(D, marka="Fiat", model="Egea", motor="1.6 Multijet", paket="Urban", yakit="Dizel", vites="Manuel")
    assert e.kayit.model == "Egea Sedan" and e.kayit.vites == "manuel"


def test_golf_ayni_paket_iki_motor_sorulur():
    # 1.5 eTSI Style hem 116 hem 150 PS ile satılıyor -> kullanıcı seçmeli
    e = eslestir(D, marka="Volkswagen", model="Golf", motor="1.5 eTSI", paket="Style", yakit="Benzin")
    assert e.tip == "en_yakin" and "birden fazla" in e.mesaj.lower()
