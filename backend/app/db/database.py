"""
TruthLens AI — Database models and persistence layer.

Uses SQLAlchemy with SQLite for the MVP. The schema mirrors the Pydantic
response models so reports can be stored and retrieved from history.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Session,
    relationship,
    sessionmaker,
)

from app.core.config import settings


class Base(DeclarativeBase):
    pass


class VerificationRecord(Base):
    __tablename__ = "verifications"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    input_type = Column(String, nullable=False)
    original_input = Column(Text, nullable=True)
    extracted_text = Column(Text, nullable=True)
    language = Column(String, default="en")
    status = Column(String, default="pending")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    claims = relationship("ClaimRecord", back_populates="verification", cascade="all, delete-orphan")


class ClaimRecord(Base):
    __tablename__ = "claims"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    verification_id = Column(String, ForeignKey("verifications.id"), nullable=False)
    claim_text = Column(Text, nullable=False)
    claim_type = Column(String, nullable=True)
    verdict = Column(String, nullable=True)
    explanation = Column(Text, nullable=True)
    evidence_assessment = Column(String, nullable=True)
    uncertainties_json = Column(Text, default="[]")

    verification = relationship("VerificationRecord", back_populates="claims")
    evidence_items = relationship("EvidenceRecord", back_populates="claim", cascade="all, delete-orphan")

    @property
    def uncertainties(self) -> list[str]:
        return json.loads(self.uncertainties_json) if self.uncertainties_json else []


class EvidenceRecord(Base):
    __tablename__ = "evidence"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    claim_id = Column(String, ForeignKey("claims.id"), nullable=False)
    source_url = Column(Text, nullable=False)
    source_title = Column(Text, nullable=True)
    publisher = Column(String, nullable=True)
    published_at = Column(String, nullable=True)
    retrieved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    snippet = Column(Text, nullable=True)
    relationship_type = Column(String, default="partially_relevant")

    claim = relationship("ClaimRecord", back_populates="evidence_items")


# ── Engine & Session ────────────────────────────────────────────────

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


# Ensure tables exist upon database module load
init_db()


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
