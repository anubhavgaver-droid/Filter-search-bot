import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    text = (
        "✨ **Welcome to Story Search Bot!** 🎬\n\n"
        "Send me any story name, and I will find it for you from the connected channel.\n"
        "Admins can use `/connect <channel_id>` and `/index` to setup."
    )
    await message.reply_text(text)

@Client.on_message(filters.new_chat_members)
async def welcome_new_user(client: Client, message: Message):
    for member in message.new_chat_members:
        welcome_text = (
            f"🎉 Welcome to the group, {member.mention}! 💎\n"
            f"Enjoy your stay and search your favorite stories anytime."
        )
        sent_msg = await message.reply_text(welcome_text)
        asyncio.create_task(delete_msg_after_delay(sent_msg, 300))

async def delete_msg_after_delay(message: Message, delay: int):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass
