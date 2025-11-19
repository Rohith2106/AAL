# LLM Accounting Automation - Backend

FastAPI backend for automated accounting with OCR, LLM validation, and ledger management.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file from `.env.example`:
```bash
cp .env.example .env
```

3. Configure environment variables:
- `GOOGLE_API_KEY`: Your Google Gemini API key
- `MONGODB_URL`: MongoDB connection string
- `DATABASE_URL`: SQL database connection string

4. Run the server:
```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --reload
```

## API Endpoints

- `POST /api/v1/process-receipt`: Process receipt/invoice through complete pipeline
- `GET /api/v1/ledger`: Get ledger entries with filters
- `GET /api/v1/ledger/{record_id}`: Get specific ledger entry
- `POST /api/v1/ledger/{record_id}/approve`: Approve pending entry
- `POST /api/v1/chat`: Chat with ledger using RAG
- `GET /api/v1/stats`: Get ledger statistics

## Architecture

- **OCR Service**: Text extraction from images/PDFs
- **Extraction Service**: Structure OCR text into JSON
- **Vector Service**: MongoDB vector database for reconciliation
- **LLM Orchestrator**: LangChain + Gemini 2.5 Pro for validation
- **Ledger Service**: SQL database for transaction storage

