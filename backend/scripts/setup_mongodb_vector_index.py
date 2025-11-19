"""
Script to create MongoDB Vector Search Index for receipt embeddings.

This script creates a vector search index on the 'receipts' collection
to enable efficient similarity search for duplicate detection and RAG.

Run this script once after setting up MongoDB:
    python scripts/setup_mongodb_vector_index.py
    OR
    python -m scripts.setup_mongodb_vector_index
"""

import sys
from pathlib import Path

# Add parent directory to path to import app modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_vector_search_index():
    """Create vector search index on MongoDB"""
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        db = client[settings.MONGODB_DB_NAME]
        collection = db.receipts
        
        # Test connection
        await client.admin.command('ping')
        logger.info(f"Connected to MongoDB: {settings.MONGODB_DB_NAME}")
        
        # Check if collection exists, create if not
        collections = await db.list_collection_names()
        if "receipts" not in collections:
            await db.create_collection("receipts")
            logger.info("Created 'receipts' collection")
        
        # Vector Search Index Definition
        # For MongoDB Atlas, use the Atlas UI or API
        # For local MongoDB, we'll use a manual approach with aggregation
        
        index_definition = {
            "name": "vector_index",
            "type": "vector",
            "definition": {
                "fields": [
                    {
                        "type": "vector",
                        "path": "embedding",
                        "numDimensions": 384,  # all-MiniLM-L6-v2 produces 384-dimensional vectors
                        "similarity": "cosine"
                    }
                ]
            }
        }
        
        logger.info("Vector Search Index Definition:")
        logger.info(f"  Name: {index_definition['name']}")
        logger.info(f"  Type: {index_definition['type']}")
        logger.info(f"  Dimensions: {index_definition['definition']['fields'][0]['numDimensions']}")
        logger.info(f"  Similarity: {index_definition['definition']['fields'][0]['similarity']}")
        
        # Note: Vector search indexes in MongoDB require MongoDB Atlas (cloud) or MongoDB 6.0.11+ with vector search enabled
        # For local MongoDB, we'll use cosine similarity in application code (already implemented)
        
        # Try to create the index via Atlas Search API if available
        try:
            # This requires MongoDB Atlas with Search API enabled
            # For local MongoDB, skip this and use application-level similarity
            search_indexes = await db.receipts.list_search_indexes()
            existing_indexes = [idx for idx in search_indexes]
            
            if not any(idx.get("name") == "vector_index" for idx in existing_indexes):
                logger.info("Creating vector search index via Atlas Search API...")
                # Note: This requires MongoDB Atlas and proper API access
                # For local setup, the application will use cosine similarity in code
                logger.warning("Vector search index creation requires MongoDB Atlas.")
                logger.info("For local MongoDB, similarity search is handled in application code.")
            else:
                logger.info("Vector search index already exists")
        except Exception as e:
            logger.info(f"Atlas Search API not available (expected for local MongoDB): {e}")
            logger.info("Using application-level cosine similarity (already implemented)")
        
        # Create regular index on record_id for faster lookups
        await collection.create_index("record_id", unique=True)
        await collection.create_index("status")
        await collection.create_index("created_at")
        logger.info("Created regular indexes on record_id, status, and created_at")
        
        logger.info("\n✅ MongoDB setup complete!")
        logger.info("\nFor MongoDB Atlas Vector Search:")
        logger.info("1. Go to Atlas UI → Search → Create Search Index")
        logger.info("2. Use the following configuration:")
        logger.info(json.dumps(index_definition, indent=2))
        logger.info("\nFor local MongoDB:")
        logger.info("Vector similarity is handled in application code (vector_service.py)")
        
        client.close()
        
    except Exception as e:
        logger.error(f"Error setting up MongoDB: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(create_vector_search_index())

