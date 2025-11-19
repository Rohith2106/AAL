# LLM Accounting Automation - Frontend

Vue 3 + Tailwind CSS frontend for the accounting automation system.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env` file:
```bash
cp .env.example .env
```

3. Configure API URL in `.env`:
```
VITE_API_URL=http://localhost:8000/api/v1
```

4. Run development server:
```bash
npm run dev
```

## Features

- **Upload Tab**: Drag & drop receipts/invoices for processing
- **Ledger Tab**: View and filter all transactions
- **Chat Tab**: RAG-powered chatbot for querying ledger

## Tech Stack

- Vue 3
- Tailwind CSS
- Axios for API calls
- Headless UI components
