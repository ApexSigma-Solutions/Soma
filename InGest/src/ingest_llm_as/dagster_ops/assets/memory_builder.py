"""SimpleMem Stage 1: Memory Builder Asset.

Implements Semantic Structured Compression:
- Entropy-based filtering to remove low-information content
- Coreference resolution (replacing pronouns with entities)
- Temporal anchoring (converting relative dates to absolute)
- Atomic fact segmentation

This asset "chews" raw data before the Brain sees it.
"""

from dagster import asset, AssetExecutionContext, Config
from pydantic import Field
from typing import Any
import re
from datetime import datetime, timedelta

from ..resources import (
    PostgresResource,
    LanceDBResource,
    OllamaResource,
    OmegaKGClient,
)


class MemoryBuilderConfig(Config):
    """Configuration for memory building."""

    min_content_length: int = Field(
        default=50, description="Minimum content length to process"
    )
    entropy_threshold: float = Field(
        default=0.3, description="Minimum entropy score to keep content"
    )


def calculate_entropy(text: str) -> float:
    """Calculate Shannon entropy of text as a measure of information density.

    Higher entropy = more unique information content.
    Lower entropy = more repetitive/low-value content.
    """
    if not text:
        return 0.0

    # Calculate character frequency
    freq: dict[str, int] = {}
    for char in text.lower():
        freq[char] = freq.get(char, 0) + 1

    # Calculate entropy
    length = len(text)
    entropy = 0.0
    for count in freq.values():
        prob = count / length
        if prob > 0:
            import math

            entropy -= prob * math.log2(prob)

    # Normalize to 0-1 range (max entropy for ASCII is ~6.6 bits)
    return min(entropy / 6.6, 1.0)


def resolve_coreferences(text: str, entities: list[dict]) -> str:
    """Replace pronouns with their antecedents.

    Simple rule-based resolution - production would use a proper coreference model.
    """
    # Build entity map from recent context
    entity_map = {}
    for ent in entities:
        ent_type = ent.get("type", "").lower()
        ent_name = ent.get("name", "")
        if ent_type == "person":
            entity_map["he"] = ent_name
            entity_map["him"] = ent_name
            entity_map["his"] = f"{ent_name}'s"
            entity_map["she"] = ent_name
            entity_map["her"] = ent_name
        elif ent_type in ("organization", "company"):
            entity_map["it"] = ent_name
            entity_map["they"] = ent_name

    # Replace pronouns (case-insensitive, word boundaries)
    result = text
    for pronoun, replacement in entity_map.items():
        pattern = rf"\b{pronoun}\b"
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


def anchor_temporal_references(
    text: str, reference_time: datetime | None = None
) -> str:
    """Convert relative time references to absolute timestamps.

    Examples:
    - "tomorrow at 2pm" -> "2026-01-22T14:00:00"
    - "next week" -> "2026-01-28"
    """
    ref = reference_time or datetime.now()

    # Pattern mappings for relative time
    replacements = [
        (r"\btomorrow\b", (ref + timedelta(days=1)).strftime("%Y-%m-%d")),
        (r"\byesterday\b", (ref - timedelta(days=1)).strftime("%Y-%m-%d")),
        (r"\bnext week\b", (ref + timedelta(weeks=1)).strftime("%Y-%m-%d")),
        (r"\blast week\b", (ref - timedelta(weeks=1)).strftime("%Y-%m-%d")),
        (r"\btoday\b", ref.strftime("%Y-%m-%d")),
    ]

    result = text
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


def segment_into_atoms(text: str) -> list[str]:
    """Segment text into atomic facts.

    Each atom should represent a single, self-contained piece of information.
    Uses sentence boundaries with some intelligence about compound statements.
    """
    # Split on sentence boundaries
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())

    atoms = []
    for sentence in sentences:
        # Skip very short fragments
        if len(sentence) < 20:
            continue

        # Check for compound sentences with 'and' or 'but'
        if " and " in sentence.lower() or " but " in sentence.lower():
            # Split compound sentences, keeping reasonable length
            parts = re.split(r"\s+(?:and|but)\s+", sentence, flags=re.IGNORECASE)
            atoms.extend(p.strip() for p in parts if len(p.strip()) > 20)
        else:
            atoms.append(sentence.strip())

    return atoms


