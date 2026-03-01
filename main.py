import os
import sys
import time
import requests
import feedparser
from datetime import datetime

# --- 1. ตั้งค่า Configuration (อ่านจาก Environment Variables) ---
# GitHub Actions จะส่งค่าเหล่านี้มาให้ผ่าน env: ในไฟล์ yml
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

# ตรวจสอบว่าได้รับ Token ครบหรือไม่ (สำคัญมากสำหรับ Debug)
if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, HF_API_TOKEN]):
    print("❌ Error: Missing Environment Variables. Please check GitHub Secrets.")
    sys.exit(1)

# URL RSS ข่าวหุ้นฮ่องกง (แก้ไข: ลบช่องว่างท้ายประโยคออก)
RSS_URL = "https://finance.yahoo.com/news/rssindex?region=HK"

# --- 2. ฟังก์ชันส่งข้อความเข้า Telegram ---
def send_telegram_message(message):
    # แก้ไข: ลบช่องว่างหลังคำว่า bot ออก และใช้ f-string ให้ถูกต้อง
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        # แก้ไข: เพิ่ม timeout และใช้ json=payload เพื่อให้ requests จัดการ encoding (UTF-8) ให้เอง
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            print("✅ ส่งแจ้งเตือนสำเร็จ")
        else:
            print(f"❌ Telegram API Error: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ ส่งแจ้งเตือนล้มเหลว: {e}")

# --- 3. ฟังก์ชันวิเคราะห์ Sentiment ด้วย Hugging Face API ---
def analyze_sentiment(text):
    # URL โมเดล FinBERT (แก้ไข: ลบช่องว่างท้ายประโยคออก)
    API_URL = "https://api-inference.huggingface.co/models/prosusai/finbert"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    
    # ตัดข้อความให้สั้นลงเพื่อประหยัด Token และป้องกัน payload ใหญ่เกิน
    short_text = text[:500] 
    
    try:
        # แก้ไข: เพิ่ม timeout และ headers
        response = requests.post(API_URL, headers=headers, json={"inputs": short_text}, timeout=30)
        result = response.json()
        
        # ตรวจสอบว่า API ส่งค่ากลับมาเป็นรูปแบบที่คาดหวัง (List)
        if isinstance(result, list) and len(result) > 0:
            label = result[0].get('label', 'UNKNOWN')
            score = result[0].get('score', 0)
            return label, score
        else:
            # กรณีโมเดลกำลังโหลด (Model Loading) API จะคืนค่าเป็น dict ที่มี key 'error'
            if isinstance(result, dict) and 'error' in result:
                print(f"⚠️ HF API Warning: {result['error']}")
            return "NEUTRAL", 0.0
            
    except requests.exceptions.Timeout:
        print("⚠️ HF API Request Timeout")
        return "NEUTRAL", 0.0
    except Exception as e:
        print(f"⚠️ Error analyzing sentiment: {e}")
        return "ERROR", 0

# --- 4. ฟังก์ชันหลักดึงข่าวและกรอง ---
def fetch_and_process_news():
    print(f"🕒 เริ่มทำงานเมื่อ: {datetime.now()}")
    
    # แก้ไข: เพิ่ม User-Agent header เพื่อป้องกันบางเว็บบล็อก request จาก script
    feed_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    feed = feedparser.parse(RSS_URL, request_headers=feed_headers)
    
    if feed.bozo:
        print(f"⚠️ Warning: มีปัญหาในการอ่าน RSS Feed: {feed.bozo_exception}")

    for entry in feed.entries[:5]: # ทดสอบแค่ 5 ข่าวล่าสุด
        title = entry.title
        link = entry.link
        published = entry.get('published', 'Unknown time')
        
        # กรองคำสำคัญ
        keywords = ["Hang Seng", "China", "Hong Kong", "Stock", "Market", "Tech"]
        if not any(k.lower() in title.lower() for k in keywords):
            continue 
            
        print(f"📰 พบข่าว: {title}")
        
        # วิเคราะห์ Sentiment
        sentiment, score = analyze_sentiment(title)
        
        # เกณฑ์กรอง MVP: ถ้าเป็น POSITIVE หรือ NEGATIVE และคะแนนความมั่นใจ > 0.7
        if sentiment in ["POSITIVE", "NEGATIVE"] and score > 0.7:
            emoji = "🟢" if sentiment == "POSITIVE" else "🔴"
            
            # จัดรูปแบบข้อความ (ใช้ f-string เพื่อจัดการ encoding ง่ายขึ้น)
            message = (
                f"{emoji} <b>ข่าวสำคัญตลาดหุ้นจีน/ฮ่องกง</b>\n"
                f"📰 <b>{title}</b>\n"
                f"📊 Sentiment: {sentiment} ({score:.2f})\n"
                f"⏰ เวลา: {published}\n"
                f"🔗 <a href=\"{link}\">อ่านเพิ่มเติม</a>"
            )
            send_telegram_message(message)
        else:
            print(f"⚪ ข้ามข่าวนี้ (Sentiment: {sentiment}, Score: {score})")

# --- 5. รันโปรแกรม ---
if __name__ == "__main__":
    fetch_and_process_news()
