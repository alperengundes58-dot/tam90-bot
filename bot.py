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
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, ChallengeRequired

# Log Defteri
LOG_MESSAGES = []
def log(msg):
    t = time.strftime('%H:%M:%S')
    formatted = f"[{t}] {msg}"
    print(formatted)
    LOG_MESSAGES.append(formatted)
    if len(LOG_MESSAGES) > 50:
        LOG_MESSAGES.pop(0)

# 1. 7/24 Web Sunucusu (Render Sağlık & Manuel Tetikleme)
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
            self.wfile.write(json.dumps({"status": "ok", "message": "Ultra HD Viral Gönderi Tetiklendi!"}).encode("utf-8"))
            threading.Thread(target=execute_post, args=(code,)).start()
            return

        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("⚽️ TAM DOKSAN (@tamdoksanaresmi) 7/24 Ultra HD & Viral Müzikli Bulut Motoru Aktif!".encode("utf-8"))

def start_server():
    with socketserver.TCPServer(("", PORT), HealthHandler) as httpd:
        log(f"Web sunucusu {PORT} portunda dinliyor...")
        httpd.serve_forever()

threading.Thread(target=start_server, daemon=True).start()

# 2. Instagram İstemcisi
IG_USERNAME = os.environ.get("IG_USERNAME", "tamdoksanaresmi")
IG_PASSWORD = os.environ.get("IG_PASSWORD", "alperenseyit10")
SESSION_FILE = Path(__file__).parent / "session.json"

cl = Client()
cl.delay_range = [1, 2]

def login_instagram(two_factor_code=None):
    log(f"@{IG_USERNAME} için Instagram oturumu kontrol ediliyor...")

    if SESSION_FILE.exists():
        try:
            cl.load_settings(SESSION_FILE)
            cl.login(IG_USERNAME, IG_PASSWORD)
            log("Kayıtlı oturum yüklendi ve doğrulandı!")
            return True
        except Exception as e:
            log(f"Kayıtlı oturum yenileniyor: {e}")

    try:
        if two_factor_code:
            log(f"2FA Kodu ({two_factor_code}) ile giriş yapılıyor...")
            cl.login(IG_USERNAME, IG_PASSWORD, verification_code=two_factor_code)
        else:
            cl.login(IG_USERNAME, IG_PASSWORD)

        cl.dump_settings(SESSION_FILE)
        log("Giriş başarılı ve session.json kaydedildi!")
        return True
    except TwoFactorRequired:
        log("HATA: 2FA gerekiyor.")
        return False
    except Exception as e:
        log(f"Giriş hatası: {type(e).__name__} - {e}")
        return False

# 3. Yüksek Çözünürlüklü Basın Fotoğrafı Çekici
def get_live_headline_and_photo():
    sources = [
        "https://www.fotomac.com.tr/rss/anasayfa.xml",
        "https://www.aspor.com.tr/rss/anasayfa.xml",
        "https://www.ntv.com.tr/sporskor.rss"
    ]

    for url in sources:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]:
                title = entry.title
                link = entry.link
                img_url = None

                if 'enclosures' in entry and len(entry.enclosures) > 0:
                    img_url = entry.enclosures[0].get('href')

                if not img_url and link:
                    try:
                        r = requests.get(link, timeout=5)
                        m = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', r.text, re.IGNORECASE)
                        if m:
                            img_url = m.group(1)
                    except:
                        pass

                if img_url:
                    # TM Grup orijinal yüksek çözünürlüklü ham basın fotoğrafını 'u=' parametresinden çıkar
                    if "u=http" in img_url:
                        try:
                            raw_original = urllib.parse.unquote(img_url.split("u=")[1])
                            img_url = raw_original
                            log(f"Ultra HD orijinal basın fotoğrafı URL'si alındı: {img_url}")
                        except:
                            pass
                    return title, img_url
        except Exception as e:
            log(f"RSS hatası: {e}")

    return "Barış Alper Yılmaz İçin Avrupa Devi Devrede!", "https://iftm.tmgrup.com.tr/2025/05/31/baris-alper-yilmazin-babasindan-flas-transfer-aciklamasi-1748678696062.jpg"

