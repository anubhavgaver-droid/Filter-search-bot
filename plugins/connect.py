import re
import time
import asyncio
from pyrogram import Client, filters
from database import add_connected_channel, remove_connected_channel, get_connected_channels, save_story, stories_col
from config import ADMIN_IDS

def clean_story_title(raw_title: str) -> str:
    if not raw_title:
        return ""
    emoji_pattern = re.compile(
        r"["
        r"\U0001F600-\U0001F64F"
        r"\U0001F300-\U0001F5FF"
        r"\U0001F680-\U0001F6FF"
        r"\U0001F1E0-\U0001F1FF"
        r"\u2600-\u26FF"
        r"\u2700-\u27BF"
        r"\U0001F900-\U0001F9FF"
        r"\U0001FA70-\U0001FAFF"
        r"\u200d"
        r"\ufe0f"
        r"]+", 
        flags=re.UNICODE
    )
    return emoji_pattern.sub("", raw_title).strip()

# Connect a channel: /connect -100xxxxxxxxxx
@Client.on_message(filters.command("connect") & filters.private)
async def connect_channel(client, message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return

    try:
        args = message.text.split()
        if len(args) < 2:
            await message.reply_text("❌ Provide channel ID. Example: `/connect -100123456789`")
            return
        channel_id = int(args[1])
        await add_connected_channel(channel_id)
        await message.reply_text(f"✅ Channel added to connected list!\nID: `{channel_id}`")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# Disconnect a channel: /disconnect -100xxxxxxxxxx
@Client.on_message(filters.command("disconnect") & filters.private)
async def disconnect_channel(client, message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return

    try:
        args = message.text.split()
        if len(args) < 2:
            await message.reply_text("❌ Provide channel ID to remove.")
            return
        channel_id = int(args[1])
        await remove_connected_channel(channel_id)
        await message.reply_text(f"🗑️ Channel ID `{channel_id}` removed from connected list.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# List all connected channels: /channels
@Client.on_message(filters.command("channels") & filters.private)
async def list_connected_channels(client, message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return

    channels = await get_connected_channels()
    if not channels:
        await message.reply_text("📭 No channels connected yet.")
        return

    text = "📡 **Connected Channels List:**\n\n"
    for cid in channels:
        text += f"• `{cid}`\n"
    await message.reply_text(text)

# Batch Indexing: /index <channel_id> <start_link> <end_link>
@Client.on_message(filters.command("index") & filters.private)
async def index_channel_messages(client, message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return

    args = message.text.split()
    if len(args) < 4:
        await message.reply_text(
            "⚠️ **Incorrect Format!**\n\n"
            "Use: `/index <channel_id> <start_link> <end_link>`\n"
            "Example: `/index -10012345 https://t.me/c/12345/1 https://t.me/c/12345/100`"
        )
        return

    try:
        channel_id = int(args[1])
        start_link = args[2]
        end_link = args[3]

        start_id = int(start_link.split("/")[-1])
        end_id = int(end_link.split("/")[-1])

        if start_id > end_id:
            start_id, end_id = end_id, start_id

        total_messages = (end_id - start_id) + 1
        status_msg = await message.reply_text(f"🚀 Indexing started for channel `{channel_id}`... Total: {total_messages}")

        start_time = time.time()
        success_count = 0
        failed_count = 0
        missing_count = 0

        chunk_size = 50
        message_ids = list(range(start_id, end_id + 1))
        processed = 0

        for i in range(0, len(message_ids), chunk_size):
            chunk = message_ids[i:i + chunk_size]
            try:
                messages = await client.get_messages(channel_id, chunk)
                for msg in messages:
                    processed += 1
                    if msg is None:
                        missing_count += 1
                        continue

                    caption = msg.caption or msg.text
                    if caption:
                        match = re.search(r"Story\s*:\s*(.*?)\s*(?=Status\s*:|$)", caption, re.IGNORECASE | re.DOTALL)
                        if match:
                            clean_title = clean_story_title(match.group(1).strip())
                            if clean_title:
                                await save_story({
                                    "message_id": msg.id,
                                    "chat_id": msg.chat.id,
                                    "title": clean_title,
                                    "link": msg.link
                                })
                                success_count += 1
                            else:
                                failed_count += 1
                        else:
                            failed_count += 1
                    else:
                        missing_count += 1

                await asyncio.sleep(1)
            except Exception:
                continue

        await status_msg.edit_text(
            f"🎉 **Indexing Completed!**\n"
            f"✅ Indexed: `{success_count}`\n"
            f"⚠️ Mismatch: `{failed_count}`\n"
            f"❌ Missing: `{missing_count}`"
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# Clear all indexed stories: /clearall
@Client.on_message(filters.command("clearall") & filters.private)
async def clear_all_indexed_stories(client, message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return

    result = await stories_col.delete_many({})
    await message.reply_text(f"🗑️ Cleared `{result.deleted_count}` indexed stories from database.")

# Auto-index new posts from ALL connected channels automatically
@Client.on_message(filters.channel)
async def auto_index_new_post(client, message):
    connected_channels = await get_connected_channels()
    if message.chat.id in connected_channels:
        caption = message.caption or message.text
        if caption:
            match = re.search(r"Story\s*:\s*(.*?)\s*(?=Status\s*:|$)", caption, re.IGNORECASE | re.DOTALL)
            if match:
                clean_title = clean_story_title(match.group(1).strip())
                if clean_title:
                    await save_story({
                        "message_id": message.id,
                        "chat_id": message.chat.id,
                        "title": clean_title,
                        "link": message.link
                    })
