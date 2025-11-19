# LLM Accounting Automation

A comprehensive accounting automation system powered by LLM (Gemini 2.5 Pro), OCR, vector databases, and modern web technologies.

## 🚀 Features

- **OCR Processing**: Extract text from receipts, invoices, and PDFs using Tesseract or EasyOCR
- **Intelligent Data Extraction**: Automatically structure extracted text into JSON format
- **Vector Database Reconciliation**: MongoDB vector store for duplicate detection and similarity matching
- **LLM Validation**: LangChain + Gemini 2.5 Pro for intelligent validation and reasoning
- **RAG Chatbot**: Query your ledger and receipts using natural language
- **SQL Ledger**: Store validated transactions in SQL database
- **Modern UI**: Clean, minimal Vue.js frontend with Tailwind CSS

## 📋 Tech Stack

### Backend
- **FastAPI**: Modern Python web framework
- **LangChain**: LLM orchestration framework
- **Google Gemini 2.5 Pro**: Large language model for validation
- **MongoDB**: Vector database for reconciliation and RAG
- **SQLAlchemy**: SQL database ORM
- **Tesseract/EasyOCR**: OCR engines for text extraction
- **Sentence Transformers**: Embedding generation

### Frontend
- **Vue 3**: Progressive JavaScript framework
- **Tailwind CSS**: Utility-first CSS framework
- **Axios**: HTTP client for API calls
- **Headless UI**: Accessible UI components

## 🏗️ Architecture

```
┌─────────────┐
│   Frontend  │ Vue + Tailwind
│  (Upload)   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│              FastAPI Backend                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │   OCR    │→ │ Extract  │→ │  Vector  │      │
│  │ Service  │  │ Service  │  │  Service │      │
│  └──────────┘  └──────────┘  └────┬─────┘      │
│                                    │            │
│  ┌──────────┐  ┌──────────┐      │            │
│  │   LLM    │← │Reconcile │←─────┘            │
│  │Orchestr. │  │  Check   │                    │
│  └────┬─────┘  └──────────┘                    │
│       │                                        │
│       ▼                                        │
│  ┌──────────┐                                 │
│  │  Ledger  │                                 │
│  │ Service  │                                 │
│  └────┬─────┘                                 │
└───────┼───────────────────────────────────────┘
        │
        ▼
┌─────────────┐  ┌─────────────┐
│  MongoDB    │  │  SQL DB     │
│ (Vector DB) │  │  (Ledger)   │
└─────────────┘  └─────────────┘
```

## 📦 Installation

### Prerequisites
- Python 3.9+
- Node.js 18+
- MongoDB (for vector database)
- MySQL (for ledger - already installed with username: root, password: 1234)

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
cp .env.example .env
```

5. Configure environment variables in `.env`:
```env
GOOGLE_API_KEY=your_google_api_key_here
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=accounting_automation
DATABASE_URL=mysql+pymysql://root:1234@localhost:3306/ledger_db
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173
```

6. Run the server:
```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env` file:
```bash
cp .env.example .env
```

4. Configure API URL in `.env`:
```env
VITE_API_URL=http://localhost:8000/api/v1
```

5. Run development server:
```bash
npm run dev
```

## 🔄 Workflow

1. **Upload**: User uploads receipt/invoice image or PDF
2. **OCR**: Extract raw text using Tesseract or EasyOCR
3. **Extraction**: Parse structured data (vendor, date, items, totals)
4. **Embedding**: Generate vector embedding for the document
5. **Reconciliation**: Check for duplicates using vector similarity
6. **Validation**: LLM validates the extracted data
7. **Reasoning**: Generate reasoning trace and explanation
8. **Storage**: Store validated entry in SQL ledger
9. **Vector Store**: Store in MongoDB for future RAG queries

## 📡 API Endpoints

### Process Receipt
```http
POST /api/v1/process-receipt
Content-Type: multipart/form-data

file: <image or pdf>
ocr_engine: tesseract | easyocr
```

### Get Ledger
```http
GET /api/v1/ledger?skip=0&limit=100&status=validated&vendor=Amazon
```

### Get Entry
```http
GET /api/v1/ledger/{record_id}
```

### Approve Entry
```http
POST /api/v1/ledger/{record_id}/approve
```

### Chat
```http
POST /api/v1/chat
Content-Type: application/json

{
  "message": "What is the total amount spent?",
  "record_id": null
}
```

### Stats
```http
GET /api/v1/stats
```

## 🎨 UI Features

- **Upload Tab**: Drag & drop interface for receipt processing
- **Ledger Tab**: Filterable table with transaction details
- **Chat Tab**: RAG-powered chatbot for natural language queries

## 🔧 Configuration

### OCR Engine
Choose between:
- `tesseract`: Faster, good for English text
- `easyocr`: Better accuracy, supports multiple languages

### LLM Model
Default: `gemini-2.5-pro`
Fallback: `gemini-1.5-pro`

### Database
- **MongoDB**: Vector storage and RAG
- **MySQL**: Transaction ledger (default: root/1234@localhost:3306)

## 📝 Notes

- Ensure MongoDB is running for vector database functionality
- Ensure MySQL is running (default: root/1234@localhost:3306)
- Google API key is required for LLM features
- First OCR run may download models (EasyOCR)
- MySQL database `ledger_db` will be created automatically on first run

## 🐛 Troubleshooting

### MongoDB Connection Error
- Ensure MongoDB is running: `mongod`
- Check connection string in `.env`

### OCR Errors
- Install Tesseract: `apt-get install tesseract-ocr` (Linux) or `brew install tesseract` (Mac)
- For EasyOCR, models download automatically on first use

### LLM API Errors
- Verify `GOOGLE_API_KEY` is set correctly
- Check API quota and limits

## 📄 License

MIT

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a pull request.

