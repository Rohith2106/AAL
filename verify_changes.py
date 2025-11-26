import asyncio
import os
import sys
from PIL import Image, ImageDraw, ImageFont
import io
import json
from dotenv import load_dotenv

# Load env from backend/.env
load_dotenv(os.path.join(os.getcwd(), "backend", ".env"))

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.ocr_service import extract_text_from_image
from app.services.extraction_service import parse_receipt_text

async def create_dummy_receipt():
    """Create a dummy receipt image for testing"""
    # Larger image, white background
    img = Image.new('RGB', (600, 800), color='white')
    d = ImageDraw.Draw(img)
    
    # Try to load a font, otherwise use default
    try:
        font = ImageFont.truetype("arial.ttf", 24)
        header_font = ImageFont.truetype("arial.ttf", 36)
    except IOError:
        font = ImageFont.load_default()
        header_font = ImageFont.load_default()
    
    # Add text with better spacing
    d.text((200, 50), "STORE NAME", fill=(0, 0, 0), font=header_font)
    d.text((50, 120), "Date: 2023-10-27", fill=(0, 0, 0), font=font)
    
    y = 200
    d.text((50, y), "Item 1", fill=(0, 0, 0), font=font)
    d.text((450, y), "$10.00", fill=(0, 0, 0), font=font)
    
    y += 50
    d.text((50, y), "Item 2", fill=(0, 0, 0), font=font)
    d.text((450, y), "$20.00", fill=(0, 0, 0), font=font)
    
    y += 80
    d.line((50, y, 550, y), fill=(0, 0, 0), width=2)
    
    y += 20
    d.text((50, y), "Total", fill=(0, 0, 0), font=header_font)
    d.text((450, y), "$30.00", fill=(0, 0, 0), font=header_font)
    
    # Save to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

async def main():
    print("Starting verification...")
    
    # Create dummy receipt
    image_bytes = await create_dummy_receipt()
    
    # Test OCR
    print("\nTesting OCR...")
    try:
        text = await extract_text_from_image(image_bytes, ocr_engine="tesseract")
        print(f"OCR Text:\n{'-'*20}\n{text}\n{'-'*20}")
    except Exception as e:
        print(f"OCR Failed: {e}")
        return

    # Test Extraction
    print("\nTesting Extraction...")
    try:
        data = await parse_receipt_text(text)
        print(f"Extracted Data:\n{json.dumps(data, indent=2)}")
        
        # Assertions
        total = data.get("total")
        vendor = data.get("vendor", "")
        
        if total != 30.0:
            print(f"FAILURE: Expected total 30.0, got {total}")
        
        if "STORE" not in vendor.upper():
            print(f"FAILURE: Vendor mismatch. Expected 'STORE' in '{vendor}'")
            
        if total == 30.0 and "STORE" in vendor.upper():
            print("\nVerification Successful!")
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"Extraction Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
