"""
backend/app/database/models.py
--------------------------------
SQLAlchemy ORM models for the Sentiment-Driven Stock Screener.

Person 2 owns this module.

Tables
------
users           — registered application users
watchlist_items — stocks a user has selected to monitor
news_records    — normalized financial news persisted by the system

Design notes
------------
- All primary keys are auto-increment integers for simplicity.
- Timestamps use server_default=func.now() so the database fills them
  in; no application-side datetime logic is required.
- news_records.news_id is unique to enforce deduplication: Person 1
  produces a news_id per article; if the same article arrives twice
  only one row is stored.
- Foreign keys enforce referential integrity at the DB level.
- No nullable=False duplication — SQLAlchemy defaults are used where
  the intent is clear from the column name.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(Base):
    """
    An application user who has registered and created a profile.

    Person 2 is responsible for the User lifecycle (registration,
    profile management).  Authentication is out of scope for Review 1.
    """

    __tablename__ = "users"

    id: int = Column(Integer, primary_key=True, index=True)
    email: str = Column(String(255), unique=True, nullable=False, index=True)
    is_active: bool = Column(Boolean, default=True, nullable=False)
    created_at: datetime = Column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationship: one user → many watchlist items
    watchlist_items = relationship(
        "WatchlistItem",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


# ---------------------------------------------------------------------------
# WatchlistItem
# ---------------------------------------------------------------------------

class WatchlistItem(Base):
    """
    A single stock symbol that a user has added to their watchlist.

    Person 1's monitoring pipeline reads watchlist symbols to know
    which stocks to ingest news for.
    Person 2 manages the CRUD operations around this table.
    """

    __tablename__ = "watchlist_items"

    id: int = Column(Integer, primary_key=True, index=True)
    user_id: int = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: str = Column(String(20), nullable=False)        # e.g. "AAPL"
    company_name: str = Column(String(255), nullable=False) # e.g. "Apple Inc."
    created_at: datetime = Column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Constraint: a user cannot add the same symbol twice
    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="uq_user_symbol"),
    )

    # Relationship: many watchlist items → one user
    user = relationship("User", back_populates="watchlist_items")

    def __repr__(self) -> str:
        return f"<WatchlistItem id={self.id} user_id={self.user_id} symbol={self.symbol!r}>"


# ---------------------------------------------------------------------------
# NewsRecord
# ---------------------------------------------------------------------------

class NewsRecord(Base):
    """
    A persisted, normalized financial news article.

    Person 1 produces normalized news (NewsItem Pydantic objects).
    Person 2 converts them into NewsRecord rows and stores them.
    Person 3's AI pipeline reads NewsRecord rows for analysis.

    news_id is unique: if Person 1 delivers the same article twice,
    the second insert is rejected at the database level (deduplication).
    """

    __tablename__ = "news_records"

    id: int = Column(Integer, primary_key=True, index=True)

    # Core fields — mirror the Pydantic NewsItem contract exactly
    news_id: str = Column(String(255), unique=True, nullable=False, index=True)
    symbol: str = Column(String(20), nullable=False, index=True)
    company_name: str = Column(String(255), nullable=False)
    title: str = Column(String(512), nullable=False)
    content: str = Column(Text, nullable=False)
    source: str = Column(String(255), nullable=False)
    url: str = Column(String(2048), nullable=False)
    published_at: datetime = Column(DateTime, nullable=False)

    # Audit field — when this row was inserted into our database
    created_at: datetime = Column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<NewsRecord id={self.id} symbol={self.symbol!r} "
            f"news_id={self.news_id!r}>"
        )


# ---------------------------------------------------------------------------
# AlertRecord
# ---------------------------------------------------------------------------

class AlertRecord(Base):
    """
    A persisted alert generated by the system (e.g. Person 3's AI decision engine).

    Stores actionable alerts produced when news crosses user or system thresholds.
    """

    __tablename__ = "alert_records"

    id: int = Column(Integer, primary_key=True, index=True)
    alert_id: str = Column(String(255), unique=True, nullable=False, index=True)
    user_id: int = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    symbol: str = Column(String(20), nullable=False, index=True)
    action: str = Column(String(50), nullable=False)        # e.g. RISK_ALERT, OPPORTUNITY, WATCH, INFORMATIONAL
    severity: int = Column(Integer, nullable=False)         # 1-10
    message: str = Column(Text, nullable=False)
    should_alert: bool = Column(Boolean, default=True, nullable=False)
    created_at: datetime = Column(
        DateTime, server_default=func.now(), nullable=False
    )

    user = relationship("User", backref="alerts")

    def __repr__(self) -> str:
        return (
            f"<AlertRecord id={self.id} alert_id={self.alert_id!r} "
            f"symbol={self.symbol!r} action={self.action!r}>"
        )


# ---------------------------------------------------------------------------
# HistoricalPrice
# ---------------------------------------------------------------------------

class HistoricalPrice(Base):
    """
    Persisted historical OHLCV market price record.

    Logical unique key: (symbol, exchange, timestamp) prevents duplicate candles.
    """

    __tablename__ = "historical_prices"

    id: int = Column(Integer, primary_key=True, index=True)
    symbol: str = Column(String(20), nullable=False, index=True)
    exchange: str = Column(String(20), nullable=False, index=True)
    timestamp: datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    open: float = Column(Float, nullable=False)
    high: float = Column(Float, nullable=False)
    low: float = Column(Float, nullable=False)
    close: float = Column(Float, nullable=False)
    volume: float = Column(Float, nullable=False, default=0.0)

    created_at: datetime = Column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("symbol", "exchange", "timestamp", name="uq_symbol_exchange_timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<HistoricalPrice id={self.id} symbol={self.symbol!r} "
            f"exchange={self.exchange!r} timestamp={self.timestamp.isoformat()}>"
        )
