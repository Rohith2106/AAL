"""
IFRS-Based Claim Rights Service

Implements claim rights recognition, classification, and amortization schedule generation
following IFRS principles and accounting constitution rules.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    # Fallback if dateutil not available
    def relativedelta(*args, **kwargs):
        raise ImportError("python-dateutil is required. Install with: pip install python-dateutil")
from sqlalchemy.orm import Session

from app.db.sql import (
    SessionLocal, ClaimRight, AmortizationSchedule, AmortizationEntry,
    LedgerEntry, Account, JournalEntry, JournalEntryLine
)

logger = logging.getLogger(__name__)


# =============================================================================
# Claim Right Classification Logic
# =============================================================================

def classify_claim_right(
    structured_data: Dict[str, Any],
    ledger_entry: Optional[LedgerEntry] = None
) -> Optional[str]:
    """
    Classify a transaction as ASSET_CLAIM or LIABILITY_CLAIM based on IFRS rules.
    
    Returns:
        "ASSET_CLAIM" if we have a right to future economic benefits
        "LIABILITY_CLAIM" if others have a right on us
        None if not a long-term transaction
    """
    # Check if this is a long-term transaction
    # Look for indicators: subscription, prepaid, deferred, EMI, loan, etc.
    description = (structured_data.get("description") or "").lower()
    category = (structured_data.get("category") or "").lower()
    vendor = (structured_data.get("vendor") or "").lower()
    payment_method = (structured_data.get("payment_method") or "").lower()
    
    # Keywords that indicate long-term transactions
    prepaid_keywords = ["prepaid", "pre-paid", "subscription", "annual", "yearly", "monthly", "quarterly"]
    deferred_keywords = ["deferred", "advance", "deposit", "retainer", "prepayment"]
    loan_keywords = ["loan", "emi", "installment", "financing", "credit"]
    service_keywords = ["service", "maintenance", "support", "license", "membership"]
    
    combined_text = f"{description} {category} {vendor} {payment_method}".lower()
    
    # Check for prepaid expenses (ASSET_CLAIM - we paid for future benefits)
    if any(keyword in combined_text for keyword in prepaid_keywords + service_keywords):
        # If we're paying for something, it's an asset claim
        if "revenue" not in combined_text and "income" not in combined_text:
            return "ASSET_CLAIM"
    
    # Check for deferred revenue (LIABILITY_CLAIM - we received payment for future delivery)
    if any(keyword in combined_text for keyword in deferred_keywords):
        # If we received payment, it's a liability claim
        return "LIABILITY_CLAIM"
    
    # Check for loans/EMI (LIABILITY_CLAIM - we owe money)
    if any(keyword in combined_text for keyword in loan_keywords):
        return "LIABILITY_CLAIM"
    
    # Check transaction amount and date patterns
    # If amount is large and description suggests recurring payment
    amount = structured_data.get("total") or structured_data.get("amount") or 0.0
    if amount > 1000:  # Threshold for potential long-term transaction
        if any(keyword in combined_text for keyword in ["annual", "yearly", "subscription"]):
            return "ASSET_CLAIM"
    
    return None  # Not a long-term transaction


def determine_amortization_periods(
    start_date: datetime,
    end_date: datetime,
    frequency: str = "monthly"
) -> int:
    """
    Calculate number of periods based on start/end dates and frequency.
    
    Args:
        start_date: Start of amortization period
        end_date: End of amortization period
        frequency: monthly, quarterly, yearly, etc.
    
    Returns:
        Number of periods
    """
    if frequency == "monthly":
        delta = relativedelta(end_date, start_date)
        return delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)
    elif frequency == "quarterly":
        delta = relativedelta(end_date, start_date)
        months = delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)
        return (months + 2) // 3  # Round up to nearest quarter
    elif frequency == "yearly":
        delta = relativedelta(end_date, start_date)
        return delta.years + (1 if delta.months > 0 or delta.days > 0 else 0)
    else:
        # Default to monthly
        delta = relativedelta(end_date, start_date)
        return delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)


def extract_period_dates(
    structured_data: Dict[str, Any]
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Extract start and end dates from structured data.
    
    Returns:
        Tuple of (start_date, end_date) or (None, None) if not found
    """
    # Try to extract dates from various fields
    date_str = structured_data.get("date")
    start_date_str = structured_data.get("start_date") or structured_data.get("period_start")
    end_date_str = structured_data.get("end_date") or structured_data.get("period_end") or structured_data.get("expiry_date")
    
    start_date = None
    end_date = None
    
    # Parse start date
    if start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
        except:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            except:
                pass
    
    # If no start date, use transaction date
    if not start_date and date_str:
        try:
            start_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            try:
                start_date = datetime.strptime(date_str, "%Y-%m-%d")
            except:
                pass
    
    # Parse end date
    if end_date_str:
        try:
            end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
        except:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            except:
                pass
    
    # If no end date, infer from description or default to 12 months
    if not end_date and start_date:
        # Try to extract period from description
        description = (structured_data.get("description") or "").lower()
        if "annual" in description or "yearly" in description:
            end_date = start_date + relativedelta(years=1)
        elif "quarterly" in description:
            end_date = start_date + relativedelta(months=3)
        elif "monthly" in description:
            end_date = start_date + relativedelta(months=1)
        else:
            # Default to 12 months
            end_date = start_date + relativedelta(years=1)
    
    return start_date, end_date


