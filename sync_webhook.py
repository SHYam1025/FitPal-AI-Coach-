import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# 1. Pull values from your .env
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# 2. Paste the active base URL string from your Serveo window here!
# (Ensure there is NO trailing slash at the end)
LIVE_TUNNEL_URL = "https://strong-warthog-50.loca.lt"

def register_webhook():
    if not BOT_TOKEN or "your_" in BOT_TOKEN:
        print("❌ ERROR: Please check that TELEGRAM_BOT_TOKEN is set inside your .env file!")
        return

    # Clean up any trailing slashes or hidden whitespaces from copy-pasting
    base_url = LIVE_TUNNEL_URL.strip().rstrip("/")
    webhook_endpoint = f"{base_url}/api/webhooks/telegram"
    
    telegram_api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    payload = {"url": webhook_endpoint}
    
    print(f"📡 Attempting to register webhook path: {webhook_endpoint}...")
    
    response = httpx.post(telegram_api_url, json=payload, timeout=10.0)
    
    print(f"\n📥 Telegram API Status Code: {response.status_code}")
    print(f"📝 Response Body: {response.text}")

if __name__ == "__main__":
    register_webhook()