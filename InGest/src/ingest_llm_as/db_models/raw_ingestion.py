"""Raw ingestion model for durable data lake persistence.

This model stores all ingestion requests (text/file/repo) BEFORE processing
to ensure 100% data retention. Workers poll this table for unprocessed records.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, LargeBinary
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from .base import Base


class RawIngestion(Base):
    """Raw ingestion records for durable data lake persistence.

    All ingestion requests (text/file/repo) are written here BEFORE processing
    to ensure 100% data retention. Workers poll this table for unprocessed records.

    Attributes:
        id: Primary key
        ingestion_id: Unique UUID for idempotency
        source_type: Type of ingestion ('text', 'file', 'python-repo')
        content_type: MIME type for files
        raw_payload: Original request body as JSONB
        file_data: Binary file data (NULL for non-file ingestions)
        raw_metadata: Source metadata, tags, user context (renamed from 'metadata')
        captured_at: Timestamp when ingestion was received
        processed: Flag indicating if worker has processed this record
        processed_at: Timestamp when processing completed
        processing_attempts: Number of processing attempts (for retry logic)
        last_error: Last error message if processing failed
        created_at: Record creation timestamp
    """

    __tablename__ = "raw_ingestions"

    id = Column(Integer, primary_key=True)
    ingestion_id = Column(PGUUID(as_uuid=True), nullable=False, unique=True)
    source_type = Column(String(50), nullable=False)
    content_type = Column(String(100), nullable=True)
    raw_payload = Column(JSONB, nullable=False)
    file_data = Column(LargeBinary, nullable=True)
    raw_metadata = Column(
        JSONB, nullable=True
    )  # Renamed from 'metadata' (SQLAlchemy reserved keyword)
    captured_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed = Column(Boolean, nullable=False, default=False)
    processed_at = Column(DateTime, nullable=True)
    processing_attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<RawIngestion {self.ingestion_id} ({self.source_type})>"
