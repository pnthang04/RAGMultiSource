from functools import lru_cache

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings


@lru_cache
def get_mongo_client() -> AsyncIOMotorClient:
    return AsyncIOMotorClient(settings.MONGODB_URI)


def get_database() -> AsyncIOMotorDatabase:
    return get_mongo_client()[settings.MONGODB_DB_NAME]
