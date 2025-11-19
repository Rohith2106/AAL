# Environment Variables Setup

## .env File Format

Create a `.env` file in the `backend/` directory with the following variables:

```env
# Google Gemini API Key (Required)
GOOGLE_API_KEY=your_google_api_key_here

# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
# For MongoDB Atlas:
# MONGODB_URL=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=accounting_automation

# SQL Database Configuration
# MySQL (default):
DATABASE_URL=mysql+pymysql://root:1234@localhost:3306/ledger_db
# SQLite (alternative):
# DATABASE_URL=sqlite:///./ledger.db

# API Settings
API_HOST=0.0.0.0
API_PORT=8000

# CORS Origins (comma-separated or JSON array)
# Option 1: Comma-separated (recommended)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
# Option 2: JSON array
# CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# LLM Settings (optional)
LLM_MODEL=gemini-2.5-pro
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4096

# OCR Settings (optional)
OCR_ENGINE=tesseract
```

## CORS_ORIGINS Format

The `CORS_ORIGINS` variable can be set in two ways:

1. **Comma-separated string** (recommended):
   ```env
   CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:8080
   ```

2. **JSON array**:
   ```env
   CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
   ```

The configuration automatically parses both formats.

## MongoDB Atlas Connection String Format

For MongoDB Atlas, use this format:
```
mongodb+srv://<username>:<password>@<cluster>.mongodb.net/<database>?retryWrites=true&w=majority
```

Example:
```
mongodb+srv://myuser:mypassword@cluster0.abc123.mongodb.net/accounting_automation?retryWrites=true&w=majority
```

## MySQL Connection String Format

```
mysql+pymysql://<username>:<password>@<host>:<port>/<database>
```

Example (default):
```
mysql+pymysql://root:1234@localhost:3306/ledger_db
```

**Note:** The `+pymysql` part tells SQLAlchemy to use the PyMySQL driver.

## Required Variables

- `GOOGLE_API_KEY` - **Required** - Get from https://makersuite.google.com/app/apikey

## Optional Variables

All other variables have defaults and are optional unless you need custom configuration.

