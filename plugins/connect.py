import re
import time
import asyncio
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

# Advanced Batch Indexing Command with Live Progress & Stats
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
        start_link = args[1]
        end_link = args[2]

        start_id = int(start_link.split("/")[-1])
        end_id = int(end_link.split("/")[-1])

        if start_id > end_id:
            start_id, end_id = end_id, start_id

        total_messages = (end_id - start_id) + 1
        status_msg = await message.reply_text(
            f"🚀 **Indexing Started...**\n"
            f"📊 Total Message Range: `{total_messages}`\n"
            f"⏳ Please wait..."
        )

        start_time = time.time()
        success_count = 0
        failed_count = 0
        missing_count = 0

        chunk_size = 50  # Fetching 50 messages per batch to avoid overload
        message_ids = list(range(start_id, end_id + 1))
        processed = 0

        for i in range(0, len(message_ids), chunk_size):
            chunk = message_ids[i:i + chunk_size]
            try:
                messages = await client.get_messages(channel_id, chunk)
                
                for msg in messages:
                    processed += 1
                    if msg is None:
                        missing_count += 1  # Deleted or missing message
                        continue

                    caption = msg.caption or msg.text
                    if caption:
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
                            success_count += 1
                        else:
                            failed_count += 1  # Format did not match
                    else:
                        missing_count += 1  # No text/caption available

                # Update live status after each batch
                elapsed_time = time.time() - start_time
                percent = (processed / total_messages) * 100
                
                await status_msg.edit_text(
                    f"⏳ **Indexing in Progress... ({percent:.1f}%)**\n\n"
                    f"📦 Processed: `{processed}/{total_messages}`\n"
                    f"✅ Successful (Indexed): `{success_count}`\n"
                    f"⚠️ Format Mismatch: `{failed_count}`\n"
                    f"❌ Missing / Deleted: `{missing_count}`\n"
                    f"⏱️ Elapsed Time: `{int(elapsed_time)} seconds`"
                )
                
                await asyncio.sleep(1) # Small delay to prevent Telegram FloodWait

            except Exception as batch_err:
                print(f"Batch Error: {batch_err}")
                continue

        total_time = time.time() - start_time
        await status_msg.edit_text(
            f"🎉 **Indexing Completed Successfully!**\n\n"
            f"📊 Total Messages: `{total_messages}`\n"
            f"✅ Successfully Indexed: `{success_count}`\n"
            f"⚠️ Format Mismatch: `{failed_count}`\n"
            f"❌ Missing / Deleted: `{missing_count}`\n"
            f"⏱️ Total Time Taken: `{int(total_time)} seconds`"
        )

    except Exception as e:
        await message.reply_text(f"❌ Critical error during indexing: `{e}`")

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
