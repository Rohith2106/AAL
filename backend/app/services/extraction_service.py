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
    r'^(?P<qty>\d+)[xX]?\s+(?P<name>[A-Za-z&\-\s]+?)\s+(?P<price>[¥$€£₹₩Rp]*\s*[\d,]+(?:\.\d{1,2})?)$',
    r'^(?P<name>[A-Za-z&\-\s]+?)\s+(?P<qty>\d+)\s+(?P<price>[¥$€£₹₩Rp]*\s*[\d,]+(?:\.\d{1,2})?)$',
    r'^(?P<name>[A-Za-z&\-\s]+?)\s+(?P<price>[¥$€£₹₩Rp]*\s*[\d,]+(?:\.\d{1,2})?)$',
    r'^(.+?)\s{2,}([\d,]+\.?\d*)$',  # Name ... Price (spaces)
    r'^(.+?)\s+([$¥€£₹₩Rp]?\s*[\d,]+\.?\d*)$',  # Name Price
]


def parse_price(price_str: str) -> Optional[float]:
    """
    Convert a currency string (e.g., '$1,200.00') into a float.
    
    Args:
        price_str: Price string with optional currency symbols
    
    Returns:
        Float value or None if parsing fails
    """
    if not price_str:
        return None
    
    # Remove currency symbols and spaces
    cleaned = re.sub(r'[\s' + CURRENCY_CHARS + ']', '', price_str).replace(',', '')
    
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


def parse_receipt_text(raw_text: str) -> Dict[str, Any]:
    """
    Parse structured data from OCR text with enhanced extraction logic.
    Implements patterns from Menna_Noseer_step1_OCR.ipynb and LLMOCR_Experiments_evan.ipynb
    
    Args:
        raw_text: Raw OCR text
    
    Returns:
        Structured dictionary with vendor, date, items, totals, etc.
    """
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
    
    # EXTRACT ITEMS
    # Parse each line and detect quantity, name, and price
    item_lines = raw_lines or lines
    for line in item_lines:
        # Skip summary lines
        if re.search(r'\b(total|subtotal|tax|cash|change|amount due|balance|payment)\b', line, re.IGNORECASE):
            continue
        
        matched = False
        for pattern in ITEM_QTY_PATTERNS:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    # Pattern: name, price
                    name, price_str = groups
                    qty = 1
                elif len(groups) == 3:
                    # Pattern: qty, name, price or name, qty, price
                    if groups[0].isdigit():
                        qty_str, name, price_str = groups
                        qty = int(qty_str) if qty_str.isdigit() else 1
                    else:
                        name, qty_str, price_str = groups
                        qty = int(qty_str) if qty_str.isdigit() else 1
                else:
                    continue
                
                price = parse_price(price_str)
                name = name.strip()
                
                if price is not None and name and len(name) > 1:
                    result["items"].append({
                        "name": name,
                        "quantity": qty,
                        "unit_price": price,
                        "line_total": price * qty
                    })
                    matched = True
                    break
        
        # Fallback: if not matched, assume last number is price
        if not matched:
            fallback_match = re.search(r'(.+?)\s+([$¥€£₹₩Rp]?\s*\d[\d,\.]*)$', line)
            if fallback_match:
                name, price_str = fallback_match.groups()
                price = parse_price(price_str)
                if price is not None and name.strip():
                    result["items"].append({
                        "name": name.strip(),
                        "quantity": 1,
                        "unit_price": price,
                        "line_total": price
                    })
    
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
