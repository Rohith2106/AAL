# Quick Start Guide

## Prerequisites

1. **Python 3.9+** installed
2. **Node.js 18+** installed
3. **MongoDB** running (for vector database)
4. **Google Gemini API Key** (get from https://makersuite.google.com/app/apikey)

## Step 1: Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env and add your GOOGLE_API_KEY
# GOOGLE_API_KEY=your_key_here

# Run backend
python main.py
```

Backend will start at `http://localhost:8000`

## Step 2: Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env

# Run frontend
npm run dev
```

Frontend will start at `http://localhost:5173`

## Step 3: Test the System

1. Open `http://localhost:5173` in your browser
2. Go to "Upload" tab
3. Drag and drop a receipt image (JPG, PNG) or PDF
4. Wait for processing (OCR → Extraction → Validation)
5. Review results and approve if valid
6. Check "Ledger" tab to see stored transactions
7. Use "Chat" tab to query your ledger

## Troubleshooting

### MongoDB not running
```bash
# Start MongoDB (Linux/Mac)
mongod

# Or use Docker
docker run -d -p 27017:27017 mongo
```

### OCR errors
- Install Tesseract: `apt-get install tesseract-ocr` (Linux) or `brew install tesseract` (Mac)
- EasyOCR will auto-download models on first use

### API errors
- Verify `GOOGLE_API_KEY` in backend/.env
- Check API quota at Google AI Studio

## Next Steps

- Upload multiple receipts to test batch processing
- Try the chat interface: "What is the total amount spent?"
- Filter ledger by vendor or status
- Review validation results and reasoning traces

