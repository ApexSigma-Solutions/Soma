#!/usr/bin/env python
"""
Omega_KG Capture Server

FastAPI server that receives AI conversations from chrome extension,
saves them to Obsidian vault, and percolates to Neo4j.

This module handles:
- Application initialization and lifespan management
- Router registration
- CORS configuration
- Neo4j percolation logic
- Scheduler for batch operations

Modular components:
- omega_kg.models.capture: Pydantic data models
- omega_kg.utils.capture_utils: Helper functions
- omega_kg.routers.capture: Endpoint handlers
"""

import asyncio
import logging
import subprocess
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
import neo4j
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase

from omega_kg.config import log_config_summary
from omega_kg.obsidian_sync import ObsidianNeo4jSync
from omega_kg.lifecycle import TaskLifecycle
from omega_kg.percolation import PercolationEngine
from omega_kg.routers import github_receiver, linear_receiver
from omega_kg.routers.capture import router as capture_router
from omega_kg.routers.capture import set_percolate_function
from omega_kg.routers.terminal import router as terminal_router
from omega_kg.settings import settings
from omega_kg.smart_parser import SmartParser
from omega_kg.utils.capture_utils import generate_conversation_hash
from omega_kg.vector_store import VectorStore, get_vector_store
from omega_kg.pre_flight import pre_flight_checks
from omega_kg.routers.guardian import router as guardian_router
from omega_kg.models.capture import (
    ConversationData,
    ObsidianUpdateRequest,
    ObsidianUpdateResponse,
)

# Import RawIngestion from InGest (single ingress point)
# NOTE: RawIngestion import moved to fallback block below with proper error handling

# TODO: Refactor - InGest is now single ingress point, but RawIngestion import is failing
# Import RawIngestion from InGest-LLM service
try:
    from omega_kg.models.raw_storage import RawIngestion

    _RAW_INGESTION_AVAILABLE = True
except ImportError:
    # Fallback local model when InGest is not available
    _RAW_INGESTION_AVAILABLE = False

    # Local fallback RawIngestion model
    import uuid
    from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
    from omega_kg.database.base import Base

    class RawIngestion(Base):
        __tablename__ = "raw_ingestions"

        id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        ingestion_id = Column(String(255), unique=True, nullable=False)
        source_type = Column(String(50), nullable=True)
        raw_payload = Column(JSONB, nullable=False)
        captured_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        processed = Column(Boolean, default=False, nullable=False)
        processed_at = Column(DateTime, nullable=True)
        processing_attempts = Column(Integer, default=0, nullable=False)
        last_error = Column(Text, nullable=True)

        def __repr__(self):
            return f"<RawIngestion(id={self.id}, source_type='{self.source_type}')>"


# Ngrok tunnel integration
try:
    from omega_kg.ngrok_tunnel import ngrok_tunnel

    _ngrok_available = True
except ImportError:
    _ngrok_available = False
    logger = logging.getLogger(__name__)
    logger.warning("ngrok_tunnel module not available. Ngrok integration disabled.")

# Async scheduling with graceful fallback
_scheduler_available = True

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
except ImportError as e:
    _scheduler_available = False

    # Define a dummy class to prevent runtime errors when APScheduler is not available
    class AsyncIOScheduler:  # type: ignore[no-redef]
        def __init__(self) -> None:
            pass

        def add_job(self, *args: object, **kwargs: object) -> None:
            pass

        def start(self) -> None:
            pass

        def shutdown(self, *args: object, **kwargs: object) -> None:
            pass

    import warnings

    warnings.warn(
        f"APScheduler not available: {e}. Background tasks will be disabled.",
        ImportWarning,
    )


from omega_kg.utils.logging import configure_logging

# Configure logging
# We assume the service runs from Omega_KG_stable/ directory, so logs are in ../logs
log_dir = Path("d:/projects/OmegaKG/logs")
configure_logging("omega_kg_capture", log_dir)
logger = logging.getLogger(__name__)


