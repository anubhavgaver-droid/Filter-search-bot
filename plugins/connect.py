import re
from pyrogram import Client, filters
from database import set_channel_id, get_channel_id, save_story
from config import ADMIN_IDS

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

# Index Command using Message Links Range (First link to Last link)
@Client.on_message(filters.command("index") & filters.private)
async def index_channel_messages(client, message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized to use this command.")
        return

    channel_id = await get_channel_id()
    if not channel_id:
        await message.reply_text("❌ Please connect a channel first using `/connect <channel_id>`.")
        return

    args = message.text.split()
    if len(args) < 3:
        await message.reply_text(
            "⚠️ **Incorrect Format!**\n\n"
            "Please provide the start message link and end message link like this:\n"
            "`/index https://t.me/c/xxxxx/100 https://t.me/c/xxxxx/500`"
        )
        return

    try:
        # Extract message IDs from the Telegram links provided by the admin
        start_link = args[1]
        end_link = args[2]

        start_id = int(start_link.split("/")[-1])
        end_id = int(end_link.split("/")[-1])

        if start_id > end_id:
            start_id, end_id = end_id, start_id

        status_msg = await message.reply_text(f"⏳ Indexing messages from ID {start_id} to {end_id}, please wait...")
        count = 0

        # Fetch messages in batches/range using get_messages
        # Telegram allows fetching individual or ranges of message IDs when the bot is an admin
        message_ids = list(range(start_id, end_id + 1))
        
        # Process in chunks to avoid overload
        chunk_size = 100
        for i in range(0, len(message_ids), chunk_size):
            chunk = message_ids[i:i + chunk_size]
            messages = await client.get_messages(channel_id, chunk)
            
            for msg in messages:
                if msg and (msg.caption or msg.text):
                    caption = msg.caption or msg.text
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

        await status_msg.edit_text(f"✅ Old messages indexing completed! Total **{count}** stories indexed from the given range.")
    
    except Exception as e:
        await status_msg.edit_text(f"❌ Error during indexing: `{e}`\n\n💡 Make sure the bot is an **Administrator** in the channel and the links are correct!")

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
