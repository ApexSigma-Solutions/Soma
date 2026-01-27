# src/
"""
AI Conversation Import Pipeline
Imports exported conversations from Claude and ChatGPT into:
- Obsidian (Dataview-compatible Markdown)
- Neo4j (graph: Session → AIQuery → AIResponse)
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase

from omega_kg.settings import settings


class AIConversationImporter:
    def __init__(self, resources_path: Optional[Path] = None):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        self.vault_path = Path(settings.obsidian_vault_path).resolve()
        self.conversation_dir = self.vault_path / "AI Conversations"
        self.conversation_dir.mkdir(parents=True, exist_ok=True)

        # Set resources path - use provided path, settings, or default
        # relative to current dir
        if resources_path:
            self.resources_path = resources_path.resolve()
        elif settings.ai_conversations_path:
            self.resources_path = Path(settings.ai_conversations_path).resolve()
        else:
            # Default to Resources folder in parent directory of the script
            script_dir = Path(__file__).parent.parent
            self.resources_path = script_dir.parent / "Resources"
            if not self.resources_path.exists():
                # Try relative to current working directory
                self.resources_path = Path.cwd() / "Resources"

    def find_claude_conversations(self) -> Optional[Path]:
        """Find Claude conversations.json file"""
        claude_path = (
            self.resources_path / "AI_Conversations" / "Claude" / "conversations.json"
        )
        return claude_path if claude_path.exists() else None

    def find_chatgpt_conversations(self) -> Optional[Path]:
        """Find ChatGPT conversations.json file"""
        chatgpt_path = (
            self.resources_path / "AI_Conversations" / "ChatGPT" / "conversations.json"
        )
        return chatgpt_path if chatgpt_path.exists() else None

    def _sanitize_title(self, title: str) -> str:
        """Create filesystem-safe title for filename"""
        return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title)[:64].strip()

    def _timestamp_to_iso(self, ts: Optional[float]) -> str:
        """Convert Unix timestamp to ISO 8601 UTC"""
        if not ts:
            return datetime.now(timezone.utc).isoformat()
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

    def _extract_tags(self, title: str) -> List[str]:
        """Extract #tags from title (e.g., '#code #python')"""
        tags = re.findall(r"#([a-zA-Z][a-zA-Z0-9]*)", title)
        return [t.lower() for t in tags if not t.isdigit()]

    def import_claude_export(self, export_file: Path):
        """Import Claude JSON export"""
        with open(export_file, encoding="utf-8") as f:
            data = json.load(f)

        conversations = data.get("conversations", [])
        for conv in conversations:
            messages = []
            for msg in conv.get("chat_messages", []):
                role = "user" if msg.get("sender") == "human" else "assistant"
                content_parts = msg.get("text", [])
                content = (
                    "\n\n".join(content_parts)
                    if isinstance(content_parts, list)
                    else str(content_parts)
                )
                messages.append(
                    {
                        "role": role,
                        "content": content,
                        "created_at": self._timestamp_to_iso(msg.get("created_at")),
                    }
                )

            self._import_conversation(
                platform="claude",
                conversation_id=conv["uuid"],
                title=conv.get("title", "Untitled"),
                messages=messages,
                created_at=self._timestamp_to_iso(conv.get("created_at")),
            )

    def import_chatgpt_export(self, export_file: Path):
        """Import ChatGPT conversations.json"""
        with open(export_file, encoding="utf-8") as f:
            raw_data = json.load(f)

        # Handle both single conversation and full export formats
        conversations = raw_data if isinstance(raw_data, list) else [raw_data]

        for conv in conversations:
            mapping = conv.get("mapping", {})
            messages = []

            # Build message list in order
            current_id = conv.get("current_node")
            while current_id:
                node = mapping.get(current_id)
                if not node:
                    break
                msg_data = node.get("message")
                if msg_data and msg_data.get("content"):
                    role = msg_data["author"]["role"]
                    if role in ("user", "assistant"):
                        parts = msg_data["content"].get("parts", [])
                        content = "\n\n".join(parts) if parts else ""
                        messages.append(
                            {
                                "role": role,
                                "content": content,
                                "created_at": self._timestamp_to_iso(
                                    msg_data.get("create_time")
                                ),
                            }
                        )
                # Traverse backward (ChatGPT stores in reverse)
                current_id = node.get("parent")

            messages.reverse()  # Restore chronological order

            self._import_conversation(
                platform="chatgpt",
                conversation_id=conv["id"],
                title=conv.get("title", "Untitled"),
                messages=messages,
                created_at=self._timestamp_to_iso(conv.get("create_time")),
            )

    def _import_conversation(
        self,
        platform: str,
        conversation_id: str,
        title: str,
        messages: List[Dict[str, Any]],
        created_at: str,
    ):
        """Write to Obsidian + Neo4j atomically"""
        # Generate filename
        safe_title = self._sanitize_title(title)
        filename = f"{platform}_{safe_title}_{conversation_id[:8]}.md"
        filepath = self.conversation_dir / filename

        # Format Markdown with Dataview frontmatter
        markdown = self._format_markdown(
            platform=platform,
            title=title,
            conversation_id=conversation_id,
            created_at=created_at,
            messages=messages,
        )

        # Write to Obsidian
        filepath.write_text(markdown, encoding="utf-8")

        # Write to Neo4j
        self._write_to_neo4j(
            platform=platform,
            conversation_id=conversation_id,
            title=title,
            filepath=filepath.relative_to(self.vault_path),
            messages=messages,
            created_at=created_at,
        )

        print(f"[OK] Imported {platform} conversation")

    def _format_markdown(
        self,
        platform: str,
        title: str,
        conversation_id: str,
        created_at: str,
        messages: List[Dict[str, Any]],
    ) -> str:
        """Generate Dataview-compatible Markdown"""
        tags = self._extract_tags(title)
        tag_str = ", ".join([f'"{t}"' for t in tags]) if tags else "[]"

        frontmatter = f"""---
ai-platform: "{platform}"
ai-id: "{conversation_id}"
ai-created: "{created_at}"
ai-tags: [{tag_str}]
tags: [ai, {platform}]
---

# {title}

**Platform:** {platform.title()}
**Created:** {datetime.fromisoformat(created_at).strftime("%Y-%m-%d %H:%M UTC")}
**ID:** `{conversation_id}`

---

"""

        body = []
        for i, msg in enumerate(messages):
            role = "**You:**" if msg["role"] == "user" else f"**{platform.title()}:**"
            content = msg["content"].strip()
            if not content:
                continue
            body.append(f"### {role}\n{content}\n")

        return frontmatter + "\n".join(body)

    def _write_to_neo4j(
        self,
        platform: str,
        conversation_id: str,
        title: str,
        filepath: Path,
        messages: List[Dict[str, Any]],
        created_at: str,
    ):
        """Upsert conversation graph in Neo4j"""
        session_id = f"{platform}:{conversation_id}"

        with self.driver.session() as session:
            # Create or merge Session
            session.run(
                """
                MERGE (s:Session {id: $session_id})
                SET s.platform = $platform,
                    s.title = $title,
                    s.created_at = datetime($created_at),
                    s.filepath = $filepath,
                    s.message_count = $msg_count
            """,
                session_id=session_id,
                platform=platform,
                title=title,
                created_at=created_at,
                filepath=str(filepath),
                msg_count=len(messages),
            )

            # Create queries and responses
            for i, msg in enumerate(messages):
                if msg["role"] == "user":
                    session.run(
                        """
                        MATCH (s:Session {id: $session_id})
                        MERGE (q:AIQuery {text: $text, platform: $platform})
                        SET q.created_at = datetime($created_at)
                        MERGE (s)-[:CONTAINS]->(q)
                    """,
                        session_id=session_id,
                        text=msg["content"],
                        platform=platform,
                        created_at=msg["created_at"],
                    )
                elif msg["role"] == "assistant":
                    session.run(
                        """
                        MATCH (s:Session {id: $session_id})
                        MERGE (r:AIResponse {
                            platform: $platform,
                            session_id: $session_id,
                            idx: $idx
                        })
                        SET r.content = $content,
                            r.created_at = datetime($created_at)
                        MERGE (s)-[:CONTAINS]->(r)
                    """,
                        session_id=session_id,
                        platform=platform,
                        idx=i,
                        content=msg["content"],
                        created_at=msg["created_at"],
                    )

    def close(self):
        self.driver.close()


