import sys
import os

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

from app.db.sql import SessionLocal, LedgerEntry, LedgerItem

db = SessionLocal()
try:
    # Find entries by record_id
    target_records = ['record_53319949d8e5', 'record_e452e5f8c438']
    
    for record_id in target_records:
        entry = db.query(LedgerEntry).filter(LedgerEntry.record_id == record_id).first()
        if entry:
            print(f"\n{'='*60}")
            print(f"Record ID: {record_id}")
            print(f"Database ID: {entry.id}")
            print(f"Vendor: {entry.vendor}")
            print(f"Total: ${entry.total}")
            print(f"Items in memory: {len(entry.items)}")
            
            # Query items directly
            direct_items = db.query(LedgerItem).filter(LedgerItem.ledger_entry_id == entry.id).all()
            print(f"Items from direct query: {len(direct_items)}")
            
            if direct_items:
                print("\nItems:")
                for item in direct_items:
                    print(f"  - {item.name}: {item.quantity} x ${item.unit_price} = ${item.line_total}")
            else:
                print("  (no items found)")
        else:
            print(f"\nRecord {record_id} NOT FOUND in database")
    
    # Also show all entries with items
    print(f"\n{'='*60}")
    print("All entries with items:")
    all_entries = db.query(LedgerEntry).all()
    for entry in all_entries:
        item_count = db.query(LedgerItem).filter(LedgerItem.ledger_entry_id == entry.id).count()
        if item_count > 0:
            print(f"  {entry.record_id} (ID={entry.id}): {item_count} items")
            
finally:
    db.close()
