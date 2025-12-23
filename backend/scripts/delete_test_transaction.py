"""
Script to delete a specific test transaction (entry 62)
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.sql import engine, SessionLocal, LedgerEntry, JournalEntry
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def delete_test_transaction(entry_id: int = 62, dry_run: bool = True):
    """Delete a specific test transaction"""
    db = SessionLocal()
    try:
        entry = db.query(LedgerEntry).filter(LedgerEntry.id == entry_id).first()
        
        if not entry:
            logger.warning(f"Entry {entry_id} not found")
            return
        
        logger.info(f"Found entry: ID={entry.id}, Record={entry.record_id}, Vendor={entry.vendor}, User={entry.user_id}")
        
        if dry_run:
            logger.info(f"DRY RUN: Would delete entry {entry_id} and related journal entries")
            # Check for related journal entries
            journal_entries = db.query(JournalEntry).filter(JournalEntry.ledger_entry_id == entry.id).all()
            logger.info(f"Would also delete {len(journal_entries)} related journal entries")
        else:
            # Delete related journal entries first
            journal_entries = db.query(JournalEntry).filter(JournalEntry.ledger_entry_id == entry.id).all()
            for je in journal_entries:
                db.delete(je)
                logger.info(f"Deleted journal entry {je.id}")
            
            # Delete the ledger entry
            db.delete(entry)
            db.commit()
            logger.info(f"Deleted ledger entry {entry_id}")
        
    except Exception as e:
        logger.error(f"Error deleting transaction: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Delete test transaction")
    parser.add_argument("--entry-id", type=int, default=62, help="Entry ID to delete")
    parser.add_argument("--fix", action="store_true", help="Actually delete (default: dry run)")
    args = parser.parse_args()
    
    logger.info(f"{'DRY RUN: ' if not args.fix else ''}Deleting entry {args.entry_id}...")
    delete_test_transaction(entry_id=args.entry_id, dry_run=not args.fix)
    if not args.fix:
        logger.info("\nTo actually delete, run with --fix flag")

