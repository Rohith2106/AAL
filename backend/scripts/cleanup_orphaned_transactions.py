"""
Script to identify and optionally clean up orphaned transactions
(transactions that don't belong to any user or belong to invalid users)
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.sql import engine, SessionLocal, LedgerEntry, JournalEntry, User
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_orphaned_transactions():
    """Find transactions that don't belong to valid users"""
    db = SessionLocal()
    try:
        # Get all user IDs
        users = db.query(User).all()
        valid_user_ids = [user.id for user in users]
        
        if not valid_user_ids:
            logger.warning("No users found in database!")
            return
        
        logger.info(f"Valid user IDs: {valid_user_ids}")
        
        # Find ledger entries with invalid or NULL user_id
        with engine.connect() as conn:
            if 'mysql' in str(engine.url):
                result = conn.execute(text("""
                    SELECT id, record_id, vendor, user_id, created_at
                    FROM ledger_entries
                    WHERE user_id IS NULL OR user_id NOT IN :valid_ids
                """), {"valid_ids": tuple(valid_user_ids)})
            else:
                # PostgreSQL
                result = conn.execute(text("""
                    SELECT id, record_id, vendor, user_id, created_at
                    FROM ledger_entries
                    WHERE user_id IS NULL OR user_id NOT IN :valid_ids
                """), {"valid_ids": tuple(valid_user_ids)})
            
            orphaned_ledger = result.fetchall()
            
            if orphaned_ledger:
                logger.warning(f"Found {len(orphaned_ledger)} orphaned ledger entries:")
                for row in orphaned_ledger:
                    logger.warning(f"  - ID: {row[0]}, Record: {row[1]}, Vendor: {row[2]}, User ID: {row[3]}, Created: {row[4]}")
            else:
                logger.info("No orphaned ledger entries found")
            
            # Find journal entries with invalid or NULL user_id
            result = conn.execute(text("""
                SELECT id, ledger_entry_id, reference, user_id, created_at
                FROM journal_entries
                WHERE user_id IS NULL OR user_id NOT IN :valid_ids
            """), {"valid_ids": tuple(valid_user_ids)})
            
            orphaned_journal = result.fetchall()
            
            if orphaned_journal:
                logger.warning(f"Found {len(orphaned_journal)} orphaned journal entries:")
                for row in orphaned_journal:
                    logger.warning(f"  - ID: {row[0]}, Ledger Entry ID: {row[1]}, Reference: {row[2]}, User ID: {row[3]}, Created: {row[4]}")
            else:
                logger.info("No orphaned journal entries found")
        
        return orphaned_ledger, orphaned_journal
        
    except Exception as e:
        logger.error(f"Error finding orphaned transactions: {e}", exc_info=True)
        raise
    finally:
        db.close()


def fix_orphaned_transactions(assign_to_user_id: int = 1, dry_run: bool = True):
    """Fix orphaned transactions by assigning them to a user"""
    db = SessionLocal()
    try:
        # Get all user IDs
        users = db.query(User).all()
        valid_user_ids = [user.id for user in users]
        
        if assign_to_user_id not in valid_user_ids:
            logger.error(f"Invalid user_id {assign_to_user_id}. Valid user IDs: {valid_user_ids}")
            return
        
        with engine.connect() as conn:
            if 'mysql' in str(engine.url):
                # Fix ledger entries
                if not dry_run:
                    conn.execute(text("""
                        UPDATE ledger_entries
                        SET user_id = :user_id
                        WHERE user_id IS NULL OR user_id NOT IN :valid_ids
                    """), {"user_id": assign_to_user_id, "valid_ids": tuple(valid_user_ids)})
                    logger.info("Fixed orphaned ledger entries")
                else:
                    result = conn.execute(text("""
                        SELECT COUNT(*) FROM ledger_entries
                        WHERE user_id IS NULL OR user_id NOT IN :valid_ids
                    """), {"valid_ids": tuple(valid_user_ids)})
                    count = result.fetchone()[0]
                    logger.info(f"Would fix {count} orphaned ledger entries")
                
                # Fix journal entries
                if not dry_run:
                    conn.execute(text("""
                        UPDATE journal_entries
                        SET user_id = :user_id
                        WHERE user_id IS NULL OR user_id NOT IN :valid_ids
                    """), {"user_id": assign_to_user_id, "valid_ids": tuple(valid_user_ids)})
                    logger.info("Fixed orphaned journal entries")
                else:
                    result = conn.execute(text("""
                        SELECT COUNT(*) FROM journal_entries
                        WHERE user_id IS NULL OR user_id NOT IN :valid_ids
                    """), {"valid_ids": tuple(valid_user_ids)})
                    count = result.fetchone()[0]
                    logger.info(f"Would fix {count} orphaned journal entries")
                
                if not dry_run:
                    conn.commit()
        
    except Exception as e:
        logger.error(f"Error fixing orphaned transactions: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Find and fix orphaned transactions")
    parser.add_argument("--fix", action="store_true", help="Actually fix the transactions (default: dry run)")
    parser.add_argument("--user-id", type=int, default=1, help="User ID to assign orphaned transactions to")
    args = parser.parse_args()
    
    logger.info("Finding orphaned transactions...")
    orphaned_ledger, orphaned_journal = find_orphaned_transactions()
    
    if orphaned_ledger or orphaned_journal:
        logger.info(f"\n{'DRY RUN: ' if not args.fix else ''}Fixing orphaned transactions...")
        fix_orphaned_transactions(assign_to_user_id=args.user_id, dry_run=not args.fix)
        if not args.fix:
            logger.info("\nTo actually fix, run with --fix flag")
    else:
        logger.info("No orphaned transactions found. Database is clean!")

