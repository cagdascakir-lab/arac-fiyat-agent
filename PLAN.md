# Uygulama Planı (adım adım, her adım test edilerek)

## Adım 1: Proje iskeleti ve veri şeması
- Python projesi, `src/` düzeni, test altyapısı (pytest), git
- `data/zero_km.json` şeması: marka, model, model_yili, motor, motor_hacmi, yakit, vites, paket, liste_fiyat, kampanyali_fiyat, kaynak, guncelleme_tarihi
- `data/rules.json` şeması: yaş, km, parça, ağır hasar oranları, karar eşikleri, kalibrasyon_tarihi
- Test: yükleyiciler şemayı doğruluyor, bozuk kayıtları reddediyor

## Adım 2: Sıfır fiyat verisi
- 6 marka (BMW, Mercedes-Benz, Volkswagen, Porsche, Opel, Fiat) için önce en çok satan 2-3 model; güncel model yılı, tüm motor + paket kombinasyonları
- Kaynak: marka resmî fiyat listeleri, araclo.com, arabam.com sıfır km sayfaları; her kayıtta kaynak ve tarih
- Toplanan veri kullanıcıya kontrol ettirilir
- Test: bir marka/model/motor/paket için doğru fiyat dönüyor; olmayan kayıt için "veri yok"

## Adım 3: Paket/motor eşleştirme
- İlandaki motor/paketi güncel listeye eşle (ör. 2020 Golf 1.6 TDI Comfortline → güncel en yakın motor + eşdeğer donanım)
- Eşleşme tipi: birebir / en yakın / bulunamadı; "en yakın" ise kullanıcı onayı gerekir
- Test: birebir, en yakın ve bulunamayan örnekler

## Adım 4: Hesap motoru
- `pricing/` saf fonksiyonlar: yaş çarpanı, km çarpanı, parça düşüşü (tavanlı), ağır hasar düşüşü, tahmin, fark yüzdesi, karar (uygun / pazarlık / pahalı), teklif aralığı
- Her sonuç uygulanan düşüşlerin dökümünü döndürür
- Test: elle hesaplanmış örneklerle birebir; sınır durumlar (0 yaş, çok yüksek km, tavanı aşan parça, ağır hasar)

## Adım 5: İlan çıkarımı
- Alanlar: marka, model, motor, paket, yıl, km, yakıt, vites, fiyat, değişen/boyalı/lokal boyalı parça listesi, ağır_hasar, tramer_tutarı, satıcı_tipi, belirsiz_alanlar
- Önce ilan metni yapıştırma girişi (LLM + şema doğrulama), sonra tek link okuma (sahibinden + arabam.com); okuma başarısızsa metne düş
- Satıcı adı/telefonu atılır
- Test: 5-10 örnek ilanla çıkarım doğruluğu; belirsiz ve çelişen alanlar işaretleniyor

## Adım 6: Agent orkestrasyonu
- Akış: link → oku/çıkar → eksik/çelişkiyi sor → paket eşleştir (gerekirse onay) → hesapla → yorumla ("uygun / pazarlık yap / pahalı" + teklif aralığı + düşüş dökümü + kaynak)
- Soru/onay noktaları CLAUDE.md'deki gibi
- Arayüz: önce CLI
- Test: uçtan uca 5 ilan senaryosu (hatasız, boyalı, değişenli, ağır hasarlı, eski paket)

## Adım 7: Kalibrasyon, değerlendirme ve yayın
- Gerçek ilanlarla tahmin–ilan fiyatı sapmasını ölç, `rules.json` oranlarını güncelle (kalibrasyon_tarihi ile)
- Sınırlılıkları README'ye yaz
- İsteğe bağlı basit web arayüzü (demo için)
- LinkedIn için: mimari özeti (kural tabanlı hesap + LLM okuma/yorum), veri güncelleme akışı, sınırlar

## Netleşen kararlar
1. Düşüşler yüzde (sabit TL değil), başlangıç oranları CLAUDE.md'de
2. Referans: en güncel model yılının liste fiyatı; eski paket/motor için en yakın güncel karşılık + kullanıcı onayı
3. Karar eşiği: ≤%5 uygun, %5-15 pazarlık, >%15 pahalı
4. Markalar: BMW, Mercedes-Benz, Volkswagen, Porsche, Opel, Fiat
5. Link okuma: sahibinden + arabam.com tek link; başarısızsa metin yapıştırma
