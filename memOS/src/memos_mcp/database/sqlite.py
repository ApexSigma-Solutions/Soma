import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    MetaData,
    Table,
)
from sqlalchemy.orm import sessionmaker, Session
from .base import Database


class SQLiteDatabase(Database):
    def __init__(self, db_path: str = "memory.db"):
        if os.environ.get("TESTING"):
            db_path = "test_memory.db"

        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        self.database_url = f"sqlite:///{db_path}"
        self.engine = create_engine(self.database_url, echo=False)
        self.metadata = MetaData()
        self._define_tables()
        self.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autoflush=False, bind=self.engine)

    def _define_tables(self):
        self.memories = Table(
            "memories",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("content", Text, nullable=False),
            Column("agent_id", String(255), nullable=False, default="default_agent"),
            Column("memory_metadata", JSON, nullable=True),
            Column("embedding_id", String(255), nullable=True),
            Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
            Column(
                "updated_at",
                DateTime,
                default=lambda: datetime.now(timezone.utc),
                onupdate=lambda: datetime.now(timezone.utc),
            ),
        )

        self.registered_tools = Table(
            "registered_tools",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("name", String(255), nullable=False, unique=True),
            Column("description", Text, nullable=False),
            Column("usage", Text, nullable=False),
            Column("tags", JSON, nullable=True),
            Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
            Column(
                "updated_at",
                DateTime,
                default=lambda: datetime.now(timezone.utc),
                onupdate=lambda: datetime.now(timezone.utc),
            ),
        )

    @contextmanager
    def get_session(self) -> Session:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def store_memory(
        self, content: str, agent_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        with self.get_session() as session:
            result = session.execute(
                self.memories.insert().values(
                    content=content, agent_id=agent_id, memory_metadata=metadata
                )
            )
            return result.inserted_primary_key[0]

    def get_memory(self, memory_id: int) -> Optional[Dict[str, Any]]:
        with self.get_session() as session:
            result = session.execute(
                self.memories.select().where(self.memories.c.id == memory_id)
            ).first()
            if result:
                row = dict(result._mapping)
                row["metadata"] = row.pop("memory_metadata")
                return row
            return None

    def get_memories_by_ids(self, memory_ids: List[int]) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            results = session.execute(
                self.memories.select().where(self.memories.c.id.in_(memory_ids))
            ).fetchall()
            output = []
            for row in results:
                new_row = dict(row._mapping)
                new_row["metadata"] = new_row.pop("memory_metadata")
                output.append(new_row)
            return output

    def update_memory_embedding_id(self, memory_id: int, embedding_id: str) -> bool:
        with self.get_session() as session:
            result = session.execute(
                self.memories.update()
                .where(self.memories.c.id == memory_id)
                .values(embedding_id=embedding_id)
            )
            return result.rowcount > 0

    def register_tool(
        self, name: str, description: str, usage: str, tags: Optional[List[str]] = None
    ) -> Optional[int]:
        with self.get_session() as session:
            result = session.execute(
                self.registered_tools.insert().values(
                    name=name, description=description, usage=usage, tags=tags
                )
            )
            return result.inserted_primary_key[0]

    def get_tool(self, tool_id: int) -> Optional[Dict[str, Any]]:
        with self.get_session() as session:
            result = session.execute(
                self.registered_tools.select().where(
                    self.registered_tools.c.id == tool_id
                )
            ).first()
            return dict(result._mapping) if result else None

    def get_tools_by_context(
        self, query_context: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            results = session.execute(
                self.registered_tools.select()
                .where(
                    (self.registered_tools.c.description.ilike(f"%{query_context}%"))
                    | (self.registered_tools.c.usage.ilike(f"%{query_context}%"))
                )
                .limit(limit)
            ).fetchall()
            return [dict(row._mapping) for row in results]

    def get_all_tools(self) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            results = session.execute(self.registered_tools.select()).fetchall()
            return [dict(row._mapping) for row in results]
