from aiohttp import web
from config import PORT

async def handle(request):
    return web.Response(text="🤖 Bot is active and running successfully on Render!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Web server started on port {PORT}")
