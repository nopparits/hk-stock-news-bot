import os
import time
import requests
import feedparser
from datetime import datetime

# --- 1. ตั้งค่า Configuration (ควรเก็บใน Environment Variable ในขั้น Production) ---
TELEGRAM_BOT_TOKEN = "ใส่_TOKEN_BOT_ของคุณ"
TELEGRAM_CHAT_ID = "ใส่_CHAT_ID_ของคุณ"
HF_API_TOKEN = "ใส่_HuggingFace_TOKEN_ของคุณ"

# URL RSS ข่าวหุ้นฮ่องกง (ตัวอย่างจาก Yahoo Finance)
RSS_URL = "https://finance.yahoo.com/news/rssindex?region=HK"

# --- 2. ฟังก์ชันส่งข้อความเข้า Telegram ---
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload)
        print("✅ ส่งแจ้งเตือนสำเร็จ")
    except Exception as e:
        print(f"❌ ส่งแจ้งเตือนล้มเหลว: {e}")

# --- 3. ฟังก์ชันวิเคราะห์ Sentiment ด้วย Hugging Face API ---
def analyze_sentiment(text):
    # ใช้โมเดล FinBERT หรือ Chinese BERT ผ่าน API
    # ที่นี่ใช้โมเดลภาษาอังกฤษสำหรับตัวอย่าง หากข่าวเป็นจีนต้องเปลี่ยนโมเดล
    API_URL = "https://api-inference.huggingface.co/models/prosusai/finbert"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    
    # ตัดข้อความให้สั้นลงเพื่อประหยัด Token
    short_text = text[:500] 
    
    response = requests.post(API_URL, headers=headers, json={"inputs": short_text})
    try:
        result = response.json()[0]
        label = result['label'] # POSITIVE / NEGATIVE / NEUTRAL
        score = result['score']
        return label, score
    except:
        return "ERROR", 0

# --- 4. ฟังก์ชันหลักดึงข่าวและกรอง ---
def fetch_and_process_news():
    print(f"🕒 เริ่มทำงานเมื่อ: {datetime.now()}")
    feed = feedparser.parse(RSS_URL)
    
    for entry in feed.entries[:5]: # ทดสอบแค่ 5 ข่าวล่าสุด
        title = entry.title
        link = entry.link
        published = entry.published
        
        # ตรวจสอบว่าเคยส่งข่าวนี้หรือยัง (ใน MVP ใช้วิธีง่ายๆ คือส่งหมดแล้วค่อยทำระบบเก็บ ID Later)
        # เพื่อป้องกัน Spam ใน MVP เราอาจจะกรองคำก่อน
        
        keywords = ["Hang Seng", "China", "Hong Kong", "Stock", "Market", "Tech"]
        if not any(k.lower() in title.lower() for k in keywords):
            continue # ข้ามข่าวที่ไม่เกี่ยวข้อง
            
        print(f"📰 พบข่าว: {title}")
        
        # วิเคราะห์ Sentiment
        sentiment, score = analyze_sentiment(title)
        
        # เกณฑ์กรอง MVP: ถ้าเป็น POSITIVE หรือ NEGATIVE และคะแนนความมั่นใจ > 0.7
        if sentiment in ["POSITIVE", "NEGATIVE"] and score > 0.7:
            emoji = "🟢" if sentiment == "POSITIVE" else "🔴"
            message = f"""
{emoji} <b>ข่าวสำคัญตลาดหุ้นจีน/ฮ่องกง</b>
📰 <b>{title}</b>
📊 Sentiment: {sentiment} ({score:.2f})
⏰ เวลา: {published}
🔗 <a href="{link}">อ่านเพิ่มเติม</a>
            """
            send_telegram_message(message)
        else:
            print(f"⚪ ข่าวไม่สำคัญพอ (Sentiment: {sentiment}, Score: {score})")

# --- 5. รันโปรแกรม ---
if __name__ == "__main__":
    fetch_and_process_news()