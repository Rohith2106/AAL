"""
Enhanced receipt/invoice text extraction and structuring service.
Implements logic from Menna_Noseer_step1_OCR.ipynb and LLMOCR_Experiments_evan.ipynb
"""

import re
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logging.warning("rapidfuzz not available, fuzzy matching disabled")

try:
    from sentence_transformers import SentenceTransformer, util
    SENTENCE_TRANSFORMER_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMER_AVAILABLE = False
    logging.warning("sentence-transformers not available, semantic fallback disabled")

logger = logging.getLogger(__name__)
from app.core.llm import get_llm
from langchain.schema import HumanMessage
import json
import asyncio


# Configuration parameters
VENDOR_TOP_LINES = 3  # Number of top lines used to detect vendor name
FUZZY_THRESHOLD = 70  # Minimum score (0-100) for fuzzy text matching
SEMANTIC_THRESHOLD = 0.65  # Cosine similarity threshold for semantic detection
CURRENCY_CHARS = r'[$¥€£₹₩]|Rp'  # Supported currency symbols

# Keyword groups for total, subtotal, payment, etc.
KEYWORDS_TOTAL = ["total", "amount due", "grand total", "balance", "final total"]
KEYWORDS_SUBTOTAL = ["subtotal", "sub total", "sub-total"]
KEYWORDS_TAX = ["tax", "vat", "gst", "sales tax"]
KEYWORDS_CASH = ["cash", "paid", "payment", "received", "cash tend"]
KEYWORDS_CHANGE = ["change", "return", "change due"]

# Regex patterns to extract items (quantity, name, price)
ITEM_QTY_PATTERNS = [
    # Walmart style: ITEM_NAME ITEM_CODE F/N/X PRICE
    r'^([A-Za-z\s&/\-]+?)\s+\d{10,}\s+[FNX]\s+([\d,\.]+)\s+[FNXOT]?\s*$',
    # Standard: 2x Item Name $12.34
    r'^(\d+)[xX]\s+([A-Za-z&\-\s]+?)\s+([\d,\.]+)$',
    # Name ... Price
    r'^(.+?)\s{2,}([\d,\.]+)$',
    # Name Price (with currency)
    r'^(.+?)\s+([$¥€£₹₩Rp]?\s*[\d,\.]+)$',
]


def parse_price(price_str: str) -> Optional[float]:
    """
    Convert a currency string into a float.
    Handles both comma and period as decimal separators.
    Enhanced to handle Indonesian format (e.g., "16,000" = 16000).
    
    Examples:
    - "144.02" → 144.02
    - "144,02" → 144.02 (if appears to be decimal)
    - "16,000" → 16000.0 (Indonesian thousands separator)
    - "175,000" → 175000.0
    - "2.96" → 2.96
    - "2,96" → 2.96
    
    Args:
        price_str: Price string with optional currency symbols
    
    Returns:
        Float value or None if parsing fails
    """
    if not price_str:
        return None
    
    # Remove currency symbols and extra spaces
    cleaned = re.sub(r'[\s' + CURRENCY_CHARS + ']', '', price_str)
    
    # Count decimal separators
    has_period = '.' in cleaned
    has_comma = ',' in cleaned
    
    # Special handling for Indonesian format: X,XXX or XX,XXX or XXX,XXX
    # If comma is present and there are exactly 3 digits after it, it's probably thousands separator
    if has_comma and not has_period:
        parts = cleaned.split(',')
        if len(parts) == 2:
            # Check if last part is exactly 3 digits (thousands separator)
            if len(parts[1]) == 3 and parts[1].isdigit():
                # Indonesian format: "16,000" -> 16000
                cleaned = cleaned.replace(',', '')
            else:
                # European decimal format: "16,50" -> 16.50
                cleaned = cleaned.replace(',', '.')
        elif len(parts) > 2:
            # Multiple commas: "175,000,000" - remove all commas
            cleaned = cleaned.replace(',', '')
        else:
            # Single part, shouldn't happen but fallback
            cleaned = cleaned.replace(',', '.')
    elif has_period and not has_comma:
        # Standard US format: 144.02 - already good
        pass
    elif has_period and has_comma:
        # Has both - determine which is decimal based on position
        last_period_pos = cleaned.rfind('.')
        last_comma_pos = cleaned.rfind(',')
        if last_period_pos > last_comma_pos:
            # Period is decimal: 1,234.56
            cleaned = cleaned.replace(',', '')
        else:
            # Comma is decimal: 1.234,56
            cleaned = cleaned.replace('.', '').replace(',', '.')
    
    try:
        return float(cleaned)
    except ValueError:
        return None



