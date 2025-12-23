"""
Migration script to add user_id column to journal_entries and accounts tables
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


def migrate_journal_entries():
    """Add user_id column to journal_entries table if it doesn't exist"""
    db = SessionLocal()
    try:
        with engine.connect() as conn:
            # For MySQL
            if 'mysql' in str(engine.url):
                # Check journal_entries
                result = conn.execute(text("""
                    SELECT COUNT(*) as count
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = 'journal_entries'
                    AND COLUMN_NAME = 'user_id'
                """))
                count = result.fetchone()[0]
                
                if count == 0:
                    logger.info("Adding user_id column to journal_entries table...")
                    result = conn.execute(text("SELECT COUNT(*) FROM journal_entries"))
                    existing_count = result.fetchone()[0]
                    
                    if existing_count > 0:
                        logger.warning(f"Found {existing_count} existing journal entries. Setting user_id to 1 (default user).")
                        conn.execute(text("""
                            ALTER TABLE journal_entries
                            ADD COLUMN user_id INT NOT NULL DEFAULT 1,
                            ADD INDEX idx_journal_entries_user_id (user_id)
                        """))
                        try:
                            conn.execute(text("""
                                ALTER TABLE journal_entries
                                ADD CONSTRAINT fk_journal_entries_user_id
                                FOREIGN KEY (user_id) REFERENCES users(id)
                                ON DELETE CASCADE
                            """))
                        except Exception as e:
                            logger.warning(f"Could not add foreign key constraint: {e}")
                    else:
                        conn.execute(text("""
                            ALTER TABLE journal_entries
                            ADD COLUMN user_id INT NOT NULL,
                            ADD INDEX idx_journal_entries_user_id (user_id)
                        """))
                        try:
                            conn.execute(text("""
                                ALTER TABLE journal_entries
                                ADD CONSTRAINT fk_journal_entries_user_id
                                FOREIGN KEY (user_id) REFERENCES users(id)
                                ON DELETE CASCADE
                            """))
                        except Exception as e:
                            logger.warning(f"Could not add foreign key constraint: {e}")
                    
                    conn.commit()
                    logger.info("Successfully added user_id column to journal_entries table")
                else:
                    logger.info("user_id column already exists in journal_entries table")
            
            # For PostgreSQL
            elif 'postgresql' in str(engine.url):
                result = conn.execute(text("""
                    SELECT COUNT(*) as count
                    FROM information_schema.columns
                    WHERE table_name = 'journal_entries'
                    AND column_name = 'user_id'
                """))
                count = result.fetchone()[0]
                
                if count == 0:
                    logger.info("Adding user_id column to journal_entries table...")
                    result = conn.execute(text("SELECT COUNT(*) FROM journal_entries"))
                    existing_count = result.fetchone()[0]
                    
                    if existing_count > 0:
                        logger.warning(f"Found {existing_count} existing journal entries. Setting user_id to 1 (default user).")
                        conn.execute(text("""
                            ALTER TABLE journal_entries
                            ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1
                        """))
                        conn.execute(text("CREATE INDEX idx_journal_entries_user_id ON journal_entries(user_id)"))
                        try:
                            conn.execute(text("""
                                ALTER TABLE journal_entries
                                ADD CONSTRAINT fk_journal_entries_user_id
                                FOREIGN KEY (user_id) REFERENCES users(id)
                                ON DELETE CASCADE
                            """))
                        except Exception as e:
                            logger.warning(f"Could not add foreign key constraint: {e}")
                    else:
                        conn.execute(text("""
                            ALTER TABLE journal_entries
                            ADD COLUMN user_id INTEGER NOT NULL
                        """))
                        conn.execute(text("CREATE INDEX idx_journal_entries_user_id ON journal_entries(user_id)"))
                        try:
                            conn.execute(text("""
                                ALTER TABLE journal_entries
                                ADD CONSTRAINT fk_journal_entries_user_id
                                FOREIGN KEY (user_id) REFERENCES users(id)
                                ON DELETE CASCADE
                            """))
                        except Exception as e:
                            logger.warning(f"Could not add foreign key constraint: {e}")
                    
                    conn.commit()
                    logger.info("Successfully added user_id column to journal_entries table")
                else:
                    logger.info("user_id column already exists in journal_entries table")
            
            # For SQLite
            else:
                logger.info("SQLite detected. Please recreate tables using Base.metadata.create_all()")
        
    except Exception as e:
        logger.error(f"Error migrating journal_entries table: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Starting migration: Adding user_id to journal_entries table")
    migrate_journal_entries()
    logger.info("Migration completed!")

