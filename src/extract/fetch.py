"""İlan girdisini düz metne çevirir: tek link, kaydedilmiş HTML dosyası veya yapıştırılmış metin.

Toplu çekim, bot, proxy veya engel aşma yok. Link okunamazsa (ör. Cloudflare 403)
LinkOkunamadi fırlatılır ve agent kullanıcıdan metni yapıştırmasını ister.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

IZINLI_ALANLAR = ("sahibinden.com", "arabam.com")
_UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
}
_TELEFON = re.compile(r"(\+?90[\s-]?)?\(?0?5\d{2}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}")
MAKS_KARAKTER = 30_000


class LinkOkunamadi(Exception):
    pass


def link_mi(girdi: str) -> bool:
    return girdi.strip().lower().startswith(("http://", "https://"))


def izinli_mi(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == a or host.endswith("." + a) for a in IZINLI_ALANLAR)


def kisisel_veriyi_temizle(metin: str) -> str:
    """Telefon numaralarını çıkarır (satıcının kişisel verisi saklanmaz/gönderilmez)."""
    return _TELEFON.sub("[telefon silindi]", metin)


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
        t.decompose()
    metin = soup.get_text("\n")
    metin = re.sub(r"\n\s*\n+", "\n", metin)
    return kisisel_veriyi_temizle(metin.strip())[:MAKS_KARAKTER]


def linki_oku(url: str, timeout: float = 20) -> str:
    if not izinli_mi(url):
        raise LinkOkunamadi("Sadece sahibinden.com ve arabam.com linkleri destekleniyor.")
    try:
        r = httpx.get(url, headers=_UA, follow_redirects=True, timeout=timeout)
    except httpx.HTTPError as e:
        raise LinkOkunamadi(f"Bağlantı hatası: {e}") from e
    if r.status_code != 200 or "Just a moment" in r.text or "cf-chl" in r.text:
        raise LinkOkunamadi(f"Site otomatik erişimi engelledi (HTTP {r.status_code}).")
    metin = html_to_text(r.text)
    if len(metin) < 200:
        raise LinkOkunamadi("Sayfa içeriği okunamadı.")
    return metin


def girdiyi_metne_cevir(girdi: str) -> str:
    """URL -> sayfayı oku; .html/.htm/.txt dosya yolu -> dosyayı oku; aksi halde yapıştırılmış metin."""
    g = girdi.strip()
    if link_mi(g):
        return linki_oku(g)
    yol = Path(g.strip('"'))
    if len(g) < 500 and yol.suffix.lower() in (".html", ".htm", ".txt") and yol.is_file():
        icerik = yol.read_text(encoding="utf-8", errors="ignore")
        return html_to_text(icerik) if yol.suffix.lower() != ".txt" else kisisel_veriyi_temizle(icerik)[:MAKS_KARAKTER]
    return kisisel_veriyi_temizle(g)[:MAKS_KARAKTER]
