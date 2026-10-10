import os

API_ID = int(os.getenv("API_ID", "1234567"))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")
MONGO_URL = os.getenv("MONGO_URL", "your_mongodb_connection_string")

# Render Web Server Port Binding
PORT = int(os.getenv("PORT", 8080))

# Admin Telegram User IDs (केवल ये एडमिन ही /connect और /index कमांड चला सकेंगे)
ADMIN_IDS = [5898522531]  # अपनी टेलीग्राम यूजर आईडी यहाँ डालें
