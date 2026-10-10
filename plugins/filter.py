import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import save_custom_filter, filters_col
from config import ADMIN_IDS

# 1. Add single custom filter manually using command: /filter Title - Link
@Client.on_message(filters.command("filter") & filters.private)
async def add_custom_filter(client, message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized to use this command.")
        return

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

# 2. Import custom filters in bulk by replying to a .txt file with /import (and auto-delete file after processing)
@Client.on_message(filters.command("import") & filters.private)
async def import_filters_file(client, message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized to use this command.")
        return

    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply_text("⚠️ Please reply to a `.txt` file with the `/import` command.")
        return

    document = message.reply_to_message.document
    if not document.file_name.endswith(".txt"):
        await message.reply_text("❌ Please provide a valid `.txt` file.")
        return

    status_msg = await message.reply_text("⏳ Downloading and parsing the text file...")
    file_path = None

    try:
        # Download the text file from Telegram
        file_path = await client.download_media(message.reply_to_message)
        
        success_count = 0
        fail_count = 0

        # Read file line by line
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                if not line or "-" not in line:
                    fail_count += 1
                    continue
                
                parts = line.split("-", 1)
                title = parts[0].strip()
                link = parts[1].strip()

                if title and link:
                    await save_custom_filter(title, link)
                    success_count += 1
                else:
                    fail_count += 1

        await status_msg.edit_text(
            f"🎉 **Import Completed Successfully!**\n\n"
            f"✅ Successfully Imported: `{success_count}` filters\n"
            f"❌ Failed / Invalid lines: `{fail_count}`"
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ Error during file import: `{e}`")
    
    finally:
        # Automatically delete the imported file from local storage to clean up space
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

# 3. Delete a specific custom filter by name: /delete Story Name
@Client.on_message(filters.command("delete") & filters.private)
async def delete_single_filter(client, message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized to use this command.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply_text(
            "⚠️ **Incorrect Format!**\n\n"
            "Please provide the story name to delete:\n"
            "`/delete Story Name`"
        )
        return

    target_title = args[1].strip()
    
    # Case-insensitive delete query matching exact title name
    result = await filters_col.delete_one({"title": {"$regex": f"^{target_title}$", "$options": "i"}})

    if result.deleted_count > 0:
        await message.reply_text(f"🗑️ Custom filter **'{target_title}'** has been deleted successfully.")
    else:
        await message.reply_text(f"❌ No custom filter found with the name **'{target_title}'**.")

# 4. Delete all custom filters: /deleteall
@Client.on_message(filters.command("deleteall") & filters.private)
async def delete_all_filters(client, message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized to use this command.")
        return

    # Delete all documents in custom filters collection
    result = await filters_col.delete_many({})
    await message.reply_text(f"🗑️ **All custom filters cleared!** Total `{result.deleted_count}` filters have been deleted.")
