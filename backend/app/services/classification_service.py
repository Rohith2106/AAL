"""
LLM-based classification service for categorizing receipts and invoices.
"""

from typing import Dict, Any, Optional, Tuple
from app.services.llm_orchestrator import get_llm
from langchain.schema import HumanMessage
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

CATEGORY_CHOICES = [
    "Food & Beverage",
    "Transportation",
    "Accommodation",
    "Office Supplies",
    "Utilities",
    "Healthcare",
    "Entertainment",
    "Retail/Shopping",
    "Professional Services",
    "Software/Technology",
    "Travel",
    "Education",
    "General Expense",
]


async def classify_transaction(structured_data: Dict[str, Any]) -> str:
    """
    Classify transaction using LLM for better accuracy
    
    Args:
        structured_data: Structured receipt data
    
    Returns:
        Category string
    """
    try:
        llm = get_llm()
        
        vendor = structured_data.get("vendor", "Unknown")
        items = structured_data.get("items", [])
        total = structured_data.get("total", 0)
        
        # Build items description
        items_text = ", ".join([item.get("name", "") for item in items[:5]])
        
        prompt = f"""
You are an expert accounting classifier. Read the transaction details and
respond with a strict JSON object describing the category and confidence.

Categories (choose the single best match):
{json.dumps(CATEGORY_CHOICES)}

Transaction Details:
- Vendor: {vendor}
- Items: {items_text or "Unknown"}
- Total: {total}

Respond with JSON ONLY in this shape:
{{
  "category": "<one of the categories>",
  "confidence": <number between 0 and 1>
}}

If unsure, choose "General Expense" with a low confidence.
"""
        
        # Run LLM call with timeout
        def call_llm():
            return llm.invoke([HumanMessage(content=prompt)])
        
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(None, call_llm),
            timeout=20.0  # Increased from 10s to 20s
        )
        
        category, confidence = _parse_llm_response(response.content)
        logger.info(f"Classified transaction as: {category} (confidence={confidence:.2f})")
        return category
    
    except asyncio.TimeoutError:
        logger.warning("Classification timed out, using rule-based fallback")
        return _rule_based_classification(structured_data)
    except Exception as e:
        logger.warning(f"Classification error: {e}, using rule-based fallback")
        return _rule_based_classification(structured_data)


def _parse_llm_response(response_text: str) -> Tuple[str, float]:
    """Parse LLM JSON response into category and confidence."""
    text = response_text.strip()
    if "```" in text:
        # Remove markdown fences
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
    text = text.strip()

    try:
        data = json.loads(text)
        category = data.get("category", "General Expense")
        confidence = float(data.get("confidence", 0.7))
    except Exception:
        category = text.splitlines()[0] if text else "General Expense"
        confidence = 0.5

    if category not in CATEGORY_CHOICES:
        category = "General Expense"
    confidence = max(0.0, min(1.0, confidence))
    return category, confidence


def _rule_based_classification(structured_data: Dict[str, Any]) -> str:
    """Fallback rule-based classification"""
    vendor = (structured_data.get("vendor") or "").lower()
    items = structured_data.get("items", [])
    items_text = " ".join([item.get("name", "").lower() for item in items])
    text = f"{vendor} {items_text}"
    
    # Food & Beverage
    if any(k in text for k in ["starbucks", "coffee", "cafe", "restaurant", "food", "pizza", "burger", "dining", "meal", "beverage", "drink"]):
        return "Food & Beverage"
    
    # Transportation
    if any(k in text for k in ["taxi", "uber", "lyft", "train", "bus", "metro", "subway", "flight", "airline", "parking", "gas", "fuel"]):
        return "Transportation"
    
    # Accommodation
    if any(k in text for k in ["hotel", "lodge", "airbnb", "accommodation", "resort"]):
        return "Accommodation"
    
    # Office Supplies
    if any(k in text for k in ["office", "stationery", "supplies", "paper", "pen", "printer"]):
        return "Office Supplies"
    
    # Utilities
    if any(k in text for k in ["electric", "water", "gas", "utility", "internet", "phone", "cable"]):
        return "Utilities"
    
    # Healthcare
    if any(k in text for k in ["pharmacy", "drug", "medical", "hospital", "clinic", "doctor", "health"]):
        return "Healthcare"
    
    # Entertainment
    if any(k in text for k in ["movie", "cinema", "theater", "concert", "sports", "game", "entertainment"]):
        return "Entertainment"
    
    # Software/Technology
    if any(k in text for k in ["software", "cloud", "saas", "subscription", "app", "tech", "it", "computer"]):
        return "Software/Technology"
    
    # Professional Services
    if any(k in text for k in ["legal", "consulting", "accounting", "service", "professional"]):
        return "Professional Services"
    
    # Retail/Shopping
    if any(k in text for k in ["store", "shop", "retail", "market", "mall", "walmart", "target", "amazon"]):
        return "Retail/Shopping"
    
    return "General Expense"

