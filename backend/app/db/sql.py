from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from app.core.config import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    ledger_entries = relationship("LedgerEntry", back_populates="user", cascade="all, delete-orphan")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    record_id = Column(String(100), index=True)
    vendor = Column(String(255), index=True)
    
    # Unique constraint on user_id + record_id combination
    __table_args__ = (
        UniqueConstraint('user_id', 'record_id', name='uq_user_record'),
    )
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
    user = relationship("User", back_populates="ledger_entries")


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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    code = Column(String(20), index=True)  # e.g., "1100", "5100"
    name = Column(String(255), nullable=False)
    account_type = Column(String(50), nullable=False)  # asset, liability, equity, revenue, expense
    parent_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Unique constraint on user_id + code combination
    __table_args__ = (
        UniqueConstraint('user_id', 'code', name='uq_user_account_code'),
    )
    
    # Self-referential relationship for parent-child accounts
    parent = relationship("Account", remote_side=[id], backref="children")
    journal_lines = relationship("JournalEntryLine", back_populates="account")


class JournalEntry(Base):
    """Double-entry journal entry - groups debit/credit lines for a transaction"""
    __tablename__ = "journal_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
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


# =============================================================================
# IFRS-Based Claim Rights and Amortization Models
# =============================================================================

class ClaimRight(Base):
    """
    IFRS-based claim rights recognition for long-term payments.
    Represents assets (our claim rights) or liabilities (others' claim rights on us).
    """
    __tablename__ = "claim_rights"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ledger_entry_id = Column(Integer, ForeignKey("ledger_entries.id"), nullable=True, index=True)
    
    # Classification
    claim_type = Column(String(50), nullable=False)  # ASSET_CLAIM or LIABILITY_CLAIM
    description = Column(Text, nullable=False)
    
    # Financial amounts
    total_amount = Column(Float, nullable=False)  # Original total amount
    remaining_amount = Column(Float, nullable=False)  # Remaining unamortized amount
    amortized_amount = Column(Float, default=0.0)  # Total amortized so far
    
    # Time period
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=False, index=True)
    frequency = Column(String(20), default="monthly")  # monthly, quarterly, yearly, etc.
    
    # Status
    status = Column(String(50), default="active")  # active, completed, cancelled
    cancellation_date = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    # IFRS Recognition Criteria
    is_probable = Column(Boolean, default=True)  # Future economic benefit/obligation is probable
    is_measurable = Column(Boolean, default=True)  # Amount can be measured reliably
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    schedule = relationship("AmortizationSchedule", back_populates="claim_right", uselist=False, cascade="all, delete-orphan")
    entries = relationship("AmortizationEntry", back_populates="claim_right", cascade="all, delete-orphan", order_by="AmortizationEntry.period_start")
    ledger_entry = relationship("LedgerEntry", backref="claim_rights")


class AmortizationSchedule(Base):
    """
    Amortization schedule for a claim right.
    Defines the time-based schedule for recognizing revenue/expense.
    """
    __tablename__ = "amortization_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_right_id = Column(Integer, ForeignKey("claim_rights.id"), nullable=False, unique=True, index=True)
    
    # Schedule configuration
    total_periods = Column(Integer, nullable=False)  # Total number of periods
    amount_per_period = Column(Float, nullable=False)  # Amount to recognize per period
    
    # Status
    is_generated = Column(Boolean, default=False)
    generated_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    claim_right = relationship("ClaimRight", back_populates="schedule")
    entries = relationship("AmortizationEntry", back_populates="schedule", cascade="all, delete-orphan", order_by="AmortizationEntry.period_start")


class AmortizationEntry(Base):
    """
    Individual period entry in the amortization schedule.
    Represents one period's accrual (revenue or expense recognition).
    """
    __tablename__ = "amortization_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_right_id = Column(Integer, ForeignKey("claim_rights.id"), nullable=False, index=True)
    schedule_id = Column(Integer, ForeignKey("amortization_schedules.id"), nullable=False, index=True)
    
    # Period information
    period_number = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    
    # Amount for this period
    amount = Column(Float, nullable=False)
    
    # Status
    status = Column(String(50), default="PENDING")  # PENDING, POSTED, SKIPPED
    posted_at = Column(DateTime, nullable=True)
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=True, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    claim_right = relationship("ClaimRight", back_populates="entries")
    schedule = relationship("AmortizationSchedule", back_populates="entries")
    journal_entry = relationship("JournalEntry", backref="amortization_entries")


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