def fuzzy_find(keywords: List[str], lines: List[str], threshold: int = FUZZY_THRESHOLD) -> Optional[str]:
    """
    Find a line that fuzzy matches any of the keywords.
    
    Args:
        keywords: List of keywords to search for
        lines: List of text lines to search
        threshold: Minimum fuzzy match score (0-100)
    
    Returns:
        Matching line or None
    """
    if not RAPIDFUZZ_AVAILABLE:
        # Fallback to simple substring search
        for line in lines:
            line_lower = line.lower()
            for keyword in keywords:
                if keyword.lower() in line_lower:
                    return line
        return None
    
    for line in lines:
        match = process.extractOne(line.lower(), keywords, scorer=fuzz.partial_ratio)
        if match and match[1] >= threshold:
            return line
    return None


def extract_amount(text: str) -> Optional[float]:
    """
    Extract amount from text line.
    
    Args:
        text: Text line containing amount
    
    Returns:
        Extracted amount or None
    """
    if not text:
        return None
    
    # Try to find amount pattern
    match = re.search(r'([¥$€£₹₩Rp]?\s*\d[\d,\.]*)', text)
    if match:
        return parse_price(match.group(1))
    return None


def semantic_fallback(lines: List[str], target_keywords: List[str]) -> Optional[float]:
    """
    Use semantic similarity to find lines containing target keywords.
    
    Args:
        lines: List of text lines
        target_keywords: Keywords to search for semantically
    
    Returns:
        Extracted amount or None
    """
    if not SENTENCE_TRANSFORMER_AVAILABLE or not lines:
        return None
    
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        key_vecs = model.encode(target_keywords, convert_to_tensor=True)
        line_vecs = model.encode(lines, convert_to_tensor=True)
        sim = util.cos_sim(line_vecs, key_vecs)
        
        # Find line with highest similarity to any keyword
        max_sim = 0
        best_line_idx = -1
        for i, line in enumerate(lines):
            max_line_sim = float(sim[i].max())
            if max_line_sim > max_sim:
                max_sim = max_line_sim
                best_line_idx = i
        
        if max_sim >= SEMANTIC_THRESHOLD and best_line_idx >= 0:
            return extract_amount(lines[best_line_idx])
    except Exception as e:
        logger.warning(f"Semantic fallback error: {e}")
    
    return None