# --- Neo4j Percolation Functions ---
async def _create_decision_nodes_async(
    session: "neo4j.work.async_.AsyncSession", conv_hash: str, data: ConversationData
) -> int:
    """
    Extract decisions from messages and create Decision nodes in Neo4j (async version).

    Only the first matching sentence per message containing a decision keyword is extracted.
    """
    decision_keywords = settings.decision_keywords
    nodes_created = 0
    if data.messages:
        for i, msg in enumerate(data.messages):
            msg_content = (
                msg.get("content", "") if isinstance(msg, dict) else msg.content
            )
            content_lower = msg_content.lower()
            for keyword in decision_keywords:
                if keyword in content_lower:
                    sentences = msg_content.split(".")
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            decision_content = sentence.strip()
                            result = await session.run(
                                """
                                MATCH (s:ChatSession {conversation_hash: $hash})
                                CREATE (d:Decision {
                                    content: $content, decision_id: $dec_id,
                                    extracted_at: datetime($created_at)
                                })
                                CREATE (s)-[:CONTAINS]->(d)
                                RETURN d
                                """,
                                hash=conv_hash,
                                content=decision_content,
                                dec_id=f"{conv_hash}-dec-{i}",
                                created_at=datetime.now().isoformat(),
                            )
                            record = await result.single()
                            if record:
                                nodes_created += 1
                            break
    return nodes_created


async def percolate_to_neo4j_with_embedding(
    file_path: Path,
    data: ConversationData,
) -> int:
    """
    Percolates a captured conversation to Neo4j WITH pending vector record creation.
    Creates a ChatSession node and queues embedding generation via vector_store.
    Captures complete immediately; embeddings are generated asynchronously by worker.

    Uses AsyncGraphDriver for non-blocking Neo4j operations.
    """
    from omega_kg.database.graph import graph_driver

    try:
        conv_hash = generate_conversation_hash(data)

        # Create ChatSession in Neo4j (WITHOUT immediate embedding) using async driver
        async with graph_driver.session() as session:
            result = await session.run(
                """
                MERGE (s:ChatSession {conversation_hash: $hash})
                ON CREATE SET
                    s.date = date($date), s.platform = $platform, s.filepath = $filepath,
                    s.url = $url, s.message_count = $msg_count, s.created_at = datetime($created_at)
                ON MATCH SET
                    s.updated_at = datetime($created_at)
                RETURN elementId(s) AS session_id
                """,
                hash=conv_hash,
                date=datetime.now().strftime("%Y-%m-%d"),
                platform=data.platform,
                filepath=str(file_path),
                url=data.url,
                msg_count=len(data.messages) if data.messages else 0,
                created_at=datetime.now().isoformat(),
            )

            record = await result.single()
            if not record:
                logger.warning(f"Failed to create ChatSession node for {conv_hash}")
                return 0

            session_id = record["session_id"]
            nodes_created = 1

            # Create Decision nodes (async)
            nodes_created += await _create_decision_nodes_async(
                session, conv_hash, data
            )

        # Queue pending embedding via vector_store (async, non-blocking)
        try:
            vector_store = await get_vector_store()
            vector_id = await vector_store.store_pending(
                message_id=session_id, node_label="ChatSession"
            )
            logger.info(
                f"[OK] Queued embedding for ChatSession {conv_hash} "
                f"(neo4j_id={session_id}, vector_id={vector_id})"
            )
        except Exception as e:
            logger.warning(f"Failed to queue embedding for {conv_hash}: {e}")
            # Non-fatal: Node created successfully, embedding will retry

        logger.info(
            f"Created {nodes_created} nodes in Neo4j + pending embedding queued"
        )
        return nodes_created

    except Exception as e:
        logger.error(f"Neo4j percolation failed: {e}")
        raise


# --- Synchronous Neo4j Percolation (for backward compatibility and tests) ---
def _create_chat_session(
    session, conv_hash: str, file_path: Path, data: ConversationData
) -> int:
    """Create or update a ChatSession node in Neo4j."""
    msg_count = len(data.messages) if data.messages else 0
    result = session.run(
        """
        MERGE (s:ChatSession {conversation_hash: $hash})
        ON CREATE SET
            s.date = date($date), s.platform = $platform, s.filepath = $filepath,
            s.url = $url, s.message_count = $msg_count, s.created_at = datetime($created_at)
        ON MATCH SET
            s.updated_at = datetime($created_at)
        RETURN s
        """,
        hash=conv_hash,
        date=datetime.now().strftime("%Y-%m-%d"),
        platform=data.platform,
        filepath=str(file_path),
        url=data.url,
        msg_count=msg_count,
        created_at=datetime.now().isoformat(),
    )
    return 1 if result.single() else 0


