import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.llm import get_llm
from langchain.schema import HumanMessage

logger = logging.getLogger(__name__)


@dataclass
class PerspectiveInput:
    our_company_name: str
    ocr_text: str
    metadata: Optional[Dict[str, Any]] = None


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _split_lines(text: str) -> List[str]:
    return [l.strip() for l in (text or "").splitlines() if l.strip()]


def _contains_company(line: str, company: str) -> bool:
    if not line or not company:
        return False
    line_l = line.lower()
    comp_l = company.lower()
    return comp_l in line_l


def _find_bill_to_name(lines: List[str], our_company: str) -> Optional[str]:
    """
    Try to detect the counterparty in typical invoice layouts:
    - 'Bill To', 'Billed To', 'Customer', 'Client', 'Ship To', 'Buyer'
    The name is usually on the same line after a colon or on the next line.
    Prioritizes explicit "Client:" or "Customer:" labels over "Bill To".
    """
    # First, try to find explicit "Client:" or "Customer:" labels (most reliable)
    explicit_patterns = [
        r"^client[:\s]",
        r"^customer[:\s]",
        r"^buyer[:\s]",
    ]
    explicit_re = re.compile("|".join(explicit_patterns), re.IGNORECASE)
    
    for idx, line in enumerate(lines):
        if not explicit_re.search(line):
            continue

        # Same-line name (e.g. 'Client: Becker Ltd')
        parts = re.split(r"[:\-]", line, maxsplit=1)
        if len(parts) == 2:
            candidate = _normalize(parts[1])
            if candidate and not _contains_company(candidate, our_company):
                # Avoid lines that look like addresses only (very numeric)
                if not re.match(r"^[\d\s,/-]+$", candidate):
                    return candidate

        # Next-line name
        if idx + 1 < len(lines):
            next_line = _normalize(lines[idx + 1])
            if next_line and not _contains_company(next_line, our_company):
                # Avoid lines that look like addresses only (very numeric)
                if not re.match(r"^[\d\s,/-]+$", next_line):
                    return next_line
    
    # Fallback to other patterns (Bill To, Ship To, etc.)
    patterns = [
        r"bill\s*to",
        r"billed\s*to",
        r"ship\s*to",
        r"sold\s*to",
    ]
    label_re = re.compile("|".join(patterns), re.IGNORECASE)

    for idx, line in enumerate(lines):
        if not label_re.search(line):
            continue

        # Same-line name (e.g. 'Bill To: ACME Corp')
        parts = re.split(r"[:\-]", line, maxsplit=1)
        if len(parts) == 2:
            candidate = _normalize(parts[1])
            if candidate and not _contains_company(candidate, our_company):
                # Avoid lines that look like addresses only (very numeric)
                if not re.match(r"^[\d\s,/-]+$", candidate):
                    return candidate

        # Next-line name
        if idx + 1 < len(lines):
            next_line = _normalize(lines[idx + 1])
            if next_line and not _contains_company(next_line, our_company):
                # Avoid lines that look like addresses only (very numeric)
                if not re.match(r"^[\d\s,/-]+$", next_line):
                    return next_line

    return None


def _find_seller_name(lines: List[str], our_company: str) -> Optional[str]:
    """
    Try to detect the seller/issuer name in invoice layouts:
    - 'Seller', 'Vendor', 'From', 'Issued By', 'Company'
    """
    patterns = [
        r"^seller",
        r"^vendor",
        r"^from",
        r"^issued\s*by",
        r"^company",
        r"^supplier",
    ]
    label_re = re.compile("|".join(patterns), re.IGNORECASE)

    for idx, line in enumerate(lines):
        if not label_re.search(line):
            continue

        # Same-line name (e.g. 'Seller: Andrews, Kirby and Valdez')
        parts = re.split(r"[:\-]", line, maxsplit=1)
        if len(parts) == 2:
            candidate = _normalize(parts[1])
            if candidate:
                return candidate

        # Next-line name
        if idx + 1 < len(lines):
            next_line = _normalize(lines[idx + 1])
            if next_line:
                # Avoid lines that look like addresses only (very numeric)
                if not re.match(r"^[\d\s,/-]+$", next_line):
                    return next_line

    return None