def main():
    parser = argparse.ArgumentParser(
        description="Import AI conversations into Obsidian + Neo4j"
    )
    parser.add_argument(
        "--claude", action="store_true", help="Import Claude conversations"
    )
    parser.add_argument(
        "--chatgpt", action="store_true", help="Import ChatGPT conversations"
    )
    parser.add_argument("--resources", type=Path, help="Path to Resources directory")
    args = parser.parse_args()

    if not (args.claude or args.chatgpt):
        parser.error("At least one of --claude or --chatgpt is required")

    importer = AIConversationImporter(resources_path=args.resources)
    try:
        if args.claude:
            claude_file = importer.find_claude_conversations()
            if claude_file:
                print(f"[INFO] Processing Claude export: {claude_file}")
                importer.import_claude_export(claude_file)
            else:
                print("[ERROR] Claude conversations.json not found")
        if args.chatgpt:
            chatgpt_file = importer.find_chatgpt_conversations()
            if chatgpt_file:
                print(f"[INFO] Processing ChatGPT export: {chatgpt_file}")
                importer.import_chatgpt_export(chatgpt_file)
            else:
                print("[ERROR] ChatGPT conversations.json not found")
        print("[DONE] Import complete")
    finally:
        importer.close()


if __name__ == "__main__":
    main()
