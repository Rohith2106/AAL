from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional, List, List as ListType
import uuid
import logging
from datetime import datetime
import json
from app.api.schemas import (
    ProcessReceiptResponse, LedgerEntryResponse, ChatMessage, ChatResponse,
    ProcessMultipleReceiptsResponse, CreateManualEntryRequest
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
            logger.info(f"Processing file {file.filename} with OCR engine: {ocr_engine}")
            if file_ext == 'pdf':
                ocr_result = await extract_text_from_pdf(file_bytes)
                # Extract text from PDF result (dict)
                raw_text = ocr_result.get("text") if isinstance(ocr_result, dict) else ocr_result
                ocr_metrics = ocr_result.get("metrics") if isinstance(ocr_result, dict) else {}
            else:
                ocr_result = await extract_text_from_image(file_bytes, ocr_engine)
                # Extract text from image result (now returns dict with metrics)
                raw_text = ocr_result.get("text") if isinstance(ocr_result, dict) else ocr_result
                ocr_metrics = ocr_result.get("metrics") if isinstance(ocr_result, dict) else {}
            
            if not raw_text:
                raise HTTPException(status_code=400, detail="No text extracted from image")
            
            # Log OCR metrics if available
            if ocr_metrics:
                logger.info(f"OCR Metrics - Confidence: {ocr_metrics.get('confidence_metrics', {}).get('average_confidence', 'N/A')}")
            
            # Step 2: Data Extraction
            structured_data = await parse_receipt_text(raw_text)
            structured_data["record_id"] = record_id
            
            # Step 2.5: Classify transaction using LLM
            if not structured_data.get("category"):
                structured_data["category"] = await classify_transaction(structured_data)
            
            # Step 3: Create embedding
            embedding = await create_embedding(raw_text)
            
            # Step 4: Check for duplicates/reconciliation
            reconciliation = await check_duplicates(record_id, embedding)
            
            # Step 5: Store in vector DB
            await store_document(record_id, structured_data, embedding, raw_text)
            
            # Step 6: LLM Orchestration
            orchestration_result = await orchestrate(
                structured_data,
                reconciliation_info=reconciliation
            )
            
            # Log validation result
            validation_status = orchestration_result["validation_result"]["status"]
            logger.info(f"Validation status: {validation_status}, Confidence: {orchestration_result['validation_result']['confidence']}")
            
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
    ocr_engine: str = Query(default="easyocr", description="OCR engine: tesseract or easyocr")
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
            logger.info(f"Processing file {file.filename} with OCR engine: {ocr_engine}")
            if file_ext == 'pdf':
                ocr_result = await extract_text_from_pdf(file_bytes)
                raw_text = ocr_result.get("text") if isinstance(ocr_result, dict) else ocr_result
            else:
                ocr_result = await extract_text_from_image(file_bytes, ocr_engine)
                raw_text = ocr_result.get("text") if isinstance(ocr_result, dict) else ocr_result
            
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
            reconciliation = await check_duplicates(record_id, embedding)
            
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

