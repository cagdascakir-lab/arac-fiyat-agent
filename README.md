# Araç Fiyat Agent'ı

sahibinden.com / arabam.com ikinci el araç ilanını okuyup aracın **en güncel sıfır fiyatından** yaş, km, boya/değişen ve ağır hasar düşüşlerini uygulayan, sonra **"uygun, alınabilir / pazarlık yap / pahalı"** önerisi ve teklif aralığı veren bir agent. Sadece Türkiye pazarı.

## Mimari

```
ilan (link / kaydedilmiş sayfa / yapıştırılan metin)
  │
  ├─ extract/fetch.py   tek linki okur; telefonları siler; engellenirse metin ister
  ├─ extract/llm.py     Claude, metni yapılandırılmış alanlara çevirir (JSON şeması)
  ├─ agent/flow.py      eksik/çelişkili bilgiyi, ağır hasarı ve paket seçimini KULLANICIYA sorar
  ├─ data/matcher.py    ilandaki motor/paketi en güncel sıfır kaydına eşler
  ├─ pricing/engine.py  saf Python hesap (LLM yok) + karar + teklif aralığı
  └─ extract/llm.py     Claude, hesaplanmış sonucu kısa Türkçe yorumlar (rakam üretmez)
```

- **Hesabı kod yapar.** LLM sadece okur ve yorumlar; fiyat yalnızca `data/zero_km.json`'dan gelir.
- **Uydurma yok.** Veri tabanında olmayan model için "VERİ YOK" der. Eski motor/paket için en yakın güncel seçenekleri listeler ve kullanıcıya seçtirir.
- Her raporda referans fiyatın kaynağı, tarihi ve uygulanan her düşüş tek tek gösterilir.

## Kurulum

```bash
python -m venv .venv
```

```bash
.venv\Scripts\python -m pip install -r requirements.txt
```

Anthropic API anahtarı gerekir (`ANTHROPIC_API_KEY` ortam değişkeni). Model: `claude-opus-5-5` (red durumunda sunucu taraflı yedek model açık).

## Kullanım

```bash
.venv\Scripts\python -m src.agent.cli "https://www.arabam.com/ilan/..."
```

Sitelerin otomatik erişimi engellemesi durumunda üç yol var:
1. Agent metni ister: ilan sayfasındaki yazıyı kopyala, yapıştır, sonra `BITTI` yaz.
2. Sayfayı tarayıcıda **Ctrl+S** ile kaydet ve dosya yolunu ver: `python -m src.agent.cli ilan.html`
3. Argümansız çalıştırıp metni doğrudan yapıştır.

## Testler

```bash
.venv\Scripts\python -m pytest
```

Hesap motoru, eşleştirme, link/metin girişi, gerçek veriyle eşleştirme ve uçtan uca 9 akış senaryosu (hatasız, boyalı/değişen, ağır hasar, eski paket, çelişki, veri yok, eksik alan, link okunamadı) test edilir. LLM ve ağ testlerde sahtedir.

## Veri

- `data/zero_km.json`: 6 marka (BMW, Mercedes-Benz, Volkswagen, Porsche, Opel, Fiat), 16 model, 67 motor/paket kaydı; Kasım 2026 tavsiye edilen anahtar teslim liste fiyatları. Kaynak ve tarih her kayıtta.
- `data/rules.json`: düşüş oranları ve karar eşikleri (bkz. CLAUDE.md). `kalibrasyon_tarihi` 6 aydan eskiyse uyarı verilir.

## Sınırlılıklar

- **Oranlar kalibre edilmedi.** Yaş/km/hasar oranları zayıf kaynaklardan alınmış başlangıç değerleri; gerçek ilanlarla sapma ölçülüp güncellenecek (PLAN.md Adım 7).
- **Link okuma çoğu zaman engelleniyor.** sahibinden.com ve arabam.com düz HTTP isteğine Cloudflare 403 dönüyor (Kasım 2026'da test edildi). Engel aşma, bot veya proxy kullanılmıyor. Pratikte metin yapıştırma veya kaydedilmiş sayfa ana yol.
- Sıfır fiyatlar haber/fiyat sitelerinden derlendi, resmî listeyle teyit edilmeli. Kaynakta tutarsız görünen Mercedes C 400 4MATIC kaydı (C 200'den ucuz görünüyordu) dışarıda bırakıldı.
- Satılmayan eski motorlar (ör. Golf 1.6 TDI) güncel benzinli karşılıkla kıyaslanır; bu, yakıt tipi farkı kadar hata payı taşır.
- Renk, şehir, opsiyonlar ve tramer tutarı hesaba girmez (tramer yalnızca uyarı).
- Sadece tavsiye verir; satıcıyla iletişim, ödeme veya randevu yok.
