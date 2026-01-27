from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class Database(ABC):
    @abstractmethod
    def store_memory(
        self, content: str, agent_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        pass

    @abstractmethod
    def get_memory(self, memory_id: int) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_memories_by_ids(self, memory_ids: List[int]) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def update_memory_embedding_id(self, memory_id: int, embedding_id: str) -> bool:
        pass

    @abstractmethod
    def register_tool(
        self, name: str, description: str, usage: str, tags: Optional[List[str]] = None
    ) -> Optional[int]:
        pass

    @abstractmethod
    def get_tool(self, tool_id: int) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_tools_by_context(
        self, query_context: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_all_tools(self) -> List[Dict[str, Any]]:
        pass
