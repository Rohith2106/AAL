from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional, List, List as ListType
import uuid
import logging
from datetime import datetime
import json
from app.api.schemas import (
    ProcessReceiptResponse,
    LedgerEntryResponse,
    ChatMessage,
    ChatResponse,
    ProcessMultipleReceiptsResponse,
    CreateManualEntryRequest,
    PerspectiveAnalysisResponse,
)
from app.services.ocr_service import extract_text_from_image, extract_text_from_pdf
from app.services.extraction_service import parse_receipt_text
from app.services.classification_service import classify_transaction
from app.services.vector_service import (
    create_embedding, store_document, check_duplicates, update_document_status, delete_document, document_exists
)
from app.services.llm_orchestrator import orchestrate
from app.services.ledger_service import (
    create_ledger_entry, get_ledger_entries, get_ledger_entry, update_ledger_entry_status, delete_ledger_entry
)
from app.services.vector_service import find_similar_documents
from app.db.mongodb import get_database
from app.core.config import settings
from app.services.perspective_service import analyze_perspective

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/process-receipt/{record_id}/logs")
async def stream_process_logs(record_id: str):
    """
    Stream processing logs for a receipt in real-time using Server-Sent Events
    """
    from app.core.log_streamer import stream_logs
    
    async def generate():
        async for log_entry in stream_logs(record_id):
            # Format as SSE
            data = json.dumps(log_entry)
            yield f"data: {data}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/process-receipt", response_model=ProcessReceiptResponse)
