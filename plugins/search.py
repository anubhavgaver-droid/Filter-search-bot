import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from rapidfuzz import process, fuzz
from database import get_all_stories, get_all_custom_filters

@Client.on_message(filters.text & ~filters.command(["connect", "index", "start", "filter", "import", "filters", "delete", "deleteall"]))
async def search_handler(client, message):
    raw_query = message.text.strip()
    query = raw_query.lower()
    
    if query.startswith("/"):
        return

    channel_stories = await get_all_stories()
    custom_filters = await get_all_custom_filters()

    all_items = channel_stories + custom_filters
    if not all_items:
        return  # Data absent -> remain silent

    # Map lowercased title to original item
    title_map = {}
    for item in all_items:
        title_lower = item["title"].lower()
        if title_lower not in title_map:
            title_map[title_lower] = item

    sent_message = None

    # STEP 1: Strict Exact Match Check (Case-Insensitive)
    if query in title_map:
        exact_item = title_map[query]
        buttons = [[InlineKeyboardButton(text=exact_item["title"], url=exact_item["link"])]]
        markup = InlineKeyboardMarkup(buttons)
        
        photo_id = exact_item.get("photo")
        if photo_id:
            sent_message = await message.reply_photo(
                photo=photo_id,
                caption=f"🔍 **Search Result:**",
                reply_markup=markup
            )
        else:
            sent_message = await message.reply_text(
                f"🔍 **Search Result:**", 
                reply_markup=markup
            )

    # STEP 2: Fuzzy Matching (Did You Mean) if exact match fails
    else:
        titles = list(title_map.keys())
        results = process.extract(query, titles, scorer=fuzz.WRatio, limit=3)
        
        suggestions = []
        for lower_title, score, index in results:
            if score >= 60:  # Threshold for partial matches/typos
                suggestions.append(title_map[titles[index]])

        if suggestions:
            seen = set()
            unique_suggestions = []
            for item in suggestions:
                if item["title"] not in seen:
                    seen.add(item["title"])
                    unique_suggestions.append(item)

            buttons = [[InlineKeyboardButton(text=item["title"], url=item["link"])] for item in unique_suggestions]
            sent_message = await message.reply_text(
                f"🤔 Exact match not found. Did you mean one of these?", 
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            return  # No relevant match -> remain completely silent

    # Auto-delete search response after 10 minutes (600 seconds)
    if sent_message:
        asyncio.create_task(delete_message_after_delay(sent_message, 600))

async def delete_message_after_delay(message, delay: int):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass
