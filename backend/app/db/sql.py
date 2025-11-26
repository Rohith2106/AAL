from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey
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


class LedgerItem(Base):
    __tablename__ = "ledger_items"
    
    id = Column(Integer, primary_key=True, index=True)
    ledger_entry_id = Column(Integer, ForeignKey("ledger_entries.id"))
    name = Column(String(255))
    quantity = Column(Integer, default=1)
    unit_price = Column(Float)
    line_total = Column(Float)
    
    entry = relationship("LedgerEntry", back_populates="items")


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

