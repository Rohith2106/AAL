"""
IFRS-Based Accrual Engine Service

Implements periodic accrual processing to recognize revenue/expense over time
following accounting constitution rules:
- Asset ↓ → Expense ↑
- Liability ↓ → Revenue ↑
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import logging

try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    # Fallback if dateutil not available
    def relativedelta(*args, **kwargs):
        raise ImportError("python-dateutil is required. Install with: pip install python-dateutil")
from sqlalchemy.orm import Session

from app.db.sql import (
    SessionLocal, ClaimRight, AmortizationEntry, AmortizationSchedule,
    Account, JournalEntry, JournalEntryLine, User
)
from app.services.accounting_service import get_or_create_account

logger = logging.getLogger(__name__)


# =============================================================================
# Account Codes for Claim Rights
# =============================================================================

# Asset claim accounts (prepaid expenses)
PREPAID_EXPENSE_ACCOUNT = "1400"  # Prepaid Expenses
DEFERRED_REVENUE_ACCOUNT = "2400"  # Deferred Revenue (liability)

# Default expense/revenue accounts (can be customized per claim)
DEFAULT_EXPENSE_ACCOUNT = "5990"  # General Expense
DEFAULT_REVENUE_ACCOUNT = "4100"  # Sales Revenue


# =============================================================================
# Accrual Processing
# =============================================================================

def process_accruals_for_period(
    user_id: int,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Process all pending accruals for a given accounting period.
    
    This function implements the core accrual logic:
    - For ASSET_CLAIM: Reduce asset, increase expense
    - For LIABILITY_CLAIM: Reduce liability, increase revenue
    
    Args:
        user_id: User ID to process accruals for
        period_start: Start of accounting period (defaults to current month start)
        period_end: End of accounting period (defaults to current month end)
        dry_run: If True, don't post entries, just return what would be posted
    
    Returns:
        Dictionary with processing results
    """
    db = SessionLocal()
    try:
        # Default to current month if not specified
        if not period_start:
            period_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if not period_end:
            next_month = period_start + relativedelta(months=1)
            period_end = next_month - timedelta(days=1)
            period_end = period_end.replace(hour=23, minute=59, second=59)
        
        # Find all pending amortization entries for this period
        pending_entries = db.query(AmortizationEntry).join(ClaimRight).filter(
            ClaimRight.user_id == user_id,
            ClaimRight.status == "active",
            AmortizationEntry.status == "PENDING",
            AmortizationEntry.period_start <= period_end,
            AmortizationEntry.period_end >= period_start
        ).all()
        
        results = {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "entries_processed": 0,
            "total_amount": 0.0,
            "asset_claims": 0,
            "liability_claims": 0,
            "errors": [],
            "posted_entries": []
        }
        
        for entry in pending_entries:
            try:
                result = process_single_accrual(entry, user_id, dry_run)
                results["entries_processed"] += 1
                results["total_amount"] += entry.amount
                
                if entry.claim_right.claim_type == "ASSET_CLAIM":
                    results["asset_claims"] += 1
                else:
                    results["liability_claims"] += 1
                
                if not dry_run:
                    results["posted_entries"].append({
                        "entry_id": entry.id,
                        "claim_right_id": entry.claim_right_id,
                        "amount": entry.amount,
                        "type": entry.claim_right.claim_type
                    })
            except Exception as e:
                error_msg = f"Error processing entry {entry.id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                results["errors"].append(error_msg)
        
        if not dry_run:
            db.commit()
        
        logger.info(f"Processed {results['entries_processed']} accruals for user {user_id}")
        
        return results
    finally:
        db.close()


def process_single_accrual(
    entry: AmortizationEntry,
    user_id: int,
    dry_run: bool = False
) -> JournalEntry:
    """
    Process a single amortization entry.
    
    Accounting logic:
    - ASSET_CLAIM: Dr Expense, Cr Prepaid Asset (Asset ↓, Expense ↑)
    - LIABILITY_CLAIM: Dr Deferred Revenue, Cr Revenue (Liability ↓, Revenue ↑)
    """
    db = SessionLocal()
    try:
        claim = entry.claim_right
        
        if claim.claim_type == "ASSET_CLAIM":
            return _process_asset_claim_accrual(entry, user_id, dry_run)
        elif claim.claim_type == "LIABILITY_CLAIM":
            return _process_liability_claim_accrual(entry, user_id, dry_run)
        else:
            raise ValueError(f"Unknown claim type: {claim.claim_type}")
    finally:
        db.close()


