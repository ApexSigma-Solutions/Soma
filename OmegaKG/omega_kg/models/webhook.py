from typing import Any, Dict, Optional
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, Boolean, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from omega_kg.database.base import Base


class RawWebhookEvent(Base):
    __tablename__ = "raw_webhook_events"

    id = Column(Integer, primary_key=True, index=True)

    source = Column(
        String,
        index=True,
        nullable=False,
        comment="Webhook source (linear, github, etc.)",
    )
    received_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Server receipt timestamp",
    )
    processed_status = Column(
        Boolean,
        default=False,
        server_default=text("false"),
        comment="Event processing status",
    )

    headers = Column(JSONB, nullable=False, comment="HTTP headers from webhook")
    payload = Column(JSONB, nullable=False, comment="Raw JSON payload")

    event_type = Column(
        String, index=True, nullable=True, comment="Event type (issue.created, etc.)"
    )

    error_log = Column(String, nullable=True, comment="Processing error details if any")


class RawWebhookEventPydantic(BaseModel):
    id: Optional[int] = None
    source: str = Field(..., description="Webhook source (linear, github, etc.)")
    received_at: Optional[datetime] = None
    processed_status: bool = False
    headers: Dict[str, Any] = Field(default_factory=dict)
    payload: Dict[str, Any] = Field(default_factory=dict)
    event_type: Optional[str] = None
    error_log: Optional[str] = None

    class Config:
        from_attributes = True