# 4. 1080x1350 Ultra HD Tam Doksan Orijinal Tasarım Motoru
def generate_tam90_post(raw_image_path, title, output_path):
    canvas_w, canvas_h = 1080, 1350
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 255))

    # 1. Gerçek Basın Fotoğrafı
    raw_img = Image.open(raw_image_path).convert("RGBA")
    
    # Netlik ve Canlılık Artırımı (Ultra HD Etkisi)
    enhancer = ImageEnhance.Sharpness(raw_img)
    raw_img = enhancer.enhance(1.25)
    color_enhancer = ImageEnhance.Color(raw_img)
    raw_img = color_enhancer.enhance(1.08)

    target_h = 960
    img_ratio = raw_img.width / raw_img.height
    target_ratio = canvas_w / target_h

    if img_ratio > target_ratio:
        scale_h = target_h
        scale_w = int(target_h * img_ratio)
    else:
        scale_w = canvas_w
        scale_h = int(canvas_w / img_ratio)

    resized_photo = raw_img.resize((scale_w, scale_h), Image.Resampling.LANCZOS)
    left = (scale_w - canvas_w) // 2
    top = (scale_h - target_h) // 2
    cropped_photo = resized_photo.crop((left, top, left + canvas_w, top + target_h))
    canvas.paste(cropped_photo, (0, 0))

    # Alt degrade (yumuşak geçiş)
    gradient_h = 450
    gradient = Image.new('L', (canvas_w, gradient_h))
    for y in range(gradient_h):
        alpha = int(255 * (y / gradient_h) ** 1.6)
        for x in range(canvas_w):
            gradient.putpixel((x, y), alpha)
    black_layer = Image.new('RGBA', (canvas_w, gradient_h), (0, 0, 0, 255))
    canvas.paste(black_layer, (0, 510), gradient)

    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 960, canvas_w, canvas_h], fill=(0, 0, 0, 255))

    # 2. Sol Üst Şeffaf TAM90 Logosu
    logo_path = Path(__file__).parent / "templates" / "tam90_logo.png"
    if logo_path.exists():
        logo_img = Image.open(logo_path).convert("RGBA")
        logo_w = 280
        logo_h = int(logo_img.height * (logo_w / logo_img.width))
        logo_resized = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
        canvas.paste(logo_resized, (30, 30), logo_resized)

    # 3. Alt Sponsorlar Barı (Ses butonsuz, %100 temiz)
    footer_path = Path(__file__).parent / "templates" / "sponsors_footer.png"
    if footer_path.exists():
        footer_img = Image.open(footer_path).convert("RGBA")
        footer_h = 200
        footer_resized = footer_img.resize((canvas_w, footer_h), Image.Resampling.LANCZOS)
        canvas.paste(footer_resized, (0, canvas_h - footer_h), footer_resized)

    # 4. Fırçasız, Net, Tok ve Tam Sığan Tipografi Motoru
    clean_title = re.sub(r'^(FLAŞ|SON DAKİKA|ÖZEL|HABER|TRANSFER|RESMİ)\s*[:|-]\s*', '', title, flags=re.I).strip()
    words = clean_title.split()
    
    # 2 satıra böl (kısa ve vurucu)
    if len(words) > 6:
        words = words[:6] # Maksimum 6 kelimelik vurucu manşet
        
    mid = max(1, len(words) // 2)
    line1 = " ".join(words[:mid]).upper()
    line2 = (" ".join(words[mid:]) + " !").upper()

    # Otomatik Font Boyutlandırma (Genişliğe göre asla taşmaz)
    font_size = 76
    font = None
    while font_size >= 44:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("arialbd.ttf", font_size)
            except:
                font = ImageFont.load_default()
                break

        b1 = draw.textbbox((0, 0), line1, font=font)
        b2 = draw.textbbox((0, 0), line2, font=font)
        w1 = b1[2] - b1[0]
        w2 = b2[2] - b2[0]

        if max(w1, w2) <= 960:
            break
        font_size -= 4

    y_pos = 900
    for line, color in [(line1, (255, 255, 255)), (line2, (255, 204, 0))]:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x_pos = (canvas_w - text_w) // 2

        # 4px kalın siyah kontur & derin gölge
        for ox in range(-3, 4):
            for oy in range(-3, 4):
                draw.text((x_pos + ox, y_pos + oy), line, font=font, fill=(0, 0, 0, 255))
        draw.text((x_pos, y_pos), line, font=font, fill=color)
        y_pos += text_h + 20

    final_rgb = canvas.convert("RGB")
    final_rgb.save(output_path, "JPEG", quality=98)
    log(f"1080x1350 Ultra HD Tam Doksan görseli hazırlandı: {output_path}")

# 5. Gönderi ve Viral Müzik Paylaşım Fonksiyonu
def execute_post(two_factor_code=None):
    log("Viral gönderi süreci başladı...")
    title, img_url = get_live_headline_and_photo()
    log(f"Seçilen haber: {title}")

    raw_path = Path(__file__).parent / "temp_raw.jpg"
    final_path = Path(__file__).parent / "temp_post_ready.jpg"

    r = requests.get(img_url, timeout=20)
    with open(raw_path, "wb") as f:
        f.write(r.content)

    generate_tam90_post(raw_path, title, final_path)

    caption = (
        f"🚨 {title}\n\n"
        f"Süper Lig'de ve Avrupa arenasında tansiyon hiç düşmüyor! Masadaki son detaylar ve perde arkasında konuşulanlar ortaya çıktı.\n\n"
        f"👉 Sizce bu karar doğru mu? Fikirlerinizi yorumlarda paylaşın! 👇⚽️\n.\n.\n"
        f"#tamdoksan #futbol #süperlig #fenerbahçe #galatasaray #beşiktaş #trabzonspor #transfer #haber #keşfet"
    )

    if login_instagram(two_factor_code):
        uploaded = False

        # 1. Instagram Viral Trend Müzik Ekleme Denemesi
        try:
            log("Instagram trend müzikleri taranıyor...")
            music_data = cl.music_in_feed_audio_browser()
            if music_data and "items" in music_data and len(music_data["items"]) > 0:
                playlist = music_data["items"][0].get("playlist", {})
                preview_items = playlist.get("preview_items", [])
                if preview_items:
                    track = preview_items[0].get("track")
                    session_id = music_data.get("alacorn_session_id")
                    if track and session_id:
                        track_title = track.get("title", "Trend Müzik")
                        log(f"Viral trend müzik bulundu: '{track_title}'. Müzikle yükleniyor...")
                        media = cl.photo_upload_with_music(
                            final_path,
                            caption=caption,
                            track=track,
                            alacorn_session_id=session_id
                        )
                        log(f"🎉🎉 HARİKA! Müzikli gönderi Instagram'da yayında: https://www.instagram.com/p/{media.code}/")
                        uploaded = True
        except Exception as music_err:
            log(f"Müzik ekleme denenirken atlandı ({music_err}), standart yüklemeye geçiliyor...")

        # 2. Müzik eklenemediyse standart yüksek kalite fotoğraf yükle
        if not uploaded:
            try:
                log("Fotoğraf Instagram'a yükleniyor...")
                media = cl.photo_upload(final_path, caption)
                log(f"🎉🎉 BAŞARILI! Gönderi Instagram'da yayında: https://www.instagram.com/p/{media.code}/")
            except Exception as e:
                log(f"Upload hatası: {type(e).__name__} - {e}")
    else:
        log("Giriş yapılamadığı için görsel yüklenemedi.")

# 7/24 Döngü (10:00, 12:00, 15:00, 17:00, 20:00, 22:00, 00:00)
TARGET_HOURS = [10, 12, 15, 17, 20, 22, 0]
posted_today = set()

while True:
    now = time.localtime(time.time() + 3 * 3600)
    hour = now.tm_hour
    minute = now.tm_min
    slot_key = f"{now.tm_year}-{now.tm_yday}_{hour}"

    if hour in TARGET_HOURS and minute == 0 and slot_key not in posted_today:
        posted_today.add(slot_key)
        try:
            execute_post()
        except Exception as e:
            log(f"Zamanlanmış hata: {e}")

    if hour == 0 and minute == 5:
        posted_today.clear()

    time.sleep(30)
