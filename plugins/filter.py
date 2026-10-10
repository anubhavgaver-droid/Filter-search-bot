from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@Client.on_message(filters.command("filter") & filters.group)
async def custom_filter_command(client, message):
    # Usage: /filter Button Name - https://t.me/link
    text_parts = message.text.split(maxsplit=1)
    if len(text_parts) < 2:
        await message.reply_text("⚠️ Correct format:\n`/filter <Button Name> - <URL>`")
        return
    
    data = text_parts[1].split("-")
    if len(data) < 2:
        await message.reply_text("⚠️ Please separate the button name and link with a hyphen (-).")
        return

    btn_text = data[0].strip()
    btn_link = data[1].strip()

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text=btn_text, url=btn_link)]])
    await message.reply_text(f"📌 Here is your custom button:", reply_markup=keyboard)
