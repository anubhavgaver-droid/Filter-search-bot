import asyncio
from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN
from web_server import start_web_server

app = Client(
    "advanced_story_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins")
)

async def main():
    # Start the Aiohttp web server for Render port binding
    await start_web_server()
    # Start the Pyrogram bot
    await app.start()
    print("🤖 Bot is successfully running and connected!")
    await asyncio.gather(*(asyncio.Event().wait(),))

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