def _guess_issuer_name(lines: List[str], metadata: Dict[str, Any], our_company: str) -> Optional[str]:
    """
    Guess the issuer/seller name.
    Priority:
      1) metadata['vendor'] if it doesn't look like our company
      2) top few non-numeric lines
    """
    vendor = (metadata or {}).get("vendor")
    if vendor and not _contains_company(vendor, our_company):
        return _normalize(vendor)

    top_lines = lines[:5]
    skip_words = {"receipt", "invoice", "tax", "thank", "you", "copy", "customer", "date", "time"}
    candidates: List[str] = []

    for line in top_lines:
        if _contains_company(line, our_company):
            continue
        if re.match(r"^[\d\s\-/:,.]+$", line):
            continue
        words = [w for w in line.split() if w.lower() not in skip_words and len(w) > 2]
        if words:
            candidates.append(" ".join(words))

    if candidates:
        return _normalize(candidates[0])
    return None


def _has_pos_receipt_language(text_l: str) -> bool:
    keywords = [
        "thank you for your purchase",
        "thank you for shopping",
        "thank you for visiting",
        "cash tendered",
        "change due",
        "items sold",
        "sales receipt",
        "till slip",
        "kasir",
    ]
    return any(k in text_l for k in keywords)


def _has_invoice_language(text_l: str) -> bool:
    return any(k in text_l for k in ["tax invoice", "invoice", "bill of sale", "statement"])


def _has_refund_language(text_l: str) -> bool:
    return any(k in text_l for k in ["refund", "refunded", "credit note", "credit memorandum", "return authorized"])


def _derive_roles_from_direction(direction: str) -> Dict[str, str]:
    """
    Enforce accounting constitution mapping:
      - OUTFLOW -> we are BUYER, counterparty is VENDOR
      - INFLOW  -> we are VENDOR, counterparty is CUSTOMER
    """
    if direction == "INFLOW":
        return {"ourRole": "VENDOR", "counterpartyRole": "CUSTOMER"}
    # Default & OUTFLOW fall-back
    return {"ourRole": "BUYER", "counterpartyRole": "VENDOR"}


