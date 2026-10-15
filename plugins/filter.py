import os
import math
import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import save_custom_filter, filters_col, get_all_stories
from config import ADMIN_IDS

# Helper function to get message link in groups or channels
def get_message_link(message):
    if message.chat.username:
        return f"https://t.me/{message.chat.username}/{message.id}"
    else:
        # For private or supergroups with -100 prefix
        chat_id_str = str(message.chat.id).replace("-100", "")
        return f"https://t.me/c/{chat_id_str}/{message.id}"

# 1. Add custom filter via Reply: /filter "Story Name"
@Client.on_message(filters.command("filter"))
async def add_custom_filter_by_reply(client, message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized to use this command.")
        return

    # Check if user replied to a message
    if not message.reply_to_message:
        await message.reply_text(
            "⚠️ **Incorrect Usage!**\n\n"
            "Please **reply** to any message/photo with:\n"
            "`/filter \"Your Story Name\"`"
        )
        return

    # Extract name inside double quotes using regex
    match = re.search(r'"([^"]+)"', message.text)
    if not match:
        await message.reply_text(
            "⚠️ **Please provide the story name inside double quotes!**\n"
            "Example: `/filter \"Shadi By Mistake\"`"
        )
        return

    title = match.group(1).strip()
    target_msg = message.reply_to_message
    
    # Generate link of the replied message
    link = get_message_link(target_msg)
    
    # Capture photo file_id if the replied message has a photo
    photo_id = target_msg.photo.file_id if target_msg.photo else None

    # Save to database
    await save_custom_filter(title, link, photo_id)

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text=title, url=link)]])
    
    if photo_id:
        await client.send_photo(
            chat_id=message.chat.id,
            photo=photo_id,
            caption=f"✅ **Custom filter added successfully via reply!**\n\n📌 **Title:** `{title}`\n🔗 **Link:** `{link}`",
            reply_markup=keyboard
        )
    else:
        await message.reply_text(
            f"✅ **Custom filter added successfully via reply!**\n\n📌 **Title:** `{title}`\n🔗 **Link:** `{link}`",
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
                    await save_custom_filter(title, link, None)
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

# 3. Delete specific filter: /delete Story Name
@Client.on_message(filters.command("delete") & filters.private)
async def delete_single_filter(client, message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply_text("⚠️ Please provide the story name:\n`/delete Story Name`")
        return

    target_title = args[1].strip()
    result = await filters_col.delete_one({"title": {"$regex": f"^{target_title}$", "$options": "i"}})

    if result.deleted_count > 0:
        await message.reply_text(f"🗑️ Filter **'{target_title}'** deleted successfully.")
    else:
        await message.reply_text(f"❌ No filter found with name **'{target_title}'**.")

# 4. Delete all custom filters: /deleteall
@Client.on_message(filters.command("deleteall") & filters.private)
async def delete_all_filters(client, message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return

    result = await filters_col.delete_many({})
    await message.reply_text(f"🗑️ All custom filters cleared! Total `{result.deleted_count}` deleted.")

# Helper for combined list
async def get_all_combined_items():
    channel_stories = await get_all_stories()
    custom_filters = await filters_col.find({}).to_list(length=None)
    
    seen_titles = set()
    combined = []
    
    for item in channel_stories + custom_filters:
        title_lower = item["title"].lower()
        if title_lower not in seen_titles:
            seen_titles.add(title_lower)
            combined.append(item)
            
    return combined

# 5. /filters command with Pagination (Works in Groups & Private)
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
