from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
from datetime import datetime


class ProcessReceiptRequest(BaseModel):
    ocr_engine: Optional[str] = "easyocr"


class ReconciliationMatch(BaseModel):
    """A matched transaction for reconciliation"""
    record_id: str
    vendor: Optional[str] = None
    date: Optional[str] = None
    total: Optional[float] = None
    similarity: float
    ledger_entry_id: Optional[int] = None
    relationship: Optional[str] = None  # "duplicate", "counterparty", "related"


class ReconciliationResponse(BaseModel):
    """Enhanced reconciliation information"""
    is_duplicate: bool = False
    is_counterparty: bool = False
    match_type: str = "none"  # "duplicate", "counterparty", "none"
    confidence: float = 0.0
    matched_records: List[ReconciliationMatch] = []
    counterparty_record: Optional[ReconciliationMatch] = None
    duplicate_record_id: Optional[str] = None
    counterparty_record_id: Optional[str] = None
    counterparty_vendor: Optional[str] = None


class ProcessReceiptResponse(BaseModel):
    record_id: str
    raw_text: str
    structured_data: Dict[str, Any]
    embedding: List[float]
    reconciliation: Dict[str, Any]  # Can be ReconciliationResponse or legacy format
    validation: Dict[str, Any]
    reasoning_trace: Dict[str, Any]
    explanation: str
    recommendations: List[str]
    ledger_entry_id: Optional[int] = None
    status: str


class ProcessMultipleReceiptsResponse(BaseModel):
    total: int
    successful: int
    failed: int
    results: List[ProcessReceiptResponse]


class PerspectiveAnalysisResponse(BaseModel):
    transactionDirection: str  # "INFLOW" | "OUTFLOW"
    ourRole: str  # "BUYER" | "VENDOR"
    counterpartyRole: str  # "VENDOR" | "CUSTOMER"
    documentRole: str  # "RECEIPT" | "PURCHASE_INVOICE" | "SALES_INVOICE" | "REFUND_NOTE"
    counterpartyName: str
    confidence: float


class LedgerItemSchema(BaseModel):
    id: int
    name: str
    quantity: int
    unit_price: float
    line_total: float

    class Config:
        from_attributes = True


# =============================================================================
# Double-Entry Accounting Schemas
# =============================================================================

class JournalEntryLineSchema(BaseModel):
    """Individual debit or credit line in a journal entry"""
    id: int
    account_id: int
    account_code: Optional[str] = None
    account_name: Optional[str] = None
    account_type: Optional[str] = None
    debit: float
    credit: float
    description: Optional[str] = None

    class Config:
        from_attributes = True


class JournalEntrySchema(BaseModel):
    """Double-entry journal entry with debit/credit lines"""
    id: int
    ledger_entry_id: Optional[int] = None
    entry_date: Optional[str] = None
    reference: Optional[str] = None
    description: Optional[str] = None
    memo: Optional[str] = None
    is_balanced: bool = True
    is_adjusting: bool = False
    created_at: Optional[str] = None
    lines: List[JournalEntryLineSchema] = []
    total_debits: float = 0.0
    total_credits: float = 0.0

    class Config:
        from_attributes = True


class AccountSchema(BaseModel):
    """Chart of Accounts entry"""
    id: int
    code: str
    name: str
    account_type: str  # asset, liability, equity, revenue, expense
    parent_id: Optional[int] = None
    description: Optional[str] = None
    balance: float = 0.0
    normal_balance: str = "debit"  # debit or credit

    class Config:
        from_attributes = True


class CreateAccountRequest(BaseModel):
    """Request to create a new account"""
    code: str
    name: str
    account_type: str
    parent_id: Optional[int] = None
    description: Optional[str] = None


class TrialBalanceAccountSchema(BaseModel):
    """Account line in trial balance"""
    account_code: str
    account_name: str
    account_type: str
    debit_balance: float
    credit_balance: float


class TrialBalanceResponse(BaseModel):
    """Trial Balance report"""
    accounts: List[TrialBalanceAccountSchema]
    total_debits: float
    total_credits: float
    is_balanced: bool
    generated_at: str


class IncomeStatementResponse(BaseModel):
    """Income Statement (P&L) report"""
    revenues: List[Dict[str, Any]]
    total_revenue: float
    expenses: List[Dict[str, Any]]
    total_expenses: float
    net_income: float
    generated_at: str


class BalanceSheetResponse(BaseModel):
    """Balance Sheet report"""
    assets: List[Dict[str, Any]]
    total_assets: float
    liabilities: List[Dict[str, Any]]
    total_liabilities: float
    equity: List[Dict[str, Any]]
    total_equity: float
    is_balanced: bool
    generated_at: str


# =============================================================================
# Ledger Entry with Journal Entry
# =============================================================================

class LedgerEntryResponse(BaseModel):
    id: int
    record_id: str
    vendor: Optional[str]
    date: Optional[str]
    amount: Optional[float]
    tax: Optional[float]
    total: Optional[float]
    currency: Optional[str] = "USD"
    exchange_rate: Optional[float] = 1.0
    usd_total: Optional[float]
    invoice_number: Optional[str]
    description: Optional[str]
    category: Optional[str]
    payment_method: Optional[str]
    status: str
    validation_confidence: Optional[float]
    validation_issues: Optional[List[Union[str, Dict[str, Any]]]]
    reasoning_trace: Optional[Dict[str, Any]] = None
    created_at: Optional[str]
    updated_at: Optional[str]
    items: List[LedgerItemSchema] = []
    journal_entry: Optional[JournalEntrySchema] = None  # Double-entry journal

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    message: str
    record_id: Optional[str] = None
    model: Optional[str] = None  # Model name, defaults to settings.LLM_MODEL


