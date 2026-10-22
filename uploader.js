const axios = require('axios');
const fs = require('fs');
const path = require('path');
const sizeOf = require('image-size');

function loadCookies() {
  const cookiePath = path.join(__dirname, 'cookies.json');
  if (!fs.existsSync(cookiePath)) {
    throw new Error('cookies.json bulunamadı. Lütfen önce giriş yapın.');
  }
  return JSON.parse(fs.readFileSync(cookiePath, 'utf-8'));
}

function getCookieHeader(cookieObj) {
  return Object.entries(cookieObj).map(([k, v]) => `${k}=${v}`).join('; ');
}

async function uploadPhoto(imagePath, caption) {
  const cookieObj = loadCookies();
  const cookieHeader = getCookieHeader(cookieObj);
  const csrftoken = cookieObj['csrftoken'];

  const fullPath = path.resolve(imagePath);
  if (!fs.existsSync(fullPath)) {
    throw new Error(`Görsel dosyası bulunamadı: ${fullPath}`);
  }

  const fileBuffer = fs.readFileSync(fullPath);
  let dimensions = { width: 1080, height: 1080 };
  try {
    const dim = sizeOf(fullPath);
    dimensions.width = dim.width;
    dimensions.height = dim.height;
  } catch (e) {
    console.log('Boyut varsayılan 1080x1080 kullanılıyor.');
  }

  const uploadId = Date.now().toString();
  const entityName = `fb_uploader_${uploadId}`;

  console.log(`[1/2] Görsel Instagram sunucularına yükleniyor (Boyut: ${dimensions.width}x${dimensions.height})...`);

  const ruploadParams = JSON.stringify({
    media_type: 1,
    upload_id: uploadId,
    upload_media_height: dimensions.height,
    upload_media_width: dimensions.width
  });

  const uploadRes = await axios.post(
    `https://www.instagram.com/rupload_igphoto/${entityName}`,
    fileBuffer,
    {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'X-Instagram-Rupload-Params': ruploadParams,
        'X-Entity-Name': entityName,
        'X-Entity-Length': fileBuffer.length.toString(),
        'Offset': '0',
        'Content-Type': 'image/jpeg',
        'X-CSRFToken': csrftoken,
        'X-IG-App-ID': '936619743392459',
        'X-ASBD-ID': '129477',
        'Origin': 'https://www.instagram.com',
        'Referer': 'https://www.instagram.com/',
        'Cookie': cookieHeader
      }
    }
  );

  if (uploadRes.status !== 200 && uploadRes.status !== 201) {
    throw new Error(`Görsel yükleme başarısız oldu: ${uploadRes.status}`);
  }

  console.log('[2/2] Gönderi oluşturuluyor ve yayınlanıyor...');

  const configParams = new URLSearchParams({
    source_type: 'library',
    caption: caption,
    upload_id: uploadId,
    disable_comments: '0',
    like_and_view_counts_disabled: '0'
  }).toString();

  const configureRes = await axios.post(
    'https://www.instagram.com/api/v1/media/configure/',
    configParams,
    {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'X-CSRFToken': csrftoken,
        'X-Requested-With': 'XMLHttpRequest',
        'X-IG-App-ID': '936619743392459',
        'X-ASBD-ID': '129477',
        'Origin': 'https://www.instagram.com',
        'Referer': 'https://www.instagram.com/',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': cookieHeader
      }
    }
  );

  console.log('Yanıt Tipi:', typeof configureRes.data);
  if (configureRes.data && configureRes.data.status === 'ok') {
    console.log('\n======================================================');
    console.log('🎉 BAŞARILI! Gönderi Instagram\'da yayınlandı!');
    console.log(`Instagram Linki: https://www.instagram.com/p/${configureRes.data.media.code}/`);
    console.log('======================================================\n');
    return configureRes.data.media;
  } else {
    console.log('Sunucu Yanıtı:', configureRes.data);
    throw new Error(`Yayınlama başarısız oldu: ${JSON.stringify(configureRes.data)}`);
  }
}

module.exports = { uploadPhoto };

if (require.main === module) {
  const index = parseInt(process.argv[2], 10) || 1;
  const posts = [
    {
      file: path.join(__dirname, 'images', 'post1_deadlift.jpg'),
      caption: `Ağır kaldır, sınırlarını aş! 💥\n\nBaşarı bir gecede gelmez; salona her adım attığında döktüğün her damla terin sonucudur. Bugün bahane üretme, hedefin için savaş!\n.\n.\n#fitness #bodybuilding #motivasyon #sporgünlüğü #antrenman #deadlift #fitkal #spor`
    },
    {
      file: path.join(__dirname, 'images', 'post2_sprinter.jpg'),
      caption: `Her gün yeni bir başlangıç! 🌅\n\nGüneş doğarken uyananlar ve durmadan koşanlar asla kaybetmez. Kendi rekorunu kırmaya hazır mısın?\n.\n.\n#koşu #kondisyon #atletizm #sabahsporu #motivasyon #hırs #odaklan #cardio`
    },
    {
      file: path.join(__dirname, 'images', 'post3_nutrition.jpg'),
      caption: `Kaslar salonda yırtılır, mutfakta inşa edilir! 🥗🥑\n\nAntrenmanın hakkını verdikten sonra vücudunu doğru besinlerle ödüllendir. Yüksek protein, kaliteli yağlar ve temiz karbonhidrat.\n.\n.\n#beslenme #fitnessbeslenme #sağlıklıyaşam #diyet #protein #sağlıklıbeslenme #fitnessyemekleri`
    }
  ];

  const selected = posts[index - 1] || posts[0];
  console.log(`Günün ${index}. gönderisi Instagram'a yükleniyor...`);
  uploadPhoto(selected.file, selected.caption).catch(err => {
    console.error('Hata:', err.message);
  });
}