def _create_decision_nodes(
    session: "neo4j.work.session.Session", conv_hash: str, data: ConversationData
) -> int:
    """
    Extract decisions from messages and create Decision nodes in Neo4j (synchronous version).

    Only the first matching sentence per message containing a decision keyword is extracted.
    """
    decision_keywords = settings.decision_keywords
    nodes_created = 0
    if data.messages:
        for i, msg in enumerate(data.messages):
            msg_content = (
                msg.get("content", "") if isinstance(msg, dict) else msg.content
            )
            content_lower = msg_content.lower()
            for keyword in decision_keywords:
                if keyword in content_lower:
                    sentences = msg_content.split(".")
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            decision_content = sentence.strip()
                            result = session.run(
                                """
                                MATCH (s:ChatSession {conversation_hash: $hash})
                                CREATE (d:Decision {
                                    content: $content, decision_id: $dec_id,
                                    extracted_at: datetime($created_at)
                                })
                                CREATE (s)-[:CONTAINS]->(d)
                                RETURN d
                                """,
                                hash=conv_hash,
                                content=decision_content,
                                dec_id=f"{conv_hash}-dec-{i}",
                                created_at=datetime.now().isoformat(),
                            )
                            if result.single():
                                nodes_created += 1
                            break
    return nodes_created


def percolate_to_neo4j(
    file_path: Path,
    data: ConversationData,
    driver=None,
) -> int:
    """
    Percolates a captured conversation markdown file and its metadata to Neo4j.
    Creates a ChatSession node and Decision nodes for detected decisions.
    Accepts an optional Neo4j driver for batch efficiency.
    Returns the number of nodes created.
    """
    own_driver = False
    if driver is None:
        driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        own_driver = True
    try:
        with driver.session() as session:
            conv_hash = generate_conversation_hash(data)
            nodes_created = _create_chat_session(session, conv_hash, file_path, data)
            nodes_created += _create_decision_nodes(session, conv_hash, data)
        logger.info(f"Created {nodes_created} nodes in Neo4j")
        return nodes_created
    except Exception as e:
        logger.error(f"Neo4j percolation failed: {e}")
        raise
    finally:
        if own_driver:
            driver.close()


