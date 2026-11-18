"""JSON veri dosyalarını yükler ve şemaya göre doğrular."""
from __future__ import annotations

import json
from pathlib import Path

from .models import Kurallar, SifirKayit, SifirVeri

VERI_KLASORU = Path(__file__).resolve().parents[2] / "data"


def sifir_fiyatlari_yukle(yol: Path | None = None) -> list[SifirKayit]:
    yol = yol or VERI_KLASORU / "zero_km.json"
    with open(yol, encoding="utf-8") as f:
        return SifirVeri.model_validate(json.load(f)).kayitlar


def kurallari_yukle(yol: Path | None = None) -> Kurallar:
    yol = yol or VERI_KLASORU / "rules.json"
    with open(yol, encoding="utf-8") as f:
        return Kurallar.model_validate(json.load(f))
