from .ingest_session import AsyncIngestSessionLocal
from .session import AsyncSessionLocal


def get_ingest_session():
    """Returns a new async session for the Ingest Database."""
    return AsyncIngestSessionLocal()


def get_vector_session():
    """Returns a new async session for the Vector/Main Database."""
    return AsyncSessionLocal()