async def _llm_fallback(
    our_company_name: str,
    ocr_text: str,
    metadata: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    LLM-based classifier used only when rules are ambiguous.
    Always post-processed to enforce role mapping invariants.
    """
    try:
        llm = get_llm()
    except Exception as e:
        logger.warning(f"LLM not available for perspective analysis: {e}")
        return {}

    meta_json = {}
    try:
        # Only pass a compact subset of metadata
        if metadata:
            for k in ["vendor", "total", "amount", "payment_method", "invoice_number", "currency"]:
                if k in metadata:
                    meta_json[k] = metadata[k]
    except Exception:
        meta_json = {}

    # Truncate very long OCR text to keep prompt small
    truncated_text = ocr_text[:4000]

    prompt = f"""
You are an accounting expert. Classify the transaction perspective based on OCR text.

ACCOUNTING CONSTITUTION (ALWAYS FOLLOW):
1. Every transaction has two parties: buyer and vendor.
2. Direction determines roles:
   - OUTFLOW → we are BUYER → counterparty is VENDOR/SUPPLIER
   - INFLOW → we are VENDOR → counterparty is CUSTOMER/BUYER
3. Buyer receives a RECEIPT. Vendor issues an INVOICE.
4. Transaction direction is PRIMARY. Wording like 'invoice' or 'receipt' does not override direction.

Our company name: "{our_company_name}"

OCR Text (possibly noisy):
\"\"\"{truncated_text}\"\"\"

Additional metadata (may be incomplete):
{meta_json}

Return ONLY a JSON object with:
{{
  "transactionDirection": "INFLOW" or "OUTFLOW",
  "documentRole": "RECEIPT" | "PURCHASE_INVOICE" | "SALES_INVOICE" | "REFUND_NOTE",
  "counterpartyName": "string or null",
  "confidence": number between 0 and 1
}}

Restrictions:
- Do NOT include any extra keys.
- Do NOT include explanations.
- The mapping between direction and roles must follow the constitution above.
"""

    try:
        def call_llm():
            return llm.invoke([HumanMessage(content=prompt)])

        import asyncio

        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(loop.run_in_executor(None, call_llm), timeout=20.0)
        text = response.content
    except Exception as e:
        logger.warning(f"LLM perspective classification failed: {e}")
        return {}

    # Best-effort JSON extraction without depending on json_parser to keep module testable
    import json

    try:
        # Strip possible markdown fences
        if "```" in text:
            if "```json" in text:
                text = text.split("```json", 1)[1].split("```", 1)[0]
            else:
                text = text.split("```", 1)[1].split("```", 1)[0]
        data = json.loads(text.strip())
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning(f"Failed to parse LLM perspective JSON: {e}")
        return {}


async def analyze_perspective(
    ocr_text: str,
    our_company_name: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Main entry point.

    Args:
        ocr_text: Raw OCR text from the document.
        our_company_name: Legal name of our company for perspective inference.
        metadata: Optional dict with keys like vendor, total, payment_method, invoice_number.

    Returns:
        Dict with fields:
        - transactionDirection: "INFLOW" | "OUTFLOW"
        - ourRole: "BUYER" | "VENDOR"
        - counterpartyRole: "VENDOR" | "CUSTOMER"
        - documentRole: "RECEIPT" | "PURCHASE_INVOICE" | "SALES_INVOICE" | "REFUND_NOTE"
        - counterpartyName: string
        - confidence: float
    """
    text_l = (ocr_text or "").lower()
    lines = _split_lines(ocr_text)
    metadata = metadata or {}
    our_company_name = our_company_name or ""

    # ------------------------------------------------------------------
    # 1) RULES-FIRST: ISSUER VS. OUR COMPANY
    # ------------------------------------------------------------------
    issuer_name = _guess_issuer_name(lines, metadata, our_company_name)
    bill_to_name = _find_bill_to_name(lines, our_company_name)
    seller_name = _find_seller_name(lines, our_company_name)

    # Check for explicit Seller and Client sections (vendor invoice pattern)
    has_seller_section = any(re.search(r"^seller|^vendor", line, re.IGNORECASE) for line in lines)
    has_client_section = any(re.search(r"^client|^customer|^buyer", line, re.IGNORECASE) for line in lines)

    our_in_header = any(_contains_company(line, our_company_name) for line in lines[:6])
    our_in_bill_to = any(
        _contains_company(line, our_company_name)
        and re.search(r"bill\s*to|billed\s*to|customer|client|ship\s*to|sold\s*to|buyer", line, re.IGNORECASE)
        for line in lines
    )
    our_in_seller = any(
        _contains_company(line, our_company_name)
        and re.search(r"^seller|^vendor|^from|^issued\s*by", line, re.IGNORECASE)
        for line in lines
    )

    direction: str
    document_role: str
    counterparty_name: Optional[str] = None
    confidence: float = 0.0

    # Case A: Our company clearly appears as the billed party => we are BUYER, OUTFLOW
    if our_in_bill_to:
        direction = "OUTFLOW"
        if _has_invoice_language(text_l):
            document_role = "PURCHASE_INVOICE"
            confidence = 0.9
        elif _has_pos_receipt_language(text_l):
            document_role = "RECEIPT"
            confidence = 0.85
        else:
            # Conservative: treat as purchase
            document_role = "PURCHASE_INVOICE"
            confidence = 0.75
        counterparty_name = issuer_name or seller_name or metadata.get("vendor")

    # Case B: Our company appears in header / seller area => we are VENDOR, INFLOW
    elif our_in_seller or (our_in_header and not _has_pos_receipt_language(text_l)):
        direction = "INFLOW"
        if _has_invoice_language(text_l):
            document_role = "SALES_INVOICE"
            confidence = 0.9
        elif _has_refund_language(text_l):
            document_role = "REFUND_NOTE"
            confidence = 0.85
        else:
            # Conservative: still treat as sales invoice if we are issuer
            document_role = "SALES_INVOICE"
            confidence = 0.8
        # When we are VENDOR, counterparty is the CLIENT/BUYER (bill_to)
        # Make sure we get the client name, not the seller name
        counterparty_name = bill_to_name
        # If bill_to_name is not found or seems wrong, try to find client explicitly
        if not counterparty_name or counterparty_name == seller_name:
            # Look for explicit Client/Customer section
            for idx, line in enumerate(lines):
                if re.search(r"^(client|customer|buyer)[:\s]", line, re.IGNORECASE):
                    # Try same line extraction
                    parts = re.split(r"[:\-]", line, maxsplit=1)
                    if len(parts) == 2:
                        candidate = _normalize(parts[1])
                        if candidate and candidate != seller_name and not re.match(r"^[\d\s,/-]+$", candidate):
                            counterparty_name = candidate
                            break
                    # Try next line
                    if idx + 1 < len(lines):
                        next_line = _normalize(lines[idx + 1])
                        if next_line and next_line != seller_name and not re.match(r"^[\d\s,/-]+$", next_line):
                            counterparty_name = next_line
                            break

    # Case C: Explicit Seller and Client sections detected (vendor invoice pattern)
    # If we have both seller and client sections, and no company match, assume we are the seller
    elif has_seller_section and has_client_section and not our_company_name:
        direction = "INFLOW"
        document_role = "SALES_INVOICE"
        confidence = 0.85
        # Client is the counterparty (buyer) - we are the seller, so counterparty is the client
        # First try to find client name explicitly
        counterparty_name = None
        for idx, line in enumerate(lines):
            # Look for "Client:" or "Customer:" labels
            if re.search(r"^(client|customer|buyer)[:\s]", line, re.IGNORECASE):
                # Try same line extraction (e.g., "Client: Becker Ltd")
                parts = re.split(r"[:\-]", line, maxsplit=1)
                if len(parts) == 2:
                    candidate = _normalize(parts[1])
                    if candidate and not re.match(r"^[\d\s,/-]+$", candidate):
                        counterparty_name = candidate
                        break
                # Try next line
                if idx + 1 < len(lines):
                    next_line = _normalize(lines[idx + 1])
                    if next_line and not re.match(r"^[\d\s,/-]+$", next_line):
                        counterparty_name = next_line
                        break
        
        # Fallback to bill_to_name if client name not found explicitly
        if not counterparty_name:
            counterparty_name = bill_to_name or _find_bill_to_name(lines, "")

    else:
        # ------------------------------------------------------------------
        # 2) HEURISTICS WITHOUT RELIABLE COMPANY MATCH
        # ------------------------------------------------------------------
        if _has_refund_language(text_l):
            # Refunds are typically money back to us; treat as INFLOW from our perspective
            direction = "INFLOW"
            document_role = "REFUND_NOTE"
            confidence = 0.8
            counterparty_name = issuer_name or bill_to_name or metadata.get("vendor")
        elif _has_pos_receipt_language(text_l) or metadata.get("payment_method") in {"CASH", "CARD"}:
            # Generic POS receipt: conservative assumption is expense (cash out)
            direction = "OUTFLOW"
            document_role = "RECEIPT"
            confidence = 0.8
            counterparty_name = issuer_name or metadata.get("vendor")
        elif _has_invoice_language(text_l):
            # Generic invoice: conservative accounting view is purchase invoice (liability)
            direction = "OUTFLOW"
            document_role = "PURCHASE_INVOICE"
            confidence = 0.7
            counterparty_name = issuer_name or metadata.get("vendor")
        else:
            # ------------------------------------------------------------------
            # 3) AMBIGUOUS -> LLM FALLBACK
            # ------------------------------------------------------------------
            llm_result = await _llm_fallback(our_company_name, ocr_text, metadata)
            if llm_result:
                direction = llm_result.get("transactionDirection", "OUTFLOW")
                document_role = llm_result.get("documentRole", "PURCHASE_INVOICE")
                counterparty_name = llm_result.get("counterpartyName") or issuer_name or metadata.get("vendor")
                try:
                    confidence = float(llm_result.get("confidence", 0.5))
                except Exception:
                    confidence = 0.5
            else:
                # Final conservative default: treat as purchase outflow
                direction = "OUTFLOW"
                document_role = "PURCHASE_INVOICE"
                counterparty_name = issuer_name or metadata.get("vendor")
                confidence = 0.5

    # Clamp & normalize
    if document_role not in {"RECEIPT", "PURCHASE_INVOICE", "SALES_INVOICE", "REFUND_NOTE"}:
        if direction == "INFLOW":
            document_role = "SALES_INVOICE"
        else:
            document_role = "PURCHASE_INVOICE"

    roles = _derive_roles_from_direction(direction)

    # Never allow invalid state:
    #  - OUTFLOW -> CUSTOMER (counterparty)
    #  - INFLOW  -> VENDOR (counterparty)
    # Enforced by _derive_roles_from_direction.

    result = {
        "transactionDirection": direction,
        "ourRole": roles["ourRole"],
        "counterpartyRole": roles["counterpartyRole"],
        "documentRole": document_role,
        "counterpartyName": counterparty_name or "",
        "confidence": max(0.0, min(1.0, confidence)),
    }

    logger.info(
        "Perspective analysis result: dir=%s, our=%s, cp=%s, doc=%s, cp_name=%s, conf=%.2f",
        result["transactionDirection"],
        result["ourRole"],
        result["counterpartyRole"],
        result["documentRole"],
        result["counterpartyName"],
        result["confidence"],
    )
    return result