async def process_receipt(
    file: UploadFile = File(...),
    ocr_engine: str = Query(default="easyocr", description="OCR engine: tesseract or easyocr"),
    language: str = Query(default="en", description="OCR language: en (English), ja (Japanese), or en_ja (both)"),
    record_id: Optional[str] = Query(default=None, description="Optional record ID for log streaming")
):
    """
    Main endpoint to process a receipt/invoice through the complete pipeline:
    1. OCR extraction
    2. Data structuring
    3. Vector embedding and reconciliation
    4. LLM validation and orchestration
    5. Ledger storage
    """
    # Set up log streaming variables (defined outside try for finally access)
    log_handler = None
    app_loggers_cleanup = []
    
    try:
        # Generate or use provided record ID
        if not record_id:
            record_id = f"record_{uuid.uuid4().hex[:12]}"
        
        # Set up log streaming - add handler to all relevant loggers
        from app.core.log_streamer import get_log_handler
        log_handler = get_log_handler(record_id)
        
        # Add handler to root logger and specific app loggers
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        
        # Also add to app-specific loggers to ensure we catch all logs
        app_loggers = [
            logging.getLogger('app'),
            logging.getLogger('app.services'),
            logging.getLogger('app.services.ocr_service'),
            logging.getLogger('app.services.extraction_service'),
            logging.getLogger('app.services.classification_service'),
            logging.getLogger('app.services.llm_orchestrator'),
            logging.getLogger('app.services.ledger_service'),
            logging.getLogger('app.api'),
        ]
        app_loggers_cleanup = app_loggers.copy()  # Copy for cleanup in finally block
        
        for app_logger in app_loggers:
            app_logger.addHandler(log_handler)
            app_logger.setLevel(logging.INFO)
        
        try:
            # Read file
            file_bytes = await file.read()
            file_ext = file.filename.split('.')[-1].lower() if file.filename else ''
            
            # Step 1: OCR Extraction
            logger.info(f"Processing file {file.filename} with OCR engine: {ocr_engine}, language: {language}")
            if file_ext == 'pdf':
                raw_text = await extract_text_from_pdf(file_bytes, language=language)
            else:
                raw_text = await extract_text_from_image(file_bytes, ocr_engine, language=language)
            
            if not raw_text:
                raise HTTPException(status_code=400, detail="No text extracted from image")
            
            # Step 2: Data Extraction
            structured_data = await parse_receipt_text(raw_text)
            structured_data["record_id"] = record_id

            # Step 2.2: Perspective-aware counterparty analysis (optional, rules-first)
            try:
                our_company_name = settings.OUR_COMPANY_NAME or ""
                if our_company_name:
                    perspective = await analyze_perspective(
                        raw_text,
                        our_company_name=our_company_name,
                        metadata={
                            "vendor": structured_data.get("vendor"),
                            "total": structured_data.get("total"),
                            "amount": structured_data.get("amount"),
                            "payment_method": structured_data.get("payment_method"),
                            "invoice_number": structured_data.get("invoice_number"),
                            "currency": structured_data.get("currency"),
                        },
                    )
                    structured_data["perspective"] = perspective
            except Exception as e:
                logger.warning(f"Perspective analysis failed for record {record_id}: {e}", exc_info=True)
            
            # DEBUG: Log items extraction
            items_count = len(structured_data.get("items", []))
            logger.info(f"Extracted {items_count} items from receipt")
            if items_count > 0:
                logger.info(f"Items: {structured_data.get('items')[:3]}...")  # Log first 3
            else:
                logger.warning("No items extracted from receipt!")
            
            # Step 2.5: Classify transaction using LLM
            if not structured_data.get("category"):
                structured_data["category"] = await classify_transaction(structured_data)
            
            # Step 3: Create embedding
            embedding = await create_embedding(raw_text)
            
            # Step 4: Check for duplicates/reconciliation
            reconciliation = await check_duplicates(record_id, embedding, structured_data)
            
            # Handle duplicate detection - if exact duplicate found, don't create ledger entry
            if reconciliation.get("is_duplicate") and reconciliation.get("duplicate_record_id"):
                duplicate_id = reconciliation.get("duplicate_record_id")
                logger.warning(f"Duplicate document detected: {record_id} matches {duplicate_id}")
                
                # Store document but mark as duplicate
                await store_document(record_id, structured_data, embedding, raw_text)
                
                # Update document with reconciliation info
                db = get_database()
                if db is not None:
                    collection = db.receipts
                    await collection.update_one(
                        {"record_id": record_id},
                        {"$set": {"reconciliation_info": reconciliation, "status": "duplicate"}}
                    )
                
                # Return response indicating duplicate
                return ProcessReceiptResponse(
                    record_id=record_id,
                    raw_text=raw_text[:500],
                    structured_data=structured_data,
                    embedding=embedding[:10],
                    reconciliation=reconciliation,
                    validation={
                        "status": "duplicate",
                        "issues": [f"Duplicate of existing transaction: {duplicate_id}"],
                        "confidence": reconciliation.get("confidence", 0.0),
                        "reasoning": "This document appears to be a duplicate of an existing transaction."
                    },
                    reasoning_trace={
                        "steps": [{"step": 1, "action": "duplicate_detection", "observation": f"Found duplicate: {duplicate_id}", "conclusion": "Duplicate document"}],
                        "final_conclusion": "Duplicate document detected",
                        "confidence_score": reconciliation.get("confidence", 0.0)
                    },
                    explanation=f"This document is a duplicate of transaction {duplicate_id}. Please review and delete if not needed.",
                    recommendations=["Review the duplicate transaction", "Delete this duplicate if it's not needed"],
                    ledger_entry_id=None,
                    status="duplicate"
                )
            
            # Step 5: Store in vector DB
            await store_document(record_id, structured_data, embedding, raw_text)
            
            # Store reconciliation info in MongoDB
            db = get_database()
            if db is not None:
                collection = db.receipts
                await collection.update_one(
                    {"record_id": record_id},
                    {"$set": {"reconciliation_info": reconciliation}}
                )
            
            # Step 6: LLM Orchestration
            orchestration_result = await orchestrate(
                structured_data,
                reconciliation_info=reconciliation
            )
            
            # Log validation result
            validation_status = orchestration_result["validation_result"]["status"]
            logger.info(f"Validation status: {validation_status}, Confidence: {orchestration_result['validation_result']['confidence']}")
            
            # Add counterparty information to recommendations if found
            if reconciliation.get("is_counterparty"):
                counterparty_id = reconciliation.get("counterparty_record_id")
                counterparty_vendor = reconciliation.get("counterparty_vendor")
                orchestration_result["recommendations"].insert(
                    0,
                    f"Counterparty document found: This appears to be the counterparty document for transaction {counterparty_id} (vendor: {counterparty_vendor})"
                )
            
            # Step 7: Store in ledger (always create entry, status depends on validation)
            ledger_entry_id = None
            try:
                ledger_entry = create_ledger_entry(record_id, structured_data, orchestration_result)
                ledger_entry_id = ledger_entry.id
                logger.info(f"Ledger entry created with ID: {ledger_entry_id}, Status: {ledger_entry.status}")
                
                if validation_status == "valid":
                    await update_document_status(record_id, "validated")
                else:
                    await update_document_status(record_id, "pending_review")
            except Exception as e:
                logger.error(f"Error creating ledger entry: {e}", exc_info=True)
                # Continue even if ledger entry creation fails
            
            return ProcessReceiptResponse(
                record_id=record_id,
                raw_text=raw_text[:500],  # Preview
                structured_data=structured_data,
                embedding=embedding[:10],  # Preview
                reconciliation=reconciliation,
                validation=orchestration_result["validation_result"],
                reasoning_trace=orchestration_result["reasoning_trace"],
                explanation=orchestration_result["explanation"],
                recommendations=orchestration_result["recommendations"],
                ledger_entry_id=ledger_entry_id,
                status="validated" if ledger_entry_id else "pending_review"
            )
        finally:
            # Clean up log handler from all loggers
            if log_handler:
                root_logger = logging.getLogger()
                try:
                    root_logger.removeHandler(log_handler)
                except:
                    pass
                for app_logger in app_loggers_cleanup:
                    try:
                        app_logger.removeHandler(log_handler)
                    except:
                        pass
            from app.core.log_streamer import cleanup_logs
            # Don't cleanup immediately - let frontend finish reading logs
            # cleanup_logs(record_id)  # Uncomment if you want immediate cleanup
    
    except Exception as e:
        logger.error(f"Error processing receipt: {e}", exc_info=True)
        # Clean up log handler on error
        if log_handler:
            root_logger = logging.getLogger()
            try:
                root_logger.removeHandler(log_handler)
            except:
                pass
            for app_logger in app_loggers_cleanup:
                try:
                    app_logger.removeHandler(log_handler)
                except:
                    pass
        raise HTTPException(status_code=500, detail=f"Error processing receipt: {str(e)}")


