"""
Add currency support columns to ledger_entries table
Run from project root: cd backend && python ../add_currency_columns.py
"""
import sys
import pymysql
from urllib.parse import urlparse

def get_db_config():
    """Parse DATABASE_URL from settings"""
    # Default MySQL connection for AAL project
    return {
        'host': 'localhost',
        'user': 'root',
        'password': '',  # Update if you have a password
        'database': 'aal_ledger',
        'port': 3306
    }

def migrate():
    """Add currency columns to ledger_entries"""
    try:
        config = get_db_config()
        print(f"Connecting to MySQL database: {config['database']}...")
        
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        
        # Check if columns exist
        cursor.execute("SHOW COLUMNS FROM ledger_entries LIKE 'currency'")
        if cursor.fetchone():
            print("✅ Currency columns already exist!")
            return
        
        print("Adding currency columns...")
        
        # Add columns
        cursor.execute("""
            ALTER TABLE ledger_entries 
            ADD COLUMN currency VARCHAR(3) DEFAULT 'USD' AFTER total
        """)
        
        cursor.execute("""
            ALTER TABLE ledger_entries 
            ADD COLUMN exchange_rate FLOAT DEFAULT 1.0 AFTER currency
        """)
        
        cursor.execute("""
            ALTER TABLE ledger_entries 
            ADD COLUMN usd_total FLOAT AFTER exchange_rate
        """)
        
        # Update existing records
        cursor.execute("""
            UPDATE ledger_entries 
            SET usd_total = total 
            WHERE usd_total IS NULL
        """)
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        print("Currency columns added:")
        print("  - currency (VARCHAR(3), default 'USD')")
        print("  - exchange_rate (FLOAT, default 1.0)")
        print("  - usd_total (FLOAT)")
        print("\nPlease restart the backend server.")
        
        cursor.close()
        conn.close()
        
    except pymysql.Error as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nIf you get 'Access denied', update the password in this script.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
