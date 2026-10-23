import os
import sys
import time
import json
import random
import re
import threading
import http.server
import socketserver
import urllib.parse
from pathlib import Path

import requests
import feedparser
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, ChallengeRequired

# 1. Log Defteri
LOG_MESSAGES = []
def log(msg):
    t = time.strftime('%H:%M:%S')
    formatted = f"[{t}] {msg}"
    print(formatted, flush=True)
    LOG_MESSAGES.append(formatted)
    if len(LOG_MESSAGES) > 60:
        LOG_MESSAGES.pop(0)

# 2. Render Kalıcı Hafıza Entegrasyonu
RENDER_API_KEY = os.environ.get("RENDER_API_KEY", "rnd_Io3TxMKKFNfiToforho4hmTXR5YN")
RENDER_SERVICE_ID = os.environ.get("RENDER_SERVICE_ID", "srv-dbd88oafngtc73fv6n70")
SESSION_FILE = Path(__file__).parent / "session.json"

def persist_session_to_cloud():
    if not SESSION_FILE.exists():
        return
    try:
        content = SESSION_FILE.read_text(encoding="utf-8")
        url = f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/env-vars/IG_SESSION_DATA"
        r = requests.put(
            url,
            headers={
                "Authorization": f"Bearer {RENDER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={"value": content},
            timeout=10
        )
        if r.status_code in [200, 201]:
            log("🔒 Oturum Render kalıcı hafızasında güncellendi.")
    except Exception as e:
        log(f"Render kalıcı kayıt hatası: {e}")

def restore_session_from_cloud():
    env_data = os.environ.get("IG_SESSION_DATA")
    if env_data and not SESSION_FILE.exists():
        try:
            SESSION_FILE.write_text(env_data, encoding="utf-8")
            log("🔓 Oturum Render kalıcı hafızasından geri yüklendi!")
            return True
        except Exception as e:
            log(f"Oturum geri yükleme hatası: {e}")
    return False

# 3. Web Sunucusu
PORT = int(os.environ.get("PORT", 10000))

class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == '/logs':
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(LOG_MESSAGES, ensure_ascii=False, indent=2).encode("utf-8"))
            return

        if parsed.path in ['/post-now', '/api/post-now']:
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.end_headers()
            code = params.get('code', [None])[0]
            self.wfile.write(json.dumps({"status": "ok", "message": "Ultra 4K Viral Gönderi Tetiklendi!"}).encode("utf-8"))
            threading.Thread(target=execute_post, args=(code,)).start()
            return

        if parsed.path == '/post-approved':
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "message": "Onaylanan 4K Ronaldo Görseli Yükleniyor!"}).encode("utf-8"))
            threading.Thread(target=execute_approved_post).start()
            return

        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("⚽️ TAM DOKSAN (@tamdoksanaresmi) 7/24 Kesintisiz Ultra 4K Otopilot Yayında!".encode("utf-8"))

# 4. Instagram İstemcisi
IG_USERNAME = os.environ.get("IG_USERNAME", "tamdoksanaresmi")
IG_PASSWORD = os.environ.get("IG_PASSWORD", "alperenseyit10")

cl = Client()
cl.delay_range = [1, 2]

def login_instagram(two_factor_code=None):
    log(f"@{IG_USERNAME} için Instagram oturumu kontrol ediliyor...")
    restore_session_from_cloud()

    if SESSION_FILE.exists():
        try:
            cl.load_settings(SESSION_FILE)
            cl.login(IG_USERNAME, IG_PASSWORD)
            log("Kayıtlı oturum yüklendi ve başarıyla doğrulandı!")
            persist_session_to_cloud()
            return True
        except Exception as e:
            log(f"Kayıtlı oturum yenileniyor: {e}")

    try:
        if two_factor_code:
            log("2FA Kodu ile giriş yapılıyor...")
            cl.login(IG_USERNAME, IG_PASSWORD, verification_code=two_factor_code)
        else:
            cl.login(IG_USERNAME, IG_PASSWORD)

        cl.dump_settings(SESSION_FILE)
        persist_session_to_cloud()
        log("Giriş başarılı ve oturum kalıcı hafızaya kaydedildi!")
        return True
    except TwoFactorRequired:
        log("HATA: 2FA gerekiyor.")
        return False
    except Exception as e:
        log(f"Giriş hatası: {type(e).__name__} - {e}")
        return False

