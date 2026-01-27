"""Linear Webhook Processor Asset.

Processes raw Linear webhook events from the 'ingest_transactions' table (formerly raw_webhook_events).
Migrated from OmegaKG legacy LinearProcessor.

Flow:
1. Poll for unprocessed 'linear' events.
2. Parse payload using Pydantic models.
3. Generate Markdown note.
4. Commit to OmegaKG Guardian (Graph + Vault).
5. Mark event as processed in Postgres.
"""

from dagster import asset, AssetExecutionContext, Config
from pydantic import Field, BaseModel
from typing import Any, Dict, Optional, List
import json

from ..resources import (
    PostgresResource,
    OmegaKGClient,
    OllamaResource,
)

# --- Models (Simplified from OmegaKG) ---


class LinearIssueData(BaseModel):
    """Minimal Linear Issue Data needed for processing."""

    id: str
    identifier: str  # e.g., "SOMA-123"
    title: str
    description: Optional[str] = None
    state: Dict[str, Any] = {}
    ssignee: Optional[Dict[str, Any]] = None
    labels: List[Dict[str, Any]] = []
    url: str
    createdAt: str
    updatedAt: str


class LinearWebhookPayload(BaseModel):
    action: str
    type: str
    data: Dict[str, Any]


# --- Config ---


class LinearProcessorConfig(Config):
    batch_size: int = Field(
        default=10, description="Number of events to process per run"
    )


@asset(
    description="Process raw Linear webhook events and sync to Knowledge Graph",
    compute_kind="python",
    group_name="ingest_pipeline",
    deps=[],
)
async def linear_processor(
    context: AssetExecutionContext,
    config: LinearProcessorConfig,
    postgres: PostgresResource,
    omegakg: OmegaKGClient,
    ollama: OllamaResource,
) -> Dict[str, Any]:
    """Process pending Linear webhook events."""

    context.log.info("Starting Linear Event Processor")

    conn = await postgres.get_connection()

    try:
        # Fetch unprocessed 'linear' events
        # Note: InGest uses 'ingest_transactions' table, but we might need to query the table
        # where webhooks are landing. Assuming 'raw_webhook_events' exists or is aliased.
        # Use postgres resource to find correct table.
        # For this migration, we assume the Receiver wrote to 'ingest_transactions'
        # with type='webhook_linear' or source='linear'.

        # Let's query 'raw_webhook_events' if it exists (legacy), or 'ingest_transactions'
        # Given InGest architecture, we should favor 'ingest_transactions'.
        # However, the current webhook receiver writes to 'raw_webhook_events'.
        # We will query 'raw_webhook_events' for now as part of the migration.

        rows = await conn.fetch(
            """
            SELECT id, payload, received_at
            FROM raw_webhook_events
            WHERE source = 'linear'
              AND processed_status = FALSE
            ORDER BY received_at ASC
            LIMIT $1
            FOR UPDATE SKIP LOCKED
            """,
            config.batch_size,
        )

        if not rows:
            context.log.info("No pending Linear events found.")
            return {"processed": 0}

        processed_count = 0
        error_count = 0

        for row in rows:
            event_id = row["id"]
            raw_payload = row["payload"]

            try:
                # 1. Parse Payload
                if isinstance(raw_payload, str):
                    payload_dict = json.loads(raw_payload)
                else:
                    payload_dict = raw_payload

                webhook = LinearWebhookPayload(**payload_dict)

                # Only process Issue events for now
                if webhook.type == "Issue" and webhook.action in ["create", "update"]:
                    issue_data = LinearIssueData(**webhook.data)

                    # 2. Generate Content (Markdown)
                    md_content = _generate_markdown(issue_data)

                    # 3. Generate Embedding
                    embedding_text = (
                        f"{issue_data.title}\n{issue_data.description or ''}"
                    )
                    embedding = await ollama.generate_embedding(embedding_text)

                    # 4. Commit to Guardian
                    # We treat Linear Issues as 'FlexibleNode' of type 'Task'
                    digest = {
                        "source_id": issue_data.id,
                        "digest_type": "linear_issue",
                        "title": f"{issue_data.identifier} {issue_data.title}",
                        "summary": issue_data.description or "No description",
                        "content": md_content,
                        "nodes": [
                            {
                                "id": issue_data.id,
                                "label": "Task",
                                "properties": {
                                    "identifier": issue_data.identifier,
                                    "status": issue_data.state.get("name"),
                                    "url": issue_data.url,
                                    "provider": "Linear",
                                },
                            }
                        ],
                        "edges": [],  # Relationships could be extracted (e.g. assignee)
                        "embedding": embedding,
                        "tags": ["linear", "task"],
                        "metadata": payload_dict,
                    }

                    response = await omegakg.commit_knowledge(
                        raw_id=issue_data.identifier, type="linear_issue", digest=digest
                    )

                    context.log.info(f"Committed {issue_data.identifier}: {response}")

                # 5. Mark Complete
                await conn.execute(
                    """
                    UPDATE raw_webhook_events
                    SET processed_status = TRUE, error_log = NULL
                    WHERE id = $1
                    """,
                    event_id,
                )
                processed_count += 1

            except Exception as e:
                error_count += 1
                context.log.error(f"Failed to process event {event_id}: {e}")
                await conn.execute(
                    """
                    UPDATE raw_webhook_events
                    SET processed_status = TRUE, error_log = $2
                    WHERE id = $1
                    """,
                    event_id,
                    str(e),
                )

        return {
            "processed": processed_count,
            "errors": error_count,
            "batch_size": len(rows),
        }

    finally:
        await conn.close()


def _generate_markdown(issue: LinearIssueData) -> str:
    """Simple markdown generator for Linear Issues."""
    md = f"# [{issue.identifier}] {issue.title}\n\n"
    md += f"**Status:** {issue.state.get('name', 'Unknown')}\n"
    md += f"**Link:** [Linear]({issue.url})\n\n"
    md += "## Description\n"
    md += f"{issue.description or 'No description provided.'}\n"
    return md