# =============================================================================
# Claim Right Creation
# =============================================================================

def create_claim_right(
    user_id: int,
    ledger_entry_id: Optional[int],
    structured_data: Dict[str, Any],
    claim_type: str,
    total_amount: float,
    start_date: datetime,
    end_date: datetime,
    frequency: str = "monthly",
    description: Optional[str] = None
) -> ClaimRight:
    """
    Create a claim right with initial recognition (no P&L impact).
    
    Following IFRS:
    - Initial recognition: Create balance sheet item only
    - No revenue/expense recognition at this stage
    """
    db = SessionLocal()
    try:
        # Validate IFRS recognition criteria
        is_probable = True  # Assume probable unless specified otherwise
        is_measurable = total_amount > 0
        
        if not is_measurable:
            raise ValueError("Claim right amount must be measurable (greater than 0)")
        
        claim = ClaimRight(
            user_id=user_id,
            ledger_entry_id=ledger_entry_id,
            claim_type=claim_type,
            description=description or structured_data.get("description", "Long-term transaction"),
            total_amount=total_amount,
            remaining_amount=total_amount,  # Initially, nothing is amortized
            amortized_amount=0.0,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            status="active",
            is_probable=is_probable,
            is_measurable=is_measurable
        )
        
        db.add(claim)
        db.commit()
        db.refresh(claim)
        
        logger.info(f"Created claim right {claim.id} of type {claim_type} for amount {total_amount}")
        
        # Generate amortization schedule
        generate_amortization_schedule(claim.id)
        
        return claim
    finally:
        db.close()


