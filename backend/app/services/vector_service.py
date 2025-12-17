from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import numpy as np
from app.db.mongodb import get_database
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Initialize embedding model (lazy loading)
_embedding_model = None


def get_embedding_model():
    """Lazy load embedding model"""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model


async def create_embedding(text: str) -> List[float]:
    """Create embedding vector for text"""
    model = get_embedding_model()
    embedding = model.encode(text)
    return embedding.tolist()


async def store_document(
    record_id: str,
    structured_data: Dict[str, Any],
    embedding: List[float],
    raw_text: str
) -> str:
    """
    Store document in MongoDB vector database
    
    Returns:
        MongoDB document ID
    """
    db = get_database()
    if db is None:
        raise ValueError("MongoDB database not connected")
    collection = db.receipts
    
    document = {
        "record_id": record_id,
        "structured_data": structured_data,
        "embedding": embedding,
        "raw_text": raw_text,
        "created_at": datetime.utcnow(),
        "status": "pending_reconciliation"
    }
    
    result = await collection.insert_one(document)
    return str(result.inserted_id)


async def find_similar_documents(
    embedding: List[float],
    threshold: float = 0.7,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Find similar documents using cosine similarity
    
    Args:
        embedding: Query embedding vector
        threshold: Similarity threshold (0-1)
        limit: Maximum number of results
    
    Returns:
        List of similar documents with similarity scores
    """
    db = get_database()
    if db is None:
        return []
    
    collection = db.receipts
    
    # Get all documents
    all_docs = await collection.find({"status": {"$ne": "deleted"}}).to_list(length=1000)
    
    if not all_docs:
        return []
    
    # Calculate cosine similarities
    query_vec = np.array(embedding)
    similarities = []
    
    for doc in all_docs:
        doc_embedding = doc.get("embedding", [])
        if not doc_embedding:
            continue
        
        doc_vec = np.array(doc_embedding)
        if len(doc_vec) == len(query_vec) and len(query_vec) > 0:
            # Cosine similarity
            norm_query = np.linalg.norm(query_vec)
            norm_doc = np.linalg.norm(doc_vec)
            if norm_query > 0 and norm_doc > 0:
                similarity = np.dot(query_vec, doc_vec) / (norm_query * norm_doc)
                if similarity >= threshold:
                    similarities.append({
                        "record_id": doc.get("record_id"),
                        "similarity": float(similarity),
                        "structured_data": doc.get("structured_data", {}),
                        "raw_text": doc.get("raw_text", "")[:200]  # Preview
                    })
    
    # Sort by similarity and return top results
    similarities.sort(key=lambda x: x["similarity"], reverse=True)
    return similarities[:limit]


async def check_duplicates(
    record_id: str,
    embedding: List[float],
    structured_data: Optional[Dict[str, Any]] = None,
    threshold: float = 0.95
) -> Dict[str, Any]:
    """
    Check for duplicate receipts and counterparty documents
    
    Args:
        record_id: Current record ID
        embedding: Document embedding vector
        structured_data: Structured data from current document (for matching logic)
        threshold: Similarity threshold for exact duplicates
    
    Returns:
        Dict with:
        - is_duplicate: True if exact duplicate found
        - is_counterparty: True if counterparty document found
        - matched_records: List of similar records
        - counterparty_record: Counterparty record if found
        - confidence: Similarity confidence
        - match_type: "duplicate", "counterparty", or "none"
    """
    # Find similar documents with lower threshold to catch counterparties
    similar = await find_similar_documents(embedding, threshold=0.7, limit=20)
    
    # Filter out self
    similar = [s for s in similar if s["record_id"] != record_id]
    
    if not similar:
        return {
            "is_duplicate": False,
            "is_counterparty": False,
            "matched_records": [],
            "counterparty_record": None,
            "confidence": 0.0,
            "match_type": "none"
        }
    
    # Get current document's structured data for comparison
    current_data = structured_data or {}
    current_total = current_data.get("total") or current_data.get("amount") or 0
    current_date = current_data.get("date", "").strip()
    current_vendor = (current_data.get("vendor") or "").strip().lower()
    current_invoice = (current_data.get("invoice_number") or "").strip().lower()
    
    # Check for exact duplicates (high similarity + same data)
    for match in similar:
        if match["similarity"] >= threshold:
            other_data = match.get("structured_data", {}) or {}
            other_total = other_data.get("total") or other_data.get("amount") or 0
            other_date = (other_data.get("date") or "").strip()
            other_vendor = (other_data.get("vendor") or "").strip().lower()
            other_invoice = (other_data.get("invoice_number") or "").strip().lower()
            
            # Check if amounts match (within 0.01 tolerance)
            amounts_match = abs(float(current_total) - float(other_total)) < 0.01 if current_total and other_total else False
            
            # Check if dates match
            dates_match = bool(current_date and other_date and current_date == other_date)
            
            # Check if vendors match
            vendors_match = bool(current_vendor and other_vendor and current_vendor == other_vendor)
            
            # Check if invoice numbers match
            invoices_match = bool(current_invoice and other_invoice and current_invoice == other_invoice)
            
            # Exact duplicate: high similarity + same vendor + same amount + same date
            if amounts_match and dates_match and vendors_match:
                return {
                    "is_duplicate": True,
                    "is_counterparty": False,
                    "matched_records": [match],
                    "counterparty_record": None,
                    "confidence": match["similarity"],
                    "match_type": "duplicate",
                    "duplicate_record_id": match["record_id"]
                }
    
    # Check for counterparty documents (same transaction, different perspective)
    # Counterparty: same amount + same date + different vendor
    for match in similar:
        if match["similarity"] >= 0.75:  # Lower threshold for counterparty detection
            other_data = match.get("structured_data", {}) or {}
            other_total = other_data.get("total") or other_data.get("amount") or 0
            other_date = (other_data.get("date") or "").strip()
            other_vendor = (other_data.get("vendor") or "").strip().lower()
            
            # Check if amounts match (within 0.01 tolerance)
            amounts_match = abs(float(current_total) - float(other_total)) < 0.01 if current_total and other_total else False
            
            # Check if dates match
            dates_match = bool(current_date and other_date and current_date == other_date)
            
            # Check if vendors are different
            vendors_different = bool(
                current_vendor and other_vendor and 
                current_vendor != other_vendor and
                current_vendor not in other_vendor and
                other_vendor not in current_vendor
            )
            
            # Counterparty match: same amount + same date + different vendor
            if amounts_match and dates_match and vendors_different:
                return {
                    "is_duplicate": False,
                    "is_counterparty": True,
                    "matched_records": similar[:5],  # Return top matches
                    "counterparty_record": match,
                    "confidence": match["similarity"],
                    "match_type": "counterparty",
                    "counterparty_record_id": match["record_id"],
                    "counterparty_vendor": other_data.get("vendor")
                }
    
    # No duplicate or counterparty found, but return similar records for reference
    return {
        "is_duplicate": False,
        "is_counterparty": False,
        "matched_records": similar[:5],
        "counterparty_record": None,
        "confidence": similar[0]["similarity"] if similar else 0.0,
        "match_type": "none"
    }


async def update_document_status(record_id: str, status: str) -> bool:
    """Update document status in MongoDB"""
    db = get_database()
    if db is None:
        logger.warning("MongoDB database not connected, cannot update document status")
        return False
    
    try:
        collection = db.receipts
        result = await collection.update_one(
            {"record_id": record_id},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}}
        )
        
        if result.matched_count > 0:
            if result.modified_count > 0:
                logger.info(f"Updated document {record_id} status to {status} in MongoDB")
            else:
                logger.info(f"Document {record_id} found but status already set to {status}")
            return True
        else:
            logger.warning(f"Document {record_id} not found in MongoDB for status update")
            return False
    except Exception as e:
        logger.error(f"Error updating document status in MongoDB: {e}", exc_info=True)
        return False


async def document_exists(record_id: str) -> bool:
    """Check if a document exists in MongoDB"""
    db = get_database()
    if db is None:
        return False
    try:
        collection = db.receipts
        count = await collection.count_documents({"record_id": record_id})
        return count > 0
    except Exception as e:
        logger.error(f"Error checking document existence: {e}", exc_info=True)
        return False


async def delete_document(record_id: str) -> bool:
    """Delete document from MongoDB vector database"""
    db = get_database()
    if db is None:
        logger.warning("MongoDB database not connected, cannot delete document")
        return False
    
    try:
        collection = db.receipts
        
        # First check if document exists
        exists = await document_exists(record_id)
        if not exists:
            logger.warning(f"Document {record_id} not found in MongoDB for deletion")
            return False
        
        result = await collection.delete_one({"record_id": record_id})
        
        if result.deleted_count > 0:
            logger.info(f"Deleted document {record_id} from MongoDB (deleted_count: {result.deleted_count})")
            return True
        else:
            logger.warning(f"Delete operation returned deleted_count=0 for record_id: {record_id}")
            return False
    except Exception as e:
        logger.error(f"Error deleting document from MongoDB: {e}", exc_info=True)
        return False
