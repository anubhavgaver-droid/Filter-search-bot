import os
import math
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import save_custom_filter, filters_col, get_all_stories
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

    await save_custom_filter(title, link)

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text=title, url=link)]])
    await message.reply_text(
        f"✅ **Custom filter added successfully!**\n\n"
        f"📌 **Title:** `{title}`\n"
        f"🔗 **Link:** `{link}`",
        reply_markup=keyboard
    )

# 2. Import custom filters in bulk by replying to a .txt file with /import
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
        file_path = await client.download_media(message.reply_to_message)
        success_count = 0
        fail_count = 0

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
        await message.reply_text("⚠️ Please provide the story name to delete:\n`/delete Story Name`")
        return

    target_title = args[1].strip()
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

    result = await filters_col.delete_many({})
    await message.reply_text(f"🗑️ **All custom filters cleared!** Total `{result.deleted_count}` filters have been deleted.")

# Helper function to get combined items (Channel Stories + Custom Filters)
async def get_all_combined_items():
    channel_stories = await get_all_stories()
    custom_filters = await filters_col.find({}).to_list(length=None)
    
    # Combine both lists (avoiding duplicates based on title if necessary)
    seen_titles = set()
    combined = []
    
    for item in channel_stories + custom_filters:
        title_lower = item["title"].lower()
        if title_lower not in seen_titles:
            seen_titles.add(title_lower)
            combined.append(item)
            
    return combined

# 5. List all filters and channel stories with 10x10 Pagination
@Client.on_message(filters.command("filters"))
async def list_custom_filters(client, message):
    all_items = await get_all_combined_items()
    
    if not all_items:
        await message.reply_text("📭 No stories or filters available right now.")
        return

    items_per_page = 10
    total_pages = math.ceil(len(all_items) / items_per_page)
    page = 1

    start = (page - 1) * items_per_page
    end = start + items_per_page
    page_items = all_items[start:end]

    keyboard_buttons = []
    for item in page_items:
        keyboard_buttons.append([InlineKeyboardButton(text=item["title"], url=item["link"])])

    nav_buttons = []
    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️ Next", callback_data=f"flt_page_{page+1}"))
    
    if nav_buttons:
        keyboard_buttons.append(nav_buttons)

    keyboard_buttons.append([InlineKeyboardButton(text=f"Page {page}/{total_pages}", callback_data="flt_noop")])

    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    sent_msg = await message.reply_text(
        f"📋 **Total Available Stories/Filters:** `{len(all_items)}`\n"
        f"📄 **Page:** `{page}/{total_pages}`\n\n"
        f"Click any button below to open the story:",
        reply_markup=reply_markup
    )

    asyncio.create_task(delete_message_after_delay(sent_msg, 600))

# Callback Query Handler for Pagination
@Client.on_callback_query(filters.regex(r"^flt_page_"))
async def paginate_filters(client, callback_query):
    data = callback_query.data
    page = int(data.split("_")[2])

    all_items = await get_all_combined_items()
    items_per_page = 10
    total_pages = math.ceil(len(all_items) / items_per_page)

    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    start = (page - 1) * items_per_page
    end = start + items_per_page
    page_items = all_items[start:end]

    keyboard_buttons = []
    for item in page_items:
        keyboard_buttons.append([InlineKeyboardButton(text=item["title"], url=item["link"])])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Back", callback_data=f"flt_page_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="➡️ Next", callback_data=f"flt_page_{page+1}"))
    
    if nav_buttons:
        keyboard_buttons.append(nav_buttons)

    keyboard_buttons.append([InlineKeyboardButton(text=f"Page {page}/{total_pages}", callback_data="flt_noop")])

    await callback_query.message.edit_text(
        f"📋 **Total Available Stories/Filters:** `{len(all_items)}`\n"
        f"📄 **Page:** `{page}/{total_pages}`\n\n"
        f"Click any button below to open the story:",
        reply_markup=InlineKeyboardMarkup(keyboard_buttons)
    )
    await callback_query.answer()

@Client.on_callback_query(filters.regex(r"^flt_noop$"))
async def noop_callback(client, callback_query):
    await callback_query.answer()

async def delete_message_after_delay(message, delay: int):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass
