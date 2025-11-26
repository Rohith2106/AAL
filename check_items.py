import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.db.sql import SessionLocal, LedgerEntry, LedgerItem

db = SessionLocal()
try:
    # Count total items
    total_items = db.query(LedgerItem).count()
    print(f"Total items in database: {total_items}")
    
    # Get recent entries with items
    entries = db.query(LedgerEntry).order_by(LedgerEntry.created_at.desc()).limit(5).all()
    
    print("\n--- Recent Entries ---")
    for entry in entries:
        item_count = len(entry.items)
        print(f"\nRecord ID: {entry.record_id}")
        print(f"Vendor: {entry.vendor}")
        print(f"Total: ${entry.total}")
        print(f"Items count: {item_count}")
        
        if entry.items:
            for item in entry.items:
                print(f"  - {item.name}: {item.quantity} x ${item.unit_price} = ${item.line_total}")
        else:
            print("  (no items)")
            
finally:
    db.close()
