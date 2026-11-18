"""Kullanıcının elle yazdığı parça listesini çözer.

Biçim: virgülle ayrılmış "parça:durum" çiftleri.
Örnek: "kaput:değişen, sol ön kapı:boyalı, arka tampon:lokal"
"""
from __future__ import annotations

from src.data.matcher import norm
from src.pricing.engine import Parca

_TIP = [
    ("tavan", "tavan"),
    ("kaput", "kaput"),
    ("motorkaput", "kaput"),
    ("bagaj", "bagaj"),
    ("kapi", "kapi"),
    ("camurluk", "camurluk"),
    ("tampon", "tampon"),
]
_DURUM = [("lokal", "lokal_boyali"), ("degis", "degisen"), ("boya", "boyali")]


class ParcaGirdiHatasi(ValueError):
    pass


def parcalari_coz(metin: str) -> list[Parca]:
    sonuc: list[Parca] = []
    for parca in filter(None, (p.strip() for p in metin.split(","))):
        if ":" not in parca:
            raise ParcaGirdiHatasi(f"'{parca}': 'parça:durum' biçiminde yaz.")
        ad, durum = (s.strip() for s in parca.split(":", 1))
        n_ad, n_durum = norm(ad), norm(durum)
        tip = next((t for anahtar, t in _TIP if anahtar in n_ad), None)
        d = next((v for anahtar, v in _DURUM if anahtar in n_durum), None)
        if tip is None:
            raise ParcaGirdiHatasi(f"'{ad}' tanınmadı (tavan, kaput, bagaj, kapı, çamurluk, tampon).")
        if d is None:
            raise ParcaGirdiHatasi(f"'{durum}' tanınmadı (değişen, boyalı, lokal).")
        konum = ad.lower()
        for kelime in ("motor", "kaputu", "kaput", "kapağı", "kapagi", "kapı", "kapi", "çamurluk", "camurluk", "tampon", "tavan", "bagaj"):
            konum = konum.replace(kelime, "")
        sonuc.append(Parca(tip, d, " ".join(konum.split())))
    return sonuc
