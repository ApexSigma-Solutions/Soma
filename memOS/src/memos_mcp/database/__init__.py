import os
import threading
from .base import Database
from .sqlite import SQLiteDatabase
from .postgres import PostgresDatabase
from .neo4j import Neo4jDatabase
from .pgvector_store import PGVectorStore, get_pgvector_store, init_pgvector_store
from ..config import settings

__all__ = [
    "Database",
    "SQLiteDatabase",
    "PostgresDatabase",
    "Neo4jDatabase",
    "PGVectorStore",
    "get_pgvector_store",
    "init_pgvector_store",
    "get_database",
]

_db_instance = None
_db_lock = threading.Lock()


def get_database() -> Database:
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                if os.environ.get("TESTING"):
                    _db_instance = SQLiteDatabase(db_path="test_memory.db")
                else:
                    db_type = settings.memos_db_type
                    if db_type == "sqlite":
                        _db_instance = SQLiteDatabase(db_path=settings.memos_db_path)
                    elif db_type == "postgres":
                        _db_instance = PostgresDatabase()
                    elif db_type == "neo4j":
                        _db_instance = Neo4jDatabase()
                    else:
                        raise ValueError(f"Unsupported database type: {db_type}")
    return _db_instance
