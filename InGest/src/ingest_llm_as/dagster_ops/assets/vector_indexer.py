"""Vector Indexer Asset - Migrated from OmegaKG.

This asset replaces omega_kg/workers/vector_index_worker.py.
Instead of writing directly to Neo4j (which violated Guardian-only-writer),
it POSTs embedding updates to OmegaKG Guardian.

Part of SimpleMem Stage 2: Structured Indexing.
"""

from dagster import asset, AssetExecutionContext, Config
from pydantic import Field
from typing import Any

from ..resources import (
    PostgresResource,
    OllamaResource,
    OmegaKGClient,
)


class VectorIndexerConfig(Config):
    """Configuration for vector indexing."""

    batch_size: int = Field(
        default=50, description="Number of items to process per run"
    )


@asset(
    description="SimpleMem Stage 2: Generate embeddings and store in Neo4j via Guardian",
    compute_kind="python",
    group_name="memory_pipeline",
    deps=["memory_builder"],
)
async def vector_indexer(
    context: AssetExecutionContext,
    config: VectorIndexerConfig,
    postgres: PostgresResource,
    ollama: OllamaResource,
    omegakg: OmegaKGClient,
) -> dict[str, Any]:
    """Process committed memory atoms and create vector indices (now stored in Neo4j)."""

    context.log.info("Starting Vector Indexer - SimpleMem Stage 2 (Neo4j)")

    conn = await postgres.get_connection()

    try:
        rows = await conn.fetch(
            """
            SELECT id, webhook_payload, updated_at
            FROM ingest_transactions
            WHERE status = 'COMMITTED'
              AND (webhook_payload->>'indexed') IS NULL
            ORDER BY updated_at DESC
            LIMIT $1
        """,
            config.batch_size,
        )

        if not rows:
            context.log.info("No new atoms to index")
            return {"indexed": 0}

        indexed = 0

        for row in rows:
            tx_id = row["id"]
            payload = row["webhook_payload"]

            try:
                content = payload.get("content", "")
                raw_id = payload.get("raw_id", f"tx-{tx_id}")
                # entities = payload.get("entities", [])

                # Generate embedding (768d for qwen3)
                embedding = await ollama.generate_embedding(content)

                # Store in Neo4j via Guardian
                # We treat these as generic MemoryAtom nodes unless type is specified
                await omegakg.store_embedding(
                    raw_id=raw_id,
                    node_label="MemoryAtom",
                    embedding=embedding,
                    content=content,
                )

                await conn.execute(
                    """
                    UPDATE ingest_transactions
                    SET webhook_payload = webhook_payload || '{"indexed": true}'::jsonb
                    WHERE id = $1
                """,
                    tx_id,
                )

                indexed += 1

            except Exception as e:
                context.log.error(f"Error indexing tx-{tx_id}: {e}")

        context.log.info(f"Vector Indexer complete: {indexed} items indexed in Neo4j")
        return {"indexed": indexed}

    finally:
        await conn.close()
