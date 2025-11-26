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

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    message: str
    record_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[Dict[str, Any]]] = None
