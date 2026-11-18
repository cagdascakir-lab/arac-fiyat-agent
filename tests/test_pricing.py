from datetime import date

import pytest

from src.data.loader import kurallari_yukle
from src.pricing.engine import Parca, hesapla, karar_ver, km_carpani, parca_dususu, yas_carpani

K = kurallari_yukle()


def test_yas_carpani_golf_ornegi():
    # CLAUDE.md örneği: 2.000.000 × 0,88 × 0,94^5 ≈ 1.291.700
    assert 2_000_000 * yas_carpani(6, K) == pytest.approx(2_000_000 * 0.88 * 0.94**5)
    assert round(2_000_000 * yas_carpani(6, K), -2) == 1_291_700


def test_yas_sifir_ve_on_bir():
    assert yas_carpani(0, K) == 1.0
    assert yas_carpani(-1, K) == 1.0
    assert yas_carpani(11, K) == pytest.approx(0.88 * 0.94**9 * 0.96)


def test_km_normal_fazla_eksik_ve_tavan():
    assert km_carpani(90_000, 6, K) == pytest.approx(1.0)
    assert km_carpani(110_000, 6, K) == pytest.approx(0.98)
    assert km_carpani(70_000, 6, K) == pytest.approx(1.02)
    assert km_carpani(500_000, 6, K) == pytest.approx(0.90)
    assert km_carpani(0, 20, K) == pytest.approx(1.10)


def test_parca_dususu_toplam_ve_tavan():
    assert parca_dususu([Parca("kaput", "degisen"), Parca("tampon", "boyali")], K) == pytest.approx(0.045)
    cok = [Parca("tavan", "degisen")] * 3
    assert parca_dususu(cok, K) == pytest.approx(0.35)
    assert parca_dususu([], K) == 0


def test_karar_esikleri():
    assert karar_ver(-0.10, K) == "uygun"
    assert karar_ver(0.05, K) == "uygun"
    assert karar_ver(0.10, K) == "pazarlik"
    assert karar_ver(0.15, K) == "pazarlik"
    assert karar_ver(0.16, K) == "pahali"


def _hesap(**ek):
    v = dict(
        referans_fiyat=2_000_000, referans_model_yili=2026, ilan_yili=2020, km=90_000,
        marka="Volkswagen", parcalar=[], agir_hasar=False, ilan_fiyati=1_300_000, k=K,
    )
    v.update(ek)
    return hesapla(**v)


def test_hesapla_hatasiz():
    s = _hesap()
    assert s.tahmin == pytest.approx(2_000_000 * 0.88 * 0.94**5)
    assert s.karar == "uygun"
    assert s.teklif_alt == pytest.approx(s.tahmin * 0.95)
    assert len(s.dokum) == 2


def test_hesapla_hasarli_ve_pahali():
    s = _hesap(parcalar=[Parca("kaput", "degisen")], agir_hasar=True, ilan_fiyati=1_300_000)
    beklenen = 2_000_000 * 0.88 * 0.94**5 * 0.96 * 0.70
    assert s.tahmin == pytest.approx(beklenen)
    assert s.karar == "pahali"
    assert any("Ağır hasar" in u for u in s.uyarilar)


def test_supheli_ucuz_ve_tramer_ve_eski_veri_uyarisi():
    s = _hesap(ilan_fiyati=900_000, tramer_tutari=200_000,
               veri_tarihi=date(2026, 1, 1), bugun=date(2026, 11, 16))
    metin = " ".join(s.uyarilar)
    assert "şüpheli" in metin and "Tramer" in metin and "gün önce" in metin


def test_teklif_ilan_fiyatini_asmaz():
    s = _hesap(ilan_fiyati=1_000_000)
    assert s.teklif_ust == 1_000_000 and s.teklif_alt == 1_000_000
    s = _hesap(ilan_fiyati=1_250_000)  # tahmin ~1.291.700 -> alt %95 = ~1.227.100
    assert s.teklif_alt == pytest.approx(s.tahmin * 0.95) and s.teklif_ust == 1_250_000


def test_gecersiz_girdi():
    with pytest.raises(ValueError):
        _hesap(ilan_fiyati=0)
    with pytest.raises(ValueError):
        _hesap(km=-5)


def test_ilan_yili_referanstan_yeni():
    s = _hesap(ilan_yili=2027, km=0)
    assert s.dokum[0].oran == 0
