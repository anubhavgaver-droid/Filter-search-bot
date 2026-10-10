import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from rapidfuzz import process, fuzz
from database import get_all_stories, get_all_custom_filters

@Client.on_message(filters.text & ~filters.command(["connect", "index", "start", "filter", "import", "filters", "delete", "deleteall"]))
async def search_handler(client, message):
    query = message.text.strip().lower()
    if query.startswith("/"):
        return

    channel_stories = await get_all_stories()
    custom_filters = await get_all_custom_filters()

    all_items = channel_stories + custom_filters
    if not all_items:
        return  # Keep silent if no database data

    title_map = {item["title"].lower(): item for item in all_items}
    titles = list(title_map.keys())
    
    results = process.extract(query, titles, scorer=fuzz.WRatio, limit=3)
    
    exact_matches = []
    suggestions = []

    for lower_title, score, index in results:
        original_item = title_map[titles[index]]
        if score >= 85:
            exact_matches.append(original_item)
        elif score >= 55:
            suggestions.append((original_item, score))

    sent_message = None

    if exact_matches:
        seen = set()
        unique_matches = []
        for item in exact_matches:
            if item["title"] not in seen:
                seen.add(item["title"])
                unique_matches.append(item)

        buttons = [[InlineKeyboardButton(text=item["title"], url=item["link"])] for item in unique_matches]
        markup = InlineKeyboardMarkup(buttons)
        
        # Check if the top match has an attached photo (custom filter photo support)
        top_item = unique_matches[0]
        photo_id = top_item.get("photo")

        if photo_id:
            sent_message = await message.reply_photo(
                photo=photo_id,
                caption=f"🔍 **Search results for '{message.text.strip()}':**",
                reply_markup=markup
            )
        else:
            sent_message = await message.reply_text(
                f"🔍 **Search results for '{message.text.strip()}':**", 
                reply_markup=markup
            )
    
    elif suggestions:
        seen = set()
        unique_suggestions = []
        for item, score in suggestions:
            if item["title"] not in seen:
                seen.add(item["title"])
                unique_suggestions.append(item)

        buttons = [[InlineKeyboardButton(text=item["title"], url=item["link"])] for item in unique_suggestions]
        sent_message = await message.reply_text(
            f"🤔 Exact match not found. Did you mean one of these?", 
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        return

    # Auto-delete search response after 10 minutes (600 seconds)
    if sent_message:
        asyncio.create_task(delete_message_after_delay(sent_message, 600))

async def delete_message_after_delay(message, delay: int):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass
