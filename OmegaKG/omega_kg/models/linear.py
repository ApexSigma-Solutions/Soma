from sqlalchemy import Column, Integer, String, DateTime, Boolean, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from omega_kg.database.base import Base


class RawLinearEvent(Base):
    __tablename__ = "raw_linear_events"

    id = Column(Integer, primary_key=True, index=True)

    # Audit Trail
    signature = Column(String, nullable=False)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    # Timestamp from Linear payload (data.createdAt)
    external_timestamp = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp from Linear payload data.createdAt",
    )

    # Metadata
    event_type = Column(String, index=True)
    action = Column(String)

    # Payload
    headers = Column(JSONB, nullable=False)
    body = Column(JSONB, nullable=False)

    # Processing Status
    processed = Column(Boolean, default=False, server_default=text("false"))
    error_log = Column(String, nullable=True)
