"""
Test MOMI receipt extraction to verify all items are captured including "Ice Java Tea"
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.ocr_service import extract_text_from_image
from app.services.extraction_service import parse_receipt_text
import json


async def test_momi_receipt():
    """Test extraction on MOMI receipt (1.jpg) - the one with Ice Java Tea"""
    image_path = "images/1.jpg"
    
    print("=" * 80)
    print("Testing MOMI Receipt (images/1.jpg)")
    print("Expected items: Woman, Ham Cheese, Ice Java Tea, Mineral Water, Black & White")
    print("=" * 80)
    
    try:
        # Read image
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
        # Extract OCR text
        print("\n1. OCR Extraction:")
        print("-" * 40)
        ocr_text = await extract_text_from_image(image_bytes)
        print(ocr_text[:500] + "..." if len(ocr_text) > 500 else ocr_text)
        
        # Parse receipt
        print("\n2. Parsing Results:")
        print("-" * 40)
        structured_data = await parse_receipt_text(ocr_text)
        
        print(f"Vendor: {structured_data.get('vendor')}")
        print(f"Date: {structured_data.get('date')}")
        print(f"Total: ${structured_data.get('total')}")
        print(f"Items Extracted: {len(structured_data.get('items', []))}")
        
        # Expected items
        expected_items = ["woman", "ham cheese", "ice java tea", "mineral water", "black & white"]
        
        if structured_data.get('items'):
            print("\n3. Line Items:")
            print("-" * 40)
            found_items = []
            for item in structured_data['items']:
                print(f"  ✓ {item['name']}: {item['quantity']} x ${item['unit_price']} = ${item['line_total']}")
                found_items.append(item['name'].lower())
            
            # Check for missing items
            print("\n4. Validation:")
            print("-" * 40)
            all_found = True
            for expected in expected_items:
                if any(expected in found.lower() for found in found_items):
                    print(f"  ✓ Found: {expected}")
                else:
                    print(f"  ✗ MISSING: {expected}")
                    all_found = False
            
            if all_found:
                print("\n✅ SUCCESS! All items captured including Ice Java Tea")
            else:
                print("\n❌ FAILURE: Some items are still missing")
                
            # Check total
            expected_total = 175000.0  # Indonesian format
            if abs(structured_data.get('total', 0) - expected_total) < 1.0:
                print(f"✅ Total matches: ${structured_data.get('total')} ≈ ${expected_total}")
            else:
                print(f"⚠️  Total mismatch: ${structured_data.get('total')} vs ${expected_total}")
        else:
            print("\n❌ FAILURE: NO ITEMS EXTRACTED!")
        
        # Save results
        output_file = "momi_test_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'ocr_text': ocr_text,
                'structured_data': structured_data
            }, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_momi_receipt())
