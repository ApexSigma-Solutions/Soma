from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from omega_kg.database.base import Base

# --- Pydantic Models ---


class TerminalCommandData(BaseModel):
    """Payload received from the terminal hook."""

    command: str
    cwd: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    exit_code: Optional[int] = None
    output: Optional[str] = None
    user: Optional[str] = None
    host: Optional[str] = None
    session_id: Optional[str] = None


class TerminalCaptureResponse(BaseModel):
    status: str
    event_id: UUID
    processed: bool


# --- SQLAlchemy Models ---


class TerminalEvent(Base):
    """Raw terminal event stored in the Ingest Database."""

    __tablename__ = "raw_terminal_events"

    id = Column(Integer, primary_key=True)
    event_id = Column(PG_UUID(as_uuid=True), unique=True, nullable=False, default=uuid4)
    session_id = Column(String(255), nullable=True)
    command = Column(Text, nullable=False)
    cwd = Column(Text, nullable=True)
    exit_code = Column(Integer, nullable=True)
    output = Column(Text, nullable=True)
    user = Column(String(255), nullable=True)
    host = Column(String(255), nullable=True)

    raw_payload = Column(JSONB, nullable=False)
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Processing Status
    processed = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    processing_attempts = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<TerminalEvent(id={self.id}, event_id={self.event_id}, command='{self.command[:20]}...')>"