# 5. Gerçek Zamanlı ve Güncel Basın Fotoğrafı + Haber Özeti Çekici
ALREADY_POSTED_FILE = Path(__file__).parent / "posted_articles.json"

def get_posted_titles():
    if ALREADY_POSTED_FILE.exists():
        try:
            return set(json.loads(ALREADY_POSTED_FILE.read_text(encoding="utf-8")))
        except:
            return set()
    return set()

def save_posted_title(title):
    posted = get_posted_titles()
    posted.add(title)
    try:
        ALREADY_POSTED_FILE.write_text(json.dumps(list(posted), ensure_ascii=False), encoding="utf-8")
    except:
        pass

def clean_html(raw_html):
    if not raw_html:
        return ""
    text = re.sub(r'<!\[CDATA\[|\]\]>', '', raw_html)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_live_headline_and_photo():
    posted_titles = get_posted_titles()

    # Sadece anlık güncellenen Full HD Türk spor kaynakları
    sources = [
        "https://www.haberturk.com/rss/spor.xml",
        "https://ajansspor.com/rss",
        "https://www.sabah.com.tr/rss/spor.xml"
    ]

    # Düşük etkileşimli/amatör/tesis haberlerini filtrele
    skip_keywords = ["inşaat", "stadyumu", "voleybol", "hentbol", "güreş", "atletizm", "boks", "tenis"]

    for url in sources:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:18]:
                title = clean_html(entry.get("title", ""))
                summary = clean_html(entry.get("summary", "") or entry.get("description", ""))
                link = entry.get("link", "")
                img_url = None

                if not title or title in posted_titles:
                    continue

                lower_t = title.lower()
                if any(sk in lower_t for sk in skip_keywords):
                    continue

                # 1. Enclosure görseli
                if 'enclosures' in entry and len(entry.enclosures) > 0:
                    img_url = entry.enclosures[0].get('href')

                # 2. Media content görseli
                if not img_url and 'media_content' in entry and len(entry.media_content) > 0:
                    img_url = entry.media_content[0].get('url')

                # 3. Sayfa içi og:image
                if not img_url and link:
                    try:
                        r = requests.get(link, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
                        m = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', r.text, re.IGNORECASE)
                        if m:
                            img_url = m.group(1)
                    except:
                        pass

                if img_url and ("http" in img_url):
                    if "u=http" in img_url:
                        try:
                            img_url = urllib.parse.unquote(img_url.split("u=")[1])
                        except:
                            pass

                    log(f"🔥 BUGÜNÜN SICAK HABERİ SEÇİLDİ: {title}")
                    log(f"📸 Orijinal HD Fotoğraf URL: {img_url}")
                    save_posted_title(title)
                    return title, summary, img_url
        except Exception as e:
            log(f"Haber çekme uyarısı ({url}): {e}")

    return (
        "Cristiano Ronaldo durdurulamıyor! 982. golünü attı",
        "Suudi Arabistan Pro Ligi'nde Al-Nassr forması giyen Portekizli dünya yıldızı Cristiano Ronaldo, takımının galibiyetinde başrol oynayarak kariyerinin 982. golüne imza attı ve 1000 gol hedefine bir adım daha yaklaştı.",
        "https://cdn.ajansspor.com/ajansspor/photo/2026/10/aaac7ade-104b-485b-a4b7-c44b8a2aa1e8.jpg"
    )

# 6. Haberin Konusuna Göre Akıllı ve Mantıklı Açıklama (Caption) Üretici
def generate_smart_caption(title, summary):
    lower = f"{title} {summary}".lower()

    # Özeti temizle ve başlıkla birebir aynıysa tekrarı önle
    body_text = summary.strip() if summary and len(summary.strip()) > 25 else ""
    if body_text.lower() == title.lower():
        body_text = ""

    # Konuya özel soru ve emoji seçimi (ASLA alakasız "Sizce bu karar doğru mu?" yazmaz!)
    if any(k in lower for k in ["hastane", "sakat", "ameliyat", "tedavi", "kırık", "şok", "sağlık", "geçmiş olsun"]):
        question = "🙏 Geçmiş olsun dileklerimizi iletiyoruz. Sizce yokluğu takımı nasıl etkiler? Yorumlarda buluşalım 👇"
    elif any(k in lower for k in ["gol", "kazandı", "mağlup", "berabere", "galip", "zafer", "puan", "derbi", "skor", "982"]):
        question = "🔥 Bu performansı ve maçın sonucunu nasıl değerlendiriyorsunuz? Yorumlarınızı bekliyoruz! 👇⚽️"
    elif any(k in lower for k in ["transfer", "imza", "teklif", "kanca", "devrede", "ayrılık", "bonservis", "sözleşme"]):
        question = "👀 Sizce bu transfer gerçekleşirse takıma doğrudan katkı sağlar mı? Fikirlerinizi yorumlara yazın! 👇⚽️"
    elif any(k in lower for k in ["hakem", "ceza", "pfdk", "tff", "kırmızı kart", "penaltı", "var ", "iptal"]):
        question = "⚖️ Verilen bu karar hakkında siz ne düşünüyorsunuz? Yorumlarda tartışalım! 👇⚽️"
    else:
        question = "💬 Bu sıcak gelişme hakkında sizin düşünceleriniz neler? Yorumlarda buluşalım! 👇⚽️"

    if body_text:
        caption = (
            f"🚨 {title}\n\n"
            f"📰 {body_text}\n\n"
            f"{question}\n.\n.\n"
            f"#tamdoksan #futbol #süperlig #fenerbahçe #galatasaray #beşiktaş #trabzonspor #sondakika #spor #keşfet"
        )
    else:
        caption = (
            f"🚨 {title}\n\n"
            f"{question}\n.\n.\n"
            f"#tamdoksan #futbol #süperlig #fenerbahçe #galatasaray #beşiktaş #trabzonspor #sondakika #spor #keşfet"
        )
    return caption

# 7. Kısa, Net ve Vurucu 2 Satırlık Manşet Motoru (YeniAçık & Tam90 Tarzı)
def tr_upper(text):
    return text.replace("i", "İ").replace("ı", "I").replace("ğ", "Ğ").replace("ü", "Ü").replace("ş", "Ş").replace("ö", "Ö").replace("ç", "Ç").upper()

def format_football_headline(title):
    clean = re.sub(r'^(FLAŞ|SON DAKİKA|ÖZEL HABER|ÖZEL|HABER|TRANSFER|RESMİ AÇIKLAMA|RESMİ|VİDEO)\s*[:|-]\s*', '', title, flags=re.I).strip()
    clean = clean.replace('"', '').replace("'", "").replace("’", "").replace("“", "").replace("”", "").strip()
    clean = clean.rstrip('.!')
    lower = clean.lower()

    if "ronaldo" in lower and "982" in lower:
        return "CRISTIANO RONALDO", "982. GOLÜNÜ ATTI !"
    if "ronaldo" in lower:
        return "CRISTIANO RONALDO", "DURDURULAMIYOR !"
    if "lille" in lower and "galatasaray" in lower:
        return "LILLE'DEN", "CİMBOM'A KANCA !"
    if "sergen" in lower:
        return "SERGEN YALÇIN", "HAREKETE GEÇTİ !"
    if "miretti" in lower or ("beşiktaş" in lower and "sakat" in lower):
        return "BEŞİKTAŞ'TA", "SAKATlık ŞOKU !"
    if "kompany" in lower or "hastane" in lower:
        return "VINCENT KOMPANY", "HASTANEYE KALDIRILDI !"
    if "mourinho" in lower:
        return "JOSE MOURINHO", "GÜNDEMİ SARSTI !"
    if "osimhen" in lower:
        return "VICTOR OSIMHEN", "KARARINI VERDİ !"
    if "icardi" in lower:
        return "MAURO ICARDI", "GERİ DÖNÜYOR !"

    if any(k in lower for k in ["berabere", "düello", "yenişemedi"]):
        if "beşiktaş" in lower:
            return "BEŞİKTAŞ'TAN", "MÜTHİŞ DÜELLO !"
        elif "fenerbahçe" in lower:
            return "FENERBAHÇE'DEN", "MÜTHİŞ DÜELLO !"
        elif "galatasaray" in lower:
            return "GALATASARAY'DAN", "MÜTHİŞ DÜELLO !"
        return "GOL DÜELLOSU", "KAZANAN ÇIKMADI !"

    if any(k in lower for k in ["galip", "kazandı", "yendi", "mağlup etti", "zafer"]):
        if "beşiktaş" in lower:
            return "BEŞİKTAŞ", "ZAFERE ULAŞTI !"
        elif "fenerbahçe" in lower:
            return "FENERBAHÇE", "ZAFERE ULAŞTI !"
        elif "galatasaray" in lower:
            return "GALATASARAY", "ZAFERE ULAŞTI !"
        return "KRİTİK MAÇTA", "DEV ZAFER !"

    words = [tr_upper(w) for w in clean.split() if w]
    if len(words) <= 2:
        return words[0], (words[1] + " !") if len(words) > 1 else "FLAŞ GELİŞME !"
    elif len(words) == 3:
        return f"{words[0]} {words[1]}", f"{words[2]} !"
    else:
        return f"{words[0]} {words[1]}", f"{words[2]} {words[3]} !"

# 8. Ultra 4K (2160x2700 Supersampled) Tam Doksan Tasarım Motoru
def render_tall_grunge_line(text, target_w, color_top, color_bot, font_path, seed):
    # Yüksek çözünürlüklü geçici katmanda çizip dikey 1.28x uzatarak (İsmail Yüksek / YeniAçık stili) oluşturur
    base_size = 240
    font = ImageFont.truetype(font_path, base_size)
    dummy = Image.new("RGBA", (10, 10))
    d_draw = ImageDraw.Draw(dummy)

    while base_size > 90:
        font = ImageFont.truetype(font_path, base_size)
        bbox = d_draw.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= target_w:
            break
        base_size -= 3

    bbox = d_draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad = 40

    layer_w = tw + pad * 2
    layer_h = th + pad * 2

    # 1. İnce keskin siyah dış kontur katmanı (3px)
    stroke_layer = Image.new("RGBA", (layer_w, layer_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(stroke_layer)
    ox = pad - bbox[0]
    oy = pad - bbox[1]
    for dx in range(-4, 5):
        for dy in range(-4, 5):
            if dx * dx + dy * dy <= 16:
                s_draw.text((ox + dx, oy + dy), text, font=font, fill=(0, 0, 0, 255))

    # 2. Harf maskesi ve iç dolgu
    mask = Image.new("L", (layer_w, layer_h), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.text((ox, oy), text, font=font, fill=255)

    fill_layer = Image.new("RGBA", (layer_w, layer_h), (0, 0, 0, 0))
    f_draw = ImageDraw.Draw(fill_layer)
    for y in range(layer_h):
        t = max(0.0, min(1.0, (y - pad) / max(1, th)))
        r = int(color_top[0] * (1 - t) + color_bot[0] * t)
        g = int(color_top[1] * (1 - t) + color_bot[1] * t)
        b = int(color_top[2] * (1 - t) + color_bot[2] * t)
        f_draw.line([(0, y), (layer_w, y)], fill=(r, g, b, 255))

    # 3. Harflerin içine hafif grunge / eskitme dokusu (İsmail Yüksek görselindeki gibi)
    rng = random.Random(seed)
    for _ in range(420):
        gx = rng.randint(pad, layer_w - pad)
        gy = rng.randint(pad + int(th * 0.25), pad + th)
        gw = rng.randint(2, 7)
        gh = rng.randint(2, 8)
        f_draw.rectangle([gx, gy, gx + gw, gy + gh], fill=(14, 14, 14, 215))

    textured_text = Image.new("RGBA", (layer_w, layer_h), (0, 0, 0, 0))
    textured_text.paste(fill_layer, (0, 0), mask)

    combined = Image.alpha_composite(stroke_layer, textured_text)

    # 4. Dikey 1.28x esnetme (Tam spor manşeti proporsiyonu)
    stretched_h = int(layer_h * 1.28)
    stretched = combined.resize((layer_w, stretched_h), Image.Resampling.LANCZOS)

    # 5. Yumuşak ve derin stadyum gölgesi (Gaussian Blur)
    shadow_alpha = stretched.split()[3]
    shadow_blur = shadow_alpha.filter(ImageFilter.GaussianBlur(radius=14))
    shadow_img = Image.new("RGBA", stretched.size, (0, 0, 0, 0))
    black_solid = Image.new("RGBA", stretched.size, (0, 0, 0, 235))
    shadow_img.paste(black_solid, (0, 0), shadow_blur)

    final_line = Image.new("RGBA", (stretched.width + 24, stretched.height + 24), (0, 0, 0, 0))
    final_line.paste(shadow_img, (12, 18), shadow_img)
    final_line.paste(stretched, (12, 6), stretched)
    return final_line

def generate_tam90_post(raw_image_path, title, output_path):
    # 2160 x 2700 GERÇEK 4K SUPERSAMPLED TUVAL
    W, H = 2160, 2700
    footer_h = 448  # 224px * 2 (Birebir kilitli alt şablon yüksekliği)
    photo_h = H - footer_h + 40  # Kesintisiz geçiş

    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))

    # 1. Basın Fotoğrafını 4K Netleştir ve Yerleştir
    raw_img = Image.open(raw_image_path).convert("RGBA")
    img_ratio = raw_img.width / raw_img.height
    target_ratio = W / photo_h

    if img_ratio > target_ratio:
        scale_h = photo_h
        scale_w = int(photo_h * img_ratio)
    else:
        scale_w = W
        scale_h = int(W / img_ratio)

    resized_photo = raw_img.resize((scale_w, scale_h), Image.Resampling.LANCZOS)
    left = (scale_w - W) // 2
    top = int((scale_h - photo_h) * 0.15)  # Yüz/kafa kesilmemesi için üst ağırlıklı kadraj
    cropped_photo = resized_photo.crop((left, top, left + W, top + photo_h))

    # Ultra 4K Keskinlik ve Canlılık
    rgb_photo = cropped_photo.convert("RGB")
    rgb_photo = rgb_photo.filter(ImageFilter.UnsharpMask(radius=1.8, percent=135, threshold=3))
    rgb_photo = ImageEnhance.Contrast(rgb_photo).enhance(1.08)
    rgb_photo = ImageEnhance.Color(rgb_photo).enhance(1.12)
    canvas.paste(rgb_photo.convert("RGBA"), (0, 0))

    # 2. Alt Kısma Sinematik Yumuşak Karartma Degradesi
    grad_h = 1150
    grad_y = (H - footer_h) - grad_h
    grad_col = Image.new("L", (1, grad_h))
    for y in range(grad_h):
        t = y / grad_h
        alpha = int(255 * (t ** 1.65))
        grad_col.putpixel((0, y), alpha)
    grad_mask = grad_col.resize((W, grad_h), Image.Resampling.BILINEAR)
    black_overlay = Image.new("RGBA", (W, grad_h), (0, 0, 0, 255))
    canvas.paste(black_overlay, (0, grad_y), grad_mask)

    # 3. Sol Üst TAM90 Logosu (Pürüzsüz, lekesiz)
    logo_path = Path(__file__).parent / "templates" / "tam90_logo.png"
    if logo_path.exists():
        logo_img = Image.open(logo_path).convert("RGBA")
        logo_w = 490
        logo_h = int(logo_img.height * (logo_w / logo_img.width))
        logo_resized = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
        canvas.paste(logo_resized, (52, 52), logo_resized)

    # 4. Birebir Alt Sponsor Şablonu (AYDESSA + SOSYAL MEDYA + LUSTER CAR - SES BUTONSUZ)
    footer_path = Path(__file__).parent / "templates" / "sponsors_footer.png"
    if footer_path.exists():
        footer_img = Image.open(footer_path).convert("RGBA")
        footer_resized = footer_img.resize((W, footer_h), Image.Resampling.LANCZOS)
        canvas.paste(footer_resized, (0, H - footer_h), footer_resized)

    # 5. Uzun, Tok, Grunge Spor Manşeti (Anton-Regular + 1.28x Dikey Stretch)
    line1, line2 = format_football_headline(title)
    font_path = str(Path(__file__).parent / "templates" / "Anton-Regular.ttf")

    line1_img = render_tall_grunge_line(line1, 1940, (255, 255, 255), (235, 235, 235), font_path, 101)
    line2_img = render_tall_grunge_line(line2, 1940, (255, 212, 0), (255, 180, 0), font_path, 202)

    # Alt şablonun hemen üstüne sıkıca istifle
    overlap_gap = -38
    total_h = line1_img.height + line2_img.height + overlap_gap
    y_start = (H - footer_h - 10) - total_h

    x1 = (W - line1_img.width) // 2
    x2 = (W - line2_img.width) // 2

    canvas.paste(line1_img, (x1, y_start), line1_img)
    canvas.paste(line2_img, (x2, y_start + line1_img.height + overlap_gap), line2_img)

    final_rgb = canvas.convert("RGB")
    final_rgb.save(output_path, "JPEG", quality=98, subsampling=0)
    log(f"✨ 2160x2700 Ultra 4K Tam Doksan görseli hazırlandı: {output_path}")

# 9. Futbol Sayfasına Özel Viral Müzik
def get_viral_football_track():
    queries = ["drill beat", "turkce drill", "football phonk", "stadium anthem", "hype drill"]
    query = random.choice(queries)
    try:
        log(f"Futbol için viral müzik taranıyor: '{query}'...")
        tracks = cl.search_music(query)
        if tracks and len(tracks) > 0:
            track = random.choice(tracks)
            log(f"🔥 Seçilen futbol müziği: '{track.title}' - {track.subtitle}")
            return track
    except Exception as e:
        log(f"Müzik arama uyarısı: {e}")
    return None

# 10. Gönderi Paylaşım Fonksiyonu
def execute_approved_post():
    log("Onaylanan 4K Ronaldo görseli paylaşılıyor...")
    approved_path = Path(__file__).parent / "templates" / "approved_ronaldo_4k.jpg"
    if not approved_path.exists():
        log("Hata: approved_ronaldo_4k.jpg bulunamadı!")
        return

    title = "Cristiano Ronaldo durdurulamıyor! 982. golünü attı"
    summary = (
        "Suudi Arabistan Pro Ligi'nde Al-Nassr forması giyen Portekizli dünya yıldızı Cristiano Ronaldo, "
        "takımının galibiyetinde başrol oynayarak kariyerinin 982. golüne imza attı ve 1000 gol hedefine bir adım daha yaklaştı."
    )
    save_posted_title(title)
    caption = generate_smart_caption(title, summary)

    if login_instagram():
        uploaded = False
        try:
            track = get_viral_football_track()
            if track:
                log(f"Onaylı 4K görsel '{track.title}' müziğiyle yükleniyor...")
                media = cl.photo_upload_with_music(approved_path, caption=caption, track=track)
                log(f"🎉🎉 HARİKA! Müzikli 4K gönderi yayında: https://www.instagram.com/p/{media.code}/")
                uploaded = True
        except Exception as music_err:
            log(f"Müzikli yükleme atlandı ({music_err}), standart 4K yükleniyor...")

        if not uploaded:
            try:
                media = cl.photo_upload(approved_path, caption)
                log(f"🎉🎉 BAŞARILI! 4K gönderi yayında: https://www.instagram.com/p/{media.code}/")
            except Exception as e:
                log(f"Upload hatası: {type(e).__name__} - {e}")

def execute_post(two_factor_code=None):
    log("Viral gönderi süreci başladı...")
    title, summary, img_url = get_live_headline_and_photo()
    log(f"Seçilen haber: {title}")

    raw_path = Path(__file__).parent / "temp_raw.jpg"
    final_path = Path(__file__).parent / "temp_post_ready.jpg"

    try:
        r = requests.get(img_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        with open(raw_path, "wb") as f:
            f.write(r.content)
    except Exception as e:
        log(f"Görsel indirme hatası: {e}")
        return

    generate_tam90_post(raw_path, title, final_path)
    caption = generate_smart_caption(title, summary)

    if login_instagram(two_factor_code):
        uploaded = False

        # 1. Kaliteli Futbol/Drill Müziği ile Yükleme
        try:
            track = get_viral_football_track()
            if track:
                log(f"Gönderi '{track.title}' müziğiyle Instagram'a yükleniyor...")
                media = cl.photo_upload_with_music(
                    final_path,
                    caption=caption,
                    track=track
                )
                log(f"🎉🎉 HARİKA! Müzikli gönderi Instagram'da yayında: https://www.instagram.com/p/{media.code}/")
                uploaded = True
        except Exception as music_err:
            log(f"Müzikli yükleme atlandı ({music_err}), standart 4K yüklemeye geçiliyor...")

        # 2. Standart 4K Yükleme
        if not uploaded:
            try:
                log("Fotoğraf Instagram'a yükleniyor...")
                media = cl.photo_upload(final_path, caption)
                log(f"🎉🎉 BAŞARILI! Gönderi Instagram'da yayında: https://www.instagram.com/p/{media.code}/")
            except Exception as e:
                log(f"Upload hatası: {type(e).__name__} - {e}")
    else:
        log("Giriş yapılamadığı için görsel yüklenemedi.")

# 11. 7/24 Kesintisiz Döngü (10:00, 12:00, 15:00, 17:00, 20:00, 22:00, 00:00)
if __name__ == "__main__":
    threading.Thread(target=lambda: socketserver.TCPServer(("", PORT), HealthHandler).serve_forever(), daemon=True).start()
    log(f"Web sunucusu {PORT} portunda dinliyor...")

    TARGET_HOURS = [10, 12, 15, 17, 20, 22, 0]
    posted_today = set()

    while True:
        now = time.localtime(time.time() + 3 * 3600)  # Türkiye Saati (UTC+3)
        hour = now.tm_hour
        minute = now.tm_min
        slot_key = f"{now.tm_year}-{now.tm_yday}_{hour}"

        if hour in TARGET_HOURS and minute == 0 and slot_key not in posted_today:
            posted_today.add(slot_key)
            try:
                execute_post()
            except Exception as e:
                log(f"Zamanlanmış paylaşım hatası: {e}")

        if hour == 0 and minute == 5:
            posted_today.clear()

        time.sleep(30)
