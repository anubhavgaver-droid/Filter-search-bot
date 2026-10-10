import re
import time
import asyncio
from pyrogram import Client, filters
from database import set_channel_id, get_channel_id, save_story, stories_col
from config import ADMIN_IDS


# Title cleaner function to strip all trailing/leading emojis and symbols
def clean_story_title(raw_title: str) -> str:
    if not raw_title:
        return ""
    
    # Raw string (r"...") used to avoid unicode escape errors
    emoji_pattern = re.compile(
        r"["
        r"\U0001F600-\U0001F64F"  # emoticons
        r"\U0001F300-\U0001F5FF"  # symbols & pictographs
        r"\U0001F680-\U0001F6FF"  # transport & map symbols
        r"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        r"\u2600-\u26FF"        # Miscellaneous Symbols
        r"\u2700-\u27BF"        # Dingbats
        r"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        r"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        r"\u200d"                 # Zero Width Joiner
        r"\ufe0f"                 # Variation Selector
        r"]+", 
        flags=re.UNICODE
    )
    clean_title = emoji_pattern.sub("", raw_title).strip()
    return clean_title


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

# Advanced Batch Indexing Command with Emoji Auto-Cleaning
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
                            raw_title = match.group(1).strip()
                            clean_title = clean_story_title(raw_title)
                            
                            if clean_title:
                                story_data = {
                                    "message_id": msg.id,
                                    "chat_id": msg.chat.id,
                                    "title": clean_title,
                                    "link": msg.link
                                }
                                await save_story(story_data)
                                success_count += 1
                            else:
                                failed_count += 1
                        else:
                            failed_count += 1
                    else:
                        missing_count += 1

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
                
                await asyncio.sleep(1)

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

# Clear All Indexed Channel Stories Command: /clearall
@Client.on_message(filters.command("clearall") & filters.private)
async def clear_all_indexed_stories(client, message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized to use this command.")
        return

    # Delete all documents from the stories collection
    result = await stories_col.delete_many({})
    await message.reply_text(f"🗑️ **All indexed stories cleared!** Total `{result.deleted_count}` indexed stories have been deleted from the database.")

# Auto-index new messages in connected channel with Emoji Cleaning
@Client.on_message(filters.channel)
async def auto_index_new_post(client, message):
    channel_id = await get_channel_id()
    if channel_id and message.chat.id == channel_id:
        caption = message.caption or message.text
        if caption:
            match = re.search(r"Story\s*:\s*(.*?)\s*(?=Status\s*:|$)", caption, re.IGNORECASE | re.DOTALL)
            if match:
                raw_title = match.group(1).strip()
                clean_title = clean_story_title(raw_title)
                if clean_title:
                    story_data = {
                        "message_id": message.id,
                        "chat_id": message.chat.id,
                        "title": clean_title,
                        "link": message.link
                    }
                    await save_story(story_data)
