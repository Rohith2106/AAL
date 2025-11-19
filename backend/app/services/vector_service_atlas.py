"""
MongoDB Atlas Vector Search implementation.

This module provides vector search using MongoDB Atlas Vector Search
when available. Falls back to application-level similarity if not available.
"""

from typing import List, Dict, Any, Optional
from app.db.mongodb import get_database
import logging

logger = logging.getLogger(__name__)


async def vector_search_atlas(
    embedding: List[float],
    collection_name: str = "receipts",
    limit: int = 5,
    score_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Perform vector search using MongoDB Atlas Vector Search.
    
    This requires:
    1. MongoDB Atlas cluster
    2. Vector Search Index created on the collection
    3. Index name: "vector_index"
    
    Args:
        embedding: Query embedding vector
        collection_name: Name of the collection
        limit: Maximum number of results
        score_threshold: Minimum similarity score
    
    Returns:
        List of matching documents with similarity scores
    """
    db = get_database()
    if db is None:
        return []
    
    collection = db[collection_name]
    
    try:
        # MongoDB Atlas Vector Search aggregation pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": embedding,
                    "numCandidates": limit * 10,  # Search more candidates for better results
                    "limit": limit
                }
            },
            {
                "$addFields": {
                    "score": {"$meta": "vectorSearchScore"}
                }
            },
            {
                "$match": {
                    "score": {"$gte": score_threshold}
                }
            },
            {
                "$project": {
                    "record_id": 1,
                    "structured_data": 1,
                    "raw_text": {"$substr": ["$raw_text", 0, 200]},
                    "similarity": "$score",
                    "created_at": 1
                }
            }
        ]
        
        results = []
        async for doc in collection.aggregate(pipeline):
            results.append({
                "record_id": doc.get("record_id"),
                "similarity": doc.get("similarity", 0.0),
                "structured_data": doc.get("structured_data", {}),
                "raw_text": doc.get("raw_text", "")
            })
        
        return results
    
    except Exception as e:
        logger.warning(f"Atlas Vector Search not available, falling back to application-level search: {e}")
        # Fall back to application-level similarity (implemented in vector_service.py)
        return []


async def check_vector_index_exists(collection_name: str = "receipts") -> bool:
    """Check if vector search index exists"""
    try:
        db = get_database()
        if db is None:
            return False
        
        collection = db[collection_name]
        indexes = await collection.list_search_indexes()
        
        for index in indexes:
            if index.get("name") == "vector_index":
                return True
        
        return False
    except Exception as e:
        logger.debug(f"Could not check vector index: {e}")
        return False