class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[Dict[str, Any]]] = None


class ManualEntryItem(BaseModel):
    name: str
    quantity: int = 1
    unit_price: float
    line_total: Optional[float] = None


class CreateManualEntryRequest(BaseModel):
    vendor: str
    date: str
    amount: Optional[float] = None
    tax: Optional[float] = None
    total: float
    currency: str = "USD"
    category: Optional[str] = None
    payment_method: Optional[str] = None
    invoice_number: Optional[str] = None
    description: Optional[str] = None
    items: List[ManualEntryItem] = []


# Authentication schemas
class UserSignup(BaseModel):
    email: str
    password: str
    company_name: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# =============================================================================
# IFRS Claim Rights Schemas
# =============================================================================

class AmortizationEntrySchema(BaseModel):
    """Amortization entry schema"""
    id: int
    period_number: int
    period_start: str
    period_end: str
    amount: float
    status: str
    posted_at: Optional[str] = None
    journal_entry_id: Optional[int] = None

    class Config:
        from_attributes = True


class AmortizationScheduleSchema(BaseModel):
    """Amortization schedule schema"""
    id: int
    total_periods: int
    amount_per_period: float
    is_generated: bool
    generated_at: Optional[str] = None
    entries: List[AmortizationEntrySchema] = []

    class Config:
        from_attributes = True


class ClaimRightSchema(BaseModel):
    """Claim right schema"""
    id: int
    ledger_entry_id: Optional[int] = None
    claim_type: str
    description: str
    total_amount: float
    remaining_amount: float
    amortized_amount: float
    start_date: str
    end_date: str
    frequency: str
    status: str
    cancellation_date: Optional[str] = None
    cancellation_reason: Optional[str] = None
    created_at: str
    schedule: Optional[AmortizationScheduleSchema] = None

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Custom validation to handle datetime conversion and lazy loading"""
        from datetime import datetime
        
        # If obj is already a dict, use it directly
        if isinstance(obj, dict):
            return super().model_validate(obj, **kwargs)
        
        # Convert ClaimRight object to dict
        if hasattr(obj, '__dict__'):
            data = {}
            for key in ['id', 'ledger_entry_id', 'claim_type', 'description', 
                       'total_amount', 'remaining_amount', 'amortized_amount',
                       'frequency', 'status', 'cancellation_reason']:
                if hasattr(obj, key):
                    value = getattr(obj, key)
                    data[key] = value
            
            # Convert datetime fields to strings
            if hasattr(obj, 'start_date') and obj.start_date:
                data['start_date'] = obj.start_date.isoformat() if isinstance(obj.start_date, datetime) else str(obj.start_date)
            else:
                data['start_date'] = ''
                
            if hasattr(obj, 'end_date') and obj.end_date:
                data['end_date'] = obj.end_date.isoformat() if isinstance(obj.end_date, datetime) else str(obj.end_date)
            else:
                data['end_date'] = ''
                
            if hasattr(obj, 'created_at') and obj.created_at:
                data['created_at'] = obj.created_at.isoformat() if isinstance(obj.created_at, datetime) else str(obj.created_at)
            else:
                data['created_at'] = ''
                
            if hasattr(obj, 'cancellation_date') and obj.cancellation_date:
                data['cancellation_date'] = obj.cancellation_date.isoformat() if isinstance(obj.cancellation_date, datetime) else str(obj.cancellation_date)
            else:
                data['cancellation_date'] = None
            
            # Handle schedule relationship (may fail if lazy loaded)
            try:
                if hasattr(obj, 'schedule') and obj.schedule:
                    data['schedule'] = AmortizationScheduleSchema.model_validate(obj.schedule)
                else:
                    data['schedule'] = None
            except Exception:
                # If schedule lazy loading fails, set to None
                data['schedule'] = None
            
            return cls(**data)
        
        # Fall back to default validation
        return super().model_validate(obj, **kwargs)

    class Config:
        from_attributes = True


class CreateClaimRightRequest(BaseModel):
    """Request to create a claim right"""
    ledger_entry_id: Optional[int] = None
    claim_type: str  # ASSET_CLAIM or LIABILITY_CLAIM
    description: str
    total_amount: float
    start_date: str
    end_date: str
    frequency: str = "monthly"  # monthly, quarterly, yearly


class ClaimRightSummarySchema(BaseModel):
    """Summary of claim rights"""
    total_claims: int
    asset_claims: int
    liability_claims: int
    total_asset_amount: float
    total_liability_amount: float
    remaining_asset_amount: float
    remaining_liability_amount: float
    pending_accruals: int


class ProcessAccrualsRequest(BaseModel):
    """Request to process accruals"""
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    dry_run: bool = False


class ProcessAccrualsResponse(BaseModel):
    """Response from processing accruals"""
    period_start: str
    period_end: str
    entries_processed: int
    total_amount: float
    asset_claims: int
    liability_claims: int
    errors: List[str] = []
    posted_entries: List[Dict[str, Any]] = []


class UserResponse(BaseModel):
    id: int
    email: str
    company_name: Optional[str] = None
    created_at: Optional[str] = None