"""
Reconciliation Service

Handles transaction reconciliation, matching related transactions,
and managing counterparty relationships.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from app.db.mongodb import get_database
from app.db.sql import SessionLocal, LedgerEntry
from app.services.vector_service import find_similar_documents

logger = logging.getLogger(__name__)


async def reconcile_transaction(
    record_id: str,
    structured_data: Dict[str, Any],
    embedding: List[float]
) -> Dict[str, Any]:
    """
    Reconcile a transaction with existing records.
    
    This function:
    1. Finds similar transactions using vector search
    2. Matches based on amount, date, and vendor
    3. Identifies counterparty documents
    4. Links related transactions
    
    Args:
        record_id: Current transaction record ID
        structured_data: Structured data from the transaction
        embedding: Document embedding vector
    
    Returns:
        Reconciliation result with matched transactions and relationships
    """
    db = get_database()
    if db is None:
        return {
            "reconciled": False,
            "matched_transactions": [],
            "counterparty_transactions": [],
            "duplicate_transactions": []
        }
    
    # Get transaction details
    total = structured_data.get("total") or structured_data.get("amount") or 0
    date = structured_data.get("date", "").strip()
    vendor = (structured_data.get("vendor") or "").strip().lower()
    invoice_number = (structured_data.get("invoice_number") or "").strip().lower()
    
    # Find similar documents
    similar_docs = await find_similar_documents(embedding, threshold=0.7, limit=20)
    similar_docs = [d for d in similar_docs if d.get("record_id") != record_id]
    
    matched_transactions = []
    counterparty_transactions = []
    duplicate_transactions = []
    
    # Get ledger entries for matching
    sql_db = SessionLocal()
    try:
        for doc in similar_docs:
            other_record_id = doc.get("record_id")
            other_data = doc.get("structured_data", {}) or {}
            
            # Get ledger entry if exists
            ledger_entry = sql_db.query(LedgerEntry).filter(
                LedgerEntry.record_id == other_record_id
            ).first()
            
            if not ledger_entry:
                continue
            
            other_total = other_data.get("total") or other_data.get("amount") or 0
            other_date = (other_data.get("date") or "").strip()
            other_vendor = (other_data.get("vendor") or "").strip().lower()
            
            # Check amount match (within 0.01 tolerance)
            amounts_match = abs(float(total) - float(other_total)) < 0.01 if total and other_total else False
            
            # Check date match
            dates_match = bool(date and other_date and date == other_date)
            
            # Check vendor match
            vendors_match = bool(vendor and other_vendor and vendor == other_vendor)
            vendors_different = bool(
                vendor and other_vendor and 
                vendor != other_vendor and
                vendor not in other_vendor and
                other_vendor not in vendor
            )
            
            # Duplicate: same amount, date, and vendor
            if amounts_match and dates_match and vendors_match:
                duplicate_transactions.append({
                    "record_id": other_record_id,
                    "vendor": other_data.get("vendor"),
                    "date": other_date,
                    "total": other_total,
                    "similarity": doc.get("similarity", 0.0),
                    "ledger_entry_id": ledger_entry.id
                })
            
            # Counterparty: same amount and date, different vendor
            elif amounts_match and dates_match and vendors_different:
                counterparty_transactions.append({
                    "record_id": other_record_id,
                    "vendor": other_data.get("vendor"),
                    "date": other_date,
                    "total": other_total,
                    "similarity": doc.get("similarity", 0.0),
                    "ledger_entry_id": ledger_entry.id,
                    "relationship": "counterparty"
                })
            
            # General match: similar amount and date
            elif amounts_match and dates_match:
                matched_transactions.append({
                    "record_id": other_record_id,
                    "vendor": other_data.get("vendor"),
                    "date": other_date,
                    "total": other_total,
                    "similarity": doc.get("similarity", 0.0),
                    "ledger_entry_id": ledger_entry.id
                })
    finally:
        sql_db.close()
    
    return {
        "reconciled": len(duplicate_transactions) > 0 or len(counterparty_transactions) > 0,
        "matched_transactions": matched_transactions,
        "counterparty_transactions": counterparty_transactions,
        "duplicate_transactions": duplicate_transactions,
        "total_matches": len(matched_transactions) + len(counterparty_transactions) + len(duplicate_transactions)
    }


async def get_reconciliation_status(record_id: str) -> Dict[str, Any]:
    """
    Get reconciliation status for a specific transaction.
    
    Args:
        record_id: Transaction record ID
    
    Returns:
        Reconciliation status with linked transactions
    """
    db = get_database()
    if db is None:
        return {"status": "not_reconciled", "linked_transactions": []}
    
    collection = db.receipts
    doc = await collection.find_one({"record_id": record_id})
    
    if not doc:
        return {"status": "not_found", "linked_transactions": []}
    
    embedding = doc.get("embedding", [])
    structured_data = doc.get("structured_data", {})
    
    if not embedding:
        return {"status": "no_embedding", "linked_transactions": []}
    
    reconciliation = await reconcile_transaction(record_id, structured_data, embedding)
    
    return {
        "status": "reconciled" if reconciliation["reconciled"] else "not_reconciled",
        "reconciliation": reconciliation
    }


async def link_transactions(record_id_1: str, record_id_2: str, relationship: str = "counterparty") -> bool:
    """
    Manually link two transactions.
    
    Args:
        record_id_1: First transaction record ID
        record_id_2: Second transaction record ID
        relationship: Relationship type ("counterparty", "duplicate", "related")
    
    Returns:
        True if linked successfully
    """
    db = get_database()
    if db is None:
        return False
    
    collection = db.receipts
    
    try:
        # Update both documents with link information
        await collection.update_one(
            {"record_id": record_id_1},
            {
                "$addToSet": {
                    "linked_transactions": {
                        "record_id": record_id_2,
                        "relationship": relationship,
                        "linked_at": datetime.utcnow()
                    }
                }
            }
        )
        
        await collection.update_one(
            {"record_id": record_id_2},
            {
                "$addToSet": {
                    "linked_transactions": {
                        "record_id": record_id_1,
                        "relationship": relationship,
                        "linked_at": datetime.utcnow()
                    }
                }
            }
        )
        
        logger.info(f"Linked transactions {record_id_1} and {record_id_2} with relationship {relationship}")
        return True
    except Exception as e:
        logger.error(f"Error linking transactions: {e}", exc_info=True)
        return False

