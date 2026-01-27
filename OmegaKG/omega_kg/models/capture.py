"""
Capture Server Pydantic Models

This module contains the data models for the capture server endpoints.
Extracted from capture_server.py for modularity.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class Token(BaseModel):
    """JWT token response model."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class Message(BaseModel):
    """Chat message model for conversation capture."""

    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="Message timestamp")


class ConversationData(BaseModel):
    """
    Main payload model for conversation capture from Chrome extension.

    Supports both dict and Message object formats for messages to accommodate
    different client implementations.
    """

    user_id: str = "extension_user"
    source: str = "chrome_extension"
    platform: str = "obsidian"
    content: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = "Untitled Capture"
    tags: List[str] = []
    # messages can be dicts or Message objects depending on caller
    messages: Optional[List[Union[Dict[str, Any], Message]]] = []
    raw_html: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CaptureResponse(BaseModel):
    """Response model for successful capture operations."""

    success: bool
    file_path: str
    nodes_created: int
    message: str


class ObsidianUpdateRequest(BaseModel):
    """Request model for Obsidian note sync to Linear."""

    note_path: str = Field(
        ...,
        description="Path to the Obsidian note (relative or absolute)",
        examples=["D:\\projects\\vault\\Tasks\\task.md"],
    )


class ObsidianUpdateResponse(BaseModel):
    """Response model for Obsidian update operations."""

    success: bool
    linear_id: Optional[str] = Field(None, description="Linear issue ID")
    linear_identifier: Optional[str] = Field(
        None, description="Linear issue identifier (e.g., LIN-123)"
    )
    linear_url: Optional[str] = Field(None, description="Linear issue URL")
    message: str


__all__ = [
    "Token",
    "Message",
    "ConversationData",
    "CaptureResponse",
    "ObsidianUpdateRequest",
    "ObsidianUpdateResponse",
]
