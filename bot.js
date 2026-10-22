const axios = require('axios');
const fs = require('fs');
const path = require('path');
const http = require('http');
const { getLatestFootballNews } = require('./news_scraper');
const { createTamDoksanPost } = require('./generator');
const { uploadPhoto } = require('./uploader');
require('dotenv').config();

// Bulut ortamında çerezleri ortam değişkeninden geri yükle
if (process.env.IG_COOKIES_JSON && !fs.existsSync(path.join(__dirname, 'cookies.json'))) {
  fs.writeFileSync(path.join(__dirname, 'cookies.json'), process.env.IG_COOKIES_JSON);
  console.log('[Bulut] Oturum çerezleri IG_COOKIES_JSON değişkeninden yüklendi.');
}

// Web Sunucusu (Render.com / Bulut 7/24 Kesintisiz Çalışma İçin)
const PORT = process.env.PORT || 3000;
http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('⚽️ TAM DOKSAN (@tamdoksanaresmi) 7/24 Orijinal Şablonlu Futbol Botu Aktif!\n\nSponsorlar: Aydessa Lingerie & Luster Car\nKaynaklar: Transfermarkt, Fotomaç, Fanatik, NTV Spor, Sports Digitale, Yağız Sabuncuoğlu');
}).listen(PORT, () => {
  console.log(`[Bulut] Web sunucusu ${PORT} portunda 7/24 yayında.`);
});

console.log('================================================================');
console.log('⚽️ TAM DOKSAN (@tamdoksanaresmi) RESMİ ŞABLON BOTU BAŞLATILDI');
console.log('💎 Sponsorlar: Aydessa Lingerie & Luster Car (Her görselde altlık)');
console.log('🏷️ Logo: Sol Üst TAM90 Futbol\'a Tutku');
console.log('📸 Görseller: %100 GERÇEK BASIN VE MAÇ FOTOĞRAFLARI (Yapay Zeka Çizimi Yok)');
console.log('🕒 Günlük Post Saatleri: 10:00, 15:00, 20:00');
console.log('================================================================\n');

// Başlığı İki Satıra Bölme (1. Satır Beyaz, 2. Satır Sarı)
function splitHeadline(title) {
  // Temizle
  let clean = title.replace(/^(FLAŞ|SON DAKİKA|ÖZEL|HABER|TRANSFER|RESMİ)\s*[:|-]\s*/i, '').trim();
  const words = clean.split(' ');

  if (words.length <= 3) {
    return {
      white: words.slice(0, 1).join(' ').toUpperCase(),
      yellow: words.slice(1).join(' ').toUpperCase() + ' !'
    };
  }

  const mid = Math.ceil(words.length / 2);
  return {
    white: words.slice(0, mid).join(' ').toUpperCase(),
    yellow: words.slice(mid).join(' ').toUpperCase() + ' !'
  };
}

// Canlı Haberi Gerçek Basın Fotoğrafıyla Tam Doksan Şablonuna Giydirip Paylaşma
async function publishTamDoksanSlot(slotName) {
  console.log(`\n-----------------------------------------------------`);
  console.log(`[${new Date().toLocaleTimeString('tr-TR')}] ⚽️ ${slotName} GÖNDERİSİ HAZIRLANIYOR...`);
  console.log(`-----------------------------------------------------`);

  try {
    const liveNews = await getLatestFootballNews();
    if (!liveNews || liveNews.length === 0) {
      console.log('Haber bulunamadı, bekleniyor...');
      return;
    }

    const item = liveNews[Math.floor(Math.random() * Math.min(liveNews.length, 6))];
    console.log(`[Haber Seçildi]: ${item.title}`);

    // Gerçek fotoğrafı haberden çek
    let realPhotoUrl = null;
    try {
      const pageRes = await axios.get(item.link, { timeout: 10000 });
      const match = pageRes.data.match(/<meta\s+property=["']og:image["']\s+content=["']([^"']+)["']/i);
      if (match) realPhotoUrl = match[1];
    } catch (e) {
      console.log('Haber sayfasından görsel çekilemedi, yedek kullanılıyor.');
    }

    // Fotoğrafı indir
    const tempPressPhoto = path.join(__dirname, 'temp_raw_press.jpg');
    if (realPhotoUrl) {
      const dlRes = await axios.get(realPhotoUrl, { responseType: 'arraybuffer' });
      fs.writeFileSync(tempPressPhoto, dlRes.data);
    } else {
      // Eğer çekilemezse mevcut en son basın fotoğrafını kullan
      fs.copyFileSync(path.join(__dirname, 'images', 'real_press_photo.jpg'), tempPressPhoto);
    }

    // Başlıkları ayarla
    const { white, yellow } = splitHeadline(item.title);

    // Orijinal Tam Doksan Şablonunu Oluştur
    const finalPostPath = path.join(__dirname, 'temp_final_tam90_post.jpg');
    createTamDoksanPost(tempPressPhoto, white, yellow, finalPostPath);

    // Instagram Açıklaması
    const caption = `🚨 ${item.title}\n\n` +
      `Süper Lig'de ve Avrupa'da sıcak gelişmeler devam ediyor. Detaylar geldikçe aktaracağız.\n\n` +
      `Sizce bu gelişme nasıl sonuçlanır? Yorumlarda buluşalım! 👇⚽️\n.\n.\n` +
      `#tamdoksan #futbol #süperlig #fenerbahçe #galatasaray #beşiktaş #trabzonspor #transfer #haber #sportsdigitale`;

    // Instagram'a Paylaş
    console.log('[Instagram] Tam Doksan şablonlu gönderi paylaşılıyor...');
    await uploadPhoto(finalPostPath, caption);
  } catch (err) {
    console.error('[Hata] Paylaşım yapılamadı:', err.message);
  }
}

// 7/24 Zamanlayıcı Döngüsü (10:00, 15:00, 20:00)
const postedToday = new Set();

setInterval(async () => {
  const now = new Date(new Date().toLocaleString('en-US', { timeZone: 'Europe/Istanbul' }));
  const hour = now.getHours();
  const minute = now.getMinutes();
  const todayKey = `${now.getFullYear()}-${now.getMonth()}-${now.getDate()}`;

  if (hour === 10 && minute === 0 && !postedToday.has(`${todayKey}_10`)) {
    postedToday.add(`${todayKey}_10`);
    await publishTamDoksanSlot('SABAH GÜNDEMİ');
  }

  if (hour === 15 && minute === 0 && !postedToday.has(`${todayKey}_15`)) {
    postedToday.add(`${todayKey}_15`);
    await publishTamDoksanSlot('ÖĞLE GÜNDEMİ');
  }

  if (hour === 20 && minute === 0 && !postedToday.has(`${todayKey}_20`)) {
    postedToday.add(`${todayKey}_20`);
    await publishTamDoksanSlot('AKŞAM GÜNDEMİ');
  }

  if (hour === 0 && minute === 1) {
    postedToday.clear();
  }
}, 30000);
