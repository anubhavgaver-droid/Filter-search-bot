from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import save_custom_filter
from config import ADMIN_IDS

@Client.on_message(filters.command("filter") & filters.private)
async def add_custom_filter(client, message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized to use this command.")
        return

    # Usage: /filter Story Name - https://t.me/link
    text_parts = message.text.split(maxsplit=1)
    if len(text_parts) < 2:
        await message.reply_text(
            "⚠️ **Incorrect Format!**\n\n"
            "Please use this format:\n"
            "`/filter Story Name - https://t.me/your_link`"
        )
        return
    
    data = text_parts[1].split("-")
    if len(data) < 2:
        await message.reply_text("⚠️ Please separate the story name and link with a hyphen (-).")
        return

    title = data[0].strip()
    link = data[1].strip()

    # Save to database
    await save_custom_filter(title, link)

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text=title, url=link)]])
    await message.reply_text(
        f"✅ **Custom filter added successfully!**\n\n"
        f"📌 **Title:** `{title}`\n"
        f"🔗 **Link:** `{link}`",
        reply_markup=keyboard
    )
