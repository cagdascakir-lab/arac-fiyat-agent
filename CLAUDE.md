# Araç Fiyat Agent'ı

Kullanıcı sahibinden.com veya arabam.com'dan bir ikinci el araç ilan linki verir. Agent ilanı okur (fiyat, marka, model, motor, paket, yıl, km, ağır hasar kaydı, değişen/boyalı parçalar), aracın **en güncel model yılı sıfır fiyatından** başlayarak yaş, km ve hasar düşüşlerini uygular, tahmini değeri ilan fiyatıyla karşılaştırır ve **"uygun, alınabilir / pazarlık yap / pahalı"** önerisi ile teklif aralığı verir. Sadece Türkiye pazarı. Kişisel proje, LinkedIn'de paylaşılacak.

## Temel kurallar
- **Hesabı kod yapar, LLM yapmaz.** Tüm düşüşler deterministik Python fonksiyonlarında. LLM sadece ilanı okur, alanları çıkarır, belirsizlikte soru sorar ve sonucu yorumlar.
- **Veri ayrı dosyada.** Sıfır fiyatlar (`data/zero_km.json`) ve düşüş kuralları (`data/rules.json`) `data/` altında. Prompt'a gömme, LLM'in kendi hafızasından fiyat verme; fiyat yalnızca agent'ın veri tabanından gelir.
- **Uydurma yok.** Veri tabanında olmayan marka/model/paket için tahmin üretme; kullanıcıya sor veya "veri yok" de. Her sonuçta hangi sıfır fiyatı ve hangi düşüşlerin uygulandığını tek tek göster.
- **Küçük adım, her adımı test et.** Bir özelliği bitirmeden diğerine geçme. Minimal değişiklik yap, gereksiz refactor yapma.
- **Agent sadece tavsiye verir.** Satıcıyla yazışma, ödeme, randevu yok.

## Veri ve hukuk
- İlan okuma: agent kullanıcının verdiği **tek linke** kendisi gider ve okur. Toplu çekim, tarama, bot/proxy yok.
- Sahibinden otomatik erişimi Cloudflare ile engelleyebilir. Okuma başarısız olursa kullanıcıdan ilan metnini yapıştırmasını iste (yedek giriş her zaman çalışmalı).
- Kasım 2026 testi: sahibinden.com ve arabam.com düz HTTP isteğine 403 (Cloudflare) dönüyor. Engeli aşmaya çalışma (headless tarayıcı, proxy, captcha çözücü yok). Desteklenen girişler: link, yapıştırılan metin, tarayıcıda kaydedilmiş .html dosyası.
- Satıcının kişisel verisini (telefon, isim) saklama, loglama.
- Sıfır fiyat kaynağı: marka resmî fiyat listeleri, araclo.com ve arabam.com sıfır km sayfaları. Her kayıtta `kaynak` ve `guncelleme_tarihi` tutulur; 60 günden eskiyse sonuçta uyarı ver.

## Fiyat modeli (sıfır fiyattan düşüş)
```
referans   = sıfır_fiyat(marka, model, motor, paket, EN GÜNCEL model yılı)   # liste fiyatı
tahmin     = referans
             × yaş_çarpanı(yaş)
             × km_çarpanı(km, yaş)
             × (1 - değişen/boya düşüşü)        # parça bazlı, toplam tavanlı
             × (1 - ağır_hasar_düşüşü)          # varsa
fark_yüzde = (ilan_fiyatı - tahmin) / tahmin
```
- **Tüm düşüşler yüzdedir, sabit TL değil.** Sabit TL (ör. yılda 100 bin) ucuz araçta fiyatı sıfıra indirir, pahalı araçta etkisiz kalır; yüzde her fiyat seviyesine ölçeklenir.
- **Referans her zaman en güncel model yılının sıfır fiyatıdır.** İlandaki aracın motoru/paketi artık satılmıyorsa en yakın güncel karşılığı (aynı model, en yakın motor hacmi ve donanım seviyesi) kullan ve bunu kullanıcıya açıkça söyle/onaylat.
- Liste fiyatı referanstır; kampanyalı fiyat varsa yalnızca bilgi olarak gösterilir.
- Renk ve şehir ilk sürümde modele girmez.

### Başlangıç düşüş oranları (`data/rules.json`, kalibre edilecek)
Kaynaklar zayıf ve birbirinden farklı (aşağıya bak); bu değerler başlangıç noktasıdır, gerçek ilanlarla ölçülüp güncellenecek. Dosyada `kalibrasyon_tarihi` tutulur.

**Yaş (azalan bakiye, her yıl bir önceki değerin yüzdesi):**
| Yaş | Yıllık düşüş |
|---|---|
| 1. yıl | %12 |
| 2-10. yıl | %6 |
| 11. yıl ve sonrası | %4 |

Örnek: 2.000.000 TL'lik güncel Golf, 6 yaşında → 2.000.000 × 0,88 × 0,94⁵ ≈ 1.292.000 TL.
Gerekçe: küresel ölçekte ilk yıl kaybı %15-25 veriliyor; Türkiye'de arz kıtlığı ve ÖTV yapısı yüzünden ikinci el fiyatlar sıfıra yakın seyrettiği için daha düşük başlatıldı.
Marka bazlı çarpan alanı (`marka_yas_carpani`, varsayılan 1,0) dosyada bulunur; veriyle ayarlanır.

