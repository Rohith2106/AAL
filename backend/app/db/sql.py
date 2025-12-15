from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from app.core.config import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

Base = declarative_base()


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(String(100), unique=True, index=True)
    vendor = Column(String(255), index=True)
    date = Column(String(50))
    amount = Column(Float)
    tax = Column(Float, nullable=True)
    total = Column(Float)
    currency = Column(String(3), default="USD")  # ISO currency code
    exchange_rate = Column(Float, default=1.0)  # Exchange rate to USD
    usd_total = Column(Float)  # Total in USD for aggregation
    invoice_number = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    payment_method = Column(String(50), nullable=True)
    status = Column(String(50), default="validated")  # validated, pending, rejected
    validation_confidence = Column(Float, nullable=True)
    validation_issues = Column(JSON, nullable=True)
    reasoning_trace = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    items = relationship("LedgerItem", back_populates="entry", cascade="all, delete-orphan")
    journal_entry = relationship("JournalEntry", back_populates="ledger_entry", uselist=False, cascade="all, delete-orphan")


class LedgerItem(Base):
    __tablename__ = "ledger_items"
    
    id = Column(Integer, primary_key=True, index=True)
    ledger_entry_id = Column(Integer, ForeignKey("ledger_entries.id"))
    name = Column(String(255))
    quantity = Column(Integer, default=1)
    unit_price = Column(Float)
    line_total = Column(Float)
    
    entry = relationship("LedgerEntry", back_populates="items")


# =============================================================================
# Double-Entry Accounting Models
# =============================================================================

class Account(Base):
    """Chart of Accounts - represents individual accounts in the accounting system"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True)  # e.g., "1100", "5100"
    name = Column(String(255), nullable=False)
    account_type = Column(String(50), nullable=False)  # asset, liability, equity, revenue, expense
    parent_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Self-referential relationship for parent-child accounts
    parent = relationship("Account", remote_side=[id], backref="children")
    journal_lines = relationship("JournalEntryLine", back_populates="account")


class JournalEntry(Base):
    """Double-entry journal entry - groups debit/credit lines for a transaction"""
    __tablename__ = "journal_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    ledger_entry_id = Column(Integer, ForeignKey("ledger_entries.id"), nullable=True)
    entry_date = Column(DateTime, nullable=False)
    reference = Column(String(100), index=True)  # Links to receipt/invoice record_id
    description = Column(Text)
    memo = Column(Text, nullable=True)
    is_balanced = Column(Boolean, default=True)
    is_adjusting = Column(Boolean, default=False)  # For adjusting entries
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ledger_entry = relationship("LedgerEntry", back_populates="journal_entry")
    lines = relationship("JournalEntryLine", back_populates="journal_entry", cascade="all, delete-orphan")


class JournalEntryLine(Base):
    """Individual debit or credit line within a journal entry"""
    __tablename__ = "journal_entry_lines"
    
    id = Column(Integer, primary_key=True, index=True)
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    debit = Column(Float, default=0.0)
    credit = Column(Float, default=0.0)
    description = Column(String(255), nullable=True)
    
    # Relationships
    journal_entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("Account", back_populates="journal_lines")


# Create engine and session
def create_database_engine():
    """Create database engine with appropriate connection args"""
    url = settings.DATABASE_URL
    
    if "sqlite" in url:
        # SQLite connection args
        connect_args = {"check_same_thread": False}
    elif "mysql" in url:
        # MySQL connection args
        connect_args = {
            "charset": "utf8mb4",
            "connect_timeout": 10
        }
    else:
        # Default (PostgreSQL, etc.)
        connect_args = {}
    
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)

engine = create_database_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