def generate_amortization_schedule(claim_right_id: int) -> AmortizationSchedule:
    """
    Generate amortization schedule for a claim right.
    Creates period entries as PENDING.
    """
    db = SessionLocal()
    try:
        claim = db.query(ClaimRight).filter(ClaimRight.id == claim_right_id).first()
        if not claim:
            raise ValueError(f"Claim right {claim_right_id} not found")
        
        if claim.schedule:
            logger.warning(f"Schedule already exists for claim right {claim_right_id}")
            return claim.schedule
        
        # Calculate periods
        total_periods = determine_amortization_periods(
            claim.start_date,
            claim.end_date,
            claim.frequency
        )
        
        if total_periods <= 0:
            raise ValueError("Invalid period: start_date must be before end_date")
        
        # Calculate amount per period
        amount_per_period = claim.total_amount / total_periods
        
        # Create schedule
        schedule = AmortizationSchedule(
            claim_right_id=claim_right_id,
            total_periods=total_periods,
            amount_per_period=amount_per_period,
            is_generated=True,
            generated_at=datetime.utcnow()
        )
        
        db.add(schedule)
        db.flush()  # Get schedule.id
        
        # Generate period entries
        current_date = claim.start_date
        period_number = 1
        
        while current_date < claim.end_date and period_number <= total_periods:
            # Calculate period end
            if claim.frequency == "monthly":
                period_end = current_date + relativedelta(months=1)
            elif claim.frequency == "quarterly":
                period_end = current_date + relativedelta(months=3)
            elif claim.frequency == "yearly":
                period_end = current_date + relativedelta(years=1)
            else:
                period_end = current_date + relativedelta(months=1)
            
            # Ensure period_end doesn't exceed claim.end_date
            if period_end > claim.end_date:
                period_end = claim.end_date
                # Adjust amount for partial period
                days_in_period = (period_end - current_date).days
                total_days = (claim.end_date - claim.start_date).days
                if total_days > 0:
                    amount = claim.total_amount * (days_in_period / total_days)
                else:
                    amount = amount_per_period
            else:
                amount = amount_per_period
            
            # For last period, ensure total matches exactly
            if period_number == total_periods:
                # Calculate remaining amount to ensure exact match
                already_allocated = (period_number - 1) * amount_per_period
                amount = claim.total_amount - already_allocated
            
            entry = AmortizationEntry(
                claim_right_id=claim_right_id,
                schedule_id=schedule.id,
                period_number=period_number,
                period_start=current_date,
                period_end=period_end,
                amount=amount,
                status="PENDING"
            )
            
            db.add(entry)
            
            # Move to next period
            current_date = period_end
            period_number += 1
        
        db.commit()
        db.refresh(schedule)
        
        logger.info(f"Generated amortization schedule with {total_periods} periods for claim right {claim_right_id}")
        
        return schedule
    finally:
        db.close()


# =============================================================================
# Claim Right Queries
# =============================================================================

def get_claim_rights(
    user_id: int,
    claim_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100
) -> List[ClaimRight]:
    """Get claim rights for a user with optional filters."""
    db = SessionLocal()
    try:
        query = db.query(ClaimRight).filter(ClaimRight.user_id == user_id)
        
        if claim_type:
            query = query.filter(ClaimRight.claim_type == claim_type)
        
        if status:
            query = query.filter(ClaimRight.status == status)
        
        return query.order_by(ClaimRight.created_at.desc()).limit(limit).all()
    finally:
        db.close()


def get_claim_right(claim_right_id: int, user_id: int) -> Optional[ClaimRight]:
    """Get a specific claim right by ID."""
    db = SessionLocal()
    try:
        return db.query(ClaimRight).filter(
            ClaimRight.id == claim_right_id,
            ClaimRight.user_id == user_id
        ).first()
    finally:
        db.close()


def cancel_claim_right(claim_right_id: int, user_id: int, reason: Optional[str] = None) -> ClaimRight:
    """
    Cancel a claim right (early termination).
    Marks remaining entries as SKIPPED.
    """
    db = SessionLocal()
    try:
        # Query claim directly in this session to avoid detached instance issues
        claim = db.query(ClaimRight).filter(
            ClaimRight.id == claim_right_id,
            ClaimRight.user_id == user_id
        ).first()
        
        if not claim:
            raise ValueError(f"Claim right {claim_right_id} not found")
        
        if claim.status == "cancelled":
            return claim
        
        claim.status = "cancelled"
        claim.cancellation_date = datetime.utcnow()
        claim.cancellation_reason = reason
        
        # Mark pending entries as skipped
        pending_entries = db.query(AmortizationEntry).filter(
            AmortizationEntry.claim_right_id == claim_right_id,
            AmortizationEntry.status == "PENDING"
        ).all()
        
        for entry in pending_entries:
            entry.status = "SKIPPED"
        
        db.commit()
        db.refresh(claim)
        
        logger.info(f"Cancelled claim right {claim_right_id}")
        
        return claim
    finally:
        db.close()