def _process_asset_claim_accrual(
    entry: AmortizationEntry,
    user_id: int,
    dry_run: bool = False
) -> JournalEntry:
    """
    Process asset claim accrual: Asset ↓ → Expense ↑
    
    Journal Entry:
    Dr Expense Account
    Cr Prepaid Expenses (Asset)
    """
    db = SessionLocal()
    try:
        claim = entry.claim_right
        
        # Get or create accounts
        prepaid_account = get_or_create_account(
            user_id, PREPAID_EXPENSE_ACCOUNT, "Prepaid Expenses", "asset"
        )
        
        # Try to get expense account from ledger entry category
        expense_account_code = DEFAULT_EXPENSE_ACCOUNT
        if claim.ledger_entry_id:
            ledger_entry = db.query(LedgerEntry).filter(
                LedgerEntry.id == claim.ledger_entry_id
            ).first()
            if ledger_entry and ledger_entry.category:
                from app.services.accounting_service import CATEGORY_TO_EXPENSE_ACCOUNT
                expense_account_code = CATEGORY_TO_EXPENSE_ACCOUNT.get(
                    ledger_entry.category, DEFAULT_EXPENSE_ACCOUNT
                )
        
        expense_account = get_or_create_account(
            user_id, expense_account_code, "Expense", "expense"
        )
        
        # Create journal entry
        journal_entry = JournalEntry(
            user_id=user_id,
            ledger_entry_id=claim.ledger_entry_id,
            entry_date=entry.period_start,
            reference=f"AMORT-{claim.id}-{entry.period_number}",
            description=f"Amortization: {claim.description} (Period {entry.period_number})",
            memo=f"Claim Right {claim.id} - Asset Claim Amortization",
            is_adjusting=True
        )
        
        db.add(journal_entry)
        db.flush()
        
        # Debit Expense (increase expense)
        expense_line = JournalEntryLine(
            journal_entry_id=journal_entry.id,
            account_id=expense_account.id,
            debit=entry.amount,
            credit=0.0,
            description=f"Expense recognition for {claim.description}"
        )
        
        # Credit Prepaid Asset (decrease asset)
        prepaid_line = JournalEntryLine(
            journal_entry_id=journal_entry.id,
            account_id=prepaid_account.id,
            debit=0.0,
            credit=entry.amount,
            description=f"Prepaid expense reduction for {claim.description}"
        )
        
        db.add(expense_line)
        db.add(prepaid_line)
        
        if not dry_run:
            # Update entry status
            entry.status = "POSTED"
            entry.posted_at = datetime.utcnow()
            entry.journal_entry_id = journal_entry.id
            
            # Update claim right amounts
            claim.amortized_amount += entry.amount
            claim.remaining_amount -= entry.amount
            
            # Check if claim is fully amortized
            if abs(claim.remaining_amount) < 0.01:  # Allow for rounding
                claim.status = "completed"
        
        db.flush()
        
        logger.info(f"Posted asset claim accrual: Entry {entry.id}, Amount {entry.amount}")
        
        return journal_entry
    finally:
        db.close()


