const axios = require('axios');
const fs = require('fs');
const path = require('path');
const http = require('http');
const { getLatestFootballNews } = require('./news_scraper');
const { createTamDoksanPost } = require('./generator');
const { uploadPhoto } = require('./uploader');
const { publishLineupStory } = require('./story_lineup');
require('dotenv').config();

// Bulut ortamında çerezleri ortam değişkeninden geri yükle
if (process.env.IG_COOKIES_JSON && !fs.existsSync(path.join(__dirname, 'cookies.json'))) {
  fs.writeFileSync(path.join(__dirname, 'cookies.json'), process.env.IG_COOKIES_JSON);
  console.log('[Bulut] Oturum çerezleri yüklendi.');
}

// 7/24 Web Sunucusu (Render için)
const PORT = process.env.PORT || 3000;
http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('⚽️ TAM DOKSAN (@tamdoksanaresmi) 7/24 VİRAL BÜYÜME VE SPONSOR ÇEKME MOTORU AKTİF!\n\nGünlük Paylaşım Saatleri: 10:00, 12:00, 15:00, 17:00, 20:00, 22:00, 00:00 (Günde 7 Gönderi)\nMaç Günleri: Sınırsız Ekstra Paylaşım ve Story Modu Aktif.');
}).listen(PORT, () => {
  console.log(`[Bulut] Web sunucusu ${PORT} portunda 7/24 canlı yayında.`);
});

console.log('================================================================');
console.log('🔥 TAM DOKSAN (@tamdoksanaresmi) VİRAL ETKİLEŞİM MODU DEVREDE');
console.log('🎯 Hedef: Yorum rekorları, keşfete düşme ve sponsor çekme');
console.log('🕒 Günlük Gönderi Saatleri: 10:00, 12:00, 15:00, 17:00, 20:00, 22:00, 00:00');
console.log('⚽️ Maç Günleri: Sınırsız ekstra gönderi ve İlk 11 Story sistemi');
console.log('================================================================\n');

// Yüksek Yorum ve Etkileşim Çeken Kanca Şablonları (Instagram Algoritması İçin)
const ENGAGEMENT_HOOKS = [
  {
    type: 'tartisma',
    question: '👉 Sizce kim haklı? Tarafsız gözle yorumlarınızı yazın, tartışalım! 👇',
    callToAction: 'Tarafını seç ve fikrini belirt! Yorumlardayız.'
  },
  {
    type: 'transfer_anket',
    question: '🔥 Bu transfer gerçekleşirse Süper Lig\'in kaderi değişir mi? Evet / Hayır?',
    callToAction: 'Takımına bu oyuncu gelse sevinir miydin? Yorumlara yaz!'
  },
  {
    type: 'hakem_var',
    question: '👀 Sizce bu pozisyonda hakemin ve VAR\'ın kararı doğru mu? Yorumlarda buluşalım! 👇',
    callToAction: 'Pozisyonu 1 ile 10 arasında puanlayın!'
  },
  {
    type: 'nostalji_karsilastirma',
    question: '⚔️ Prime dönemlerini kıyaslarsak hangisi takımında banko oynar? A mı B mi?',
    callToAction: 'Geceye damga vuracak cevabını yoruma bırak!'
  }
];

// Başlığı İki Satıra Bölme (1. Satır Beyaz, 2. Satır Sarı ve Sansasyonel)
function splitHeadline(title) {
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

// Viral Post Yayınlama Motoru
async function publishViralPost(slotName) {
  console.log(`\n======================================================`);
  console.log(`[${new Date().toLocaleTimeString('tr-TR')}] 🔥 ${slotName} VİRAL GÖNDERİSİ HAZIRLANIYOR...`);
  console.log(`======================================================`);

  try {
    const liveNews = await getLatestFootballNews();
    if (!liveNews || liveNews.length === 0) {
      console.log('Haber bulunamadı, bekleniyor...');
      return;
    }

    const item = liveNews[Math.floor(Math.random() * Math.min(liveNews.length, 8))];
    console.log(`[Haber Seçildi]: ${item.title}`);

    // Gerçek fotoğrafı haberden çek
    let realPhotoUrl = null;
    try {
      const pageRes = await axios.get(item.link, { timeout: 10000 });
      const match = pageRes.data.match(/<meta\s+property=["']og:image["']\s+content=["']([^"']+)["']/i);
      if (match) realPhotoUrl = match[1];
    } catch (e) {}

    const tempPressPhoto = path.join(__dirname, 'temp_raw_press.jpg');
    if (realPhotoUrl) {
      const dlRes = await axios.get(realPhotoUrl, { responseType: 'arraybuffer' });
      fs.writeFileSync(tempPressPhoto, dlRes.data);
    } else {
      fs.copyFileSync(path.join(__dirname, 'images', 'real_press_photo.jpg'), tempPressPhoto);
    }

    const { white, yellow } = splitHeadline(item.title);
    const finalPostPath = path.join(__dirname, 'temp_final_tam90_post.jpg');
    await createTamDoksanPost(tempPressPhoto, white, yellow, finalPostPath);

    const hook = ENGAGEMENT_HOOKS[Math.floor(Math.random() * ENGAGEMENT_HOOKS.length)];

    // Maksimum Yorum Çekecek Instagram Açıklaması
    const caption = `🚨 ${item.title}\n\n` +
      `Süper Lig'de ve Avrupa arenasında tansiyon hiç düşmüyor! Masadaki son detaylar ve perde arkasında konuşulanlar ortaya çıktı.\n\n` +
      `${hook.question}\n\n` +
      `💬 ${hook.callToAction}\n` +
      `👉 Takip etmeyi ve bildirimleri açmayı unutmayın: @tamdoksanaresmi\n.\n.\n` +
      `#tamdoksan #futbol #süperlig #fenerbahçe #galatasaray #beşiktaş #trabzonspor #transfer #haber #keşfet #futbolcaps #derbi`;

    console.log('[Instagram] Viral Tam Doksan gönderisi sayfaya yükleniyor...');
    await uploadPhoto(finalPostPath, caption);
  } catch (err) {
    console.error('[Hata] Paylaşım yapılamadı:', err.message);
  }
}

// 7/24 Kesintisiz Zamanlayıcı (10:00, 12:00, 15:00, 17:00, 20:00, 22:00, 00:00)
const postedSlots = new Set();
const TARGET_HOURS = [10, 12, 15, 17, 20, 22, 0];

setInterval(async () => {
  const now = new Date(new Date().toLocaleString('en-US', { timeZone: 'Europe/Istanbul' }));
  const hour = now.getHours();
  const minute = now.getMinutes();
  const todayKey = `${now.getFullYear()}-${now.getMonth()}-${now.getDate()}`;

  for (const targetHour of TARGET_HOURS) {
    const slotKey = `${todayKey}_slot_${targetHour}`;

    if (hour === targetHour && minute === 0 && !postedSlots.has(slotKey)) {
      postedSlots.add(slotKey);
      await publishViralPost(`SAAT ${targetHour}:00 GÜNDEMİ`);
    }
  }

  // Gece yarısı hafızayı tazele
  if (hour === 0 && minute === 5) {
    postedSlots.clear();
  }
}, 30000);
