# Database Setup Guide

## MongoDB Configuration

### Local MongoDB

For local development, MongoDB runs on `localhost:27017` by default.

**Configuration in `.env`:**
```env
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=accounting_automation
```

**Setup:**
1. Install MongoDB: https://www.mongodb.com/try/download/community
2. Start MongoDB service
3. Run setup script: `python scripts/setup_mongodb_vector_index.py`

### MongoDB Atlas (Cloud)

For production or vector search, use MongoDB Atlas.

**Configuration in `.env`:**
```env
MONGODB_URL=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=accounting_automation
```

**Setup Steps:**

1. **Create MongoDB Atlas Cluster:**
   - Go to https://www.mongodb.com/cloud/atlas
   - Create a free cluster (M0)
   - Note your cluster connection string

2. **Create Database and Collection:**
   - Database name: `accounting_automation`
   - Collection name: `receipts`

3. **Create Vector Search Index:**
   
   **Option A: Using Atlas UI**
   - Go to Atlas → Search → Create Search Index
   - Select "JSON Editor"
   - Use this configuration:
   ```json
   {
     "name": "vector_index",
     "type": "vector",
     "definition": {
       "fields": [
         {
           "type": "vector",
           "path": "embedding",
           "numDimensions": 384,
           "similarity": "cosine"
         }
       ]
     }
   }
   ```

   **Option B: Using Setup Script**
   ```bash
   python scripts/setup_mongodb_vector_index.py
   ```
   (Note: Script will guide you through Atlas UI setup)

4. **Network Access:**
   - Add your IP address to Atlas Network Access
   - Or use `0.0.0.0/0` for development (not recommended for production)

5. **Database User:**
   - Create a database user with read/write permissions
   - Use credentials in connection string

### Vector Search Index Details

- **Index Name:** `vector_index`
- **Field:** `embedding`
- **Dimensions:** 384 (all-MiniLM-L6-v2 model)
- **Similarity:** Cosine
- **Collection:** `receipts`

The index enables:
- Fast similarity search for duplicate detection
- Efficient RAG queries
- Scalable vector operations

**Note:** Vector search requires MongoDB Atlas. For local MongoDB, the application uses application-level cosine similarity (already implemented in `vector_service.py`).

---

## SQL Database Configuration

### SQLite (Default - No Configuration Needed)

SQLite is used by default and requires no setup.

**Configuration in `.env`:**
```env
DATABASE_URL=sqlite:///./ledger.db
```

**Features:**
- ✅ No installation required
- ✅ Database file created automatically
- ✅ Perfect for development
- ✅ File-based storage

**Location:** Database file is created at `backend/ledger.db`

### MySQL (Production)

MySQL is used for production with better performance and concurrent access.

**Default Configuration:**
- Username: `root`
- Password: `1234`
- Host: `localhost`
- Port: `3306`
- Database: `ledger_db`

**Setup:**

1. **Create Database:**
   ```sql
   CREATE DATABASE IF NOT EXISTS ledger_db;
   USE ledger_db;
   ```

2. **Configuration in `.env`:**
   ```env
   DATABASE_URL=mysql+pymysql://root:1234@localhost:3306/ledger_db
   ```

3. **Install MySQL Driver:**
   Already included in `requirements.txt`:
   - `pymysql==1.1.1`
   - `cryptography==43.0.1`

4. **Run Migration:**
   The tables are created automatically on first run via SQLAlchemy.

**Note:** If you need to change the MySQL credentials, update the `DATABASE_URL` in your `.env` file.

### Database Schema

**Table: `ledger_entries`**

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| record_id | String | Unique record identifier |
| vendor | String | Vendor name |
| date | String | Transaction date |
| amount | Float | Base amount |
| tax | Float | Tax amount |
| total | Float | Total amount |
| invoice_number | String | Invoice/receipt number |
| description | Text | Transaction description |
| category | String | Expense category |
| payment_method | String | Payment method |
| status | String | Validation status |
| validation_confidence | Float | LLM confidence score |
| validation_issues | JSON | List of validation issues |
| reasoning_trace | JSON | LLM reasoning trace |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

**Indexes:**
- Primary key on `id`
- Unique index on `record_id`
- Index on `vendor` for faster filtering
- Index on `status` for status filtering

---

## Quick Setup Commands

### MongoDB Local
```bash
# Start MongoDB
mongod

# Or with Docker
docker run -d -p 27017:27017 --name mongodb mongo

# Run setup script
cd backend
python scripts/setup_mongodb_vector_index.py
```

### MongoDB Atlas
1. Create cluster at https://cloud.mongodb.com
2. Get connection string
3. Update `.env` with connection string
4. Create vector search index (see above)

### MySQL
```bash
# MySQL should already be installed
# Create database
mysql -u root -p1234
CREATE DATABASE IF NOT EXISTS ledger_db;
EXIT;

# Update .env (already configured by default)
DATABASE_URL=mysql+pymysql://root:1234@localhost:3306/ledger_db
```

---

## Verification

### Test MongoDB Connection
```python
from app.db.mongodb import connect_to_mongo
import asyncio

asyncio.run(connect_to_mongo())
```

### Test SQL Connection
```python
from app.db.sql import init_db, engine
init_db()
print("Database tables created successfully")
```

### Check Vector Index (Atlas)
```python
from app.services.vector_service_atlas import check_vector_index_exists
import asyncio

exists = asyncio.run(check_vector_index_exists())
print(f"Vector index exists: {exists}")
```

---

## Troubleshooting

### MongoDB Connection Issues
- Check MongoDB is running: `mongod --version`
- Verify connection string format
- Check network access (for Atlas)
- Verify database user credentials

### Vector Search Not Working
- Ensure MongoDB Atlas (not local)
- Verify vector index is created
- Check index name matches: `vector_index`
- Verify embedding dimensions: 384

### SQL Database Issues
- SQLite: Check file permissions
- MySQL: Verify user permissions and database exists
- Check connection string format
- Ensure MySQL service is running
- Verify credentials (username: root, password: 1234)