**Km (yıllık 15.000 km normal kabul):**
- Beklenen km = yaş × 15.000. Her 10.000 km fazlası için −%1, eksiği için +%1.
- Toplam km etkisi ±%10 ile sınırlı.

**Değişen / boyalı parçalar (parça başına, tahminin yüzdesi):**
| Parça | Değişen | Boyalı | Lokal boyalı |
|---|---|---|---|
| Tavan | %15 | %8 | %4 |
| Kaput | %4 | %1,5 | %0,75 |
| Bagaj kapağı | %3 | %1 | %0,5 |
| Kapı (her biri) | %2,5 | %1 | %0,5 |
| Çamurluk (her biri) | %2,5 | %1 | %0,5 |
| Ön/arka tampon | %1 | %0,5 | %0 |

- Parça düşüşleri toplanır, toplam **%35** ile sınırlanır.
- Gerekçe: ilan analizinde değişen parçalı araçlarda medyan fark ~%9,6, 1-2 parça boyalıda ~%3,2; tavan boyası takla şüphesiyle %15-20'ye kadar değer kaybettirebiliyor; temizlik amaçlı tampon boyası değeri pek etkilemiyor.

**Ağır hasar kaydı:** %30 düşüş (kaynaklarda %20-50 aralığı). Ağır hasar varsa kullanıcıya mutlaka sor (kaydın tarihi, hasarın yeri), sonucu "yüksek belirsizlik" olarak etiketle.

**Tramer tutarı:** v1'de hesaba girmez; tahminin %10'unu aşıyorsa uyarı olarak gösterilir.

## Karar eşiği
| İlan fiyatı tahmine göre | Öneri |
|---|---|
| ≤ %5 üstü (veya altı) | **Uygun, alınabilir** |
| %5 - %15 üstü | **Pazarlık yap** |
| > %15 üstü | **Pahalı** |

Teklif aralığı: tahminin %95'i ile %100'ü arası (pazarlıkta açılış teklifi ve üst sınır olarak).
Tahminin %20'den fazla altındaki ilanlar için "şüpheli derecede ucuz, ekspertiz ve tramer kontrolü yaptır" uyarısı ver.

## İnsan onayı / soru sorma noktaları
Agent kendi başına karar vermesin, kullanıcıya sorsun:
- Motor/paket ilandan net anlaşılmıyorsa
- İlandaki motor/paket artık satılmıyorsa ve en yakın güncel karşılık kullanılacaksa
- İlandaki bilgiler çelişiyorsa (başlık "hatasız", açıklama "boyalı" gibi)
- Ağır hasar kaydı varsa (kaydın tarihini ve hasarın yerini sor)
- Tramer yok beyanı: tek başına güvenme, "beyan" olarak etiketle

## Kapsam (v1)
Markalar: **BMW, Mercedes-Benz, Volkswagen, Porsche, Opel, Fiat.** Her marka için Türkiye'de satılan güncel modeller, motorlar ve paketler. Önce her markadan en çok satılan 2-3 model ile akışı uçtan uca çalıştır, sonra o markaların diğer modellerine genişlet.

## Kod düzeni (öneri)
```
src/
  extract/    # ilan linki/metni -> yapılandırılmış alanlar (fetch + LLM + şema doğrulama)
  pricing/    # saf Python düşüş fonksiyonları (unit test'li)
  data/       # sıfır fiyat ve kural yükleyiciler, paket eşleştirme
  agent/      # orkestrasyon, soru sorma/onay mantığı
tests/
data/
  zero_km.json
  rules.json
```
Stack: Python + JSON (gerekirse SQLite), Anthropic SDK.

## Araştırma kaynakları (başlangıç oranları için)
- [araclo.com – değer kaybı hesabı](https://www.araclo.com/blog/sifir-araba-mi-2-3-yasinda-ikinci-el-mi-deger-kaybi-hesabi)
- [aracendeks.com – boyalı ve değişenli araç ne kadar ucuz](https://aracendeks.com/blog/boyali-degisenli-arac-ne-kadar-ucuz)
- [rsotoekspertiz.com – araç değeri hesaplama rehberi](https://rsotoekspertiz.com/arabam-ne-kadar-eder-piyasa-degeri-hesaplama/)
- [eksperman.com – değişen parça değer kaybı](https://www.eksperman.com/blog/degisen-parca-deger-kaybi)
- [otokocikinciel.com – araç değer kaybı](https://www.otokocikinciel.com/blog/arac-deger-kaybi-nasil-hesaplanir)
- [turkiyesigorta.com.tr – ağır hasar kaydı](https://www.turkiyesigorta.com.tr/blog/arac/agir-hasar-kaydi-nedir)
- [kisadalga.net – ikinci el reel değer kaybı](https://kisadalga.net/haber/otomobil/ikinci-el-aracin-zarari-iki-yila-dayandi-124907)
