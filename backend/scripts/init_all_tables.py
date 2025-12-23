"""
Initialize all database tables including new claim rights tables
Run this to ensure all tables are created
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.sql import init_db, Base, engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("Initializing all database tables...")
    try:
        # This will create all tables defined in Base
        Base.metadata.create_all(bind=engine)
        logger.info("✅ All tables initialized successfully!")
        logger.info("Created/verified tables:")
        for table_name in Base.metadata.tables.keys():
            logger.info(f"  - {table_name}")
    except Exception as e:
        logger.error(f"Error initializing tables: {e}", exc_info=True)
        raise

