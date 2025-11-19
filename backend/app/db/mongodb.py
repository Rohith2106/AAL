from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

client: AsyncIOMotorClient = None
database = None


async def connect_to_mongo():
    """Create database connection"""
    global client, database
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        database = client[settings.MONGODB_DB_NAME]
        # Test connection
        await client.admin.command('ping')
        logger.info("Connected to MongoDB")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close database connection"""
    global client
    if client:
        client.close()
        logger.info("Disconnected from MongoDB")


def get_database():
    """Get database instance"""
    return database

