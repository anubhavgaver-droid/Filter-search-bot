from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL

client = AsyncIOMotorClient(MONGO_URL)
db = client["story_search_bot_db"]
stories_col = db["stories"]
filters_col = db["custom_filters"]
settings_col = db["settings"]

async def save_story(data):
    await stories_col.update_one(
        {"message_id": data["message_id"], "chat_id": data["chat_id"]},
        {"$set": data},
        upsert=True
    )

async def get_all_stories():
    return await stories_col.find({}).to_list(length=None)

async def save_custom_filter(title, link, photo_id=None):
    await filters_col.update_one(
        {"title": {"$regex": f"^{title}$", "$options": "i"}},
        {"$set": {"title": title, "link": link, "photo": photo_id}},
        upsert=True
    )

async def get_all_custom_filters():
    return await filters_col.find({}).to_list(length=None)

# Multiple Channels Database Functions
async def add_connected_channel(chat_id):
    await settings_col.update_one(
        {"_id": "connected_channels"},
        {"$addToSet": {"ids": chat_id}},
        upsert=True
    )

async def remove_connected_channel(chat_id):
    await settings_col.update_one(
        {"_id": "connected_channels"},
        {"$pull": {"ids": chat_id}}
    )

async def get_connected_channels():
    res = await settings_col.find_one({"_id": "connected_channels"})
    return res["ids"] if res and "ids" in res else []
