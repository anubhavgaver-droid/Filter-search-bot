import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# यहाँ अपनी चैनल और ग्रुप/बोट की लिंक डाल दें
CHANNEL_LINK = "https://t.me/freestoryhubMR"  # आपके स्टोरी चैनल की लिंक
GROUP_LINK = "https://t.me/pratilipifm0900"      # आपके डिस्कशन/सर्च ग्रुप की लिंक

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    welcome_text = (
        "✨ **Welcome to our Official Filter Bot!** 🎬\n\n"
        "You can use this bot in our official group to search for any story instantly.\n\n"
        "👇 Join our channel and group using the buttons below:"
    )
    
    # इनलाइन बटन (चैनल और ग्रुप/बोट लिंक के साथ)
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_LINK),
            InlineKeyboardButton(text="💬 Join Group", url=GROUP_LINK)
        ]
    ])
    
    sent_msg = await message.reply_text(welcome_text, reply_markup=keyboard)
    
    # वेलकम मैसेज को भी 10 मिनट (600 सेकंड्स) बाद ऑटो-डिलिट करने के लिए (वैकल्पिक)
    asyncio.create_task(delete_msg_after_delay(sent_msg, 600))

@Client.on_message(filters.new_chat_members)
async def welcome_new_user(client: Client, message: Message):
    for member in message.new_chat_members:
        welcome_text = (
            f"🎉 Welcome to the group, {member.mention}! 💎\n"
            f"Send any story name here to search instantly."
        )
        sent_msg = await message.reply_text(welcome_text)
        asyncio.create_task(delete_msg_after_delay(sent_msg, 300))

async def delete_msg_after_delay(message: Message, delay: int):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass
