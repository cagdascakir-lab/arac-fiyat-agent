"""Komut satırı arayüzü.

Kullanım:
    python -m src.agent.cli "https://www.arabam.com/ilan/..."
    python -m src.agent.cli ilan.html
    python -m src.agent.cli            # sonra linki veya metni yapıştır
"""
from __future__ import annotations

import sys

from src.data.loader import kurallari_yukle, sifir_fiyatlari_yukle
from src.extract.llm import LLMHatasi, ilani_cikar, sonucu_yorumla

from .flow import analiz_et


class KonsolIO:
    def yaz(self, metin: str) -> None:
        print(metin)

    def sor(self, soru: str) -> str:
        return input(f"\n{soru}\n> ")

    def metin_iste(self, soru: str) -> str:
        print(f"\n{soru}\n(Bitirmek için boş satırda 'BITTI' yaz.)")
        satirlar = []
        while True:
            try:
                s = input()
            except EOFError:
                break
            if s.strip().upper() == "BITTI":
                break
            satirlar.append(s)
        return "\n".join(satirlar)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    io = KonsolIO()
    girdi = " ".join(sys.argv[1:]).strip()
    if not girdi:
        girdi = io.metin_iste("sahibinden.com / arabam.com ilan linkini, kaydedilmiş sayfa yolunu veya ilan metnini yapıştır.")
    try:
        analiz_et(girdi, io, sifir_fiyatlari_yukle(), kurallari_yukle(), ilani_cikar, sonucu_yorumla)
    except LLMHatasi as e:
        print(f"Hata: {e}")
        return 1
    except KeyboardInterrupt:
        print("\nİptal edildi.")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
