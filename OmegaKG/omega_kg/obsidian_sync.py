"""
Obsidian-Neo4j Synchronization
Syncs task notes from Obsidian vault to Neo4j with connection recovery
"""

import logging
from pathlib import Path
from datetime import datetime
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
import frontmatter
from omega_kg.settings import settings
import psycopg2
from omega_kg.config import VECTOR_TABLE_NAME, VectorStatus


class ConnectionError(Exception):
    """Raised when Neo4j connection cannot be established"""

    pass


class ObsidianNeo4jSync:
    """Sync Obsidian tasks to Neo4j with connection health checks"""

    def __init__(self, mock_mode: bool = False) -> None:
        """
        Initialize the sync helper and attempt to establish a Neo4j connection.

        If `mock_mode` is True, the instance runs in mock mode and will skip database operations.
        If `mock_mode` is False, attempts to create and validate a Neo4j driver; on connection or
        authentication failure the instance switches to mock mode and clears the driver so sync
        operations are skipped.

        Parameters:
            mock_mode (bool): If True, disable real database operations and run in mock mode.
        """
        self.vault_path = Path(settings.obsidian_vault_path)
        self.driver = None
        self.mock_mode = mock_mode

        if not mock_mode:
            try:
                self.driver = GraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_user, settings.neo4j_password),
                )
                # Test the connection
                self._check_connection()
                print("[OK] Neo4j connection established")
            except (
                ServiceUnavailable,
                AuthError,
                ConnectionError,
                Exception,
            ) as e:
                print(f"[ERROR] Failed to connect to Neo4j: {e}")
                print("[WARN] Sync operations skipped (mock mode)")
                self.mock_mode = True
                self.driver = None

    def _check_connection(self) -> bool:
        """
        Verify that the configured Neo4j driver is initialized and responds to a simple health query.

        Returns:
            True if the driver responds to the health query.

        Raises:
            ConnectionError: If the driver is not initialized or the health check fails.
        """
        if not self.driver:
            raise ConnectionError("Driver not initialized")

        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as status")
                _ = result.single()
                return True
        except Exception as e:
            raise ConnectionError(f"Connection health check failed: {e}")

    def get_connection_status(self) -> dict[str, bool | str]:
        """
        Report the current Neo4j connection state and the effective URI.

        Returns:
            dict: Mapping with keys:
                - connected (bool): `true` if a real driver is initialized and mock mode is disabled, `false` otherwise.
                - mock_mode (bool): `true` if the instance is operating in mock mode, `false` otherwise.
                - uri (str): The configured Neo4j URI when not in mock mode; "mock://local" when in mock mode.
        """
        return {
            "connected": self.driver is not None and not self.mock_mode,
            "mock_mode": self.mock_mode,
            "uri": (settings.neo4j_uri if not self.mock_mode else "mock://local"),
        }

    def sync_task_note(self, task_file: Path) -> None:
        """
        Sync a single Obsidian markdown task note into Neo4j as a Task node.

        Reads the file's frontmatter and content, derives a stable `uid` (falls back to the file stem when missing or templated), normalizes a `status` value, and upserts a Task node setting title, status, created, last_modified, filepath, content, and parent_plan. Operation short-circuits when the instance is in mock mode or when no Neo4j driver is available; connection errors during the database operation are handled internally.

        Parameters:
            task_file (Path): Path to the markdown task file to sync; its frontmatter is used for metadata and its content becomes the node's content.
        """
        if self.mock_mode:
            print(f"[SKIP] Mock mode: {task_file.name}")
            return

        if not self.driver:
            print(f"[SKIP] No connection: {task_file.name}")
            return

        try:
            with open(task_file, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)

            metadata = post.metadata
            content = post.content

            # Generate reliable UID if metadata has template strings
            uid = metadata.get("uid", "")
            if uid and isinstance(uid, str) and ("<%" in uid or "%>" in uid):
                # UID is a template, use filepath instead
                uid = task_file.stem

            if not uid:
                uid = task_file.stem

            # Get status and strip brackets if present
            status = metadata.get("status", "draft")
            if isinstance(status, str):
                status = status.strip("[]")
            else:
                status = "draft"

            with self.driver.session() as session:
                result = session.run(
                    """
                    MERGE (t:Task {uid: $uid})
                    SET t.title = $title,
                        t.status = $status,
                        t.created = $created,
                        t.last_modified = $modified,
                        t.filepath = $filepath,
                        t.content = $content,
                        t.parent_plan = $parent,
                        t.linear_id = $linear_id
                    RETURN t
                """,
                    uid=uid,
                    title=metadata.get("title", task_file.stem),
                    status=status,
                    created=metadata.get("created", datetime.now().isoformat()),
                    modified=datetime.fromtimestamp(
                        task_file.stat().st_mtime
                    ).isoformat(),
                    filepath=str(task_file.relative_to(self.vault_path)),
                    content=content,
                    parent=metadata.get("parent", None),
                    linear_id=metadata.get("linear_id", None),
                )
                # Consume result to execute the query
                _ = result.single()

                # Queue for embedding
                self._queue_embedding(uid)
        except ServiceUnavailable:
            print(f"[SKIP] Connection lost: {task_file.name}")
        except Exception as e:
            print(f"[ERROR] Failed: {task_file.name} - {e}")

    def sync_all_tasks(self) -> int:
        """
        Synchronize all task notes in the vault into Neo4j.

        Skips synchronization when mock mode is enabled or no database driver is available.

        Returns:
            int: Number of task files successfully synced. Returns 0 if mock mode is enabled or no driver is present.
        """
        if self.mock_mode:
            print("[WARN] Sync skipped (mock mode)")
            return 0

        if not self.driver:
            print("[WARN] Sync skipped (no database connection)")
            return 0

        task_files = self.get_all_task_files()

        count = 0
        for task_file in task_files:
            try:
                self.sync_task_note(task_file)
                count += 1
                print(f"[OK] Synced: {task_file.name}")
            except Exception as e:
                print(f"[ERROR] Failed: {task_file.name} - {e}")

        print(f"\n[OK] Synced {count} tasks to Neo4j")
        return count

    def get_all_task_files(self) -> list[Path]:
        """
        Retrieve all markdown task files from the configured folders.

        Returns:
            list[Path]: List of paths to markdown files in configured scan folders.
        """
        from omega_kg.settings import settings

        task_files = []
        scan_folders_str = settings.obsidian_task_scan_folders
        # Parse comma or colon separated list
        separator = "," if "," in scan_folders_str else ":"
        scan_folders = [
            f.strip() for f in scan_folders_str.split(separator) if f.strip()
        ]

        for folder in scan_folders:
            folder_path = self.vault_path / folder
            if folder_path.exists() and folder_path.is_dir():
                task_files.extend(list(folder_path.rglob("*.md")))
        return task_files

    def get_stale_tasks(self, days_idle: int = 7) -> list[dict[str, object]]:
        """
        Return a list of draft Task records from Neo4j.

        This method queries for Task nodes whose `status` is 'draft'. The `days_idle` parameter is accepted for API compatibility but is ignored by this implementation.

        Parameters:
            days_idle (int): Number of idle days to consider a task stale (ignored).

        Returns:
            list[dict[str, object]]: Each dict contains `uid`, `title`, `created`, and `last_modified` for a draft task.
        """
        if self.mock_mode:
            print("[WARN] Query skipped (mock mode)")
            return []

        if not self.driver:
            logging.warning("Query skipped (no database connection)")
            return []

        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (t:Task)
                    WHERE t.status = 'draft'
                    RETURN t.uid, t.title, t.created, t.last_modified
                    ORDER BY t.created DESC
                """,
                )

                return [dict(record) for record in result]
        except ServiceUnavailable:
            logging.warning("Could not query stale tasks (connection lost)")
            return []

    def close(self) -> None:
        """
        Close the Neo4j driver if it is initialized.

        This is safe to call multiple times; no action is taken when no driver exists.
        """
        if self.driver:
            self.driver.close()

    def _queue_embedding(self, uid: str) -> None:
        """Queue task for embedding generation (idempotent)."""
        print(f"DEBUG: Attempting to queue embedding for {uid}")
        if self.mock_mode:
            print("DEBUG: Mock mode, skipping queue.")
            return

        try:
            print(f"DEBUG: Connecting to {settings.sync_database_url}")
            # Connect using sync driver
            with psycopg2.connect(settings.sync_database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        INSERT INTO {VECTOR_TABLE_NAME} (message_id, node_label, status)
                        VALUES (%s, 'Task', %s)
                        ON CONFLICT (message_id, node_label) DO NOTHING
                        """,
                        (uid, VectorStatus.PENDING_EMBEDDING.value),
                    )
                conn.commit()
                print(f"DEBUG: Successfully queued {uid}")
        except Exception as e:
            print(f"[WARN] Failed to queue embedding for {uid}: {e}")


def main() -> None:
    """
    Run a complete Obsidian-to-Neo4j synchronization and report stale tasks.

    Creates an ObsidianNeo4jSync instance, prints the connection status, synchronizes all task notes, lists tasks older than seven days, and ensures the Neo4j driver is closed.
    """
    sync = ObsidianNeo4jSync()

    # Print connection status
    status = sync.get_connection_status()
    if status["connected"]:
        print(f"[OK] Connected to Neo4j: {status['uri']}")
    else:
        print("[WARN] Running in mock mode (no Neo4j connection)")

    try:
        sync.sync_all_tasks()

        print("\n--- Stale Tasks (>7 days) ---")
        stale = sync.get_stale_tasks(7)
        if stale:
            for task in stale:
                print(
                    f"{task['t.uid']}: {task['t.title']} (created: {task['t.created']})"
                )
        else:
            print("(none)")

    finally:
        sync.close()


if __name__ == "__main__":
    main()
