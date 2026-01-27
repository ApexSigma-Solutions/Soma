"""
Omega_KG Task Lifecycle Enforcement
Implements time-based state transitions with email notifications
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
import frontmatter
from dateutil import parser

from omega_kg.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ConnectionError(Exception):
    """Raised when Neo4j connection cannot be established"""

    pass


class TaskStatus(Enum):
    """Task lifecycle states"""

    DRAFT = "draft"
    READY = "ready"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class LifecycleRule:
    """Defines a lifecycle transition rule"""

    from_status: TaskStatus
    to_status: TaskStatus
    days_threshold: int
    condition: Optional[str] = None  # Cypher WHERE clause
    action: str = "auto"  # auto, warn, manual


class TaskLifecycle:
    """Enforces task lifecycle rules and generates reports"""

    # Lifecycle rules (the thermodynamics)
    RULES = [
        # Draft tasks decay to archive
        LifecycleRule(
            from_status=TaskStatus.DRAFT,
            to_status=TaskStatus.ARCHIVED,
            days_threshold=14,
            condition="NOT t.pinned = true",
            action="auto",
        ),
        # Draft tasks warn before archival
        LifecycleRule(
            from_status=TaskStatus.DRAFT,
            to_status=TaskStatus.DRAFT,  # No transition, just warn
            days_threshold=10,
            condition="NOT t.pinned = true AND NOT t.warned = true",
            action="warn",
        ),
        # Active tasks stale after 30 days without commits
        LifecycleRule(
            from_status=TaskStatus.ACTIVE,
            to_status=TaskStatus.BLOCKED,  # Flag as blocked
            days_threshold=30,
            condition="NOT EXISTS((t)<-[:IMPLEMENTS]-(:Commit))",
            action="warn",
        ),
        # Completed tasks archive after 90 days
        LifecycleRule(
            from_status=TaskStatus.COMPLETED,
            to_status=TaskStatus.ARCHIVED,
            days_threshold=90,
            action="auto",
        ),
    ]

    def __init__(self, mock_mode: bool = False):
        """
        Initialize the TaskLifecycle manager and configure persistence and vault settings.

        Sets the Obsidian vault path and, unless mock_mode is True, attempts to establish a Neo4j driver; on connection failure the instance is switched to mock mode and the driver is cleared.

        Parameters:
            mock_mode (bool): If True, skip connecting to Neo4j and operate using mock data.
        """
        self.driver = None
        self.vault_path = Path(settings.obsidian_vault_path)
        self.mock_mode = mock_mode

        if not mock_mode:
            try:
                self.driver = GraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_user, settings.neo4j_password),
                )
                # Test the connection
                self._check_connection()
                logger.info("Neo4j connection established")
            except (ServiceUnavailable, AuthError, ConnectionError) as e:
                logger.error("Failed to connect to Neo4j: %s: %s", type(e).__name__, e)
                logger.warning("Falling back to mock mode (dry-run only)")
                self.mock_mode = True
                self.driver = None

    def _check_connection(self) -> bool:
        """
        Validate that the configured Neo4j driver can execute a simple health query.

        Returns:
            True if the driver responded to the health check query.

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

    def get_connection_status(self) -> Dict[str, Any]:
        """
        Return current Neo4j connection and mock-mode status.

        Returns:
            dict: Mapping with connection information:
                connected: `true` if a Neo4j driver is configured and mock mode is not active, `false` otherwise.
                mock_mode: `true` if operating in mock mode, `false` otherwise.
                uri: the active Neo4j URI when connected, or `"mock://local"` when in mock mode.
        """
        return {
            "connected": self.driver is not None and not self.mock_mode,
            "mock_mode": self.mock_mode,
            "uri": settings.neo4j_uri if not self.mock_mode else "mock://local",
        }

    def enforce_lifecycle(
        self, dry_run: bool = False
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Enforces configured lifecycle rules, applying transitions or warnings to matching tasks.

        Parameters:
            dry_run (bool): If True, simulate actions without modifying the database or files.

        Returns:
            results (Dict[str, List[Dict[str, Any]]]): Mapping of result categories to lists of task records or error entries.
                - "archived": tasks that were auto-transitioned to ARCHIVED.
                - "warned": tasks that were flagged with a warning.
                - "blocked": tasks that were transitioned to BLOCKED.
                - "failed": entries describing tasks or operations that failed with error details.
                - "skipped": records explaining why processing was skipped (e.g., database unavailable).
        """
        results: Dict[str, List[Dict[str, Any]]] = {
            "archived": [],
            "warned": [],
            "blocked": [],
            "failed": [],
            "skipped": [],
        }

        if self.mock_mode:
            logger.warning("Running in mock mode - no database operations")
            return self._get_mock_results()

        if not self.driver:
            logger.error("No database connection available")
            return results

        try:
            with self.driver.session() as session:
                for rule in self.RULES:
                    violations = self._find_violations(session, rule)

                    for task in violations:
                        try:
                            if dry_run:
                                logger.info(
                                    "[DRY RUN] Would %s: %s", rule.action, task["t.uid"]
                                )
                                continue

                            if rule.action == "auto":
                                self._transition_task(session, task["t.uid"], rule)
                                results[rule.to_status.value].append(task)
                            elif rule.action == "warn":
                                self._warn_task(session, task["t.uid"], rule)
                                results["warned"].append(task)

                        except Exception as e:
                            logger.error("Failed to process %s: %s", task["t.uid"], e)
                            results["failed"].append({"task": task, "error": str(e)})

        except ServiceUnavailable as e:
            logger.error("Database connection lost: %s", e)
            logger.info("Tip: Ensure Neo4j is running on %s", settings.neo4j_uri)
            results["skipped"].append(
                {"reason": "Database unavailable", "error": str(e)}
            )
        except Exception as e:
            logger.error("Unexpected error: %s", e)
            results["failed"].append(
                {"reason": "Lifecycle enforcement failed", "error": str(e)}
            )

        return results

    def _get_mock_results(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Return a predefined mock lifecycle results dictionary used when a real database connection is not available.

        Returns:
            mock_results (Dict[str, List[Dict[str, Any]]]): Mapping with keys 'archived', 'warned', 'blocked', 'failed', and 'skipped'. Each value is a list of task records; task records contain the keys 't.uid', 't.title', 't.filepath', 't.status', and 'days_old'.
        """
        return {
            "archived": [
                {
                    "t.uid": "mock-draft-001",
                    "t.title": "Old Draft Task (Mock)",
                    "t.filepath": "Tasks/old_draft.md",
                    "t.status": "draft",
                    "days_old": 15,
                }
            ],
            "warned": [
                {
                    "t.uid": "mock-draft-002",
                    "t.title": "Draft Task Approaching Expiry (Mock)",
                    "t.filepath": "Tasks/expiring_draft.md",
                    "t.status": "draft",
                    "days_old": 11,
                }
            ],
            "blocked": [],
            "failed": [],
            "skipped": [],
        }

    def _find_violations(
        self, session: Any, rule: LifecycleRule
    ) -> List[Dict[str, Any]]:
        """
        Find tasks that match a lifecycle rule's status and age criteria.

        Performs date parsing and filtering in Python to handle inconsistent date formats (Strings vs DateTime).
        """

        # Build Cypher query - Fetch all candidates matching status and condition
        # We fetch t.created and filter by age in Python
        query = f"""
            MATCH (t:Task)
            WHERE t.status = $from_status
              {f"AND ({rule.condition})" if rule.condition else ""}
            RETURN t.uid, t.title, t.filepath, t.status, t.created
        """

        result = session.run(
            query,
            from_status=rule.from_status.value,
        )

        candidates = [dict(record) for record in result]
        violations = []
        now = datetime.now()

        for task in candidates:
            created_val = task.get("t.created")
            if not created_val:
                continue

            try:
                # Parse date (robustly handles "Mon, 27th Oct" and ISO)
                if isinstance(created_val, str):
                    # dateutil handles "27th" and various formats better
                    created_dt = parser.parse(created_val)
                elif hasattr(created_val, "isoformat"):  # DateTime object
                    created_dt = created_val
                else:
                    # Attempt to cast or skip
                    continue

                # Make naive/aware compatible
                if created_dt.tzinfo and not now.tzinfo:
                    # Compare with active timezone or convert to naive
                    # Simplest: ignore tz for age calc (approximate days)
                    created_dt = created_dt.replace(tzinfo=None)
                elif not created_dt.tzinfo and now.tzinfo:
                    now_naive = now.replace(tzinfo=None)

                # Use naive comparison for robust "days age"
                age = (datetime.now() - created_dt.replace(tzinfo=None)).days

                if age > rule.days_threshold:
                    task["days_old"] = age
                    violations.append(task)

            except Exception as e:
                logger.warning(
                    f"Failed to parse date for task {task.get('t.uid')}: {e}"
                )
                continue

        # Sort by days_old descending
        violations.sort(key=lambda x: x.get("days_old", 0), reverse=True)
        return violations

    def _transition_task(self, session: Any, uid: str, rule: LifecycleRule) -> None:
        """
        Apply a lifecycle rule to a task and persist the transition to both Neo4j and its Obsidian note.

        Sets the task's status and transition metadata in the database, updates the task's markdown frontmatter and appends a human-readable transition notice to the file, and prints a confirmation message.
        """

        # Update Neo4j
        session.run(
            """
            MATCH (t:Task {uid: $uid})
            SET t.status = $new_status,
                t.transitioned_at = datetime(),
                t.transition_reason = $reason
        """,
            uid=uid,
            new_status=rule.to_status.value,
            reason=(
                f"Lifecycle rule: {rule.from_status.value} -> "
                f"{rule.to_status.value} after {rule.days_threshold} days"
            ),
        )

        # Update Obsidian file
        self._update_task_file(uid, rule.to_status.value, rule)

        logger.info(
            "Transitioned %s: %s → %s",
            uid,
            rule.from_status.value,
            rule.to_status.value,
        )

    def _warn_task(self, session: Any, uid: str, rule: LifecycleRule) -> None:
        """
        Record that a task has been warned to avoid duplicate warnings.

        Sets the Task node's `warned` flag to true and `warned_at` to the current datetime in the database; used when a lifecycle rule issues a warning (e.g., an approaching automatic transition).
        """

        session.run(
            """
            MATCH (t:Task {uid: $uid})
            SET t.warned = true,
                t.warned_at = datetime()
        """,
            uid=uid,
        )

        logger.warning("Warned %s: approaching %s", uid, rule.to_status.value)

    def _update_task_file(self, uid: str, new_status: str, rule: LifecycleRule) -> None:
        """
        Update an Obsidian note's frontmatter and content to record a lifecycle transition.

        Sets the note's frontmatter "status" to new_status, adds a "lifecycle_transition" metadata object containing from/to/reason/date, and appends a human-readable transition notice to the note body. If no matching note file for the given UID is found, the function logs a warning and returns without making changes.

        Parameters:
            uid (str): Unique task identifier used to locate the note file in the vault.
            new_status (str): Status value to set in the note frontmatter.
            rule (LifecycleRule): LifecycleRule that triggered the transition; used to populate transition metadata.
        """

        # Find task file
        # Support both TN-XXX-000 format and legacy TASK-XXX format
        task_files = list(self.vault_path.glob(f"Tasks/**/{uid}*.md"))
        if not task_files:
            # Try alternative pattern for TN prefix
            task_files = list(self.vault_path.glob(f"TN/**/{uid}*.md"))
        if not task_files:
            logger.warning("Task file not found for %s", uid)
            return

        task_path = task_files[0]

        # Update frontmatter
        with open(task_path, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        post.metadata["status"] = new_status
        post.metadata["lifecycle_transition"] = {
            "from": rule.from_status.value,
            "to": rule.to_status.value,
            "reason": f"Auto-transitioned after {rule.days_threshold} days",
            "date": datetime.now().isoformat(),
        }

        # Append notice to content
        notice = f"""

---

**🤖 Lifecycle Transition:** {rule.from_status.value} → **{new_status}**
*Reason:* Automatic transition after {rule.days_threshold} days of inactivity.
*Date:* {datetime.now().strftime("%Y-%m-%d %H:%M")}

"""
        post.content += notice

        # Write back
        with open(task_path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))

    def generate_report(self, results: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Create a human-readable lifecycle report summarizing actions taken and current stale tasks.

        Parameters:
            results (Dict[str, List[Dict[str, Any]]]): Mapping of lifecycle outcome categories to lists of task records.
                Expected keys include:
                - "archived": list of tasks auto-archived (each record contains 't.uid', 't.title', 'days_old', etc.)
                - "warned": list of tasks that were warned (each record contains 't.uid', 't.title', 'days_old', etc.)
                - "failed": list of task records that failed processing
                - other keys are permitted but ignored by this function.

        Returns:
            str: A multi-line text report containing sections for auto-archived tasks, warnings, stale active tasks, and a summary with counts.
        """

        report_lines = [
            "🔄 Task Lifecycle Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 50,
            "",
        ]

        # Auto-archived tasks
        if results.get("archived"):
            report_lines.append("🗄️  AUTO-ARCHIVED (14+ days draft):")
            for task in results["archived"][:10]:  # Limit to 10
                report_lines.append(
                    f"  • {task['t.uid']}: {task['t.title']} ({task['days_old']} days)"
                )
            if len(results["archived"]) > 10:
                report_lines.append(f"  ... and {len(results['archived']) - 10} more")
            report_lines.append("")

        # Warnings
        if results.get("warned"):
            report_lines.append("⚠️  WARNINGS (approaching expiry):")
            for task in results["warned"][:10]:
                days_remaining = 14 - task["days_old"]
                report_lines.append(
                    f"  • {task['t.uid']}: {task['t.title']} ({days_remaining} days until auto-archive)"
                )
            report_lines.append("")

        # Stale active tasks
        stale_active = self._get_stale_active_tasks()
        if stale_active:
            report_lines.append("🐌 STALE ACTIVE (30+ days, no commits):")
            for task in stale_active[:5]:
                report_lines.append(
                    f"  • {task['t.linear_id'] or task['t.uid']}: {task['t.title']}"
                )
            report_lines.append("")

        # Summary
        report_lines.extend(
            [
                "=" * 50,
                "SUMMARY:",
                f"  Archived: {len(results.get('archived', []))}",
                f"  Warned: {len(results.get('warned', []))}",
                f"  Stale Active: {len(stale_active)}",
                f"  Failed: {len(results.get('failed', []))}",
            ]
        )

        return "\n".join(report_lines)

    def _get_stale_active_tasks(self) -> List[Dict[str, Any]]:
        """
        Find active tasks older than 30 days with no commits in the last 7 days.

        Returns:
            A list of dictionaries representing stale active tasks. Each dictionary contains:
            - `uid`: task unique identifier
            - `title`: task title
            - `linear_id`: task linear identifier
            - `stale`: number of days since task creation

            Returns an empty list if no database driver is available or no tasks match.
        """

        if not self.driver:
            return []

        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (t:Task)
                WHERE t.status = 'active'
                  AND duration.between(t.created, datetime()).days > 30
                  AND NOT EXISTS {
                      MATCH (t)<-[:IMPLEMENTS]-(c:Commit)
                      WHERE duration.between(c.timestamp, datetime()).days < 7
                  }
                RETURN t.uid, t.title, t.linear_id,
                       duration.between(t.created, datetime()).days as stale
                ORDER BY stale DESC
                LIMIT 10
            """
            )

            return [dict(record) for record in result]

    def send_email_report(self, report: str) -> None:
        """
        Send the lifecycle report via SMTP to the configured recipient.

        If SMTP host, user, or recipient are not configured, the call does nothing. When configured, this composes a plain-text message whose subject includes the current date, connects to the SMTP server with STARTTLS, authenticates with the configured credentials, and sends the message. Prints a confirmation on success or an error message on failure.

        Parameters:
            report (str): Plain-text report body to include in the email.
        """

        # Check if email is configured
        if not all([settings.smtp_host, settings.smtp_user, settings.email_to]):
            logger.warning("Email not configured, skipping")
            return
            return

        msg = MIMEMultipart()
        msg["From"] = settings.smtp_user or ""
        msg["To"] = settings.email_to or ""
        msg["Subject"] = (
            f"Omega_KG Lifecycle Report - {datetime.now().strftime('%Y-%m-%d')}"
        )

        msg.attach(MIMEText(report, "plain"))

        try:
            with smtplib.SMTP(
                settings.smtp_host or "localhost", settings.smtp_port
            ) as server:
                server.starttls()
                server.login(settings.smtp_user or "", settings.smtp_password or "")
                server.send_message(msg)

            logger.info("Email report sent")
        except Exception as e:
            logger.error("Failed to send email: %s", e)

    def close(self) -> None:
        """
        Close the Neo4j driver if one is initialized.

        Does nothing if no driver is configured.
        """
        if self.driver:
            self.driver.close()


def main() -> None:
    """
    Command-line entry point that runs the TaskLifecycle enforcement flow.

    Parses CLI flags:
      --dry-run: preview lifecycle actions without applying changes.
      --no-email: do not send the generated report via email.

    Executes enforcement, prints connection status and the generated human-readable report, optionally sends the report by email, and ensures lifecycle resources are closed on exit.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Enforce Omega_KG task lifecycle")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying",
    )
    parser.add_argument("--no-email", action="store_true", help="Skip email report")
    args = parser.parse_args()

    lifecycle = TaskLifecycle()

    # Print connection status
    status = lifecycle.get_connection_status()
    if status["connected"]:
        logger.info("Connected to Neo4j: %s", status["uri"])
    else:
        logger.warning("Running in mock mode (no Neo4j connection)")

    try:
        logger.info("Running lifecycle enforcement...")
        results = lifecycle.enforce_lifecycle(dry_run=args.dry_run)

        report = lifecycle.generate_report(results)
        print(f"\n{report} - lifecycle.py:578")

        if not args.dry_run and not args.no_email:
            lifecycle.send_email_report(report)

    finally:
        lifecycle.close()


if __name__ == "__main__":
    main()
