"""
Migration script to add user_id column to ledger_entries table
Run this script to update existing database schema
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.sql import engine, SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_ledger_entries():
    """Add user_id column to ledger_entries table if it doesn't exist"""
    db = SessionLocal()
    try:
        # Check if column exists
        with engine.connect() as conn:
            # For MySQL
            if 'mysql' in str(engine.url):
                result = conn.execute(text("""
                    SELECT COUNT(*) as count
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = 'ledger_entries'
                    AND COLUMN_NAME = 'user_id'
                """))
                count = result.fetchone()[0]
                
                if count == 0:
                    logger.info("Adding user_id column to ledger_entries table...")
                    # First, check if there are existing records
                    result = conn.execute(text("SELECT COUNT(*) FROM ledger_entries"))
                    existing_count = result.fetchone()[0]
                    
                    if existing_count > 0:
                        logger.warning(f"Found {existing_count} existing ledger entries. Setting user_id to 1 (default user).")
                        # Add column with default value
                        conn.execute(text("""
                            ALTER TABLE ledger_entries
                            ADD COLUMN user_id INT NOT NULL DEFAULT 1,
                            ADD INDEX idx_user_id (user_id)
                        """))
                        # Add foreign key constraint
                        try:
                            conn.execute(text("""
                                ALTER TABLE ledger_entries
                                ADD CONSTRAINT fk_ledger_entries_user_id
                                FOREIGN KEY (user_id) REFERENCES users(id)
                                ON DELETE CASCADE
                            """))
                        except Exception as e:
                            logger.warning(f"Could not add foreign key constraint: {e}")
                            logger.info("Continuing without foreign key constraint...")
                    else:
                        # No existing records, can add column without default
                        conn.execute(text("""
                            ALTER TABLE ledger_entries
                            ADD COLUMN user_id INT NOT NULL,
                            ADD INDEX idx_user_id (user_id)
                        """))
                        # Add foreign key constraint
                        try:
                            conn.execute(text("""
                                ALTER TABLE ledger_entries
                                ADD CONSTRAINT fk_ledger_entries_user_id
                                FOREIGN KEY (user_id) REFERENCES users(id)
                                ON DELETE CASCADE
                            """))
                        except Exception as e:
                            logger.warning(f"Could not add foreign key constraint: {e}")
                            logger.info("Continuing without foreign key constraint...")
                    
                    conn.commit()
                    logger.info("Successfully added user_id column to ledger_entries table")
                else:
                    logger.info("user_id column already exists in ledger_entries table")
            
            # For SQLite
            elif 'sqlite' in str(engine.url):
                # SQLite doesn't support ALTER TABLE ADD COLUMN easily, but SQLAlchemy handles it
                logger.info("SQLite detected. Please recreate tables using Base.metadata.create_all()")
                logger.info("Or manually add the column using: ALTER TABLE ledger_entries ADD COLUMN user_id INTEGER")
            
            # For PostgreSQL
            else:
                result = conn.execute(text("""
                    SELECT COUNT(*) as count
                    FROM information_schema.columns
                    WHERE table_name = 'ledger_entries'
                    AND column_name = 'user_id'
                """))
                count = result.fetchone()[0]
                
                if count == 0:
                    logger.info("Adding user_id column to ledger_entries table...")
                    result = conn.execute(text("SELECT COUNT(*) FROM ledger_entries"))
                    existing_count = result.fetchone()[0]
                    
                    if existing_count > 0:
                        logger.warning(f"Found {existing_count} existing ledger entries. Setting user_id to 1 (default user).")
                        conn.execute(text("""
                            ALTER TABLE ledger_entries
                            ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1
                        """))
                        conn.execute(text("CREATE INDEX idx_ledger_entries_user_id ON ledger_entries(user_id)"))
                        try:
                            conn.execute(text("""
                                ALTER TABLE ledger_entries
                                ADD CONSTRAINT fk_ledger_entries_user_id
                                FOREIGN KEY (user_id) REFERENCES users(id)
                                ON DELETE CASCADE
                            """))
                        except Exception as e:
                            logger.warning(f"Could not add foreign key constraint: {e}")
                    else:
                        conn.execute(text("""
                            ALTER TABLE ledger_entries
                            ADD COLUMN user_id INTEGER NOT NULL
                        """))
                        conn.execute(text("CREATE INDEX idx_ledger_entries_user_id ON ledger_entries(user_id)"))
                        try:
                            conn.execute(text("""
                                ALTER TABLE ledger_entries
                                ADD CONSTRAINT fk_ledger_entries_user_id
                                FOREIGN KEY (user_id) REFERENCES users(id)
                                ON DELETE CASCADE
                            """))
                        except Exception as e:
                            logger.warning(f"Could not add foreign key constraint: {e}")
                    
                    conn.commit()
                    logger.info("Successfully added user_id column to ledger_entries table")
                else:
                    logger.info("user_id column already exists in ledger_entries table")
        
    except Exception as e:
        logger.error(f"Error migrating ledger_entries table: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Starting migration: Adding user_id to ledger_entries table")
    migrate_ledger_entries()
    logger.info("Migration completed!")

