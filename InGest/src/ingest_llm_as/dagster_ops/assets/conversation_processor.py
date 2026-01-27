"""Conversation Processor Asset - Migrated from OmegaKG.

This asset processes raw conversation ingestions (source: raw_ingestions table),
synthesizes knowledge digests via InGest-LLM API, and commits them to OmegaKG Guardian.
"""

from dagster import asset, AssetExecutionContext, Config
from pydantic import Field
from typing import Any, Dict
import json
from datetime import datetime

from ..resources import (
    PostgresResource,
    OmegaKGClient,
)


class ConversationProcessorConfig(Config):
    """Configuration for conversation processing."""

    batch_size: int = Field(
        default=10, description="Number of conversations to process per run"
    )
    ingest_api_url: str = Field(
        default="http://localhost:8000", description="InGest-LLM API URL"
    )


@asset(
    description="Process raw conversations into Flexible Knowledge Digests",
    compute_kind="python",
    group_name="ingest_pipeline",
)
async def conversation_processor(
    context: AssetExecutionContext,
    config: ConversationProcessorConfig,
    postgres: PostgresResource,
    omegakg: OmegaKGClient,
) -> Dict[str, Any]:
    """Process raw conversation records."""
    import httpx

    context.log.info("Starting Conversation Processor")
    processed_count = 0

    conn = await postgres.get_connection()

    try:
        # Fetch unprocessed conversation records
        # Assuming table raw_ingestions exists in postgres resource DB
        rows = await conn.fetch(
            """
            SELECT ingestion_id, source_type, raw_payload, created_at
            FROM raw_ingestions
            WHERE source_type LIKE 'conversation-%'
              AND processed = false
            ORDER BY created_at ASC
            LIMIT $1
            """,
            config.batch_size,
        )

        if not rows:
            context.log.info("No new conversations to process")
            return {"processed": 0}

        context.log.info(f"Found {len(rows)} conversations to synthesize")

        for row in rows:
            ingesty_id = row["ingestion_id"]
            source_type = row["source_type"]
            raw_payload = row["raw_payload"]

            # Extract platform (e.g. "conversation-Perplexity" -> "Perplexity")
            platform = (
                source_type.replace("conversation-", "") if source_type else "unknown"
            )

            context.log.info(f"Processing Record {ingesty_id} ({platform})")

            try:
                # 1. Call InGest-LLM for Synthesis
                async with httpx.AsyncClient(timeout=300.0) as client:
                    # Prepare content
                    content_to_digest = ""
                    if isinstance(raw_payload, dict) and "messages" in raw_payload:
                        content_to_digest = json.dumps(raw_payload["messages"])
                    else:
                        content_to_digest = json.dumps(raw_payload)

                    raw_title = "Conversation"
                    raw_url = ""
                    if isinstance(raw_payload, dict):
                        raw_title = raw_payload.get("title", "Conversation")
                        raw_url = raw_payload.get("url", "")

                    resp = await client.post(
                        f"{config.ingest_api_url}/ingest/digest",
                        json={
                            "content": content_to_digest,
                            "metadata": {
                                "source": "dagster_processor",
                                "content_type": "json",
                                "title": raw_title,
                                "source_url": raw_url,
                            },
                        },
                    )
                    resp.raise_for_status()
                    digest_data = resp.json()

                # 2. Map to Flexible Schema (Dicts)
                nodes = []
                edges = []

                # Session info
                session_title = digest_data.get("title", "Unknown")
                session_summary = digest_data.get("summary", "")

                # Map Entities
                for ent in digest_data.get("entities", []):
                    ent_name = ent.get("name")
                    if not ent_name:
                        continue
                    ent_id = f"ent-{ent_name.replace(' ', '-').lower()}"
                    nodes.append(
                        {
                            "id": ent_id,
                            "label": ent.get("type", "Entity"),
                            "properties": {"name": ent_name},
                        }
                    )

                # Map Concepts
                for concept in digest_data.get("concepts", []):
                    con_id = f"con-{concept.replace(' ', '-').lower()}"
                    nodes.append(
                        {
                            "id": con_id,
                            "label": "Concept",
                            "properties": {"name": concept},
                        }
                    )

                # Map Decisions
                for i, dec in enumerate(digest_data.get("decisions", [])):
                    nodes.append(
                        {
                            "id": f"dec-{i}",
                            "label": "Decision",
                            "properties": {"content": dec},
                        }
                    )

                # Map Outcomes
                for i, out in enumerate(digest_data.get("outcomes", [])):
                    nodes.append(
                        {
                            "id": f"out-{i}",
                            "label": "Outcome",
                            "properties": {"content": out},
                        }
                    )

                digest = {
                    "source_id": str(ingesty_id),
                    "digest_type": "conversation",
                    "title": session_title,
                    "summary": session_summary,
                    "nodes": nodes,
                    "edges": edges,
                    "tags": digest_data.get("tags", []),
                    "captured_at": datetime.utcnow().isoformat(),
                    "metadata": {"platform": platform, "url": raw_url},
                }

                # 3. Commit to Guardian
                await omegakg.commit_knowledge(
                    raw_id=str(ingesty_id),
                    type="conversation",
                    digest=digest,
                    metadata={"platform": platform},
                )

                # 4. Mark as processed
                await conn.execute(
                    """
                    UPDATE raw_ingestions
                    SET processed = true, processed_at = NOW()
                    WHERE ingestion_id = $1
                    """,
                    ingesty_id,
                )

                processed_count += 1
                context.log.info(f"Successfully processed {ingesty_id}")

            except Exception as e:
                context.log.error(f"Failed to process {ingesty_id}: {e}")
                await conn.execute(
                    """
                    UPDATE raw_ingestions
                    SET last_error = $1
                    WHERE ingestion_id = $2
                    """,
                    str(e),
                    ingesty_id,
                )

    finally:
        await conn.close()

    context.log.info(f"Conversation Processor complete: {processed_count} items")
    return {"processed": processed_count}
