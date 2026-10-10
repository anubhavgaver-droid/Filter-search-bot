from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL

client = AsyncIOMotorClient(MONGO_URL)
db = client["story_search_bot_db"]
stories_col = db["stories"]
settings_col = db["settings"]

async def save_story(data):
    await stories_col.update_one(
        {"message_id": data["message_id"], "chat_id": data["chat_id"]},
        {"$set": data},
        upsert=True
    )

async def get_all_stories():
    return await stories_col.find({}).to_list(length=None)

async def set_channel_id(chat_id):
    await settings_col.update_one(
        {"_id": "config"},
        {"$set": {"channel_id": chat_id}},
        upsert=True
    )

async def get_channel_id():
    res = await settings_col.find_one({"_id": "config"})
    return res["channel_id"] if res else None
