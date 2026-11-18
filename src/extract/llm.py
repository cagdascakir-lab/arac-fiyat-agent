"""Claude ile ilan metninden alan çıkarımı ve sonuç yorumu.

LLM hesap yapmaz: sadece metni okur ve hesaplanmış sonucu Türkçe yorumlar.
"""
from __future__ import annotations

import anthropic

from .schema import IlanBilgisi

MODEL = "claude-opus-5-5"
_FALLBACK = dict(betas=["server-side-fallback-2026-07-01"], fallbacks="default")

CIKARIM_SISTEM = """Türkiye'deki ikinci el araç ilanlarından bilgi çıkaran bir asistansın.
Kurallar:
- Sadece ilan metninde yazanı çıkar. Tahmin etme, hafızandan bilgi ekleme. Metinde yoksa null bırak ve alan adını belirsiz_alanlar'a ekle.
- Fiyat ve km'yi tam sayı TL / km olarak yaz (ör. "1.250.000 TL" -> 1250000).
- Boya/değişen parçaları ekspertiz bölümünden ve açıklamadan topla. Her parça ayrı satır. "Orijinal" parçaları yazma.
  Parça tipleri: tavan, kaput, bagaj (bagaj kapağı), kapi, camurluk, tampon. Bunların dışındaki parçaları diger_parcalar'a yaz.
  Lokal boya -> lokal_boyali, boyalı -> boyali, değişen -> degisen.
- "Hatasız", "boyasız" gibi ifade varsa parca_bilgisi_var = true ve parcalar boş.
- Başlık ile açıklama veya ekspertiz tablosu birbirini tutmuyorsa (ör. başlık "hatasız", açıklama "kaput boyalı") celiskiler'e yaz.
- Satıcının adı ve telefonu gibi kişisel bilgileri hiçbir alana yazma."""

YORUM_SISTEM = """İkinci el araç alıcısına kısa tavsiye yazan bir asistansın.
Sana kod tarafından hesaplanmış sonuç verilecek. Rakamları değiştirme, yeni rakam üretme, kendi fiyat bilgini ekleme.
3-5 cümlelik, sade Türkçe bir yorum yaz: kararı söyle, en çok etkileyen düşüşü belirt, pazarlıkta neye dikkat edileceğini ve varsa uyarıları vurgula.
Bunun yalnızca tavsiye olduğunu, ekspertiz yaptırmanın önemli olduğunu bir kez hatırlat."""


class LLMHatasi(Exception):
    pass


def _istemci() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def ilani_cikar(metin: str, istemci: anthropic.Anthropic | None = None) -> IlanBilgisi:
    istemci = istemci or _istemci()
    try:
        yanit = istemci.beta.messages.parse(
            model=MODEL,
            max_tokens=16000,
            system=CIKARIM_SISTEM,
            messages=[{"role": "user", "content": f"<ilan>\n{metin}\n</ilan>"}],
            output_format=IlanBilgisi,
            **_FALLBACK,
        )
    except anthropic.AuthenticationError as e:
        raise LLMHatasi("Anthropic API anahtarı geçersiz veya tanımlı değil (ANTHROPIC_API_KEY).") from e
    except anthropic.RateLimitError as e:
        raise LLMHatasi("API istek sınırına takıldı, biraz sonra tekrar dene.") from e
    except anthropic.APIConnectionError as e:
        raise LLMHatasi("Anthropic API'ye bağlanılamadı.") from e
    except anthropic.APIStatusError as e:
        raise LLMHatasi(f"API hatası ({e.status_code}).") from e
    if yanit.stop_reason == "refusal" or yanit.parsed_output is None:
        raise LLMHatasi("Model ilanı işleyemedi.")
    return yanit.parsed_output


def sonucu_yorumla(ozet: str, istemci: anthropic.Anthropic | None = None) -> str | None:
    """Yorum isteğe bağlıdır; hata olursa None döner, hesap sonucu yine gösterilir."""
    istemci = istemci or _istemci()
    try:
        yanit = istemci.beta.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=YORUM_SISTEM,
            messages=[{"role": "user", "content": ozet}],
            output_config={"effort": "low"},
            **_FALLBACK,
        )
    except anthropic.APIError:
        return None
    if yanit.stop_reason == "refusal":
        return None
    return "".join(b.text for b in yanit.content if b.type == "text").strip() or None
