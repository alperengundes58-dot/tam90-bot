// 4 Büyükler Maç Önü İlk 11 Story Paylaşım Modülü
// Galatasaray, Fenerbahçe, Beşiktaş, Trabzonspor
const fs = require('fs');
const path = require('path');
const axios = require('axios');
const { IgApiClient } = require('instagram-private-api');
const tough = require('tough-cookie');

const BIG_FOUR = {
  GS: { name: 'Galatasaray', tag: '#Galatasaray', color: '#A90432' },
  FB: { name: 'Fenerbahçe', tag: '#Fenerbahçe', color: '#002D72' },
  BJK: { name: 'Beşiktaş', tag: '#Beşiktaş', color: '#000000' },
  TS: { name: 'Trabzonspor', tag: '#Trabzonspor', color: '#670001' }
};

async function getAuthenticatedClient() {
  const ig = new IgApiClient();
  const cookiePath = path.join(__dirname, 'cookies.json');
  const cookies = JSON.parse(fs.readFileSync(cookiePath, 'utf-8'));

  ig.state.generateDevice('tamdoksanaresmi');

  for (const [key, val] of Object.entries(cookies)) {
    const cookie = new tough.Cookie({
      key: key,
      value: val,
      domain: 'instagram.com',
      path: '/'
    });
    await new Promise((res, rej) => ig.state.cookieStore.putCookie(cookie, err => err ? rej(err) : res()));
  }

  return ig;
}

// Maç önü ilk 11 Story görseli üretme (9:16 Hikaye Formatı)
async function generateLineupStoryImage(teamCode, opponent, lineupText) {
  const team = BIG_FOUR[teamCode] || { name: teamCode };
  const prompt = `football starting 11 tactical lineup poster for ${team.name} vs ${opponent}, vertical 9:16 story format, professional sports graphic design, neon stadium floodlights, dark atmospheric background, ultra high quality`;
  
  const encoded = encodeURIComponent(prompt);
  const seed = Math.floor(Math.random() * 1000000);
  const url = `https://image.pollinations.ai/prompt/${encoded}?width=1080&height=1920&nologo=true&seed=${seed}`;

  console.log(`[Story] ${team.name} İlk 11 görseli üretiliyor...`);
  const res = await axios.get(url, { responseType: 'arraybuffer', timeout: 60000 });
  const storyFile = path.join(__dirname, `story_${teamCode.toLowerCase()}_lineup.jpg`);
  fs.writeFileSync(storyFile, res.data);
  return storyFile;
}

// Story olarak paylaş
async function publishLineupStory(teamCode, opponent, lineupText) {
  try {
    const team = BIG_FOUR[teamCode] || { name: teamCode };
    console.log(`\n======================================================`);
    console.log(`🚨 STORY GÖREVİ: ${team.name} - ${opponent} İLK 11'LERİ`);
    console.log(`======================================================`);

    const imagePath = await generateLineupStoryImage(teamCode, opponent, lineupText);
    const ig = await getAuthenticatedClient();

    const fileBuffer = fs.readFileSync(imagePath);
    console.log('[Instagram] Story yükleniyor...');
    
    // Story publish
    await ig.publish.story({
      file: fileBuffer
    });

    console.log(`🎉 ${team.name} İlk 11 Story'si Başarıyla Paylaşıldı!`);
  } catch (err) {
    console.error('[Story Hatası]:', err.message);
  }
}

module.exports = { publishLineupStory, BIG_FOUR };

// Test amaçlı çalıştırma: node story_lineup.js FB GS
if (require.main === module) {
  const team = process.argv[2] || 'FB';
  const opp = process.argv[3] || 'Rakip';
  publishLineupStory(team, opp, 'Muhtemel 11');
}
