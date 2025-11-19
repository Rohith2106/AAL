"""
Script to create MySQL database for the ledger.

This script creates the ledger_db database if it doesn't exist.

Run this script once before starting the application:
    python scripts/setup_mysql_db.py
    OR
    python -m scripts.setup_mysql_db
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import app modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import pymysql
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_mysql_database():
    """Create MySQL database if it doesn't exist"""
    try:
        # Parse connection string
        # Format: mysql+pymysql://root:1234@localhost:3306/ledger_db
        url = settings.DATABASE_URL
        
        # Extract connection details
        if "mysql+pymysql://" in url:
            url = url.replace("mysql+pymysql://", "")
        
        # Split into parts
        auth_part, host_part = url.split("@")
        username, password = auth_part.split(":")
        host, db_part = host_part.split("/")
        hostname, port = host.split(":") if ":" in host else (host, "3306")
        database = db_part.split("?")[0] if "?" in db_part else db_part
        
        logger.info(f"Connecting to MySQL at {hostname}:{port}")
        logger.info(f"Username: {username}")
        logger.info(f"Target database: {database}")
        
        # Connect to MySQL (without specifying database)
        connection = pymysql.connect(
            host=hostname,
            port=int(port),
            user=username,
            password=password,
            charset='utf8mb4'
        )
        
        try:
            with connection.cursor() as cursor:
                # Create database if it doesn't exist
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                logger.info(f"✅ Database '{database}' created or already exists")
                
                # Show databases
                cursor.execute("SHOW DATABASES")
                databases = cursor.fetchall()
                logger.info(f"\nAvailable databases:")
                for db in databases:
                    logger.info(f"  - {db[0]}")
        
        finally:
            connection.close()
        
        logger.info(f"\n✅ MySQL setup complete!")
        logger.info(f"Database '{database}' is ready to use.")
        logger.info(f"\nThe application will create tables automatically on first run.")
        
    except Exception as e:
        logger.error(f"Error setting up MySQL database: {e}")
        logger.error("\nTroubleshooting:")
        logger.error("1. Ensure MySQL is running")
        logger.error("2. Verify credentials (username: root, password: 1234)")
        logger.error("3. Check MySQL service status")
        raise


if __name__ == "__main__":
    setup_mysql_database()

