const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

let puppeteer = null;
try {
  puppeteer = require('puppeteer');
} catch (e) {}

/**
 * Tam Doksan Resmi Gönderi Tasarım Motoru (Çapraz Platform - Windows & Render Linux)
 */
async function createTamDoksanPost(bgImagePath, whiteText, yellowText, outputPath) {
  const logoPath = path.join(__dirname, 'templates', 'tam90_logo.png').replace(/\\/g, '/');
  const footerPath = path.join(__dirname, 'templates', 'sponsors_footer.png').replace(/\\/g, '/');
  const normalizedBg = path.resolve(bgImagePath).replace(/\\/g, '/');
  const normalizedOut = path.resolve(outputPath);

  const htmlContent = `
<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Anton&display=swap');

    * { margin: 0; padding: 0; box-sizing: border-box; }
    body, html { width: 825px; height: 1024px; overflow: hidden; background: #000; font-family: 'Anton', 'Impact', sans-serif; }

    .canvas {
      position: relative;
      width: 825px;
      height: 1024px;
      background: #000;
      overflow: hidden;
    }

    /* 1. Gerçek Basın / Maç Fotoğrafı */
    .bg-photo {
      position: absolute;
      top: 0;
      left: 0;
      width: 825px;
      height: 720px;
      object-fit: cover;
      object-position: center top;
      filter: contrast(1.08) brightness(0.98);
    }

    /* Fotoğrafın altındaki koyu geçiş */
    .gradient-overlay {
      position: absolute;
      left: 0;
      top: 350px;
      width: 825px;
      height: 380px;
      background: linear-gradient(to bottom, rgba(0,0,0,0) 0%, rgba(0,0,0,0.85) 60%, rgba(0,0,0,1) 100%);
      pointer-events: none;
    }

    /* 2. Sol Üst TAM90 Şeffaf Logosu */
    .header-logo {
      position: absolute;
      top: 15px;
      left: 15px;
      width: 215px;
      filter: drop-shadow(0px 3px 6px rgba(0,0,0,0.9));
      z-index: 10;
    }

    /* 3. Manşet Başlık Alanı (Fırçasız, net, tok, güçlü) */
    .headline-container {
      position: absolute;
      left: 20px;
      right: 20px;
      bottom: 165px;
      text-align: center;
      z-index: 10;
    }

    .headline-white {
      font-size: 70px;
      line-height: 1.05;
      color: #FFFFFF;
      text-transform: uppercase;
      letter-spacing: 1px;
      text-shadow: 0px 4px 15px rgba(0,0,0,0.95), 0px 0px 8px rgba(0,0,0,0.8);
    }

    .headline-yellow {
      font-size: 70px;
      line-height: 1.05;
      color: #FFCC00;
      text-transform: uppercase;
      letter-spacing: 1px;
      text-shadow: 0px 4px 15px rgba(0,0,0,0.95), 0px 0px 8px rgba(0,0,0,0.8);
    }

    /* 4. Alt Sponsorluklar ve Sosyal Medya Barı */
    .footer-bar {
      position: absolute;
      bottom: 0;
      left: 0;
      width: 825px;
      height: 164px;
      object-fit: cover;
      z-index: 15;
    }
  </style>
</head>
<body>
  <div class="canvas">
    <img class="bg-photo" src="file:///${normalizedBg}">
    <div class="gradient-overlay"></div>
    <img class="header-logo" src="file:///${logoPath}">

    <div class="headline-container">
      <div class="headline-white">${whiteText}</div>
      <div class="headline-yellow">${yellowText}</div>
    </div>

    <img class="footer-bar" src="file:///${footerPath}">
  </div>
</body>
</html>
`;

  const tempHtml = path.join(__dirname, 'render_temp.html');
  fs.writeFileSync(tempHtml, htmlContent, 'utf-8');

  let rendered = false;
  if (puppeteer) {
    try {
      const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
      });
      const page = await browser.newPage();
      await page.setViewport({ width: 825, height: 1024 });
      await page.goto(`file:///${tempHtml.replace(/\\/g, '/')}`, { waitUntil: 'load' });
      await page.screenshot({ path: normalizedOut });
      await browser.close();
      rendered = true;
    } catch (e) {
      console.log('Puppeteer fallback yapılıyor:', e.message);
    }
  }

  if (!rendered) {
    const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
    if (fs.existsSync(edgePath)) {
      const cmd = `"${edgePath}" --headless --disable-gpu --screenshot="${normalizedOut}" --window-size=825,1024 "file:///${tempHtml.replace(/\\/g, '/')}"`;
      execSync(cmd, { stdio: 'ignore' });
      rendered = true;
    }
  }

  if (fs.existsSync(tempHtml)) fs.unlinkSync(tempHtml);

  console.log(`Tam Doksan Tasarımı Başarıyla Oluşturuldu: ${normalizedOut}`);
  return normalizedOut;
}

module.exports = { createTamDoksanPost };