async def batch_percolate_sessions():
    """
    Batch percolates all session logs from Obsidian vault to Neo4j AND syncs tasks.
    Intended to run periodically via scheduler.

    Operations:
    1. Scan Tasks/Workflow/Linear folders:
       - Sync to Linear (if new/missing ID) via SmartParser
       - Sync to Neo4j via ObsidianNeo4jSync
    2. Scan Sessions (and configured folders):
       - Percolate commit/task references via PercolationEngine
    """
    driver = None
    try:
        import frontmatter
        import time

        start_time = time.time()
        logger.info("→ Scheduler execution started: batch_percolate_sessions")

        # --- Phase 1: Task Sync (Linear + Neo4j) ---
        sync_stats = {"linear_created": 0, "neo4j_synced": 0, "errors": 0}

        try:
            obsidian_sync = ObsidianNeo4jSync()
            # Initialize SmartParser (only if linear sync is configured)
            smart_parser = None
            if settings.linear_team_id:
                smart_parser = SmartParser()

            task_files = obsidian_sync.get_all_task_files()
            logger.info(f"Found {len(task_files)} task files to process")

            for task_file in task_files:
                try:
                    # 1. Sync to Linear if needed (missing linear_id)
                    if smart_parser:
                        meta = {}
                        try:
                            # lightweight check before full parse
                            with open(task_file, "r", encoding="utf-8") as f:
                                meta = frontmatter.load(f).metadata
                        except Exception:
                            pass

                        if not meta.get("linear_id"):
                            logger.info(f"Syncing new task to Linear: {task_file.name}")
                            await smart_parser.sync_note_to_linear(task_file)
                            sync_stats["linear_created"] += 1

                    # 2. Sync to Neo4j
                    obsidian_sync.sync_task_note(task_file)
                    sync_stats["neo4j_synced"] += 1

                except Exception as e:
                    logger.error(f"Failed to sync task {task_file.name}: {e}")
                    sync_stats["errors"] += 1

            obsidian_sync.close()
            logger.info(f"[OK] Task Sync phase complete: {sync_stats}")

        except Exception as e:
            logger.error(f"Task Sync phase failed: {e}", exc_info=True)

        # --- Phase 2: Session/Reference Percolation ---
        # Parse scan folders from settings
        # Use explicit session scan folders setting (TN-103/TN-301)
        scan_folders_str = settings.obsidian_session_scan_folders
        separator = "," if "," in scan_folders_str else ":"
        scan_folders = [
            f.strip() for f in scan_folders_str.split(separator) if f.strip()
        ]

        logger.info(f"Scanning folders for percolation: {', '.join(scan_folders)}")

        # Validate each folder exists
        valid_folders = []
        vault_base = Path(settings.obsidian_vault_path)
        for folder_name in scan_folders:
            folder_path = vault_base / folder_name
            if folder_path.exists():
                valid_folders.append(folder_path)
                logger.debug(f"Validated folder: {folder_path}")
            else:
                logger.warning(f"Percolation folder does not exist: {folder_path}")

        if not valid_folders:
            logger.warning(
                "No valid percolation folders found - skipping percolation phase"
            )
            return

        driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        engine = PercolationEngine(driver)

        # Percolate from vault root with filtered folder list
        valid_folder_names = [p.name for p in valid_folders]
        logger.debug(
            f"Initiating percolation from: {vault_base} for folders: {valid_folder_names}"
        )

        total_stats = engine.percolate_from_vault(
            vault_base, scan_folders=valid_folder_names
        )

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            f"[OK] Scheduler completed in {elapsed_ms:.0f}ms: "
            f"Synced {sync_stats['neo4j_synced']} tasks ({sync_stats['linear_created']} new to Linear). "
            f"Percolated {total_stats['tasks']} refs, {total_stats['links']} links."
        )
        logger.debug(f"Stats detail: {total_stats}")
    except Exception as e:
        logger.error(f"Batch session percolation failed: {e}", exc_info=True)
    finally:
        if driver is not None:
            driver.close()


async def run_lifecycle_check():
    """
    Run lifecycle enforcement periodically.
    """
    import asyncio

    logger.info("→ Scheduler execution started: run_lifecycle_check")
    lifecycle = None
    try:
        lifecycle = TaskLifecycle()
        # Run enforcement in executor to avoid blocking the loop
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(
            None, lambda: lifecycle.enforce_lifecycle(dry_run=False)
        )

        report = lifecycle.generate_report(results)
        logger.info(f"[OK] Lifecycle check complete:\n{report}")

        # Send email if configured
        if settings.email_to:
            await loop.run_in_executor(
                None, lambda: lifecycle.send_email_report(report)
            )

    except Exception as e:
        logger.error(f"Lifecycle check failed: {e}", exc_info=True)
    finally:
        if lifecycle:
            lifecycle.close()


# --- Ollama Service Management ---
_ollama_process: Optional[subprocess.Popen] = None
_heartbeat_task: Optional[asyncio.Task] = None

OLLAMA_EXE_PATHS = [
    Path(sys.prefix) / "Scripts" / "ollama.exe",  # Virtual env
    Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe",
    Path("C:/Program Files/Ollama/ollama.exe"),
]


async def _check_ollama_ready(timeout: int = 30) -> bool:
    """Check if Ollama is ready to accept requests."""
    ollama_url = settings.ollama_base_url
    async with httpx.AsyncClient() as client:
        for _ in range(timeout):
            try:
                resp = await client.get(f"{ollama_url}/api/tags", timeout=2)
                if resp.status_code == 200:
                    logger.info(f"[OK] Ollama ready at {ollama_url}")
                    return True
            except Exception:
                pass
            await asyncio.sleep(1)
    return False