def _process_liability_claim_accrual(
    entry: AmortizationEntry,
    user_id: int,
    dry_run: bool = False
) -> JournalEntry:
    """
    Process liability claim accrual: Liability ↓ → Revenue ↑
    
    Journal Entry:
    Dr Deferred Revenue (Liability)
    Cr Revenue Account
    """
    db = SessionLocal()
    try:
        claim = entry.claim_right
        
        # Get or create accounts
        deferred_account = get_or_create_account(
            user_id, DEFERRED_REVENUE_ACCOUNT, "Deferred Revenue", "liability"
        )
        
        # Try to get revenue account from ledger entry
        revenue_account_code = DEFAULT_REVENUE_ACCOUNT
        if claim.ledger_entry_id:
            ledger_entry = db.query(LedgerEntry).filter(
                LedgerEntry.id == claim.ledger_entry_id
            ).first()
            if ledger_entry:
                # Use service revenue for service-based transactions
                revenue_account_code = "4200"  # Service Revenue
        
        revenue_account = get_or_create_account(
            user_id, revenue_account_code, "Revenue", "revenue"
        )
        
        # Create journal entry
        journal_entry = JournalEntry(
            user_id=user_id,
            ledger_entry_id=claim.ledger_entry_id,
            entry_date=entry.period_start,
            reference=f"AMORT-{claim.id}-{entry.period_number}",
            description=f"Amortization: {claim.description} (Period {entry.period_number})",
            memo=f"Claim Right {claim.id} - Liability Claim Amortization",
            is_adjusting=True
        )
        
        db.add(journal_entry)
        db.flush()
        
        # Debit Deferred Revenue (decrease liability)
        deferred_line = JournalEntryLine(
            journal_entry_id=journal_entry.id,
            account_id=deferred_account.id,
            debit=entry.amount,
            credit=0.0,
            description=f"Deferred revenue reduction for {claim.description}"
        )
        
        # Credit Revenue (increase revenue)
        revenue_line = JournalEntryLine(
            journal_entry_id=journal_entry.id,
            account_id=revenue_account.id,
            debit=0.0,
            credit=entry.amount,
            description=f"Revenue recognition for {claim.description}"
        )
        
        db.add(deferred_line)
        db.add(revenue_line)
        
        if not dry_run:
            # Update entry status
            entry.status = "POSTED"
            entry.posted_at = datetime.utcnow()
            entry.journal_entry_id = journal_entry.id
            
            # Update claim right amounts
            claim.amortized_amount += entry.amount
            claim.remaining_amount -= entry.amount
            
            # Check if claim is fully amortized
            if abs(claim.remaining_amount) < 0.01:  # Allow for rounding
                claim.status = "completed"
        
        db.flush()
        
        logger.info(f"Posted liability claim accrual: Entry {entry.id}, Amount {entry.amount}")
        
        return journal_entry
    finally:
        db.close()


# =============================================================================
# Utility Functions
# =============================================================================

def get_pending_accruals_count(user_id: int) -> int:
    """Get count of pending accrual entries for a user."""
    db = SessionLocal()
    try:
        return db.query(AmortizationEntry).join(ClaimRight).filter(
            ClaimRight.user_id == user_id,
            ClaimRight.status == "active",
            AmortizationEntry.status == "PENDING"
        ).count()
    finally:
        db.close()


def get_claim_right_summary(user_id: int) -> Dict[str, Any]:
    """Get summary of claim rights for a user."""
    db = SessionLocal()
    try:
        claims = db.query(ClaimRight).filter(
            ClaimRight.user_id == user_id,
            ClaimRight.status == "active"
        ).all()
        
        asset_total = sum(c.total_amount for c in claims if c.claim_type == "ASSET_CLAIM")
        liability_total = sum(c.total_amount for c in claims if c.claim_type == "LIABILITY_CLAIM")
        asset_remaining = sum(c.remaining_amount for c in claims if c.claim_type == "ASSET_CLAIM")
        liability_remaining = sum(c.remaining_amount for c in claims if c.claim_type == "LIABILITY_CLAIM")
        
        return {
            "total_claims": len(claims),
            "asset_claims": len([c for c in claims if c.claim_type == "ASSET_CLAIM"]),
            "liability_claims": len([c for c in claims if c.claim_type == "LIABILITY_CLAIM"]),
            "total_asset_amount": asset_total,
            "total_liability_amount": liability_total,
            "remaining_asset_amount": asset_remaining,
            "remaining_liability_amount": liability_remaining,
            "pending_accruals": get_pending_accruals_count(user_id)
        }
    finally:
        db.close()

