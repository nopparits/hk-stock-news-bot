import os
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print(f"🔍 Testing with Token: {TOKEN[:10]}... and Chat ID: {CHAT_ID}")

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": "✅ <b>Test Successful!</b>\nBot เชื่อมต่อ GitHub Actions เรียบร้อยแล้ว 🎉",
    "parse_mode": "HTML"
}

response = requests.post(url, json=payload, timeout=30)
print(f"📡 Response Status: {response.status_code}")
print(f"📦 Response Body: {response.text}")

if response.status_code == 200:
    print("🎉 ส่งข้อความสำเร็จ!")
else:
    print("❌ ส่งข้อความล้มเหลว")