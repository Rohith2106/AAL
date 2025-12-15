"""
Double-Entry Accounting Service

Implements core double-entry accounting logic:
- Chart of Accounts management
- Journal entry creation and validation
- Auto-generation of journal entries from receipt transactions
- Account balance calculations
- Financial reports (Trial Balance, Income Statement, Balance Sheet)
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging
from sqlalchemy.orm import joinedload

from app.db.sql import SessionLocal, Account, JournalEntry, JournalEntryLine, LedgerEntry

logger = logging.getLogger(__name__)


# =============================================================================
# Category to Account Mapping
# =============================================================================

# Maps transaction categories to expense account codes
CATEGORY_TO_EXPENSE_ACCOUNT = {
    "Food & Beverage": "5100",
    "Transportation": "5200",
    "Accommodation": "5300",
    "Office Supplies": "5400",
    "Utilities": "5500",
    "Healthcare": "5600",
    "Entertainment": "5700",
    "Retail/Shopping": "5800",
    "Professional Services": "5900",
    "Software/Technology": "5910",
    "Travel": "5920",
    "Education": "5930",
    "General Expense": "5990",
}

# Maps payment methods to asset/liability account codes
PAYMENT_METHOD_TO_ACCOUNT = {
    "cash": "1100",           # Cash
    "credit card": "2200",    # Credit Card Payable (liability)
    "credit": "2200",         # Credit Card Payable
    "debit card": "1100",     # Cash (debit card = cash equivalent)
    "bank transfer": "1100",  # Cash
    "check": "1100",          # Cash
    "accounts payable": "2100",  # Accounts Payable
    None: "1100",             # Default to Cash
}

# Account type normal balances
NORMAL_BALANCES = {
    "asset": "debit",
    "liability": "credit",
    "equity": "credit",
    "revenue": "credit",
    "expense": "debit",
}


# =============================================================================
# Default Chart of Accounts
# =============================================================================

DEFAULT_ACCOUNTS = [
    # Assets (1000s)
    {"code": "1000", "name": "Assets", "account_type": "asset", "parent_id": None},
    {"code": "1100", "name": "Cash", "account_type": "asset", "parent_id": "1000"},
    {"code": "1200", "name": "Accounts Receivable", "account_type": "asset", "parent_id": "1000"},
    {"code": "1300", "name": "Petty Cash", "account_type": "asset", "parent_id": "1000"},
    
    # Liabilities (2000s)
    {"code": "2000", "name": "Liabilities", "account_type": "liability", "parent_id": None},
    {"code": "2100", "name": "Accounts Payable", "account_type": "liability", "parent_id": "2000"},
    {"code": "2200", "name": "Credit Card Payable", "account_type": "liability", "parent_id": "2000"},
    
    # Equity (3000s)
    {"code": "3000", "name": "Equity", "account_type": "equity", "parent_id": None},
    {"code": "3100", "name": "Owner's Equity", "account_type": "equity", "parent_id": "3000"},
    {"code": "3200", "name": "Retained Earnings", "account_type": "equity", "parent_id": "3000"},
    
    # Revenue (4000s)
    {"code": "4000", "name": "Revenue", "account_type": "revenue", "parent_id": None},
    {"code": "4100", "name": "Sales Revenue", "account_type": "revenue", "parent_id": "4000"},
    {"code": "4200", "name": "Service Revenue", "account_type": "revenue", "parent_id": "4000"},
    
    # Expenses (5000s)
    {"code": "5000", "name": "Expenses", "account_type": "expense", "parent_id": None},
    {"code": "5100", "name": "Food & Beverage Expense", "account_type": "expense", "parent_id": "5000"},
    {"code": "5200", "name": "Transportation Expense", "account_type": "expense", "parent_id": "5000"},
    {"code": "5300", "name": "Accommodation Expense", "account_type": "expense", "parent_id": "5000"},
    {"code": "5400", "name": "Office Supplies Expense", "account_type": "expense", "parent_id": "5000"},
    {"code": "5500", "name": "Utilities Expense", "account_type": "expense", "parent_id": "5000"},
    {"code": "5600", "name": "Healthcare Expense", "account_type": "expense", "parent_id": "5000"},
    {"code": "5700", "name": "Entertainment Expense", "account_type": "expense", "parent_id": "5000"},
    {"code": "5800", "name": "Retail/Shopping Expense", "account_type": "expense", "parent_id": "5000"},
    {"code": "5900", "name": "Professional Services Expense", "account_type": "expense", "parent_id": "5000"},
    {"code": "5910", "name": "Software/Technology Expense", "account_type": "expense", "parent_id": "5000"},
    {"code": "5920", "name": "Travel Expense", "account_type": "expense", "parent_id": "5000"},
    {"code": "5930", "name": "Education Expense", "account_type": "expense", "parent_id": "5000"},
    {"code": "5990", "name": "General Expense", "account_type": "expense", "parent_id": "5000"},
]


# =============================================================================
# Chart of Accounts Functions
# =============================================================================

def initialize_chart_of_accounts():
    """Initialize the default chart of accounts if not exists"""
    db = SessionLocal()
    try:
        # Check if accounts already exist
        existing_count = db.query(Account).count()
        if existing_count > 0:
            logger.info(f"Chart of accounts already initialized with {existing_count} accounts")
            return
        
        # First pass: create all accounts without parent links
        account_map = {}
        for acc_data in DEFAULT_ACCOUNTS:
            account = Account(
                code=acc_data["code"],
                name=acc_data["name"],
                account_type=acc_data["account_type"],
                is_active=True
            )
            db.add(account)
            db.flush()  # Get the ID
            account_map[acc_data["code"]] = account.id
        
        # Second pass: set parent relationships
        for acc_data in DEFAULT_ACCOUNTS:
            if acc_data["parent_id"]:
                parent_code = acc_data["parent_id"]
                if parent_code in account_map:
                    account = db.query(Account).filter(Account.code == acc_data["code"]).first()
                    account.parent_id = account_map[parent_code]
        
        db.commit()
        logger.info(f"Initialized chart of accounts with {len(DEFAULT_ACCOUNTS)} accounts")
    except Exception as e:
        db.rollback()
        logger.error(f"Error initializing chart of accounts: {e}")
        raise
    finally:
        db.close()


def get_account_by_code(code: str) -> Optional[Account]:
    """Get account by its code"""
    db = SessionLocal()
    try:
        return db.query(Account).filter(Account.code == code).first()
    finally:
        db.close()


def get_all_accounts() -> List[Dict[str, Any]]:
    """Get all accounts with their current balances"""
    db = SessionLocal()
    try:
        accounts = db.query(Account).filter(Account.is_active == True).order_by(Account.code).all()
        result = []
        for acc in accounts:
            balance = calculate_account_balance(acc.id)
            result.append({
                "id": acc.id,
                "code": acc.code,
                "name": acc.name,
                "account_type": acc.account_type,
                "parent_id": acc.parent_id,
                "description": acc.description,
                "balance": balance,
                "normal_balance": NORMAL_BALANCES.get(acc.account_type, "debit")
            })
        return result
    finally:
        db.close()


# =============================================================================
# Journal Entry Functions
# =============================================================================

def create_journal_entry(
    ledger_entry_id: Optional[int],
    entry_date: datetime,
    reference: str,
    description: str,
    lines: List[Dict[str, Any]],
    memo: Optional[str] = None
) -> JournalEntry:
    """
    Create a new journal entry with debit/credit lines.
    
    Args:
        ledger_entry_id: Optional link to ledger entry
        entry_date: Date of the transaction
        reference: Reference number (e.g., record_id)
        description: Description of the entry
        lines: List of line items with account_id, debit, credit, description
        memo: Optional additional notes
    
    Returns:
        Created JournalEntry object
    """
    db = SessionLocal()
    try:
        # Validate that debits = credits
        total_debits = sum(line.get("debit", 0) for line in lines)
        total_credits = sum(line.get("credit", 0) for line in lines)
        
        if abs(total_debits - total_credits) > 0.01:  # Allow small rounding errors
            raise ValueError(f"Journal entry not balanced: debits={total_debits}, credits={total_credits}")
        
        # Create journal entry
        journal_entry = JournalEntry(
            ledger_entry_id=ledger_entry_id,
            entry_date=entry_date,
            reference=reference,
            description=description,
            memo=memo,
            is_balanced=True
        )
        db.add(journal_entry)
        db.flush()  # Get the ID
        
        # Create journal entry lines
        for line in lines:
            journal_line = JournalEntryLine(
                journal_entry_id=journal_entry.id,
                account_id=line["account_id"],
                debit=line.get("debit", 0),
                credit=line.get("credit", 0),
                description=line.get("description")
            )
            db.add(journal_line)
        
        db.commit()
        db.refresh(journal_entry)
        logger.info(f"Created journal entry {journal_entry.id} with {len(lines)} lines")
        return journal_entry
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating journal entry: {e}")
        raise
    finally:
        db.close()


def auto_generate_journal_entry(ledger_entry: LedgerEntry, category: Optional[str] = None) -> Optional[JournalEntry]:
    """
    Automatically generate a journal entry for a ledger entry based on category and payment method.
    
    For expense transactions (receipts):
    - DEBIT: Expense account (based on category)
    - CREDIT: Cash/Credit Card/AP account (based on payment method)
    
    Args:
        ledger_entry: The ledger entry to create journal entry for
        category: Transaction category (e.g., "Food & Beverage")
    
    Returns:
        Created JournalEntry or None if failed
    """
    db = SessionLocal()
    try:
        # Get expense account based on category
        expense_account_code = CATEGORY_TO_EXPENSE_ACCOUNT.get(category, "5990")  # Default to General Expense
        expense_account = db.query(Account).filter(Account.code == expense_account_code).first()
        
        # Get payment account based on payment method
        payment_method = (ledger_entry.payment_method or "").lower().strip()
        payment_account_code = PAYMENT_METHOD_TO_ACCOUNT.get(payment_method, "1100")
        payment_account = db.query(Account).filter(Account.code == payment_account_code).first()
        
        if not expense_account or not payment_account:
            logger.warning(f"Could not find accounts for category={category}, payment_method={payment_method}")
            # Initialize accounts if missing
            initialize_chart_of_accounts()
            expense_account = db.query(Account).filter(Account.code == expense_account_code).first()
            payment_account = db.query(Account).filter(Account.code == payment_account_code).first()
        
        if not expense_account or not payment_account:
            logger.error("Failed to find or create required accounts")
            return None
        
        # Determine the amount
        amount = ledger_entry.total or ledger_entry.amount or 0
        
        if amount <= 0:
            logger.warning(f"Cannot create journal entry for zero or negative amount: {amount}")
            return None
        
        # Parse entry date
        try:
            if ledger_entry.date:
                entry_date = datetime.strptime(ledger_entry.date, "%Y-%m-%d")
            else:
                entry_date = ledger_entry.created_at or datetime.utcnow()
        except (ValueError, TypeError):
            entry_date = datetime.utcnow()
        
        # Determine if payment account is liability (credit increases) or asset (credit decreases)
        is_liability = payment_account.account_type == "liability"
        
        # Build journal entry lines
        # For expenses: DEBIT expense, CREDIT cash (if asset) or CREDIT liability (if credit card)
        lines = []
        
        # Debit: Expense account
        lines.append({
            "account_id": expense_account.id,
            "debit": amount,
            "credit": 0,
            "description": f"{category or 'Expense'} - {ledger_entry.vendor or 'Unknown'}"
        })
        
        # Credit: Payment account (Cash or Liability)
        lines.append({
            "account_id": payment_account.id,
            "debit": 0,
            "credit": amount,
            "description": f"Payment for {ledger_entry.vendor or 'transaction'}"
        })
        
        # Create the journal entry
        journal_entry = JournalEntry(
            ledger_entry_id=ledger_entry.id,
            entry_date=entry_date,
            reference=ledger_entry.record_id,
            description=f"{ledger_entry.vendor or 'Unknown'} - {category or 'Expense'}",
            is_balanced=True
        )
        db.add(journal_entry)
        db.flush()
        
        # Add lines
        for line in lines:
            journal_line = JournalEntryLine(
                journal_entry_id=journal_entry.id,
                account_id=line["account_id"],
                debit=line["debit"],
                credit=line["credit"],
                description=line["description"]
            )
            db.add(journal_line)
        
        db.commit()
        db.refresh(journal_entry)
        
        logger.info(f"Auto-generated journal entry {journal_entry.id} for ledger entry {ledger_entry.id}")
        logger.info(f"  DEBIT {expense_account.code} {expense_account.name}: ${amount}")
        logger.info(f"  CREDIT {payment_account.code} {payment_account.name}: ${amount}")
        
        return journal_entry
    except Exception as e:
        db.rollback()
        logger.error(f"Error auto-generating journal entry: {e}", exc_info=True)
        return None
    finally:
        db.close()


def get_journal_entry(journal_entry_id: int) -> Optional[Dict[str, Any]]:
    """Get journal entry with its lines"""
    db = SessionLocal()
    try:
        entry = db.query(JournalEntry).options(
            joinedload(JournalEntry.lines).joinedload(JournalEntryLine.account)
        ).filter(JournalEntry.id == journal_entry_id).first()
        
        if not entry:
            return None
        
        return format_journal_entry(entry)
    finally:
        db.close()


def get_journal_entry_by_ledger_entry(ledger_entry_id: int) -> Optional[Dict[str, Any]]:
    """Get journal entry for a specific ledger entry"""
    db = SessionLocal()
    try:
        entry = db.query(JournalEntry).options(
            joinedload(JournalEntry.lines).joinedload(JournalEntryLine.account)
        ).filter(JournalEntry.ledger_entry_id == ledger_entry_id).first()
        
        if not entry:
            return None
        
        return format_journal_entry(entry)
    finally:
        db.close()


def format_journal_entry(entry: JournalEntry) -> Dict[str, Any]:
    """Format journal entry for API response"""
    return {
        "id": entry.id,
        "ledger_entry_id": entry.ledger_entry_id,
        "entry_date": entry.entry_date.isoformat() if entry.entry_date else None,
        "reference": entry.reference,
        "description": entry.description,
        "memo": entry.memo,
        "is_balanced": entry.is_balanced,
        "is_adjusting": entry.is_adjusting,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "lines": [
            {
                "id": line.id,
                "account_id": line.account_id,
                "account_code": line.account.code if line.account else None,
                "account_name": line.account.name if line.account else None,
                "account_type": line.account.account_type if line.account else None,
                "debit": line.debit,
                "credit": line.credit,
                "description": line.description
            }
            for line in entry.lines
        ],
        "total_debits": sum(line.debit for line in entry.lines),
        "total_credits": sum(line.credit for line in entry.lines)
    }


# =============================================================================
# Account Balance and Reports
# =============================================================================

def calculate_account_balance(account_id: int) -> float:
    """
    Calculate the current balance of an account.
    
    For assets and expenses: balance = sum(debits) - sum(credits)
    For liabilities, equity, revenue: balance = sum(credits) - sum(debits)
    """
    db = SessionLocal()
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            return 0.0
        
        lines = db.query(JournalEntryLine).filter(JournalEntryLine.account_id == account_id).all()
        
        total_debits = sum(line.debit for line in lines)
        total_credits = sum(line.credit for line in lines)
        
        # Determine balance based on account type
        if account.account_type in ["asset", "expense"]:
            return total_debits - total_credits
        else:  # liability, equity, revenue
            return total_credits - total_debits
    finally:
        db.close()


def get_trial_balance() -> Dict[str, Any]:
    """
    Generate a trial balance report.
    Sum of all debit balances should equal sum of all credit balances.
    """
    db = SessionLocal()
    try:
        accounts = db.query(Account).filter(Account.is_active == True).order_by(Account.code).all()
        
        trial_balance = []
        total_debits = 0
        total_credits = 0
        
        for account in accounts:
            balance = calculate_account_balance(account.id)
            
            if abs(balance) < 0.01:  # Skip zero balances
                continue
            
            debit_balance = 0
            credit_balance = 0
            
            # Determine which column the balance goes in
            if account.account_type in ["asset", "expense"]:
                if balance >= 0:
                    debit_balance = balance
                else:
                    credit_balance = abs(balance)
            else:  # liability, equity, revenue
                if balance >= 0:
                    credit_balance = balance
                else:
                    debit_balance = abs(balance)
            
            trial_balance.append({
                "account_code": account.code,
                "account_name": account.name,
                "account_type": account.account_type,
                "debit_balance": debit_balance,
                "credit_balance": credit_balance
            })
            
            total_debits += debit_balance
            total_credits += credit_balance
        
        return {
            "accounts": trial_balance,
            "total_debits": total_debits,
            "total_credits": total_credits,
            "is_balanced": abs(total_debits - total_credits) < 0.01,
            "generated_at": datetime.utcnow().isoformat()
        }
    finally:
        db.close()


def get_income_statement() -> Dict[str, Any]:
    """Generate income statement (Profit & Loss)"""
    db = SessionLocal()
    try:
        accounts = db.query(Account).filter(Account.is_active == True).all()
        
        revenues = []
        expenses = []
        total_revenue = 0
        total_expenses = 0
        
        for account in accounts:
            balance = calculate_account_balance(account.id)
            if abs(balance) < 0.01:
                continue
            
            item = {
                "account_code": account.code,
                "account_name": account.name,
                "amount": balance
            }
            
            if account.account_type == "revenue":
                revenues.append(item)
                total_revenue += balance
            elif account.account_type == "expense":
                expenses.append(item)
                total_expenses += balance
        
        net_income = total_revenue - total_expenses
        
        return {
            "revenues": revenues,
            "total_revenue": total_revenue,
            "expenses": expenses,
            "total_expenses": total_expenses,
            "net_income": net_income,
            "generated_at": datetime.utcnow().isoformat()
        }
    finally:
        db.close()


def get_balance_sheet() -> Dict[str, Any]:
    """Generate balance sheet (Assets = Liabilities + Equity)"""
    db = SessionLocal()
    try:
        accounts = db.query(Account).filter(Account.is_active == True).all()
        
        assets = []
        liabilities = []
        equity = []
        total_assets = 0
        total_liabilities = 0
        total_equity = 0
        
        for account in accounts:
            balance = calculate_account_balance(account.id)
            if abs(balance) < 0.01:
                continue
            
            item = {
                "account_code": account.code,
                "account_name": account.name,
                "amount": balance
            }
            
            if account.account_type == "asset":
                assets.append(item)
                total_assets += balance
            elif account.account_type == "liability":
                liabilities.append(item)
                total_liabilities += balance
            elif account.account_type == "equity":
                equity.append(item)
                total_equity += balance
        
        # Add net income to equity (from income statement)
        income_statement = get_income_statement()
        net_income = income_statement["net_income"]
        if abs(net_income) >= 0.01:
            equity.append({
                "account_code": "NET",
                "account_name": "Net Income (Current Period)",
                "amount": net_income
            })
            total_equity += net_income
        
        return {
            "assets": assets,
            "total_assets": total_assets,
            "liabilities": liabilities,
            "total_liabilities": total_liabilities,
            "equity": equity,
            "total_equity": total_equity,
            "is_balanced": abs(total_assets - (total_liabilities + total_equity)) < 0.01,
            "generated_at": datetime.utcnow().isoformat()
        }
    finally:
        db.close()