def _consolidate_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge duplicate line items with similar names."""
    consolidated: List[Dict[str, Any]] = []
    index_map: Dict[str, int] = {}

    for item in items:
        name = re.sub(r'\s+', ' ', item.get("name", "")).strip()
        if not name:
            continue
        key = re.sub(r'[^a-z0-9]+', '', name.lower())
        if key in index_map:
            idx = index_map[key]
            consolidated[idx]["quantity"] += item.get("quantity", 1)
            consolidated[idx]["line_total"] += item.get("line_total", 0.0)
            if consolidated[idx]["quantity"] > 0:
                consolidated[idx]["unit_price"] = round(
                    consolidated[idx]["line_total"] / consolidated[idx]["quantity"], 2
                )
        else:
            cleaned = {
                "name": name,
                "quantity": item.get("quantity", 1),
                "unit_price": item.get("unit_price", 0.0),
                "line_total": item.get("line_total", 0.0)
            }
            consolidated.append(cleaned)
            index_map[key] = len(consolidated) - 1

    return consolidated


def _normalize_amount(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


async def extract_with_llm(raw_text: str) -> Dict[str, Any]:
    """
    Extract structured data from raw OCR text using LLM.
    
    Args:
        raw_text: Raw OCR text
    
    Returns:
        Structured dictionary
    """
    llm = get_llm()
    
    prompt = f"""You are an expert data extraction system. Extract structured financial data from the following OCR text from a receipt or invoice.

    OCR Text:
    {raw_text}
    
    Extract the following fields:
    - vendor: Name of the vendor/store
    - date: Date of transaction (YYYY-MM-DD format if possible, otherwise preserve original format)
    - invoice_number: Invoice or receipt number
    - currency: ISO currency code (USD, IDR, ZAR, EUR, GBP, etc.) based on the country/vendor location
    - items: List of ALL items purchased. For each item include:
      * name: string - the item name
      * quantity: number - quantity purchased (default to 1 if not specified)
      * unit_price: string - price per unit (preserve formatting like "16,000" or "74.00")
      * line_total: string - total for this line item (preserve formatting)
    - subtotal: Subtotal amount (as string, preserve formatting like "175,000")
    - tax: Tax amount (as string)
    - total: Total amount (as string)
    - usd_equivalent: Convert the total to USD (as float, e.g., 175000 IDR = 11.67 USD)
    - exchange_rate: Exchange rate used for conversion (local currency to USD, e.g., 15000 for IDR)
    - payment_method: Payment method (CASH, CARD, etc.)
    - cash_given: Cash given/tendered (if applicable)
    - change: Change returned (if applicable)
    
    CRITICAL INSTRUCTIONS:
    1. Extract EVERY line item from the receipt - do not skip any items
    2. Return all monetary values as STRINGS to preserve formatting (e.g., "175,000" not 175000, "16.00" not 16)
    3. Look for patterns like "1 Item Name    16,000" or "2x Item Name $10.00" or "Item Name        $5.99"
    4. For items with quantity at the start (e.g., "1 Ice Java Tea"), make sure quantity field is set correctly
    5. Ensure the number of items in your response matches the actual line items on the receipt
    6. DETECT CURRENCY: Look at vendor location, country, currency symbols to determine the currency
       - Indonesian receipts (MOMI, Jakarta, Indonesia) → currency = "IDR", exchange_rate ≈ 15000
       - South African receipts (SPAR, ZAR, Rand) → currency = "ZAR", exchange_rate ≈ 18
       - US receipts → currency = "USD", exchange_rate = 1
    7. CONVERT TO USD: Calculate usd_equivalent = total / exchange_rate
    
    EXAMPLE FORMAT (Indonesian Receipt):
    {{
      "vendor": "MOMI & Toy's",
      "date": "26/01/2015",
      "currency": "IDR",
      "items": [
        {{"name": "Woman", "quantity": 1, "unit_price": "0", "line_total": "0"}},
        {{"name": "Ham Cheese", "quantity": 2, "unit_price": "8,000", "line_total": "16,000"}},
        {{"name": "Ice Java Tea", "quantity": 1, "unit_price": "16,000", "line_total": "16,000"}},
        {{"name": "Mineral Water", "quantity": 1, "unit_price": "13,000", "line_total": "13,000"}}
      ],
      "subtotal": "175,000",
      "total": "175,000",
      "usd_equivalent": 11.67,
      "exchange_rate": 15000,
      "payment_method": "CASH"
    }}
    
    Return ONLY a valid JSON object with these fields. If a field is missing, set it to null.
    """
    
    try:
        # Run LLM call in executor
        def call_llm():
            return llm.invoke([HumanMessage(content=prompt)])
        
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(None, call_llm),
            timeout=30.0
        )
        response_text = response.content
        
        # Parse JSON
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        logger.debug(f"LLM response (first 500 chars): {response_text[:500]}")
        
        data = json.loads(response_text)
        
        # Post-process monetary values: convert strings to floats using parse_price
        if data.get('subtotal'):
            data['subtotal'] = parse_price(str(data['subtotal']))
        if data.get('tax'):
            data['tax'] = parse_price(str(data['tax']))
        if data.get('total'):
            data['total'] = parse_price(str(data['total']))
        if data.get('cash_given'):
            data['cash_given'] = parse_price(str(data['cash_given']))
        if data.get('change'):
            data['change'] = parse_price(str(data['change']))
        
        # Process items
        if data.get('items'):
            for item in data['items']:
                if item.get('unit_price'):
                    item['unit_price'] = parse_price(str(item['unit_price']))
                if item.get('line_total'):
                    item['line_total'] = parse_price(str(item['line_total']))
        
        return data
    except json.JSONDecodeError as json_err:
        logger.error(f"LLM JSON parsing error: {json_err} | Response: {response_text[:200]}")
        return {}
    except Exception as e:
        logger.error(f"LLM extraction error: {e}", exc_info=True)
        return {}



async def parse_receipt_text(raw_text: str) -> Dict[str, Any]:
    """
    Parse structured data from OCR text with enhanced extraction logic.
    Uses LLM as primary extractor, falling back to regex/heuristic logic if needed.
    
    Args:
        raw_text: Raw OCR text
    
    Returns:
        Structured dictionary with vendor, date, items, totals, etc.
    """
    # Try LLM extraction first
    try:
        llm_result = await extract_with_llm(raw_text)
        if llm_result and llm_result.get("total") is not None:
            llm_result["raw_text"] = raw_text
            # Ensure description is present
            if not llm_result.get("description"):
                if llm_result.get("items"):
                    item_names = [item["name"] for item in llm_result["items"][:3]]
                    llm_result["description"] = f"Purchase: {', '.join(item_names)}"
                    if len(llm_result["items"]) > 3:
                        llm_result["description"] += f" and {len(llm_result['items']) - 3} more items"
                else:
                    llm_result["description"] = f"Transaction from {llm_result.get('vendor', 'Unknown')}"
            return llm_result
    except Exception as e:
        logger.warning(f"LLM extraction failed, falling back to regex: {e}")

    # Fallback to regex logic
    # Clean and prepare text

    # Clean and prepare text
    raw_lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    clean_text = re.sub(r'[^\w\s\.\,\-:\/\$\¥\€\£\₹\₩Rp]', ' ', raw_text)
    processed_lines = [line.strip() for line in clean_text.split("\n") if line.strip()]
    lines = processed_lines or raw_lines
    
    result = {
        "vendor": None,
        "date": None,
        "items": [],
        "subtotal": None,
        "tax": None,
        "total": None,
        "payment_method": None,
        "cash_given": None,
        "change": None,
        "invoice_number": None,
        "description": None,
        "raw_text": raw_text
    }
    
    # EXTRACT VENDOR NAME
    # The top few lines usually contain the store or brand name
    vendor_lines = raw_lines or lines
    if vendor_lines:
        vendor_candidates = []
        skip_words = {"receipt", "invoice", "bill", "thank", "you", "copy", "customer", "date", "time"}
        
        for line in vendor_lines[: VENDOR_TOP_LINES + 2]:
            words = line.split()
            # Filter out lines that are mostly numbers or dates
            if not re.match(r'^[\d\s\-\/\.:]+$', line):
                # Filter out common header words
                filtered = [w for w in words if w.lower() not in skip_words and len(w) > 2]
                if filtered:
                    vendor_candidates.append(" ".join(filtered))
                    if len(vendor_candidates) >= 2:  # Take first 2 meaningful lines
                        break
        
        if vendor_candidates:
            vendor_name = " ".join(vendor_candidates)[:100].strip()
            
            # Clean common OCR errors
            vendor_name = vendor_name.replace('Te]', 'Tel')
            vendor_name = vendor_name.replace(']', 'l')
            vendor_name = vendor_name.replace('|', 'I')
            # Remove special characters except common ones
            vendor_name = re.sub(r'[^\w\s&\-\']', '', vendor_name)
            
            result["vendor"] = vendor_name.title() if vendor_name else "Unknown Vendor"
        else:
            # Fallback: use first line, clean it
            first_line = re.sub(r'[\d\|\:\#]', '', lines[0]).strip()[:100]
            result["vendor"] = first_line.title() if first_line else "Unknown Vendor"
    
    # EXTRACT DATE
    # Common date formats used in receipts
    date_patterns = [
        r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',  # MM/DD/YYYY or DD/MM/YYYY
        r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',  # YYYY-MM-DD
        r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b',  # Month DD, YYYY
        r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b',  # DD Month YYYY
        r'Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # Date: MM/DD/YYYY
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            result["date"] = match.group(1) if match.groups() else match.group(0)
            break
    # Normalize date format if detected
    if result["date"]:
        result["date"] = result["date"].strip()
    
    # EXTRACT INVOICE/RECEIPT NUMBER
    invoice_patterns = [
        r'(?:invoice|receipt|inv|rec)[\s#:]*([A-Z0-9\-]+)',
        r'#\s*([A-Z0-9\-]+)',
        r'No[.:]\s*([A-Z0-9\-]+)',
        r'REF[#:\s]+([A-Z0-9\-]+)',
    ]
    for pattern in invoice_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            result["invoice_number"] = match.group(1)
            break
    
    # EXTRACT ITEMS - Enhanced for multiple receipt formats
    logger.info("Starting item extraction...")
    item_lines = raw_lines or lines
    items_extracted = 0
    
    for line in item_lines:
        # Skip summary lines, headers, and non-item lines
        # More precise filtering - only skip if line STARTS with these keywords or is clearly a total line
        if re.search(r'^\s*(?:total|subtotal|tax|amount due|balance|payment|thank you|scan with)', line, re.IGNORECASE):
            continue
        if re.search(r'\b(?:cash|change)\s*(?:tendered|given|due)?\s*[\d,\.]+\s*$', line, re.IGNORECASE):
            continue
        if re.search(r'(?:items sold|store hours|customer copy|merchant copy)', line, re.IGNORECASE):
            continue
        if len(line.strip()) < 3:
            continue
        
        # PATTERN 0: SPAR/Multi-column format - "ITEM_NAME    SIZE/UNIT    PRICE [LETTER]"
        # Example: "LAZENBY WORCESTER SAUCE   12SML        17,99 A"
        # Example: "MILKY BAR CHOC            80GR         16,99"
        # Matches: uppercase item name, size/unit (digits+letters), price, optional letter suffix
        spar_match = re.match(r'^([A-Z][A-Z\s/\-&]+?)\s{2,}([\dA-Z]+(?:GR|ML|KG|L|G|M|S|TUB|\'S)?)\s{2,}([\d,\.]+)\s*[A-Z\+\*]?\s*$', line)
        if spar_match:
            name, size, price_str = spar_match.groups()
            price = parse_price(price_str)
            
            if price is not None and price > 0 and len(name.strip()) > 2:
                # Include size in item name for clarity
                full_name = f"{name.strip()} ({size})"
                result["items"].append({
                    "name": full_name,
                    "quantity": 1,
                    "unit_price": price,
                    "line_total": price
                })
                items_extracted += 1
                logger.debug(f"Extracted SPAR item: {full_name} = ${price}")
                continue
            
        # PATTERN 1: Quantity first - "1 Ice Java Tea       16,000" or "2 Ham Cheese         74,000"
        qty_first_match = re.match(r'^(\d+)\s+([A-Za-z][A-Za-z\s&/\-]+?)\s{2,}([\d,\.]+)\s*$', line)
        if qty_first_match:
            qty_str, name, price_str = qty_first_match.groups()
            qty = int(qty_str) if qty_str.isdigit() else 1
            price = parse_price(price_str)
            
            if price is not None and price >= 0 and len(name.strip()) > 2:
                result["items"].append({
                    "name": name.strip(),
                    "quantity": qty,
                    "unit_price": price / qty if qty > 0 else price,
                    "line_total": price
                })
                items_extracted += 1
                logger.debug(f"Extracted qty-first item: {qty}x {name.strip()} = ${price}")
                continue
        
        # PATTERN 2: Walmart style - "ITEM_NAME    ITEMCODE F  PRICE O"
        walmart_match = re.match(r'^([A-Z][A-Z\s&/\-]+?)\s+(\d{10,})\s+[FNXOT]\s+([\d,\.]+)\s*[FNXOT]?\s*$', line)
        if walmart_match:
            name = walmart_match.group(1).strip()
            price_str = walmart_match.group(3)
            price = parse_price(price_str)
            
            if price is not None and price > 0 and len(name) > 2:
                result["items"].append({
                    "name": name,
                    "quantity": 1,
                    "unit_price": price,
                    "line_total": price
                })
                items_extracted += 1
                logger.debug(f"Extracted Walmart item: {name} = ${price}")
                continue
        
        # PATTERN 3: Quantity with x - "2x Item Name $12.34" or "2x Item Name    12.34"
        qty_x_match = re.match(r'^(\d+)[xX\*]\s+(.+?)\s{2,}([\d,\.]+)$', line)
        if qty_x_match:
            qty_str, name, price_str = qty_x_match.groups()
            qty = int(qty_str) if qty_str.isdigit() else 1
            price = parse_price(price_str)
            
            if price is not None and price > 0 and len(name.strip()) > 2:
                result["items"].append({
                    "name": name.strip(),
                    "quantity": qty,
                    "unit_price": price / qty if qty > 0 else price,
                    "line_total": price
                })
                items_extracted += 1
                logger.debug(f"Extracted qty-x item: {qty}x {name} = ${price}")
                continue
        
        # PATTERN 4: Name with multiple spaces then price - "Item Name        12.34"
        space_match = re.match(r'^(.+?)\s{2,}([\d,\.]+)$', line)
        if space_match:
            name, price_str = space_match.groups()
            
            # Additional check: name shouldn't be just numbers or dates
            if re.match(r'^[\d\s\-\/\.:]+$', name):
                continue
                
            price = parse_price(price_str)
            
            if price is not None and price >= 0 and len(name.strip()) > 2:
                result["items"].append({
                    "name": name.strip(),
                    "quantity": 1,
                    "unit_price": price,
                    "line_total": price
                })
                items_extracted += 1
                logger.debug(f"Extracted spaced item: {name.strip()} = ${price}")
                continue
        
        # PATTERN 5: Mixed case with single space - "Item Name 12.34" (more relaxed)
        # Only try this if name has letters and price is at the end
        simple_match = re.match(r'^([A-Za-z][A-Za-z\s&/\-]+?)\s+([\d,\.]+)$', line)
        if simple_match:
            name, price_str = simple_match.groups()
            price = parse_price(price_str)
            
            # Only accept if price seems reasonable and name is meaningful
            if price is not None and price > 0 and len(name.strip()) > 3:
                # Check that the last word before price isn't a keyword
                words = name.strip().split()
                if words and words[-1].lower() not in ['subtotal', 'total', 'tax', 'cash', 'change', 'balance']:
                    result["items"].append({
                        "name": name.strip(),
                        "quantity": 1,
                        "unit_price": price,
                        "line_total": price
                    })
                    items_extracted += 1
                    logger.debug(f"Extracted simple item: {name.strip()} = ${price}")
                    continue
    
    logger.info(f"Extracted {items_extracted} items from receipt")    
    # Consolidate items to avoid duplicates
    if result["items"]:
        result["items"] = _consolidate_items(result["items"])

    # EXTRACT TOTALS AND PAYMENT INFO
    # Use fuzzy matching for better keyword detection
    total_line = fuzzy_find(KEYWORDS_TOTAL, lines) if RAPIDFUZZ_AVAILABLE else None
    subtotal_line = fuzzy_find(KEYWORDS_SUBTOTAL, lines) if RAPIDFUZZ_AVAILABLE else None
    tax_line = fuzzy_find(KEYWORDS_TAX, lines) if RAPIDFUZZ_AVAILABLE else None
    cash_line = fuzzy_find(KEYWORDS_CASH, lines) if RAPIDFUZZ_AVAILABLE else None
    change_line = fuzzy_find(KEYWORDS_CHANGE, lines) if RAPIDFUZZ_AVAILABLE else None
    
    # Extract total using regex first
    # Try SPAR format: "TOTAL    FOR 14 ITEMS    338.16" or "TOTAL FOR 14 ITEMS 338.16"
    total_match_spar = re.search(
        r'TOTAL\s+(?:FOR\s+)?\d+\s+ITEMS?\s+([\d,\.]+)',
        raw_text, re.IGNORECASE
    )
    if total_match_spar:
        price = parse_price(total_match_spar.group(1))
        if price and price > 0:
            result["total"] = price
            logger.debug(f"Extracted SPAR format total: ${price}")
    
    # Standard total pattern
    if not result["total"]:
        total_match = re.search(
            r'\b(?:total|amount\s+due|grand\s+total|balance|final\s+total)[\s:]*([$¥€£₹₩Rp]?\s*[\d,]+\.?\d{2}?)',
            raw_text, re.IGNORECASE
        )
        if total_match:
            price = parse_price(total_match.group(1))
            if price and price > 0:
                result["total"] = price
    elif total_line:
        result["total"] = extract_amount(total_line)
    else:
        # Semantic fallback for total
        result["total"] = semantic_fallback(lines, KEYWORDS_TOTAL)
    
    # Extract subtotal
    subtotal_match = re.search(
        r'\b(?:subtotal|sub\s+total|sub-total)[\s:]*([$¥€£₹₩Rp]?\s*[\d,]+\.?\d{2}?)',
        raw_text, re.IGNORECASE
    )
    if subtotal_match:
        price = parse_price(subtotal_match.group(1))
        if price and price > 0:
            result["subtotal"] = price
    elif subtotal_line:
        result["subtotal"] = extract_amount(subtotal_line)
    
    # Extract tax
    tax_match = re.search(
        r'\b(?:tax|vat|gst|sales\s+tax)[\s:]*([$¥€£₹₩Rp]?\s*[\d,]+\.?\d{2}?)',
        raw_text, re.IGNORECASE
    )
    if tax_match:
        price = parse_price(tax_match.group(1))
        if price and price > 0:
            result["tax"] = price
    elif tax_line:
        result["tax"] = extract_amount(tax_line)
    
    # Extract cash given
    if cash_line:
        result["cash_given"] = extract_amount(cash_line)
    else:
        cash_match = re.search(
            r'\b(?:cash|paid|payment|cash\s+tend)[\s:]*([$¥€£₹₩Rp]?\s*[\d,]+\.?\d*)',
            raw_text, re.IGNORECASE
        )
        if cash_match:
            result["cash_given"] = parse_price(cash_match.group(1))
    
    # Extract change
    if change_line:
        result["change"] = extract_amount(change_line)
    else:
        change_match = re.search(
            r'\b(?:change|return|change\s+due)[\s:]*([$¥€£₹₩Rp]?\s*[\d,]+\.?\d*)',
            raw_text, re.IGNORECASE
        )
        if change_match:
            result["change"] = parse_price(change_match.group(1))
    
    # DETECT PAYMENT METHOD
    if re.search(r'\bCASH\b', raw_text, re.IGNORECASE):
        result["payment_method"] = "CASH"
    elif re.search(r'\bCARD\b|\bVISA\b|\bMASTER\b|\bDEBIT\b|\bCREDIT\b', raw_text, re.IGNORECASE):
        result["payment_method"] = "CARD"
    else:
        result["payment_method"] = "UNKNOWN"
    
    # POST-PROCESSING
    # Calculate subtotal if missing
    if result["subtotal"] is None and result["items"]:
        result["subtotal"] = sum(item["line_total"] for item in result["items"])
    
    # Set total if missing
    if result["total"] is None:
        if result["subtotal"] and result["tax"]:
            result["total"] = result["subtotal"] + result["tax"]
        elif result["subtotal"]:
            result["total"] = result["subtotal"]
    
    # Normalize monetary fields
    for key in ["subtotal", "tax", "total", "cash_given", "change"]:
        result[key] = _normalize_amount(result[key])

    # If subtotal and tax exist but total differs significantly, recompute total
    if result["subtotal"] is not None and result["tax"] is not None:
        combined = round(result["subtotal"] + result["tax"], 2)
        if result["total"] is None or abs(combined - result["total"]) > 0.5:
            result["total"] = combined

    # Generate description
    if result["items"]:
        item_names = [item["name"] for item in result["items"][:3]]
        result["description"] = f"Purchase: {', '.join(item_names)}"
        if len(result["items"]) > 3:
            result["description"] += f" and {len(result['items']) - 3} more items"
    else:
        result["description"] = f"Transaction from {result['vendor']}"
    
    return result