@asset(
    description="SimpleMem Stage 1: Compress raw dialogues into atomic memory units",
    compute_kind="python",
    group_name="memory_pipeline",
)
async def memory_builder(
    context: AssetExecutionContext,
    config: MemoryBuilderConfig,
    postgres: PostgresResource,
    lancedb: LanceDBResource,
    ollama: OllamaResource,
    omegakg: OmegaKGClient,
) -> dict[str, Any]:
    """Process pending raw content into compressed memory atoms.

    Returns:
        Dictionary with processing statistics.
    """
    context.log.info("Starting Memory Builder - SimpleMem Stage 1")

    conn = await postgres.get_connection()

    try:
        # Fetch pending items from ingest queue
        rows = await conn.fetch("""
            SELECT id, webhook_payload, created_at
            FROM ingest_transactions
            WHERE status = 'PENDING'
            ORDER BY created_at ASC
            LIMIT 50
        """)

        if not rows:
            context.log.info("No pending items to process")
            return {"processed": 0, "atoms_created": 0, "filtered": 0}

        processed = 0
        atoms_created = 0
        filtered = 0

        for row in rows:
            tx_id = row["id"]
            payload = row["webhook_payload"]
            created_at = row["created_at"]

            try:
                # Extract content from payload
                content = payload.get("content", "")
                entities = payload.get("entities", [])
                raw_id = payload.get("raw_id", f"tx-{tx_id}")

                # Step 1: Entropy filter
                entropy = calculate_entropy(content)
                if entropy < config.entropy_threshold:
                    context.log.debug(
                        f"Filtered tx-{tx_id}: low entropy ({entropy:.2f})"
                    )
                    await conn.execute(
                        "UPDATE ingest_transactions SET status = 'FILTERED' WHERE id = $1",
                        tx_id,
                    )
                    filtered += 1
                    continue

                # Step 2: Coreference resolution
                resolved_content = resolve_coreferences(content, entities)

                # Step 3: Temporal anchoring
                anchored_content = anchor_temporal_references(
                    resolved_content, created_at
                )

                # Step 4: Segment into atoms
                atoms = segment_into_atoms(anchored_content)

                if not atoms:
                    context.log.debug(f"No atoms extracted from tx-{tx_id}")
                    await conn.execute(
                        "UPDATE ingest_transactions SET status = 'FILTERED' WHERE id = $1",
                        tx_id,
                    )
                    filtered += 1
                    continue

                # Step 5: Generate embeddings and store in LanceDB
                for i, atom in enumerate(atoms):
                    embedding = await ollama.generate_embedding(atom)

                    # Prepare memory unit for Guardian commit
                    memory_digest = {
                        "title": f"Memory Atom {raw_id}:{i}",
                        "summary": atom,
                        "entities": entities,
                        "concepts": [],  # TODO: Extract concepts
                        "decisions": [],
                        "outcomes": [],
                        "tags": ["memory_atom", "simplemem_stage1"],
                    }

                    # Commit to OmegaKG Guardian (sole writer)
                    await omegakg.commit_knowledge(
                        raw_id=f"{raw_id}:atom:{i}",
                        type="memory_atom",
                        digest=memory_digest,
                        metadata={
                            "source_tx_id": tx_id,
                            "entropy": entropy,
                            "embedding_model": ollama.embedding_model,
                        },
                    )

                    atoms_created += 1

                # Mark transaction as committed
                await conn.execute(
                    "UPDATE ingest_transactions SET status = 'COMMITTED', updated_at = NOW() WHERE id = $1",
                    tx_id,
                )
                processed += 1

            except Exception as e:
                context.log.error(f"Error processing tx-{tx_id}: {e}")
                await conn.execute(
                    "UPDATE ingest_transactions SET status = 'FAILED', updated_at = NOW() WHERE id = $1",
                    tx_id,
                )

        context.log.info(
            f"Memory Builder complete: {processed} processed, "
            f"{atoms_created} atoms created, {filtered} filtered"
        )

        return {
            "processed": processed,
            "atoms_created": atoms_created,
            "filtered": filtered,
        }

    finally:
        await conn.close()
