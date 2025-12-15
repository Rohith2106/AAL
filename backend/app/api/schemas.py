from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
from datetime import datetime


class ProcessReceiptRequest(BaseModel):
    ocr_engine: Optional[str] = "easyocr"


class ProcessReceiptResponse(BaseModel):
    record_id: str
    raw_text: str
    structured_data: Dict[str, Any]
    embedding: List[float]
    reconciliation: Dict[str, Any]
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