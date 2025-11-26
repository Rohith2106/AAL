import re
from typing import Optional

CURRENCY_CHARS = r'[$¥€£₹₩]|Rp'

def parse_price(price_str: str) -> Optional[float]:
    """
    Convert a currency string into a float.
    Simple rule: comma is always treated as decimal separator.
    """
    if not price_str:
        return None
    
    # Remove currency symbols and spaces
    cleaned = re.sub(r'[\s' + CURRENCY_CHARS + ']', '', price_str)
    
    # Simple rule: replace comma with period (decimal point)
    cleaned = cleaned.replace(',', '.')
    
    try:
        return float(cleaned)
    except ValueError:
        return None

test_cases = [
    "175,000",
    "74,000",
    "16,000",
    "13,000",
    "72,000",
    "1,234.56",
    "1.234,56",
    "175.000",
    "175,000.",
    "TOTAL 175,000",
    "175,000 "
]

print(f"{'Input':<20} | {'Parsed':<10} | {'Expected':<10}")
print("-" * 45)

for case in test_cases:
    # Simulate extraction cleaning if needed, but parse_price handles it
    result = parse_price(case)
    print(f"{case:<20} | {str(result):<10} | {'?'}")