@router.post("/process-receipts-batch", response_model=ProcessMultipleReceiptsResponse)
async def process_multiple_receipts(
    files: ListType[UploadFile] = File(..., description="Multiple receipt/invoice files"),
    ocr_engine: str = Query(default="easyocr", description="OCR engine: tesseract or easyocr"),
    language: str = Query(default="en", description="OCR language: en (English), ja (Japanese), or en_ja (both)")
):
    """
    Process multiple receipts/invoices in batch
    
    Args:
        files: List of uploaded files
        ocr_engine: OCR engine to use
    
    Returns:
        Batch processing results
    """
    results = []
    successful = 0
    failed = 0
    
    for file in files:
        try:
            # Generate record ID
            record_id = f"record_{uuid.uuid4().hex[:12]}"
            
            # Read file
            file_bytes = await file.read()
            file_ext = file.filename.split('.')[-1].lower() if file.filename else ''
            
            # Step 1: OCR Extraction
            logger.info(f"Processing file {file.filename} with OCR engine: {ocr_engine}, language: {language}")
            if file_ext == 'pdf':
                raw_text = await extract_text_from_pdf(file_bytes, language=language)
            else:
                raw_text = await extract_text_from_image(file_bytes, ocr_engine, language=language)
            
            if not raw_text:
                raise Exception("No text extracted from image")
            
            # Step 2: Data Extraction
            structured_data = await parse_receipt_text(raw_text)
            structured_data["record_id"] = record_id
            
            # Step 2.5: Classify transaction
            if not structured_data.get("category"):
                structured_data["category"] = await classify_transaction(structured_data)
            
            # Step 3: Create embedding
            embedding = await create_embedding(raw_text)
            
            # Step 4: Check for duplicates/reconciliation
            reconciliation = await check_duplicates(record_id, embedding, structured_data)
            
            # Step 5: Store in vector DB
            await store_document(record_id, structured_data, embedding, raw_text)
            
            # Step 6: LLM Orchestration
            orchestration_result = await orchestrate(
                structured_data,
                reconciliation_info=reconciliation
            )
            
            # Step 7: Store in ledger
            ledger_entry_id = None
            try:
                ledger_entry = create_ledger_entry(record_id, structured_data, orchestration_result)
                ledger_entry_id = ledger_entry.id
                validation_status = orchestration_result["validation_result"]["status"]
                if validation_status == "valid":
                    await update_document_status(record_id, "validated")
                else:
                    await update_document_status(record_id, "pending_review")
            except Exception as e:
                logger.error(f"Error creating ledger entry: {e}", exc_info=True)
            
            results.append(ProcessReceiptResponse(
                record_id=record_id,
                raw_text=raw_text[:500],
                structured_data=structured_data,
                embedding=embedding[:10],
                reconciliation=reconciliation,
                validation=orchestration_result["validation_result"],
                reasoning_trace=orchestration_result["reasoning_trace"],
                explanation=orchestration_result["explanation"],
                recommendations=orchestration_result["recommendations"],
                ledger_entry_id=ledger_entry_id,
                status="validated" if ledger_entry_id else "pending_review"
            ))
            successful += 1
            
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {e}", exc_info=True)
            failed += 1
    
    return ProcessMultipleReceiptsResponse(
        total=len(files),
        successful=successful,
        failed=failed,
        results=results
    )


@router.get("/ledger", response_model=List[LedgerEntryResponse])
async def get_ledger(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    status: Optional[str] = Query(default=None),
    vendor: Optional[str] = Query(default=None)
):
    """Get ledger entries with optional filters"""
    try:
        entries = get_ledger_entries(skip=skip, limit=limit, status=status, vendor=vendor)
        logger.info(f"Retrieved {len(entries)} ledger entries (skip={skip}, limit={limit}, status={status})")
        return [LedgerEntryResponse(**entry) for entry in entries]
    except Exception as e:
        logger.error(f"Error fetching ledger: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ledger/{record_id}", response_model=LedgerEntryResponse)
