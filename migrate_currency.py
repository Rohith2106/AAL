"""
Database migration to add currency support to ledger_entries table
Run this from the backend directory: python ../migrate_currency.py
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.db.sql import SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Add currency columns to ledger_entries table"""
    db = SessionLocal()
    
    try:
        logger.info("Starting database migration for currency support...")
        
        # Check if columns already exist
        result = db.execute(text("SHOW COLUMNS FROM ledger_entries LIKE 'currency'")).first()
        if result:
            logger.info("Currency columns already exist. Migration not needed.")
            return
        
        # Add currency column
        logger.info("Adding currency column...")
        db.execute(text("""
            ALTER TABLE ledger_entries 
            ADD COLUMN currency VARCHAR(3) DEFAULT 'USD' AFTER total
        """))
        
        # Add exchange_rate column
        logger.info("Adding exchange_rate column...")
        db.execute(text("""
            ALTER TABLE ledger_entries 
            ADD COLUMN exchange_rate FLOAT DEFAULT 1.0 AFTER currency
        """))
        
        # Add usd_total column
        logger.info("Adding usd_total column...")
        db.execute(text("""
            ALTER TABLE ledger_entries 
            ADD COLUMN usd_total FLOAT AFTER exchange_rate
        """))
        
        # Update existing records to set usd_total = total for USD entries
        logger.info("Updating existing records...")
        db.execute(text("""
            UPDATE ledger_entries 
            SET usd_total = total 
            WHERE usd_total IS NULL
        """))
        
        db.commit()
        logger.info("=" * 60)
        logger.info("✅ Migration completed successfully!")
        logger.info("=" * 60)
        logger.info("Please restart the backend server for changes to take effect.")
        
    except Exception as e:
        db.rollback()
        logger.error("=" * 60)
        logger.error(f"❌ Migration failed: {e}")
        logger.error("=" * 60)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
