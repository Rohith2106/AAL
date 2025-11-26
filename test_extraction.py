"""
Test extraction accuracy with sample receipts to identify specific issues
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


async def test_receipt(image_path: str):
    """Test extraction on a single receipt"""
    print(f"\n{'='*80}")
    print(f"Testing: {os.path.basename(image_path)}")
    print(f"{'='*80}")
    
    try:
        # Read image
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
        # Extract OCR text
        print("\n1. OCR Extraction:")
        print("-" * 40)
        ocr_text = await extract_text_from_image(image_bytes)
        print(ocr_text)
        
        # Parse receipt
        print("\n2. Parsing Results:")
        print("-" * 40)
        structured_data = await parse_receipt_text(ocr_text)
        
        print(f"Vendor: {structured_data.get('vendor')}")
        print(f"Date: {structured_data.get('date')}")
        print(f"Total: ${structured_data.get('total')}")
        print(f"Items Extracted: {len(structured_data.get('items', []))}")
        
        if structured_data.get('items'):
            print("\nLine Items:")
            for item in structured_data['items']:
                print(f"  - {item['name']}: {item['quantity']} x ${item['unit_price']} = ${item['line_total']}")
        else:
            print("\n⚠️  NO ITEMS EXTRACTED!")
        
        # Save results
        output_file = f"extraction_result_{os.path.basename(image_path)}.json"
        with open(output_file, 'w') as f:
            json.dump({
                'ocr_text': ocr_text,
                'structured_data': structured_data
            }, f, indent=2)
        print(f"\nResults saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Test multiple receipts from the images folder"""
    images_dir = Path("images")
    
    # Test with a few sample receipts
    test_files = [
        "1.jpg",  # MOMI receipt (the one with Ice Java Tea)
        "0.jpg",
        "2.jpg",
        "3.jpg",
        "4.jpg",
    ]
    
    for filename in test_files:
        image_path = images_dir / filename
        if image_path.exists():
            await test_receipt(str(image_path))
        else:
            print(f"⚠️  File not found: {image_path}")
    
    print(f"\n{'='*80}")
    print("Testing Complete!")
    print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())
