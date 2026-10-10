from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from rapidfuzz import process, fuzz
from database import get_all_stories

@Client.on_message(filters.text & ~filters.command(["connect", "index", "start", "filter", "import"]))
async def search_handler(client, message):
    query = message.text.strip()
    if query.startswith("/"):
        return

    all_stories = await get_all_stories()
    if not all_stories:
        return  # यदि डेटाबेस खाली है, तो बोट पूरी तरह साइलेंट रहेगा

    titles = [s["title"] for s in all_stories]
    
    # RapidFuzz search matching top results
    results = process.extract(query, titles, scorer=fuzz.WRatio, limit=3)
    
    exact_matches = []
    suggestions = []

    for title, score, index in results:
        if score >= 85:
            exact_matches.append(all_stories[index])
        elif score >= 55:  # "Did you mean?" suggestions range
            suggestions.append((all_stories[index], score))

    if exact_matches:
        buttons = [[InlineKeyboardButton(text=item["title"], url=item["link"])] for item in exact_matches]
        await message.reply_text(f"🔍 **Search results for '{query}':**", reply_markup=InlineKeyboardMarkup(buttons))
    
    elif suggestions:
        buttons = [[InlineKeyboardButton(text=item["title"], url=item["link"])] for item, score in suggestions]
        await message.reply_text(
            f"🤔 Exact match not found. Did you mean one of these?", 
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        # यदि मैसेज पूरी तरह आउट ऑफ कॉन्टेक्स्ट है, तो बोट कोई रिप्लाई नहीं देगा (बिल्कुल साइलेंट रहेगा)
        return
