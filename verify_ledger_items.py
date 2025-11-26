import asyncio
import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Load env from backend/.env
load_dotenv(os.path.join(os.getcwd(), "backend", ".env"))

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.ledger_service import create_ledger_entry, get_ledger_entry, delete_ledger_entry
from app.db.sql import init_db

async def main():
    print("Starting ledger items verification...")
    
    # Initialize DB to ensure tables exist
    init_db()
    
    # Create dummy data
    record_id = f"test_record_{datetime.now().timestamp()}"
    structured_data = {
        "vendor": "Test Store",
        "date": "2023-10-27",
        "total": 30.0,
        "items": [
            {"name": "Item 1", "quantity": 1, "unit_price": 10.0, "line_total": 10.0},
            {"name": "Item 2", "quantity": 2, "unit_price": 10.0, "line_total": 20.0}
        ]
    }
    orchestration_result = {
        "validation_result": {
            "status": "valid",
            "confidence": 0.9
        }
    }
    
    try:
        # Create entry
        print(f"Creating entry {record_id}...")
        entry = create_ledger_entry(record_id, structured_data, orchestration_result)
        print(f"Entry created with ID: {entry.id}")
        
        # Retrieve entry
        print("Retrieving entry...")
        retrieved = get_ledger_entry(record_id)
        print(f"Retrieved entry:\n{json.dumps(retrieved, indent=2, default=str)}")
        
        # Verify items
        items = retrieved.get("items", [])
        if len(items) != 2:
            print(f"FAILURE: Expected 2 items, got {len(items)}")
            sys.exit(1)
            
        item1 = next((i for i in items if i["name"] == "Item 1"), None)
        if not item1 or item1["line_total"] != 10.0:
            print(f"FAILURE: Item 1 mismatch: {item1}")
            sys.exit(1)
            
        print("\nVerification Successful!")
        
        # Cleanup
        delete_ledger_entry(record_id)
        print("Cleanup complete")
        
    except Exception as e:
        print(f"Verification Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
