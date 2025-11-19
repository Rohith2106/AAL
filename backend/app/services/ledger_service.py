from sqlalchemy.orm import Session
from app.db.sql import SessionLocal, LedgerEntry
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def format_validation_issues(issues):
    """Convert validation issues to a consistent format (dicts to strings)"""
    if not issues:
        return None
    if isinstance(issues, list):
        # Convert dict issues to strings for display
        formatted = []
        for issue in issues:
            if isinstance(issue, dict):
                # Format as: "CODE: message" or just "message"
                code = issue.get("code", "")
                message = issue.get("message", str(issue))
                if code:
                    formatted.append(f"{code}: {message}")
                else:
                    formatted.append(message)
            else:
                formatted.append(str(issue))
        return formatted
    return issues


def create_ledger_entry(
    record_id: str,
    structured_data: Dict[str, Any],
    orchestration_result: Dict[str, Any]
) -> LedgerEntry:
    """Create ledger entry from validated record"""
    db = SessionLocal()
    try:
        validation_status = orchestration_result["validation_result"]["status"]
        logger.info(f"Creating ledger entry for record_id: {record_id}, validation_status: {validation_status}")
        
        # Determine entry status based on validation
        entry_status = "validated" if validation_status == "valid" else "pending"
        
        entry = LedgerEntry(
            record_id=record_id,
            vendor=structured_data.get("vendor") or "Unknown Vendor",
            date=structured_data.get("date") or "N/A",
            amount=structured_data.get("subtotal") or structured_data.get("total") or 0.0,
            tax=structured_data.get("tax"),
            total=structured_data.get("total") or structured_data.get("subtotal") or 0.0,
            invoice_number=structured_data.get("invoice_number"),
            description=structured_data.get("description") or f"Transaction from {structured_data.get('vendor', 'Unknown')}",
            category=structured_data.get("category"),
            payment_method=structured_data.get("payment_method"),
            status=entry_status,
            validation_confidence=orchestration_result["validation_result"].get("confidence"),
            validation_issues=orchestration_result["validation_result"].get("issues", []),
            reasoning_trace=orchestration_result.get("reasoning_trace")
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        logger.info(f"Successfully created ledger entry with ID: {entry.id}, Status: {entry.status}")
        return entry
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating ledger entry: {e}", exc_info=True)
        raise
    finally:
        db.close()


def get_ledger_entries(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    vendor: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get ledger entries with filters"""
    db = SessionLocal()
    try:
        query = db.query(LedgerEntry)
        
        if status:
            query = query.filter(LedgerEntry.status == status)
        if vendor:
            query = query.filter(LedgerEntry.vendor.ilike(f"%{vendor}%"))
        
        entries = query.order_by(LedgerEntry.created_at.desc()).offset(skip).limit(limit).all()
        
        return [
            {
                "id": entry.id,
                "record_id": entry.record_id,
                "vendor": entry.vendor,
                "date": entry.date,
                "amount": entry.amount,
                "tax": entry.tax,
                "total": entry.total,
                "invoice_number": entry.invoice_number,
                "description": entry.description,
                "category": entry.category,
                "payment_method": entry.payment_method,
                "status": entry.status,
                "validation_confidence": entry.validation_confidence,
                "validation_issues": format_validation_issues(entry.validation_issues),
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
                "updated_at": entry.updated_at.isoformat() if entry.updated_at else None
            }
            for entry in entries
        ]
    finally:
        db.close()


def get_ledger_entry(record_id: str) -> Optional[Dict[str, Any]]:
    """Get single ledger entry by record_id"""
    db = SessionLocal()
    try:
        entry = db.query(LedgerEntry).filter(LedgerEntry.record_id == record_id).first()
        if not entry:
            return None
        
        return {
            "id": entry.id,
            "record_id": entry.record_id,
            "vendor": entry.vendor,
            "date": entry.date,
            "amount": entry.amount,
            "tax": entry.tax,
            "total": entry.total,
            "invoice_number": entry.invoice_number,
            "description": entry.description,
            "category": entry.category,
            "payment_method": entry.payment_method,
            "status": entry.status,
            "validation_confidence": entry.validation_confidence,
            "validation_issues": format_validation_issues(entry.validation_issues),
            "reasoning_trace": entry.reasoning_trace,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "updated_at": entry.updated_at.isoformat() if entry.updated_at else None
        }
    finally:
        db.close()


def update_ledger_entry_status(record_id: str, status: str):
    """Update ledger entry status"""
    db = SessionLocal()
    try:
        entry = db.query(LedgerEntry).filter(LedgerEntry.record_id == record_id).first()
        if entry:
            entry.status = status
            entry.updated_at = datetime.utcnow()
            db.commit()
            logger.info(f"Updated ledger entry {record_id} status to {status}")
            return True
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating ledger entry: {e}")
        raise
    finally:
        db.close()


def delete_ledger_entry(record_id: str) -> bool:
    """Delete ledger entry from MySQL database"""
    db = SessionLocal()
    try:
        entry = db.query(LedgerEntry).filter(LedgerEntry.record_id == record_id).first()
        if entry:
            db.delete(entry)
            db.commit()
            logger.info(f"Deleted ledger entry {record_id} from MySQL")
            return True
        logger.warning(f"Ledger entry {record_id} not found in MySQL")
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting ledger entry: {e}")
        raise
    finally:
        db.close()

