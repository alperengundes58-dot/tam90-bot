import os
import sys
import time
import json
import random
import re
import threading
import http.server
import socketserver
from pathlib import Path

import requests
import feedparser
from PIL import Image, ImageDraw, ImageFont
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, ChallengeRequired

# 1. 7/24 Web Sunucusu (Render Sağlık Kontrolü İçin)
PORT = int(os.environ.get("PORT", 3000))

class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("⚽️ TAM DOKSAN (@tamdoksanaresmi) 7/24 Python Bulut Motoru Aktif!".encode("utf-8"))

def start_server():
    with socketserver.TCPServer(("", PORT), HealthHandler) as httpd:
        print(f"[Render] Web sunucusu {PORT} portunda dinliyor...")
        httpd.serve_forever()

threading.Thread(target=start_server, daemon=True).start()

# 2. Instagram İstemcisi
IG_USERNAME = os.environ.get("IG_USERNAME", "tamdoksanaresmi")
IG_PASSWORD = os.environ.get("IG_PASSWORD", "alperenseyit10")
SESSION_FILE = Path(__file__).parent / "session.json"

cl = Client()
cl.delay_range = [1, 3]

def login_instagram():
    print(f"[Instagram] @{IG_USERNAME} hesabına bağlanılıyor...")
    
    if SESSION_FILE.exists():
        try:
            cl.load_settings(SESSION_FILE)
            cl.login(IG_USERNAME, IG_PASSWORD)
            print("Kayıtlı oturum başarıyla yüklendi!")
            return True
        except Exception as e:
            print(f"Kayıtlı oturum geçersiz ({e}), sıfırdan deneniyor...")

    try:
        cl.login(IG_USERNAME, IG_PASSWORD)
        cl.dump_settings(SESSION_FILE)
        print("Giriş başarılı ve oturum kaydedildi!")
        return True
    except TwoFactorRequired:
        print("2FA Kodu gerekiyor. Oturum için yedek kod veya SMS girilmeli.")
        return False
    except Exception as e:
        print(f"Giriş hatası: {e}")
        return False

# 3. Canlı Haber Çekici (Fotomaç, Fanatik, NTV Spor)
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
                
                # Fotoğrafı bul
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
                    return title, img_url
        except Exception as e:
            print(f"RSS okuma hatası ({url}): {e}")
            
    return "Barış Alper Yılmaz İçin Avrupa Devi Devrede!", "https://iaftm.tmgrup.com.tr/91a580/1200/675/0/0/1320/742?u=https://iftm.tmgrup.com.tr/2025/05/31/baris-alper-yilmazin-babasindan-flas-transfer-aciklamasi-1748678696062.jpg"

