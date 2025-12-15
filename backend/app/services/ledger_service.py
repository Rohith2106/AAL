from sqlalchemy.orm import Session, joinedload
from app.db.sql import SessionLocal, LedgerEntry, LedgerItem
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
        
        # Use validated currency from LLM if available, otherwise use extracted currency
        validated_currency = orchestration_result["validation_result"].get("currency")
        currency = validated_currency if validated_currency else structured_data.get("currency", "USD")
        
        entry = LedgerEntry(
            record_id=record_id,
            vendor=structured_data.get("vendor") or "Unknown Vendor",
            date=structured_data.get("date") or "N/A",
            amount=structured_data.get("subtotal") or structured_data.get("total") or 0.0,
            tax=structured_data.get("tax"),
            total=structured_data.get("total") or structured_data.get("subtotal") or 0.0,
            currency=currency,
            exchange_rate=structured_data.get("exchange_rate", 1.0),
            usd_total=structured_data.get("usd_equivalent", structured_data.get("total", 0.0)),
            invoice_number=structured_data.get("invoice_number"),
            description=structured_data.get("description") or f"Transaction from {structured_data.get('vendor', 'Unknown')}",
            category=structured_data.get("category"),
            payment_method=structured_data.get("payment_method"),
            status=entry_status,
            validation_confidence=orchestration_result["validation_result"].get("confidence"),
            validation_issues=orchestration_result["validation_result"].get("issues", []),
            reasoning_trace=orchestration_result.get("reasoning_trace")
        )
        # Add items if present
        items_to_add = structured_data.get("items", [])
        logger.info(f"Processing {len(items_to_add)} items for ledger entry")
        
        if items_to_add:
            for idx, item_data in enumerate(items_to_add):
                item = LedgerItem(
                    name=item_data.get("name"),
                    quantity=item_data.get("quantity", 1),
                    unit_price=item_data.get("unit_price", 0.0),
                    line_total=item_data.get("line_total", 0.0)
                )
                entry.items.append(item)
                logger.info(f"Added item {idx + 1}: {item.name} - {item.quantity} x ${item.unit_price}")
        else:
            logger.warning(f"No items in structured_data for record_id: {record_id}")
        
        db.add(entry)
        db.commit()
        db.refresh(entry)
        logger.info(f"Successfully created ledger entry with ID: {entry.id}, Status: {entry.status}")
        
        # Auto-generate double-entry journal entry
        try:
            from app.services.accounting_service import auto_generate_journal_entry, initialize_chart_of_accounts
            # Initialize chart of accounts if needed
            initialize_chart_of_accounts()
            # Generate journal entry
            category = structured_data.get("category")
            journal_entry = auto_generate_journal_entry(entry, category)
            if journal_entry:
                logger.info(f"Auto-generated journal entry {journal_entry.id} for ledger entry {entry.id}")
            else:
                logger.warning(f"Failed to auto-generate journal entry for ledger entry {entry.id}")
        except Exception as je:
            logger.error(f"Error generating journal entry: {je}", exc_info=True)
            # Don't fail the ledger entry creation if journal entry fails
        
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
                "currency": entry.currency,
                "exchange_rate": entry.exchange_rate,
                "usd_total": entry.usd_total,
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
    """Get single ledger entry by record_id with eager loading of items"""
    db = SessionLocal()
    try:
        # Use joinedload to eagerly load items relationship
        entry = db.query(LedgerEntry).options(joinedload(LedgerEntry.items)).filter(
            LedgerEntry.record_id == record_id
        ).first()
        
        if not entry:
            logger.warning(f"Entry not found for record_id: {record_id}")
            return None
        
        # DEBUG: Log items count
        items_count = len(entry.items)
        logger.info(f"Found entry {entry.id} with {items_count} items")
        if items_count > 0:
            logger.info(f"First item: {entry.items[0].name} x{entry.items[0].quantity} = ${entry.items[0].line_total}")
        
        items_list = [
            {
                "id": item.id,
                "name": item.name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "line_total": item.line_total
            }
            for item in entry.items
        ]
        
        logger.info(f"Returning {len(items_list)} items in response")
        
        return {
            "id": entry.id,
            "record_id": entry.record_id,
            "vendor": entry.vendor,
            "date": entry.date,
            "amount": entry.amount,
            "tax": entry.tax,
            "total": entry.total,
            "currency": entry.currency,
            "exchange_rate": entry.exchange_rate,
            "usd_total": entry.usd_total,
            "invoice_number": entry.invoice_number,
            "description": entry.description,
            "category": entry.category,
            "payment_method": entry.payment_method,
            "status": entry.status,
            "validation_confidence": entry.validation_confidence,
            "validation_issues": format_validation_issues(entry.validation_issues),
            "reasoning_trace": entry.reasoning_trace,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
            "items": items_list,
            "journal_entry": get_journal_entry_for_ledger(entry.id)
        }
    finally:
        db.close()


def get_journal_entry_for_ledger(ledger_entry_id: int) -> Optional[Dict[str, Any]]:
    """Get journal entry data for a ledger entry"""
    try:
        from app.services.accounting_service import get_journal_entry_by_ledger_entry
        return get_journal_entry_by_ledger_entry(ledger_entry_id)
    except Exception as e:
        logger.warning(f"Could not fetch journal entry for ledger {ledger_entry_id}: {e}")
        return None


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

