"""GitHub Webhook Processor Asset.

Processes raw GitHub webhook events from 'raw_webhook_events'.
Migrated from OmegaKG legacy GitHubProcessor.

Flow:
1. Poll for unprocessed 'github' events.
2. Detect PR Merge events.
3. Extract 'Fixes [LIN-123]' patterns.
4. Commit linkage to OmegaKG Guardian.
"""

from dagster import asset, AssetExecutionContext, Config
from pydantic import Field
from typing import Any, Dict
import json
import re

from ..resources import (
    PostgresResource,
    OmegaKGClient,
)

# Regex for Linear Issue linking
ISSUE_REF_PATTERN = re.compile(
    r"\b(?:fixes|closes|resolves)\s+\[([A-Z]+-\d+)\]", re.IGNORECASE
)


class GitHubProcessorConfig(Config):
    batch_size: int = Field(default=10, description="Events per batch")


@asset(
    description="Process GitHub PR merges and link to tasks",
    compute_kind="python",
    group_name="ingest_pipeline",
    deps=[],
)
async def github_processor(
    context: AssetExecutionContext,
    config: GitHubProcessorConfig,
    postgres: PostgresResource,
    omegakg: OmegaKGClient,
) -> Dict[str, Any]:
    """Process pending GitHub events."""

    context.log.info("Starting GitHub Event Processor")

    conn = await postgres.get_connection()

    try:
        rows = await conn.fetch(
            """
            SELECT id, payload, received_at
            FROM raw_webhook_events
            WHERE source = 'github'
              AND processed_status = FALSE
            ORDER BY received_at ASC
            LIMIT $1
            FOR UPDATE SKIP LOCKED
            """,
            config.batch_size,
        )

        if not rows:
            return {"processed": 0}

        processed_count = 0

        for row in rows:
            event_id = row["id"]
            raw_payload = row["payload"]

            try:
                payload = (
                    json.loads(raw_payload)
                    if isinstance(raw_payload, str)
                    else raw_payload
                )

                # Check for PR Merge
                action = payload.get("action")
                pr = payload.get("pull_request", {})

                if action == "closed" and pr.get("merged"):
                    # Extract Data
                    repo_name = payload.get("repository", {}).get("full_name")
                    pr_title = pr.get("title", "")
                    pr_body = pr.get("body", "") or ""
                    pr_url = pr.get("html_url")

                    # Find Linked Issues
                    matches = ISSUE_REF_PATTERN.findall(f"{pr_title} {pr_body}")

                    if matches:
                        context.log.info(
                            f"PR {repo_name}#{pr.get('number')} links to: {matches}"
                        )

                        # Commit Relationships to Guardian
                        # We create a 'Commit' or 'PR' node and link it to the 'Task' node
                        digest = {
                            "source_id": f"pr-{pr.get('id')}",
                            "digest_type": "github_pr",
                            "title": f"PR: {pr_title}",
                            "summary": f"Merged PR in {repo_name}. Linked issues: {matches}",
                            "content": pr_body,
                            "nodes": [
                                {
                                    "id": f"pr-{pr.get('id')}",
                                    "label": "PullRequest",
                                    "properties": {
                                        "url": pr_url,
                                        "repo": repo_name,
                                        "number": pr.get("number"),
                                    },
                                }
                            ],
                            "edges": [],
                            "tags": ["github", "pr", "merge"],
                            "metadata": {"linked_issues": matches},
                        }

                        # Add edges for each linked issue
                        for issue_id in matches:
                            digest["edges"].append(
                                {
                                    "source_id": f"pr-{pr.get('id')}",
                                    "target_id": issue_id,  # Assuming Task node exists with this raw_id/identifier
                                    "type": "RESOLVES",
                                    "properties": {"detected_at": "now"},
                                }
                            )

                        await omegakg.commit_knowledge(
                            raw_id=f"pr-{pr.get('id')}", type="github_pr", digest=digest
                        )

                # Mark Done
                await conn.execute(
                    "UPDATE raw_webhook_events SET processed_status = TRUE, error_log = NULL WHERE id = $1",
                    event_id,
                )
                processed_count += 1

            except Exception as e:
                context.log.error(f"Error processing GitHub event {event_id}: {e}")
                await conn.execute(
                    "UPDATE raw_webhook_events SET processed_status = TRUE, error_log = $2 WHERE id = $1",
                    event_id,
                    str(e),
                )

        return {"processed": processed_count, "batch_size": len(rows)}

    finally:
        await conn.close()
