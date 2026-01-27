"""
Capture Utility Functions

Helper functions for conversation capture operations including:
- Hash generation for conversation IDs
- Markdown formatting for Obsidian vault
- File I/O for writing to Obsidian

Extracted from capture_server.py for modularity.
"""

import hashlib
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from omega_kg.settings import settings

if TYPE_CHECKING:
    from omega_kg.models.capture import ConversationData

logger = logging.getLogger(__name__)


def _generate_content_string(data: "ConversationData") -> str:
    """Generate the canonical content string for hashing."""
    # Limit to first 5 messages and first 500 characters for scalability
    if not data.messages:
        limited_messages = []
    else:
        limited_messages = data.messages[:5]
    # Handle both dict and Message object formats
    messages_text = "|".join(
        (msg.get("content", "") if isinstance(msg, dict) else msg.content)[:100]
        for msg in limited_messages
    )
    msg_count = len(data.messages) if data.messages else 0
    return f"{data.platform}-{data.url}-{msg_count}-{messages_text}"


def generate_conversation_hash(data: "ConversationData") -> str:
    """
    Generate a short hash for a conversation using platform, URL, message count,
    and a limited portion of message content.

    Args:
        data (ConversationData): The conversation data.

    Returns:
        str: An 8-character hash string.
    """
    content = _generate_content_string(data)
    hash_obj = hashlib.md5(content.encode())
    return hash_obj.hexdigest()[:8]


def generate_conversation_uuid(data: "ConversationData") -> uuid.UUID:
    """
    Generate a deterministic UUID for a conversation based on its content.

    Args:
        data (ConversationData): The conversation data.

    Returns:
        uuid.UUID: A deterministic UUID derived from the content hash.
    """
    content = _generate_content_string(data)
    hash_obj = hashlib.md5(content.encode())
    return uuid.UUID(hex=hash_obj.hexdigest())


def format_conversation_markdown(data: "ConversationData") -> str:
    """
    Formats the conversation data into Markdown with Golden Schema Frontmatter.

    Schema:
      - id: CAP-{YYYYMMDD}-{HASH} (Standardized ID)
      - type: Conversation (Standardized Type)
      - status: new (Default status)
      - title: ...
      - created_at: ...

    Args:
        data: ConversationData object with conversation details.

    Returns:
        str: Formatted markdown content with frontmatter.
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    timestamp_str = now.isoformat()

    # Generate a robust Content ID
    conv_hash = generate_conversation_hash(data)
    # ID Format: CAP (Capture) - Date - Hash
    content_id = f"CAP-{now.strftime('%Y%m%d')}-{conv_hash}"

    # --- Golden Schema Frontmatter ---
    frontmatter_lines = [
        "---",
        f"id: {content_id}",
        "type: Conversation",
        "status: new",
        f"title: {data.title or f'{data.platform} Conversation'}",
        f"created_at: {timestamp_str}",
        f"date: {date_str}",
        f"platform: {data.platform}",
        f"url: {data.url}",
        f"conversation_hash: {conv_hash}",
        f"message_count: {len(data.messages) if data.messages else 0}",
    ]

    # Add Participants (Roles) - handle both dict and Message object formats
    roles = []
    if data.messages:
        roles = list(
            set(
                msg.get("role", "unknown") if isinstance(msg, dict) else msg.role
                for msg in data.messages
            )
        )
    participants_str = ", ".join(sorted(roles))
    frontmatter_lines.append(f"participants: {participants_str}")

    # Add any extra metadata
    if data.metadata:
        for key, value in data.metadata.items():
            # Prevent duplicate keys if they overlap with schema
            if key not in ["id", "type", "status", "title", "created_at"]:
                frontmatter_lines.append(f"{key}: {value}")

    frontmatter_lines.append("---")

    # --- Content Body ---
    title_header = data.title or f"{data.platform} Conversation"
    content_lines = [
        f"\n# {title_header}",
        f"\n**ID**: `{content_id}`",
        f"**Date**: {date_str}",
        f"**Platform**: {data.platform}",
        f"**URL**: [{data.url}]({data.url})",
        "---\n",
    ]

    messages_list = data.messages or []
    for i, msg in enumerate(messages_list, 1):
        # Handle both dict and Message object formats
        if isinstance(msg, dict):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp")
        else:
            role = msg.role
            content = msg.content
            timestamp = msg.timestamp

        role_emoji = "👤" if role.lower() == "user" else "🤖"
        role_title = role.title()
        content_lines.append(f"\n## {role_emoji} Message {i} ({role_title})\n")
        content_lines.append(content)
        content_lines.append("\n")
        if timestamp:
            content_lines.append(f"*Sent: {timestamp}*\n")

    return "\n".join(frontmatter_lines + content_lines)


def write_to_obsidian(platform: str, content: str, conversation_hash: str) -> Path:
    """
    Writes the given conversation markdown content to the Obsidian vault under
    the 'AI_Conversations' folder (hardcoded convention; see project architecture).
    Creates a subfolder for the platform and names the file using the current date
    and conversation hash.

    Args:
        platform (str): The AI platform name (used for subfolder). Must be safe (no path traversal).
        content (str): The markdown content to write.
        conversation_hash (str): Unique hash for the conversation.

    Returns:
        Path: The path to the written markdown file.

    Raises:
        ValueError: If the Obsidian vault path does not exist or platform contains path traversal.
        IOError: If writing the file fails.
    """
    # Validate platform parameter to prevent path traversal
    if not platform or ".." in platform or "/" in platform or "\\" in platform:
        raise ValueError(
            f"Invalid platform name: {platform} (contains path traversal characters)"
        )

    # Normalize platform name to safe directory name
    platform_folder = re.sub(r'[<>:"|?*\x00-\x1f]', "", platform.replace(" ", "_"))
    if not platform_folder:
        platform_folder = "unknown"

    vault_path = Path(settings.obsidian_vault_path).resolve()
    if not vault_path.exists():
        logger.warning(
            f"Obsidian vault not found at: {vault_path} - creating directory for write operations."
        )
        vault_path.mkdir(parents=True, exist_ok=True)

    # Construct and resolve the target path
    ai_conv_path = (vault_path / "AI_Conversations" / platform_folder).resolve()

    # Robust path traversal prevention using Path.relative_to() (Python 3.9+)
    try:
        ai_conv_path.relative_to(vault_path)
    except ValueError:
        raise ValueError(
            f"Path traversal detected: {platform_folder} would escape vault directory"
        )

    # Additional check: ensure the path is not a special device or symlink escape
    if ai_conv_path.is_symlink():
        logger.warning(f"Symlink detected at {ai_conv_path}, resolving to target")
        ai_conv_path = ai_conv_path.resolve()

    ai_conv_path.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date_str}-{conversation_hash}.md"
    file_path = ai_conv_path / filename

    try:
        file_path.write_text(content, encoding="utf-8")
        logger.info(f"Wrote conversation to: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Failed to write file: {e}")
        raise IOError(f"Failed to write markdown file: {e}")


__all__ = [
    "generate_conversation_hash",
    "generate_conversation_uuid",
    "format_conversation_markdown",
    "write_to_obsidian",
]
