from datetime import datetime
from uuid import uuid4
from pathlib import Path
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from omega_kg.database.base import Base

# Import RawIngestion from InGest service for consolidated storage
import sys

# Calculate path to InGest/src/ingest_llm_as relative to this file
ingest_llm_src = (
    Path(__file__).resolve().parents[4] / "InGest" / "src" / "ingest_llm_as"
)

if ingest_llm_src.exists():
    if str(ingest_llm_src) not in sys.path:
        sys.path.insert(0, str(ingest_llm_src))
else:
    print(f"WARNING: InGest path not found at {str(ingest_llm_src)}")

try:
    from ingest_llm_as.db_models.raw_ingestion import RawIngestion

    _RAW_INGESTION_AVAILABLE = True
except ImportError:
    # Fallback if InGest is not available
    _RAW_INGESTION_AVAILABLE = False
    RawIngestion = None


class RawConversation(Base):
    """
    DEPRECATED: Stores raw conversation data received from Chrome extension.

    This model is being replaced by RawIngestion from InGest-LLM service
    to consolidate storage across all ingestion types.

    Use RawIngestion instead with source_type='conversation-{platform}'.
    """

    __tablename__ = "raw_conversations"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id = Column(String(255), unique=True, nullable=False)
    platform = Column(String(50), nullable=True)
    raw_payload = Column(JSONB, nullable=False)
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# Export RawIngestion for use in other modules
__all__ = ["RawConversation", "RawIngestion", "_RAW_INGESTION_AVAILABLE"]

# Also export the availability flag
_RAW_INGESTION_AVAILABLE = None