# 4. Tam Doksan Orijinal Görsel Tasarım Motoru (Pillow ile %100 Kusursuz)
def generate_tam90_post(raw_image_path, title, output_path):
    canvas_w, canvas_h = 825, 1024
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 255))
    
    # 1. Gerçek Basın Fotoğrafı
    raw_img = Image.open(raw_image_path).convert("RGBA")
    
    # Oranları koruyarak 825x720 alanına sığdır / kırp
    target_h = 720
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
    
    # Alt degrade (gradient)
    gradient = Image.new('L', (canvas_w, 350))
    for y in range(350):
        alpha = int(255 * (y / 350) ** 1.5)
        for x in range(canvas_w):
            gradient.putpixel((x, y), alpha)
            
    black_layer = Image.new('RGBA', (canvas_w, 350), (0, 0, 0, 255))
    canvas.paste(black_layer, (0, 370), gradient)
    
    # Alt kısmı tamamen siyah yap
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 720, canvas_w, canvas_h], fill=(0, 0, 0, 255))
    
    # 2. Sol Üst Şeffaf TAM90 Logosu
    logo_path = Path(__file__).parent / "templates" / "tam90_logo.png"
    if logo_path.exists():
        logo_img = Image.open(logo_path).convert("RGBA")
        logo_w = int(canvas_w * 0.28)
        logo_h = int(logo_img.height * (logo_w / logo_img.width))
        logo_resized = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
        canvas.paste(logo_resized, (15, 15), logo_resized)
        
    # 3. Alt Sponsorlar ve Sosyal Medya Barı
    footer_path = Path(__file__).parent / "templates" / "sponsors_footer.png"
    if footer_path.exists():
        footer_img = Image.open(footer_path).convert("RGBA")
        footer_h = int(canvas_h * 0.16)
        footer_resized = footer_img.resize((canvas_w, footer_h), Image.Resampling.LANCZOS)
        canvas.paste(footer_resized, (0, canvas_h - footer_h), footer_resized)
        
    # 4. Fırçasız Net Tok Büyük Manşet
    clean_title = re.sub(r'^(FLAŞ|SON DAKİKA|ÖZEL|HABER|TRANSFER|RESMİ)\s*[:|-]\s*', '', title, flags=re.I).strip()
    words = clean_title.split()
    mid = max(1, len(words) // 2)
    line1 = " ".join(words[:mid]).upper()
    line2 = (" ".join(words[mid:]) + " !").upper()
    
    # Font bul veya varsayılan font
    font = None
    try:
        font = ImageFont.truetype("arialbd.ttf", 68)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
        except:
            font = ImageFont.load_default()
            
    # Yazıları çiz (Gölge + Net Yazı)
    y_pos = 650
    for line, color in [(line1, (255, 255, 255)), (line2, (255, 204, 0))]:
        # Metin genişliği
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x_pos = (canvas_w - text_w) // 2
        
        # Siyah gölge (3D tok etki)
        for offset_x, offset_y in [(-2, -2), (2, -2), (-2, 2), (2, 2), (0, 3)]:
            draw.text((x_pos + offset_x, y_pos + offset_y), line, font=font, fill=(0, 0, 0, 255))
            
        draw.text((x_pos, y_pos), line, font=font, fill=color)
        y_pos += 80
        
    final_rgb = canvas.convert("RGB")
    final_rgb.save(output_path, "JPEG", quality=95)
    print(f"Orijinal Tam Doksan görseli hazırlandı: {output_path}")

# 5. Gönderi Paylaşma Fonksiyonu
def execute_post():
    print("\n[Gönderi Hazırlığı Başladı]")
    title, img_url = get_live_headline_and_photo()
    print(f"Haber: {title}")
    
    # Basın fotoğrafını indir
    raw_path = Path(__file__).parent / "temp_raw.jpg"
    final_path = Path(__file__).parent / "temp_post_ready.jpg"
    
    res = requests.get(img_url, timeout=15)
    with open(raw_path, "wb") as f:
        f.write(res.content)
        
    # Orijinal şablonu bas
    generate_tam90_post(raw_path, title, final_path)
    
    # Açıklama
    caption = (
        f"🚨 {title}\n\n"
        f"Süper Lig'de ve Avrupa'da sıcak gelişmeler devam ediyor. Detaylar geldikçe aktaracağız.\n\n"
        f"👉 Sizce bu karar doğru mu? Fikirlerinizi yorumlarda paylaşın! 👇⚽️\n.\n.\n"
        f"#tamdoksan #futbol #süperlig #fenerbahçe #galatasaray #beşiktaş #trabzonspor #transfer #haber"
    )
    
    if login_instagram():
        print("Instagram'a görsel yükleniyor...")
        try:
            media = cl.photo_upload(final_path, caption)
            print(f"🎉 BAŞARILI! Gönderi paylaşıldı: https://www.instagram.com/p/{media.code}/")
        except Exception as e:
            print(f"Paylaşım hatası: {e}")

# İlk açılışta hemen bir test gönderisi paylaş
print("🚀 Tam Doksan Botu Başlatıldı! İlk örnek gönderi gönderiliyor...")
try:
    execute_post()
except Exception as e:
    print(f"İlk gönderi hatası: {e}")

# 6. 7/24 Zamanlayıcı (10:00, 12:00, 15:00, 17:00, 20:00, 22:00, 00:00)
TARGET_HOURS = [10, 12, 15, 17, 20, 22, 0]
posted_today = set()

while True:
    now = time.localtime(time.time() + 3 * 3600) # UTC+3 Türkiye
    hour = now.tm_hour
    minute = now.tm_min
    slot_key = f"{now.tm_year}-{now.tm_yday}_{hour}"
    
    if hour in TARGET_HOURS and minute == 0 and slot_key not in posted_today:
        posted_today.add(slot_key)
        try:
            execute_post()
        except Exception as e:
            print(f"Zamanlanmış gönderi hatası: {e}")
            
    if hour == 0 and minute == 5:
        posted_today.clear()
        
    time.sleep(30)
