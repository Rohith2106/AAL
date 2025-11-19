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


class LedgerEntryResponse(BaseModel):
    id: int
    record_id: str
    vendor: Optional[str]
    date: Optional[str]
    amount: Optional[float]
    tax: Optional[float]
    total: Optional[float]
    invoice_number: Optional[str]
    description: Optional[str]
    category: Optional[str]
    payment_method: Optional[str]
    status: str
    validation_confidence: Optional[float]
    validation_issues: Optional[List[Union[str, Dict[str, Any]]]]
    created_at: Optional[str]
    updated_at: Optional[str]


class ChatMessage(BaseModel):
    message: str
    record_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[Dict[str, Any]]] = None