async def _start_ollama() -> bool:
    """Start Ollama service if not already running."""
    global _ollama_process

    # First check if already running
    if await _check_ollama_ready(timeout=2):
        logger.info("Ollama already running")
        return True

    # Find Ollama executable
    ollama_path = None
    for path in OLLAMA_EXE_PATHS:
        if path.exists():
            ollama_path = path
            break

    if not ollama_path:
        logger.warning("Ollama executable not found - embeddings will be disabled")
        return False

    # Start Ollama as subprocess
    try:
        logger.info(f"Starting Ollama from {ollama_path}...")
        _ollama_process = subprocess.Popen(
            [str(ollama_path), "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

        # Wait for Ollama to be ready
        if await _check_ollama_ready(timeout=30):
            logger.info("[OK] Ollama started successfully")
            return True
        else:
            logger.error("Ollama started but not responding")
            return False

    except Exception as e:
        logger.error(f"Failed to start Ollama: {e}")
        return False


async def _stop_ollama():
    """Stop Ollama service if we started it."""
    global _ollama_process
    if _ollama_process is not None:
        try:
            _ollama_process.terminate()
            _ollama_process.wait(timeout=5)
            logger.info("[OK] Ollama stopped")
        except Exception as e:
            logger.error(f"Error stopping Ollama: {e}")
        _ollama_process = None


async def _run_heartbeat_loop():
    """Run Quipu heartbeat monitoring as background task."""
    from omega_kg.database.quipu import init_heartbeat_table, insert_heartbeat
    from omega_kg.quipu_ollama_heartbeat import check_ollama_health

    if not await init_heartbeat_table():
        logger.warning("Quipu heartbeat table init failed - monitoring disabled")
        return

    logger.info(
        f"[OK] Quipu heartbeat started (interval: {settings.heartbeat_interval_sec}s)"
    )

    while True:
        try:
            from datetime import timezone

            timestamp = datetime.now(timezone.utc)
            status, latency, model, meta = check_ollama_health()

            await insert_heartbeat(
                service_name=settings.quipu_service_name,
                timestamp=timestamp,
                status=status,
                latency_ms=latency,
                model_loaded=model,
                meta=meta,
            )

            await asyncio.sleep(settings.heartbeat_interval_sec)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            await asyncio.sleep(5)


# --- Lifespan Handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler to initialize Ollama, vector store, start worker, and schedule batch percolation."""
    global _heartbeat_task

    # 0. Pre-flight checks - fail fast if environment is broken
    logger.info("[SYSTEM] Starting Pre-Flight Checks...")
    pre_flight_checks_passed = pre_flight_checks()
    if not pre_flight_checks_passed:
        logger.critical("[CRITICAL] Pre-flight checks failed. Server will not start.")
        raise RuntimeError("Pre-flight checks failed")
    logger.info("[OK] Pre-flight checks passed")

    logger.info("Starting Omega_KG Capture Server...")

    # Initialize scheduler variable to ensure it's available in shutdown
    scheduler = None

    # 1. Start Ollama service (required for embeddings) - DISABLED, using Docker Model Runner
    # ollama_started = await _start_ollama()
    # if not ollama_started:
    #     logger.warning("Ollama not available - embeddings will fail")
    ollama_started = True
    logger.info("Docker Model Runner detected - Ollama checks disabled")

    # 2. Initialize vector store
    try:
        await get_vector_store()
        logger.info("[OK] Vector store initialized")
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {e}")
        raise

    # 3. Guardian Mode
    logger.info("[GUARDIAN] Omega_KG is now in Guardian Mode (Passive Storage).")

    # 4. Start Quipu heartbeat as background task - DISABLED (Docker Model Runner handles this)
    # try:
    #     _heartbeat_task = asyncio.create_task(_run_heartbeat_loop())
    # except Exception as e:
    #     logger.warning(f"Failed to start heartbeat: {e}")

    # 5. Start scheduler for batch percolation - DISABLED FOR NOW
    # try:
    #     if not _scheduler_available:
    #         logger.warning(
    #             "Scheduler not available - APScheduler import failed. Background tasks disabled."
    #         )
    #     else:
    try:
        if not _scheduler_available:
            logger.warning(
                "Scheduler not available - APScheduler import failed. Background tasks disabled."
            )
        else:
            scheduler = AsyncIOScheduler()
            scheduler.add_job(
                batch_percolate_sessions,
                "interval",
                minutes=5,
                id="session_percolation",
            )
            scheduler.add_job(
                run_lifecycle_check,
                "interval",
                hours=1,
                id="task_lifecycle",
            )
            scheduler.start()
            logger.info("[OK] Session percolation scheduled (every 5 minutes)")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        scheduler = None

    # Log startup summary
    logger.info(log_config_summary())

    yield

    # Shutdown sequence
    logger.info("Shutting down Omega_KG Capture Server...")

    # Stop heartbeat task
    if _heartbeat_task is not None:
        try:
            _heartbeat_task.cancel()
            await asyncio.sleep(0.1)  # Allow cancellation to propagate
            logger.info("[OK] Heartbeat task stopped")
        except Exception as e:
            logger.error(f"Error stopping heartbeat: {e}")

    # Stop embedding worker gracefully (obsolete in guardian mode)
    pass

    # Stop scheduler (only if it was started)
    if scheduler is not None:
        try:
            scheduler.shutdown(wait=False)
            logger.info("[OK] Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    else:
        logger.info("Scheduler was not started - skipping shutdown")

    # Close vector store pool
    try:
        await VectorStore.close_pool()
        logger.info("[OK] Vector store pool closed")
    except Exception as e:
        logger.error(f"Error closing vector store: {e}")

    # Stop Ollama if we started it
    await _stop_ollama()


# --- App Initialization ---
app = FastAPI(
    title="Omega_KG Capture Server",
    description="Receives AI conversations and integrates with Neo4j",
    version="1.0.0",
    lifespan=lifespan,
    max_request_size=50 * 1024 * 1024,  # 50MB limit for large conversation captures
)

# TODO: Refactor - LinearSync moved to InGest as single ingress point
# sync_engine = LinearSync()
sync_engine = None

# Inject percolate function into capture router
set_percolate_function(percolate_to_neo4j_with_embedding)

# Register routers
app.include_router(capture_router)
app.include_router(terminal_router)
app.include_router(linear_receiver.router, tags=["Linear Ingest"])
app.include_router(github_receiver.router, tags=["GitHub Ingest"])

# Validation API Gateway (TN-CORE-102)
from omega_kg.routers.validation import router as validation_router

app.include_router(validation_router, tags=["Validation API"])

from omega_kg.routers import telemetry
from omega_kg.routers import auth

app.include_router(telemetry.router)
app.include_router(auth.router)

# Service Control (Subprocess Management)
from omega_kg.routers.service_control import router as service_control_router

app.include_router(service_control_router)
app.include_router(guardian_router)

from omega_kg.routers.log_summary import router as log_summary_router

app.include_router(log_summary_router)


# CORS middleware
cors_origins = []
if settings.chrome_extension_id:
    cors_origins.append(f"chrome-extension://{settings.chrome_extension_id}")
else:
    # Allow any chrome-extension origin if extension ID not configured (development mode)
    cors_origins.append("chrome-extension://*")
# Allow localhost for development (Backend)
cors_origins.extend(["http://localhost:8765", "http://127.0.0.1:8765"])
# Allow CortexBridge Frontend (Vite Dev & Preview)
cors_origins.extend(
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:6001",
        "http://127.0.0.1:6001",
    ]
)
# Allow Tailscale access (Hybrid Architecture - Desktop as Central Brain)
cors_origins.extend(
    [
        "http://sigma-desktop:8765",  # Tailscale hostname
        "http://sigma-desktop:5173",  # Cortex via Tailscale
        "http://100.*",  # Tailscale IP range (100.x.x.x)
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, OPTIONS, PUT, DELETE)
    allow_headers=["*"],  # Allow all headers
)


# --- Root Endpoint ---
@app.get("/")
async def root():
    return {
        "service": "Omega_KG Capture Server",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "capture": "POST /capture",
            "health": "GET /health",
            "obsidian_update": "POST /obsidian-update",
            "linear_webhook": "POST /webhooks/linear",
            "github_webhook": "POST /webhooks/github",
        },
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


# --- Obsidian Update Endpoint ---
@app.post("/obsidian-update")
async def obsidian_update_endpoint(
    data: ObsidianUpdateRequest,
) -> ObsidianUpdateResponse:
    """
    Sync an Obsidian note to Linear.

    This endpoint is triggered by the Obsidian client to create or update
    a Linear issue based on the note content. The SmartParser handles parsing
    tags, assignees, labels, and priority from the note content.

    Args:
        data: ObsidianUpdateRequest with note_path

    Returns:
        ObsidianUpdateResponse with Linear ticket ID and URL

    Raises:
        HTTPException: 500 if sync fails
    """
    logger.info(f"Received Obsidian update request for: {data.note_path}")

    try:
        # Initialize SmartParser and sync note
        parser = SmartParser()
        result = await parser.sync_note_to_linear(data.note_path)

        if result is None:
            logger.error(f"Failed to sync note: {data.note_path}")
            raise HTTPException(
                status_code=500,
                detail="Failed to sync note to Linear - parser returned None (check LINEAR_TEAM_ID configuration and note content)",
            )

        # Extract Linear issue details from result
        linear_id = result.get("id")
        linear_identifier = result.get("identifier")
        linear_url = result.get("url")

        logger.info(
            f"Successfully synced {data.note_path} to Linear issue {linear_identifier}"
        )

        return ObsidianUpdateResponse(
            success=True,
            linear_id=linear_id,
            linear_identifier=linear_identifier,
            linear_url=linear_url,
            message=f"Successfully synced to Linear issue {linear_identifier}",
        )

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error syncing note to Linear: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# NOTE: Linear webhook endpoint moved to omega_kg/routers/linear_receiver.py
# This uses the newer "dumb and fast" pattern at /webhooks/linear (plural)
# The old /webhook/linear (singular) endpoint has been removed to avoid conflicts


# --- Main Entry Point ---
def main():
    """Starts the Omega_KG Capture Server using Uvicorn."""
    import os

    import uvicorn

    logger.info("Starting Omega_KG Capture Server...")
    logger.info(f"Server: {settings.app_host}:{settings.app_port}")
    logger.info(f"Vault path: {settings.obsidian_vault_path}")
    logger.info(f"Neo4j URI: {settings.neo4j_uri}")
    logger.info(f"Extension ID: {settings.chrome_extension_id}")

    # Start ngrok tunnel if enabled (optional, won't crash server if fails)
    if _ngrok_available:
        try:
            enable_ngrok = os.getenv("ENABLE_NGROK", "false").lower() == "true"
            if enable_ngrok:
                logger.info("🚀 Ngrok tunnel enabled - starting tunnel...")
                try:
                    import asyncio
                    import threading

                    def start_tunnel():
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            tunnel_url = loop.run_until_complete(
                                ngrok_tunnel.start_tunnel(port=settings.app_port)
                            )
                            if tunnel_url:
                                logger.info(f"[OK] Ngrok tunnel active: {tunnel_url}")
                                logger.info(
                                    f"📡 Linear webhook URL: {tunnel_url}/webhook/linear"
                                )
                                logger.info(
                                    "💡 Update your Linear webhook to use this URL"
                                )
                            else:
                                logger.warning("⚠️ Failed to start ngrok tunnel")
                        except Exception as e:
                            logger.error(f"[ERROR] Error starting ngrok tunnel: {e}")
                            logger.info(
                                "Continuing without ngrok (webhook testing will not work)"
                            )

                    # Start ngrok in background thread so it doesn't block server startup
                    tunnel_thread = threading.Thread(target=start_tunnel, daemon=True)
                    tunnel_thread.start()
                    logger.info("Ngrok tunnel starting in background...")
                except Exception as e:
                    logger.warning(f"Ngrok tunnel error: {e}")
                    logger.info("Continuing without ngrok...")
            else:
                logger.info("Ngrok tunnel disabled (set ENABLE_NGROK=true to enable)")
        except Exception as e:
            logger.warning(f"Error checking ngrok configuration: {e}")
    else:
        logger.info("Ngrok integration not available (ngrok_tunnel module not found)")

    uvicorn.run(
        "omega_kg.capture_server:app",
        host=settings.app_host,
        port=settings.app_port,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
