from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL

client = AsyncIOMotorClient(MONGO_URL)
db = client["story_search_bot_db"]
stories_col = db["stories"]
filters_col = db["custom_filters"]  # Collection for manual filters
settings_col = db["settings"]

# Save channel indexed stories
async def save_story(data):
    await stories_col.update_one(
        {"message_id": data["message_id"], "chat_id": data["chat_id"]},
        {"$set": data},
        upsert=True
    )

async def get_all_stories():
    return await stories_col.find({}).to_list(length=None)

# Save manual custom filters
async def save_custom_filter(title, link):
    await filters_col.update_one(
        {"title": {"$regex": f"^{title}$", "$options": "i"}},
        {"$set": {"title": title, "link": link}},
        upsert=True
    )

async def get_all_custom_filters():
    return await filters_col.find({}).to_list(length=None)

# Channel ID settings
async def set_channel_id(chat_id):
    await settings_col.update_one(
        {"_id": "config"},
        {"$set": {"channel_id": chat_id}},
        upsert=True
    )

async def get_channel_id():
    res = await settings_col.find_one({"_id": "config"})
    return res["channel_id"] if res else None
