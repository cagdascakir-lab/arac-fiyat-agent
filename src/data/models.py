"""Veri şemaları: sıfır fiyat kaydı ve düşüş kuralları."""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

ParcaTipi = Literal["tavan", "kaput", "bagaj", "kapi", "camurluk", "tampon"]
ParcaDurumu = Literal["degisen", "boyali", "lokal_boyali"]


class SifirKayit(BaseModel):
    marka: str
    model: str
    model_yili: int = Field(ge=2000, le=2100)
    motor: str                      # ör. "1.5 eTSI 150 PS"
    motor_hacmi: Optional[float] = Field(default=None, ge=0)  # litre; elektrikli 0; kaynak vermiyorsa None
    yakit: str                      # benzin, dizel, hibrit, elektrik
    vites: str                      # manuel, otomatik
    paket: str                      # ör. "Style"
    liste_fiyat: int = Field(gt=0)  # TL
    kampanyali_fiyat: Optional[int] = Field(default=None, gt=0)
    kaynak: str
    guncelleme_tarihi: date

    @field_validator("marka", "model", "motor", "paket", "kaynak")
    @classmethod
    def bos_olmasin(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("boş olamaz")
        return v.strip()


class SifirVeri(BaseModel):
    kayitlar: list[SifirKayit]


class YasKurali(BaseModel):
    ilk_yil: float = Field(ge=0, lt=1)
    yil_2_10: float = Field(ge=0, lt=1)
    yil_11_ve_sonrasi: float = Field(ge=0, lt=1)
    marka_yas_carpani: dict[str, float] = {}


class KmKurali(BaseModel):
    yillik_normal_km: int = Field(gt=0)
    her_10000_km_orani: float = Field(ge=0, lt=1)
    maksimum_etki: float = Field(ge=0, lt=1)


class ParcaOranlari(BaseModel):
    degisen: float = Field(ge=0, lt=1)
    boyali: float = Field(ge=0, lt=1)
    lokal_boyali: float = Field(ge=0, lt=1)


class KararKurali(BaseModel):
    uygun_ust_sinir: float
    pazarlik_ust_sinir: float
    supheli_ucuz_alt_sinir: float


class TeklifKurali(BaseModel):
    alt: float = Field(gt=0, le=1)
    ust: float = Field(gt=0, le=1.5)


class Kurallar(BaseModel):
    kalibrasyon_tarihi: date
    yas: YasKurali
    km: KmKurali
    parca: dict[ParcaTipi, ParcaOranlari]
    parca_toplam_tavan: float = Field(ge=0, lt=1)
    agir_hasar: float = Field(ge=0, lt=1)
    tramer_uyari_orani: float = Field(ge=0)
    karar: KararKurali
    teklif: TeklifKurali
    veri_eskime_gun: int = Field(gt=0)
