import pytest

from src.extract.fetch import LinkOkunamadi, girdiyi_metne_cevir, html_to_text, izinli_mi, kisisel_veriyi_temizle, linki_oku


def test_izinli_alanlar():
    assert izinli_mi("https://www.sahibinden.com/ilan/vasita-otomobil-1")
    assert izinli_mi("https://arabam.com/ilan/x")
    assert not izinli_mi("https://ornek.com/ilan")
    assert not izinli_mi("https://sahibinden.com.kotu.net/ilan")


def test_izinsiz_link_reddedilir():
    with pytest.raises(LinkOkunamadi):
        linki_oku("https://ornek.com/ilan")


def test_telefon_silinir():
    t = kisisel_veriyi_temizle("Ara: 0532 123 45 67 veya +90 555-111-22-33")
    assert "532" not in t and "555" not in t


def test_html_to_text_script_atilir():
    t = html_to_text("<html><script>var x=1</script><h1>Golf 1.6 TDI</h1><p>Fiyat 1.250.000 TL</p></html>")
    assert "Golf 1.6 TDI" in t and "var x" not in t


def test_yapistirilan_metin_aynen_doner(tmp_path):
    assert girdiyi_metne_cevir("2020 Golf, 90.000 km") == "2020 Golf, 90.000 km"
    f = tmp_path / "ilan.html"
    f.write_text("<p>Kaput boyalı</p>", encoding="utf-8")
    assert girdiyi_metne_cevir(str(f)) == "Kaput boyalı"
