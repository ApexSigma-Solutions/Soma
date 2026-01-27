import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from .base import Database
from ..config import settings

Base = declarative_base()


class Memory(Base):
    __tablename__ = "memories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    agent_id = Column(String(255), nullable=False, default="default_agent")
    memory_metadata = Column(JSON, nullable=True)
    embedding_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class RegisteredTool(Base):
    __tablename__ = "registered_tools"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    usage = Column(Text, nullable=False)
    tags = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class PostgresDatabase(Database):
    def __init__(self):
        self.database_url = os.environ.get("DATABASE_URL")
        if not self.database_url:
            self.database_url = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"

        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

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
            memory = Memory(
                content=content, agent_id=agent_id, memory_metadata=metadata
            )
            session.add(memory)
            session.flush()
            return memory.id

    def get_memory(self, memory_id: int) -> Optional[Dict[str, Any]]:
        with self.get_session() as session:
            memory = session.query(Memory).filter(Memory.id == memory_id).first()
            if memory:
                return {
                    "id": memory.id,
                    "content": memory.content,
                    "agent_id": memory.agent_id,
                    "metadata": memory.memory_metadata,
                    "embedding_id": memory.embedding_id,
                    "created_at": memory.created_at,
                    "updated_at": memory.updated_at,
                }
            return None

    def get_memories_by_ids(self, memory_ids: List[int]) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            memories = session.query(Memory).filter(Memory.id.in_(memory_ids)).all()
            return [
                {
                    "id": m.id,
                    "content": m.content,
                    "agent_id": m.agent_id,
                    "metadata": m.memory_metadata,
                    "embedding_id": m.embedding_id,
                    "created_at": m.created_at,
                    "updated_at": m.updated_at,
                }
                for m in memories
            ]

    def update_memory_embedding_id(self, memory_id: int, embedding_id: str) -> bool:
        with self.get_session() as session:
            result = (
                session.query(Memory)
                .filter(Memory.id == memory_id)
                .update({"embedding_id": embedding_id})
            )
            return result > 0

    def register_tool(
        self, name: str, description: str, usage: str, tags: Optional[List[str]] = None
    ) -> Optional[int]:
        with self.get_session() as session:
            tool = RegisteredTool(
                name=name, description=description, usage=usage, tags=tags
            )
            session.add(tool)
            session.flush()
            return tool.id

    def get_tool(self, tool_id: int) -> Optional[Dict[str, Any]]:
        with self.get_session() as session:
            tool = (
                session.query(RegisteredTool)
                .filter(RegisteredTool.id == tool_id)
                .first()
            )
            if tool:
                return {
                    "id": tool.id,
                    "name": tool.name,
                    "description": tool.description,
                    "usage": tool.usage,
                    "tags": tool.tags,
                    "created_at": tool.created_at,
                    "updated_at": tool.updated_at,
                }
            return None

    def get_tools_by_context(
        self, query_context: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            tools = (
                session.query(RegisteredTool)
                .filter(
                    (RegisteredTool.description.ilike(f"%{query_context}%"))
                    | (RegisteredTool.usage.ilike(f"%{query_context}%"))
                )
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "usage": t.usage,
                    "tags": t.tags,
                    "created_at": t.created_at,
                    "updated_at": t.updated_at,
                }
                for t in tools
            ]

    def get_all_tools(self) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            tools = session.query(RegisteredTool).all()
            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "usage": t.usage,
                    "tags": t.tags,
                    "created_at": t.created_at,
                    "updated_at": t.updated_at,
                }
                for t in tools
            ]
