"""
percolation.py

Provides functions for extracting and linking commit and task data from markdown content into the database.

This module is part of the Omega_KG package and handles the percolation of knowledge
from Obsidian notes into the Neo4j knowledge graph through commit and task extraction.
"""

import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from neo4j import Driver, GraphDatabase

from omega_kg.settings import settings

logger = logging.getLogger(__name__)


class PercolationEngine:
    """Engine for extracting and linking commit and task data from markdown content."""

    def __init__(self, driver: Driver):
        """
        Create a PercolationEngine bound to the provided Neo4j driver.

        Parameters:
            driver (neo4j.Driver): Neo4j driver used for database operations by the engine.
        """
        self.driver = driver

    def percolate_from_vault(
        self, vault_path: Path, scan_folders: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """
        Percolates tasks, commits, and session/decision links from markdown files in specified folders.

        Scans the given vault directory recursively for `.md` files in configured folders,
        extracts frontmatter and content, and delegates per-file processing to the engine's task,
        commit, and session percolation routines. Errors reading or processing individual files
        are caught and do not halt the overall run.

        Parameters:
            vault_path (Path): Root directory of the Obsidian vault to scan.
            scan_folders (Optional[List[str]]): List of folder names to scan within the vault.
                If None, uses default from settings.obsidian_vault_scan_folders.

        Returns:
            dict: Counts of processed items with keys "tasks", "commits", and "links".
        """
        # Parse scan folders from settings if not provided
        if scan_folders is None:
            scan_folders_str = settings.obsidian_vault_scan_folders
            scan_folders = [f.strip() for f in scan_folders_str.split(",") if f.strip()]

        logger.info(f"[DIAGNOSTIC] Percolation scan folders: {scan_folders}")
        logger.info(f"[DIAGNOSTIC] Vault path: {vault_path}")

        stats = {"tasks": 0, "commits": 0, "links": 0}
        files_scanned = 0
        files_with_frontmatter = 0
        files_without_frontmatter = 0

        for folder_name in scan_folders:
            folder_path = vault_path / folder_name
            if not folder_path.exists():
                logger.warning(f"Percolation folder does not exist: {folder_path}")
                continue

            logger.info(f"[DIAGNOSTIC] Scanning percolation folder: {folder_path}")

            # Find all markdown files in this folder
            md_files = list(folder_path.rglob("*.md"))
            logger.info(
                f"[DIAGNOSTIC] Found {len(md_files)} markdown files in {folder_name}"
            )

            for md_file in md_files:
                files_scanned += 1
                try:
                    content = md_file.read_text(encoding="utf-8")
                    metadata = self._extract_frontmatter(content)

                    if metadata:
                        files_with_frontmatter += 1
                        logger.debug(
                            f"[DIAGNOSTIC] File has frontmatter: {md_file.name}"
                        )

                        # Extract and percolate tasks
                        task_count = self._percolate_task(md_file, metadata, content)
                        stats["tasks"] += task_count

                        # Extract and percolate commits
                        commit_count = self._percolate_commits(
                            md_file, metadata, content
                        )
                        stats["commits"] += commit_count

                        # Extract and percolate session data
                        session_count = self._percolate_session(
                            md_file, metadata, content
                        )
                        stats["links"] += session_count
                    else:
                        files_without_frontmatter += 1
                        logger.debug(
                            f"[DIAGNOSTIC] File missing frontmatter: {md_file.name}"
                        )

                except Exception as e:
                    logger.error(f"Error percolating {md_file}: {e}")

        logger.info(
            f"[DIAGNOSTIC] Scan summary: {files_scanned} files scanned, "
            f"{files_with_frontmatter} with frontmatter, {files_without_frontmatter} without frontmatter"
        )
        return stats

    def _extract_frontmatter(self, content: str) -> Optional[Dict]:
        """
        Extract top-level YAML frontmatter keys and values from the start of a Markdown string.

        Returns a dictionary of key-value pairs if frontmatter is present and well-formed, or None otherwise.
        """
        if not content.startswith("---"):
            return None

        try:
            _, frontmatter, _ = content.split("---", 2)
            metadata = {}

            for line in frontmatter.strip().split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip()

            return metadata
        except Exception:
            return None

    def _percolate_task(self, path: Path, metadata: Dict, content: str) -> int:
        """
        Find task UIDs in the given Markdown content, ensure corresponding Task nodes exist in the graph, and optionally link them to a Decision.

        Parameters:
            path (Path): Filesystem path of the Markdown file where tasks were found.
            metadata (Dict): Parsed frontmatter metadata; may contain "date" for created timestamp and "decision_id" to link tasks to a Decision node.
            content (str): Full Markdown file content to search for task references (e.g., [[PROJ-123]]).

        Returns:
            int: Number of task references processed.
        """
        task_count = 0

        # Look for task references (e.g., [[DRAFT-001]])
        task_pattern = r"\[\[([A-Z]+-\d+)\]\]"
        tasks = re.findall(task_pattern, content)

        # Look for checkbox task references (e.g., - [x] [[DRAFT-001]])
        checkbox_task_pattern = r"^\s*-\s*\[([ x])\]\s*\[\[([A-Z]+-\d+)\]\]"
        checkbox_tasks = re.findall(checkbox_task_pattern, content, re.MULTILINE)
        if checkbox_tasks:
            logger.info(
                f"[DIAGNOSTIC] Found {len(checkbox_tasks)} checkbox task references in {path.name}"
            )
            # Extract UIDs from checkbox tasks and add to tasks list
            for checkbox_match in checkbox_tasks:
                checkbox_state, task_uid = checkbox_match.groups()
                if checkbox_state.strip() == "x":  # Only process checked checkboxes
                    tasks.append(task_uid)
                    logger.debug(
                        f"[DIAGNOSTIC] Extracted checkbox task UID: {task_uid}"
                    )

        logger.info(
            f"[DIAGNOSTIC] Task extraction from {path.name}: "
            f"pattern={task_pattern}, found={len(tasks)} tasks"
        )
        if tasks:
            logger.debug(f"[DIAGNOSTIC] Task UIDs found: {tasks}")

        # Check for checkbox patterns (for diagnostic purposes)
        checkbox_pattern = r"^\s*-\s*\[[ x]\]"
        checkboxes = re.findall(checkbox_pattern, content, re.MULTILINE)
        if checkboxes:
            logger.warning(
                f"[DIAGNOSTIC] Found {len(checkboxes)} checkbox items in {path.name} "
                f"but checkbox parsing is NOT IMPLEMENTED. "
                f"Only [[UID-123]] format is supported."
            )

        with self.driver.session() as session:
            for task_uid in tasks:
                # Create or update task node
                session.run(
                    """
                    MERGE (t:Task {uid: $uid})
                    SET t.filepath = $filepath,
                        t.created = $created,
                        t.pinned = false
                    RETURN t
                    """,
                    uid=task_uid,
                    filepath=str(path),
                    created=metadata.get("date", datetime.now().isoformat()),
                )
                task_count += 1
                logger.debug(f"[DIAGNOSTIC] Created/updated Task node: {task_uid}")

                # Link task to decision if in a decision context
                decision_id = metadata.get("decision_id")
                if decision_id:
                    session.run(
                        """
                        MATCH (t:Task {uid: $uid})
                        MATCH (d:Decision {id: $decision_id})
                        MERGE (t)-[:IMPLEMENTS]->(d)
                        """,
                        uid=task_uid,
                        decision_id=decision_id,
                    )

        return task_count

    def _percolate_commits(self, path: Path, metadata: Dict, content: str) -> int:
        """
        Create or update Commit nodes from markdown commit blocks and link them to Task nodes when a Linear ID is present.

        Links each discovered commit (by hash) to an existing Task using the Linear ID when available.

        Returns:
            int: Number of commit entries processed.
        """
        commit_count = 0

        # Parse commits from markdown (format: #### Git Commit [repo]: `hash`)
        commit_pattern = r"#### Git Commit \[(.+?)\]: `(.+?)`\n(?:\*\*Linear:\*\* \[\[(.+?)\]\])?\n?(?:\*\*Message:\*\*\n)?```\n(.+?)\n```"
        commits = re.finditer(commit_pattern, content, re.DOTALL)

        with self.driver.session() as session:
            for commit_match in commits:
                repo, commit_hash, linear_id, message = commit_match.groups()
                commit_count += 1

                # Create commit node
                session.run(
                    """
                    MERGE (c:Commit {hash: $hash})
                    SET c.message = $message,
                        c.repo = $repo,
                        c.timestamp = $timestamp
                    RETURN c
                    """,
                    hash=commit_hash,
                    message=message.strip(),
                    repo=repo.strip(),
                    timestamp=datetime.now().isoformat(),
                )

                # Link to task if linear_id provided
                if linear_id:
                    session.run(
                        """
                        MATCH (c:Commit {hash: $hash})
                        MATCH (t:Task {linear_id: $linear_id})
                        MERGE (c)-[:IMPLEMENTS]->(t)
                        """,
                        hash=commit_hash,
                        linear_id=linear_id.strip(),
                    )

        return commit_count

    def _percolate_session(self, path: Path, metadata: Dict, content: str) -> int:
        """
        Create or link a chat session from the file's metadata and extract Decision sections from the content, creating Decision nodes and CONTAINS relationships to the session.

        Parameters:
            path (Path): Path to the markdown file (used for context).
            metadata (Dict): Frontmatter metadata. Must include a 'date' value and may include 'topic'.
            content (str): Full markdown content to scan for decision sections beginning with "## Decision".

        Returns:
            int: Number of Decision-to-ChatSession links created.
        """
        link_count = 0
        session_date = metadata.get("date")

        if not session_date:
            return link_count

        with self.driver.session() as session:
            # Create or match session node
            session.run(
                """
                MERGE (s:ChatSession {date: $date})
                SET s.topic = $topic
                RETURN s
                """,
                date=session_date,
                topic=metadata.get("topic", "Unknown"),
            )

            # Extract decisions (look for ## Decision markers)
            decision_pattern = r"## Decision\n\n(.+?)(?=\n##|\Z)"
            decisions = re.finditer(decision_pattern, content, re.DOTALL)

            for decision_match in decisions:
                decision_text = decision_match.group(1).strip()
                decision_id = self._generate_decision_id(decision_text)

                # Create decision node
                session.run(
                    """
                    MERGE (d:Decision {id: $id})
                    SET d.content = $content,
                        d.created = $created
                    RETURN d
                    """,
                    id=decision_id,
                    content=decision_text[:500],  # Store first 500 chars
                    created=session_date,
                )

                # Link decision to session
                session.run(
                    """
                    MATCH (s:ChatSession {date: $date})
                    MATCH (d:Decision {id: $id})
                    MERGE (s)-[:CONTAINS]->(d)
                    """,
                    date=session_date,
                    id=decision_id,
                )
                link_count += 1

        return link_count

    @staticmethod
    def _generate_decision_id(content: str) -> str:
        """
        Generate a compact decision identifier from decision text.

        Parameters:
            content (str): Decision text used to derive the identifier; the function uses the first three words to compute the suffix.

        Returns:
            str: Identifier in the form "DEC-XXXX" where "XXXX" is a zero-padded 4-digit numeric suffix derived deterministically from the initial words of the content.
        """
        # Create a simple hash from the first words
        words = content.split()[:3]
        hash_input = "-".join(words).lower()[:20]
        return f"DEC-{hash(hash_input) % 10000:04d}"

    def detect_stale_tasks(self, days_threshold: int = 30) -> List[Dict]:
        """
        Finds tasks with status 'active' or 'ready' created more than a given number of days ago.

        Parameters:
            days_threshold (int): Number of days since creation after which a task is considered stale. Defaults to 30.

        Returns:
            List[Dict]: A list of dictionaries for each stale task containing the keys 'uid', 'title', 'status', and 'created'. Results are ordered by 'created' in ascending order.
        """
        stale_tasks = []

        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (t:Task)
                WHERE t.status IN ['active', 'ready']
                  AND duration.between(
                    datetime(t.created),
                    datetime()
                  ).days > $threshold
                RETURN t.uid, t.title, t.status, t.created
                ORDER BY t.created ASC
                """,
                threshold=days_threshold,
            )

            for record in result:
                stale_tasks.append(
                    {
                        "uid": record["t.uid"],
                        "title": record["t.title"],
                        "status": record["t.status"],
                        "created": record["t.created"],
                    }
                )

        return stale_tasks

    def find_similar_tasks(
        self, task_uid: str, similarity_threshold: Optional[float] = None
    ) -> List[Dict]:
        """
        Find tasks similar to the given task based on vector similarity.

        Parameters:
            task_uid (str): The UID of the task to find similarities for
            similarity_threshold (float, optional): Minimum similarity score (0.0-1.0).
                                                   If None, uses settings.percolation_similarity_threshold

        Returns:
            List[Dict]: List of similar tasks with their similarity scores
        """
        if similarity_threshold is None:
            # Use the configurable threshold from the global settings object
            similarity_threshold = settings.percolation_similarity_threshold

        similar_tasks: List[Dict] = []

        with self.driver.session() as session:
            # Get the embedding for the source task
            source_result = session.run(
                """
                MATCH (t:Task {uid: $task_uid})
                RETURN t.embedding as embedding
                """,
                task_uid=task_uid,
            )

            source_record = source_result.single()
            if not source_record or not source_record["embedding"]:
                return similar_tasks

            source_embedding = source_record["embedding"]

            # Find similar tasks using vector similarity
            result = session.run(
                """
                MATCH (t:Task)
                WHERE t.uid <> $task_uid
                  AND t.embedding IS NOT NULL
                  AND vector.similarity(t.embedding, $source_embedding) >= $threshold
                RETURN t.uid, t.title, t.status,
                       vector.similarity(t.embedding, $source_embedding) as similarity
                ORDER BY similarity DESC
                LIMIT 10
                """,
                task_uid=task_uid,
                source_embedding=source_embedding,
                threshold=similarity_threshold,
            )

            for record in result:
                similar_tasks.append(
                    {
                        "uid": record["t.uid"],
                        "title": record["t.title"],
                        "status": record["t.status"],
                        "similarity": record["similarity"],
                    }
                )

        return similar_tasks

    def create_relationships_based_on_similarity(
        self, similarity_threshold: Optional[float] = None
    ) -> int:
        """
        Create RELATES_TO relationships between tasks based on vector similarity.

        Parameters:
            similarity_threshold (float, optional): Minimum similarity score (0.0-1.0).
                                                   If None, uses settings.percolation_similarity_threshold

        Returns:
            int: Number of relationships created
        """
        if similarity_threshold is None:
            # Use the configurable threshold from the global settings object
            similarity_threshold = settings.percolation_similarity_threshold

        with self.driver.session() as session:
            # Find similar task pairs and create relationships in a single query
            result = session.run(
                """
                MATCH (t1:Task), (t2:Task)
                WHERE t1.uid < t2.uid  // Avoid duplicate relationships and self-links
                  AND t1.embedding IS NOT NULL
                  AND t2.embedding IS NOT NULL
                  AND vector.similarity(t1.embedding, t2.embedding) >= $threshold
                WITH t1, t2, vector.similarity(t1.embedding, t2.embedding) AS similarity
                MERGE (t1)-[r:RELATES_TO]->(t2)
                ON CREATE SET r.similarity = similarity, r.created = datetime()
                ON MATCH SET r.similarity = similarity, r.updated = datetime()
                RETURN count(r) AS relationships_created
                """,
                threshold=similarity_threshold,
            )

            record = result.single()
            relationships_created = record["relationships_created"] if record else 0

        return relationships_created


def create_percolation_engine(uri: str, user: str, password: str) -> PercolationEngine:
    """
    Create a PercolationEngine configured with a Neo4j driver.

    Parameters:
        uri (str): Neo4j connection URI.
        user (str): Neo4j username.
        password (str): Neo4j password.

    Returns:
        PercolationEngine: Engine instance initialized with a Neo4j driver.
    """
    driver = GraphDatabase.driver(uri, auth=(user, password))
    return PercolationEngine(driver)
