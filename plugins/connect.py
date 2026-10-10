import re
from pyrogram import Client, filters
from database import set_channel_id, get_channel_id, save_story
from config import ADMIN_IDS

# Connect Channel Command (Admin Only)
@Client.on_message(filters.command("connect") & filters.private)
async def connect_channel(client, message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized to use this command.")
        return

    try:
        args = message.text.split()
        if len(args) < 2:
            await message.reply_text("❌ Please provide the channel ID. Example: `/connect -100123456789`")
            return
        channel_id = int(args[1])
        await set_channel_id(channel_id)
        await message.reply_text(f"✅ Channel connected successfully!\nID: `{channel_id}`")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# Index Command (Admin Only)
@Client.on_message(filters.command("index") & filters.private)
async def index_channel_messages(client, message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized to use this command.")
        return

    channel_id = await get_channel_id()
    if not channel_id:
        await message.reply_text("❌ Please connect a channel first using `/connect <channel_id>`.")
        return

    status_msg = await message.reply_text("⏳ Indexing started, please wait...")
    count = 0
    
    try:
        async for msg in client.get_chat_history(channel_id):
            caption = msg.caption or msg.text
            if caption:
                # Regex matching your specific format: 'Story : [Name]' and before 'Status :'
                match = re.search(r"Story\s*:\s*(.*?)\s*(?=Status\s*:|$)", caption, re.IGNORECASE | re.DOTALL)
                if match:
                    title = match.group(1).strip()
                    story_data = {
                        "message_id": msg.id,
                        "chat_id": msg.chat.id,
                        "title": title,
                        "link": msg.link
                    }
                    await save_story(story_data)
                    count += 1
        
        await status_msg.edit_text(f"✅ Indexing completed! Total **{count}** stories indexed.")
    except Exception as e:
        await status_msg.edit_text(f"❌ Error during indexing: {e}")

# Auto-index new messages in the connected channel
@Client.on_message(filters.channel)
async def auto_index_new_post(client, message):
    channel_id = await get_channel_id()
    if channel_id and message.chat.id == channel_id:
        caption = message.caption or message.text
        if caption:
            match = re.search(r"Story\s*:\s*(.*?)\s*(?=Status\s*:|$)", caption, re.IGNORECASE | re.DOTALL)
            if match:
                title = match.group(1).strip()
                story_data = {
                    "message_id": message.id,
                    "chat_id": message.chat.id,
                    "title": title,
                    "link": message.link
                }
                await save_story(story_data)