async def get_ledger_entry_by_id(record_id: str):
    """Get specific ledger entry by record_id"""
    entry = get_ledger_entry(record_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Ledger entry not found")
    return LedgerEntryResponse(**entry)


@router.get("/ledger/{record_id}/perspective", response_model=PerspectiveAnalysisResponse)
async def get_ledger_entry_perspective(
    record_id: str,
    our_company_name: Optional[str] = Query(
        default=None,
        description="Override for our company name; if omitted, uses settings.OUR_COMPANY_NAME",
    ),
):
    """
    Analyze transaction perspective (direction, roles, counterparty) for a given record.

    Uses stored OCR text and structured data from the vector store (MongoDB).
    """
    from app.db.mongodb import get_database

    db = get_database()
    if db is None:
        raise HTTPException(status_code=500, detail="MongoDB database not connected")

    collection = db.receipts
    doc = await collection.find_one({"record_id": record_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Receipt document not found")

    raw_text = doc.get("raw_text") or ""
    structured_data = doc.get("structured_data") or {}

    # Prefer explicit query param, then stored env config; allow empty to still run heuristics
    company = (our_company_name or settings.OUR_COMPANY_NAME or "").strip()

    perspective = await analyze_perspective(
        raw_text,
        our_company_name=company,
        metadata={
            "vendor": structured_data.get("vendor"),
            "total": structured_data.get("total"),
            "amount": structured_data.get("amount"),
            "payment_method": structured_data.get("payment_method"),
            "invoice_number": structured_data.get("invoice_number"),
            "currency": structured_data.get("currency"),
        },
    )

    # ------------------------------------------------------------------
    # Vector reconciliation: detect duplicates or counterpart transactions
    # ------------------------------------------------------------------
    try:
        embedding = doc.get("embedding") or []
        if embedding:
            # Use same helper as other parts of the system
            similar_docs = await find_similar_documents(embedding, threshold=0.95, limit=5)
            # Exclude self
            similar_docs = [d for d in similar_docs if d.get("record_id") != record_id]

            if similar_docs:
                top = similar_docs[0]
                other_sd = top.get("structured_data", {}) or {}

                this_total = structured_data.get("total")
                other_total = other_sd.get("total")
                this_date = (structured_data.get("date") or "").strip()
                other_date = (other_sd.get("date") or "").strip()
                this_vendor = (structured_data.get("vendor") or "").strip().lower()
                other_vendor = (other_sd.get("vendor") or "").strip().lower()

                same_total = (
                    isinstance(this_total, (int, float))
                    and isinstance(other_total, (int, float))
                    and abs(float(this_total) - float(other_total)) < 0.01
                )
                same_date = bool(this_date and other_date and this_date == other_date)
                same_vendor = bool(this_vendor and other_vendor and this_vendor == other_vendor)

                if same_total and same_date and same_vendor:
                    # Likely duplicate of an existing receipt – keep roles but reduce confidence
                    logger.info(
                        "Perspective reconciliation: record %s is likely a duplicate of %s",
                        record_id,
                        top.get("record_id"),
                    )
                    try:
                        perspective_conf = float(perspective.get("confidence", 0.8))
                    except Exception:
                        perspective_conf = 0.8
                    # Lower but not zero, to signal uncertainty
                    perspective["confidence"] = min(perspective_conf, 0.4)
                elif same_total and same_date and not same_vendor:
                    # Same transaction seen from counterparty side
                    logger.info(
                        "Perspective reconciliation: record %s appears to be counterpart of %s",
                        record_id,
                        top.get("record_id"),
                    )
                    # If we don't already have a counterparty name, use the other vendor
                    if not perspective.get("counterpartyName"):
                        counterparty_name = other_sd.get("vendor")
                        if counterparty_name:
                            perspective["counterpartyName"] = counterparty_name
    except Exception as e:
        logger.warning(f"Error during perspective reconciliation for {record_id}: {e}", exc_info=True)

    return PerspectiveAnalysisResponse(**perspective)


@router.put("/ledger/{record_id}/status")
async def update_ledger_entry_status_endpoint(record_id: str, status: str = Query(..., description="New status: validated, pending, or rejected")):
    """Update ledger entry status"""
    try:
        if status not in ["validated", "pending", "rejected"]:
            raise HTTPException(status_code=400, detail="Status must be one of: validated, pending, rejected")
        
        entry = get_ledger_entry(record_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Ledger entry not found")
        
        # Update in MySQL
        mysql_updated = update_ledger_entry_status(record_id, status)
        if not mysql_updated:
            raise HTTPException(status_code=404, detail="Ledger entry not found in MySQL")
        
        # Update in MongoDB vector DB
        vector_status = "validated" if status == "validated" else "pending_review" if status == "pending" else "rejected"
        
        # Check if document exists in MongoDB first
        mongo_exists = await document_exists(record_id)
        if not mongo_exists:
            logger.warning(f"Document {record_id} does not exist in MongoDB. It may have been created before MongoDB was set up, or record_id mismatch.")
            mongo_updated = False
        else:
            mongo_updated = await update_document_status(record_id, vector_status)
            if not mongo_updated:
                logger.warning(f"MySQL update succeeded but MongoDB update failed for record_id: {record_id}")
        
        return {
            "message": f"Entry status updated to {status}",
            "record_id": record_id,
            "status": status,
            "mysql_updated": mysql_updated,
            "mongo_updated": mongo_updated
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating entry status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ledger/{record_id}/approve")
async def approve_ledger_entry(record_id: str):
    """Approve a pending ledger entry (deprecated - use PUT /ledger/{record_id}/status instead)"""
    try:
        entry = get_ledger_entry(record_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Ledger entry not found")
        
        if entry["status"] == "pending":
            # Create ledger entry if not exists
            # This would require fetching the original structured data
            update_ledger_entry_status(record_id, "validated")
            await update_document_status(record_id, "validated")
            return {"message": "Entry approved and validated"}
        else:
            return {"message": f"Entry already {entry['status']}"}
    except Exception as e:
        logger.error(f"Error approving entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/ledger/{record_id}")
async def delete_ledger_entry_endpoint(record_id: str):
    """Delete a ledger entry from both MySQL and MongoDB vector database"""
    try:
        entry = get_ledger_entry(record_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Ledger entry not found")
        
        # Delete from MySQL
        mysql_deleted = delete_ledger_entry(record_id)
        
        # Delete from MongoDB vector DB
        mongo_exists = await document_exists(record_id)
        if mongo_exists:
            mongo_deleted = await delete_document(record_id)
        else:
            logger.info(f"Document {record_id} does not exist in MongoDB, skipping MongoDB deletion")
            mongo_deleted = False
        
        if mysql_deleted or mongo_deleted:
            return {
                "message": "Entry deleted successfully",
                "record_id": record_id,
                "mysql_deleted": mysql_deleted,
                "mongo_deleted": mongo_deleted
            }
        else:
            raise HTTPException(status_code=404, detail="Entry not found in any database")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ledger(message: ChatMessage):
    """
    RAG chatbot for querying ledger and receipts using LLM (Gemini)
    """
    try:
        from app.core.llm import get_llm
        from langchain.schema import HumanMessage
        
        # Get LLM with specified model (defaults to settings.LLM_MODEL)
        llm = get_llm(model=message.model)
        db = get_database()
        if db is None:
            raise HTTPException(status_code=500, detail="MongoDB database not connected")
        collection = db.receipts
        
        # Create embedding for query
        query_embedding = await create_embedding(message.message)
        
        # Find relevant documents
        similar_docs = await find_similar_documents(query_embedding, threshold=0.5, limit=5)
        
        # Build context from similar documents
        context = ""
        sources = []
        if similar_docs:
            for doc in similar_docs:
                context += f"\nRecord ID: {doc['record_id']}\n"
                context += f"Vendor: {doc['structured_data'].get('vendor', 'Unknown')}\n"
                context += f"Date: {doc['structured_data'].get('date', 'Unknown')}\n"
                context += f"Total: {doc['structured_data'].get('total', 0)}\n"
                context += f"Text preview: {doc['raw_text']}\n"
                sources.append({
                    "record_id": doc['record_id'],
                    "similarity": doc['similarity'],
                    "vendor": doc['structured_data'].get('vendor')
                })
        
        # Get ledger summary if no specific record
        if not message.record_id:
            ledger_entries = get_ledger_entries(limit=10)
            if ledger_entries:
                context += "\n\nRecent Ledger Entries:\n"
                for entry in ledger_entries[:5]:
                    context += f"- {entry['vendor']}: ${entry['total']} on {entry['date']}\n"
        
        # Build prompt
        prompt = f"""You are an AI assistant for an accounting automation system. 
Answer questions about receipts, invoices, and ledger entries based on the following context.

Context:
{context}

User Question: {message.message}

Provide a helpful, accurate answer based on the context. If the information is not available, say so clearly."""
        
        response = llm.invoke([HumanMessage(content=prompt)])
        
        return ChatResponse(
            response=response.content,
            sources=sources if sources else None
        )
    
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


@router.get("/stats")
async def get_stats():
    """Get statistics about the ledger"""
    try:
        entries = get_ledger_entries(limit=10000)
        
        total_entries = len(entries)
        # Use USD totals for aggregation to handle multi-currency
        total_amount = sum(e.get("usd_total", e.get("total", 0)) or 0 for e in entries)
        validated_count = sum(1 for e in entries if e.get("status") == "validated")
        pending_count = sum(1 for e in entries if e.get("status") == "pending")
        
        # Get unique vendors
        vendors = set(e.get("vendor") for e in entries if e.get("vendor"))
        
        return {
            "total_entries": total_entries,
            "validated_entries": validated_count,
            "pending_entries": pending_count,
            "total_amount": total_amount,  # In USD
            "unique_vendors": len(vendors),
            "average_transaction": total_amount / total_entries if total_entries > 0 else 0
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert-currency")
async def convert_currency(
    amount: float = Query(..., description="Amount to convert"),
    from_currency: str = Query(..., description="Source currency code (e.g., IDR, ZAR, EUR)"),
    to_currency: str = Query(default="USD", description="Target currency code")
):
    """
    Convert currency amount using LLM to get current exchange rate
    """
    try:
        from app.core.llm import get_llm
        from langchain.schema import HumanMessage
        import json
        import asyncio
        
        if from_currency == to_currency:
            return {
                "amount": amount,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "exchange_rate": 1.0,
                "converted_amount": amount
            }
        
        llm = get_llm()
        
        prompt = f"""You are a currency conversion expert. Convert {amount} {from_currency} to {to_currency}.

Provide the current exchange rate and converted amount in the following JSON format:
{{
    "exchange_rate": <rate from {from_currency} to {to_currency}>,
    "converted_amount": <converted amount in {to_currency}>,
    "source": "LLM estimation"
}}

Use realistic current exchange rates. For example:
- IDR to USD: approximately 1 USD = 15,000-16,000 IDR
- ZAR to USD: approximately 1 USD = 18-19 ZAR
- EUR to USD: approximately 1 USD = 0.90-0.95 EUR

Return ONLY the JSON object, no additional text."""
        
        def call_llm():
            return llm.invoke([HumanMessage(content=prompt)])
        
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(None, call_llm),
            timeout=15.0
        )
        response_text = response.content
        
        # Parse JSON
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        conversion_data = json.loads(response_text)
        
        return {
            "amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "exchange_rate": conversion_data.get("exchange_rate", 1.0),
            "converted_amount": conversion_data.get("converted_amount", amount)
        }
    except asyncio.TimeoutError:
        logger.error("Currency conversion timed out")
        raise HTTPException(status_code=500, detail="Currency conversion timed out")
    except Exception as e:
        logger.error(f"Error converting currency: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error converting currency: {str(e)}")


@router.post("/ledger/manual", response_model=LedgerEntryResponse)
async def create_manual_entry(entry_data: CreateManualEntryRequest):
    """
    Create a manual ledger entry without OCR processing
    """
    try:
        import uuid
        from app.services.llm_orchestrator import orchestrate
        
        # Generate record ID
        record_id = f"manual_{uuid.uuid4().hex[:12]}"
        
        # Prepare structured data
        structured_data = {
            "record_id": record_id,
            "vendor": entry_data.vendor,
            "date": entry_data.date,
            "amount": entry_data.amount or entry_data.total,
            "tax": entry_data.tax,
            "total": entry_data.total,
            "currency": entry_data.currency,
            "category": entry_data.category,
            "payment_method": entry_data.payment_method,
            "invoice_number": entry_data.invoice_number,
            "description": entry_data.description or f"Manual entry: {entry_data.vendor}",
            "items": [
                {
                    "name": item.name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "line_total": item.line_total or (item.quantity * item.unit_price)
                }
                for item in entry_data.items
            ]
        }
        
        # Calculate exchange rate and USD equivalent if not USD
        exchange_rate = 1.0
        usd_total = entry_data.total
        
        if entry_data.currency != "USD":
            # Use LLM to get exchange rate
            try:
                from app.core.llm import get_llm
                from langchain.schema import HumanMessage
                import json
                import asyncio
                
                llm = get_llm()
                prompt = f"""What is the current exchange rate from {entry_data.currency} to USD?
                
Return ONLY a JSON object:
{{
    "exchange_rate": <rate from {entry_data.currency} to USD>,
    "usd_amount": <{entry_data.total} {entry_data.currency} converted to USD>
}}

Use realistic current exchange rates."""
                
                def call_llm():
                    return llm.invoke([HumanMessage(content=prompt)])
                
                loop = asyncio.get_event_loop()
                response = await asyncio.wait_for(
                    loop.run_in_executor(None, call_llm),
                    timeout=10.0
                )
                response_text = response.content
                
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                
                conversion_data = json.loads(response_text)
                exchange_rate = conversion_data.get("exchange_rate", 1.0)
                usd_total = conversion_data.get("usd_amount", entry_data.total)
            except Exception as e:
                logger.warning(f"Error getting exchange rate: {e}, using default")
                # Fallback: use approximate rates
                if entry_data.currency == "IDR":
                    exchange_rate = 15000
                    usd_total = entry_data.total / exchange_rate
                elif entry_data.currency == "ZAR":
                    exchange_rate = 18
                    usd_total = entry_data.total / exchange_rate
                else:
                    exchange_rate = 1.0
                    usd_total = entry_data.total
        
        structured_data["exchange_rate"] = exchange_rate
        structured_data["usd_equivalent"] = usd_total
        
        # Create a minimal orchestration result for manual entries
        # Manual entries are considered validated by default
        orchestration_result = {
            "validation_result": {
                "status": "valid",
                "issues": [],
                "confidence": 1.0,
                "reasoning": "Manual entry created by user",
                "currency": entry_data.currency,
                "currency_validated": True
            },
            "reasoning_trace": {
                "steps": [{"step": 1, "action": "manual_entry", "observation": "User created manual entry", "conclusion": "Entry validated"}],
                "final_conclusion": "Manual entry created and validated",
                "confidence_score": 1.0,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Create ledger entry
        ledger_entry = create_ledger_entry(record_id, structured_data, orchestration_result)
        
        # Get the created entry with items
        entry_dict = get_ledger_entry(record_id)
        if not entry_dict:
            raise HTTPException(status_code=500, detail="Failed to retrieve created entry")
        
        return LedgerEntryResponse(**entry_dict)
    
    except Exception as e:
        logger.error(f"Error creating manual entry: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating manual entry: {str(e)}")


@router.get("/health/mongodb")
async def check_mongodb_health():
    """Check MongoDB connection and document count"""
    try:
        db = get_database()
        if db is None:
            return {
                "connected": False,
                "error": "MongoDB database not initialized. Check if MongoDB is running and connection is established."
            }
        
        # Try to get collection and count documents
        collection = db.receipts
        doc_count = await collection.count_documents({})
        
        # Try a simple query
        sample_doc = await collection.find_one({})
        
        return {
            "connected": True,
            "database": settings.MONGODB_DB_NAME,
            "collection": "receipts",
            "document_count": doc_count,
            "sample_document_exists": sample_doc is not None
        }
    except Exception as e:
        logger.error(f"Error checking MongoDB health: {e}", exc_info=True)
        return {
            "connected": False,
            "error": str(e)
        }


# =============================================================================
# Double-Entry Accounting Endpoints
# =============================================================================

from app.api.schemas import (
    AccountSchema, JournalEntrySchema, CreateAccountRequest,
    TrialBalanceResponse, IncomeStatementResponse, BalanceSheetResponse
)


@router.get("/accounts", response_model=List[AccountSchema])
async def get_accounts():
    """Get all accounts in the Chart of Accounts with their current balances"""
    try:
        from app.services.accounting_service import get_all_accounts, initialize_chart_of_accounts
        # Ensure chart of accounts exists
        initialize_chart_of_accounts()
        accounts = get_all_accounts()
        return accounts
    except Exception as e:
        logger.error(f"Error getting accounts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts", response_model=AccountSchema)
async def create_account(account_data: CreateAccountRequest):
    """Create a new account in the Chart of Accounts"""
    try:
        from app.services.accounting_service import get_account_by_code
        from app.db.sql import SessionLocal, Account
        
        # Check if account code already exists
        existing = get_account_by_code(account_data.code)
        if existing:
            raise HTTPException(status_code=400, detail=f"Account with code {account_data.code} already exists")
        
        db = SessionLocal()
        try:
            account = Account(
                code=account_data.code,
                name=account_data.name,
                account_type=account_data.account_type,
                parent_id=account_data.parent_id,
                description=account_data.description,
                is_active=True
            )
            db.add(account)
            db.commit()
            db.refresh(account)
            
            return {
                "id": account.id,
                "code": account.code,
                "name": account.name,
                "account_type": account.account_type,
                "parent_id": account.parent_id,
                "description": account.description,
                "balance": 0.0,
                "normal_balance": "debit" if account.account_type in ["asset", "expense"] else "credit"
            }
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating account: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{account_id}/balance")
async def get_account_balance(account_id: int):
    """Get current balance for a specific account"""
    try:
        from app.services.accounting_service import calculate_account_balance
        from app.db.sql import SessionLocal, Account
        
        db = SessionLocal()
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                raise HTTPException(status_code=404, detail="Account not found")
            
            balance = calculate_account_balance(account_id)
            return {
                "account_id": account_id,
                "account_code": account.code,
                "account_name": account.name,
                "account_type": account.account_type,
                "balance": balance,
                "normal_balance": "debit" if account.account_type in ["asset", "expense"] else "credit"
            }
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting account balance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ledger/{record_id}/journal", response_model=JournalEntrySchema)
async def get_ledger_journal_entry(record_id: str):
    """Get the journal entry for a specific ledger entry"""
    try:
        from app.services.accounting_service import get_journal_entry_by_ledger_entry
        from app.db.sql import SessionLocal, LedgerEntry
        
        db = SessionLocal()
        try:
            ledger = db.query(LedgerEntry).filter(LedgerEntry.record_id == record_id).first()
            if not ledger:
                raise HTTPException(status_code=404, detail="Ledger entry not found")
            
            journal = get_journal_entry_by_ledger_entry(ledger.id)
            if not journal:
                raise HTTPException(status_code=404, detail="No journal entry found for this ledger entry")
            
            return journal
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting journal entry: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/journal-entries")
async def get_journal_entries(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """Get all journal entries with pagination"""
    try:
        from app.db.sql import SessionLocal, JournalEntry
        from sqlalchemy.orm import joinedload
        from app.services.accounting_service import format_journal_entry
        
        db = SessionLocal()
        try:
            entries = db.query(JournalEntry).options(
                joinedload(JournalEntry.lines)
            ).order_by(JournalEntry.entry_date.desc()).offset(skip).limit(limit).all()
            
            return [format_journal_entry(entry) for entry in entries]
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error getting journal entries: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/trial-balance", response_model=TrialBalanceResponse)
async def get_trial_balance_report():
    """Generate a Trial Balance report - sum of all debits should equal sum of all credits"""
    try:
        from app.services.accounting_service import get_trial_balance, initialize_chart_of_accounts
        initialize_chart_of_accounts()
        return get_trial_balance()
    except Exception as e:
        logger.error(f"Error generating trial balance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/income-statement", response_model=IncomeStatementResponse)
async def get_income_statement_report():
    """Generate an Income Statement (Profit & Loss) report"""
    try:
        from app.services.accounting_service import get_income_statement, initialize_chart_of_accounts
        initialize_chart_of_accounts()
        return get_income_statement()
    except Exception as e:
        logger.error(f"Error generating income statement: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/balance-sheet", response_model=BalanceSheetResponse)
async def get_balance_sheet_report():
    """Generate a Balance Sheet report - Assets = Liabilities + Equity"""
    try:
        from app.services.accounting_service import get_balance_sheet, initialize_chart_of_accounts
        initialize_chart_of_accounts()
        return get_balance_sheet()
    except Exception as e:
        logger.error(f"Error generating balance sheet: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts/initialize")
async def initialize_accounts():
    """Initialize the default Chart of Accounts"""
    try:
        from app.services.accounting_service import initialize_chart_of_accounts
        initialize_chart_of_accounts()
        return {"message": "Chart of accounts initialized successfully"}
    except Exception as e:
        logger.error(f"Error initializing accounts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Reconciliation Endpoints
# =============================================================================

from app.api.schemas import ReconciliationResponse, ReconciliationMatch
from app.services.reconciliation_service import (
    get_reconciliation_status,
    link_transactions
)


@router.get("/ledger/{record_id}/reconciliation", response_model=ReconciliationResponse)
async def get_reconciliation(record_id: str):
    """Get reconciliation status for a specific transaction"""
    try:
        from app.services.reconciliation_service import get_reconciliation_status
        from app.db.mongodb import get_database
        
        db = get_database()
        if db is None:
            raise HTTPException(status_code=500, detail="MongoDB database not connected")
        
        collection = db.receipts
        doc = await collection.find_one({"record_id": record_id})
        
        if not doc:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Get reconciliation info from document or compute it
        reconciliation_info = doc.get("reconciliation_info", {})
        
        # If not stored, return basic info
        if not reconciliation_info:
            return ReconciliationResponse(
                is_duplicate=False,
                is_counterparty=False,
                match_type="none",
                confidence=0.0,
                matched_records=[],
                counterparty_record=None
            )
        
        # Convert to response format
        return ReconciliationResponse(**reconciliation_info)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reconciliation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ledger/{record_id_1}/link/{record_id_2}")
async def link_transactions_endpoint(
    record_id_1: str,
    record_id_2: str,
    relationship: str = Query(default="counterparty", description="Relationship type: counterparty, duplicate, or related")
):
    """Manually link two transactions"""
    try:
        if relationship not in ["counterparty", "duplicate", "related"]:
            raise HTTPException(status_code=400, detail="Relationship must be one of: counterparty, duplicate, related")
        
        success = await link_transactions(record_id_1, record_id_2, relationship)
        
        if success:
            return {
                "message": f"Transactions {record_id_1} and {record_id_2} linked successfully",
                "record_id_1": record_id_1,
                "record_id_2": record_id_2,
                "relationship": relationship
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to link transactions")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking transactions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ledger/{record_id}/perspective/toggle", response_model=PerspectiveAnalysisResponse)
async def toggle_perspective(record_id: str):
    """
    Toggle the perspective of a transaction (swap direction, roles, and counterparty).
    This is useful when the company name is not configured and the perspective needs manual adjustment.
    """
    try:
        from app.db.mongodb import get_database
        
        db = get_database()
        if db is None:
            raise HTTPException(status_code=500, detail="MongoDB database not connected")
        
        collection = db.receipts
        doc = await collection.find_one({"record_id": record_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Receipt document not found")
        
        # Get current perspective - try to get from stored perspective first, otherwise analyze
        raw_text = doc.get("raw_text") or ""
        structured_data = doc.get("structured_data") or {}
        company = (settings.OUR_COMPANY_NAME or "").strip()
        
        # Check if perspective is stored in document
        stored_perspective = doc.get("perspective")
        if stored_perspective:
            current_perspective = stored_perspective
        else:
            # Analyze if not stored
            current_perspective = await analyze_perspective(
                raw_text,
                our_company_name=company,
                metadata={
                    "vendor": structured_data.get("vendor"),
                    "total": structured_data.get("total"),
                    "amount": structured_data.get("amount"),
                    "payment_method": structured_data.get("payment_method"),
                    "invoice_number": structured_data.get("invoice_number"),
                    "currency": structured_data.get("currency"),
                },
            )
        
        # Toggle the perspective
        new_direction = "INFLOW" if current_perspective.get("transactionDirection") == "OUTFLOW" else "OUTFLOW"
        
        # Swap roles
        if new_direction == "INFLOW":
            new_our_role = "VENDOR"
            new_counterparty_role = "CUSTOMER"
            new_document_role = "SALES_INVOICE"
        else:
            new_our_role = "BUYER"
            new_counterparty_role = "VENDOR"
            new_document_role = "PURCHASE_INVOICE"
        
        # Swap counterparty name intelligently
        # The vendor field in structured_data typically represents the seller/issuer
        # The counterparty in current perspective represents the other party
        vendor_name = structured_data.get("vendor", "")
        current_counterparty = current_perspective.get("counterpartyName", "")
        
        # Get ledger entry vendor for reference
        from app.services.ledger_service import get_ledger_entry
        ledger_entry = get_ledger_entry(record_id)
        entry_vendor = ledger_entry.get("vendor", "") if ledger_entry else ""
        
        # If current direction is OUTFLOW (we are buyer), counterparty is typically the vendor/seller
        # After toggle to INFLOW (we are vendor), counterparty should be the client/buyer
        # If current direction is INFLOW (we are vendor), counterparty is the client/buyer
        # After toggle to OUTFLOW (we are buyer), counterparty should be the vendor/seller
        if current_perspective.get("transactionDirection") == "OUTFLOW":
            # Currently we are buyer, counterparty is vendor
            # After toggle: we are vendor, counterparty should be client
            # The current counterparty is the vendor, so we need to find the client
            # For vendor invoices, the client is usually in the "Client" or "Bill To" section
            # If counterparty matches vendor, we need to find client from document
            if current_counterparty and vendor_name and current_counterparty.lower() == vendor_name.lower():
                # Counterparty matches vendor, need to find client
                # Re-analyze with empty company to find client name
                temp_perspective = await analyze_perspective(
                    raw_text,
                    our_company_name="",
                    metadata=structured_data,
                )
                # Try to get client name from temp analysis or use a fallback
                new_counterparty_name = temp_perspective.get("counterpartyName") or entry_vendor or "Client"
            else:
                # Counterparty might already be client, keep it
                new_counterparty_name = current_counterparty or entry_vendor or vendor_name
        else:
            # Currently we are vendor, counterparty is client
            # After toggle: we are buyer, counterparty should be vendor
            # Use vendor from structured_data as the counterparty
            new_counterparty_name = vendor_name or entry_vendor or current_counterparty
        
        toggled_perspective = {
            "transactionDirection": new_direction,
            "ourRole": new_our_role,
            "counterpartyRole": new_counterparty_role,
            "documentRole": new_document_role,
            "counterpartyName": new_counterparty_name or current_perspective.get("counterpartyName", ""),
            "confidence": current_perspective.get("confidence", 0.5)  # Keep same confidence
        }
        
        return PerspectiveAnalysisResponse(**toggled_perspective)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling perspective: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
