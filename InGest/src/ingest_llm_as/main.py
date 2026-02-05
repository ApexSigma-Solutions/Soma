import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from .config import get_settings
from .models import HealthResponse
from .api.ingestion import router as ingestion_router
from .api.repository import router as repository_router
from .api.ecosystem import router as ecosystem_router
from .api.analysis import router as analysis_router
from .api.graph_parser import router as graph_parser_router
from .api.vitals import router as vitals_router
from .api.config import router as config_router  # TN-CTX-203: Config management

from .api.omega_ingest import router as omega_ingest_router

from .routers.eod_logs import router as eod_logs_router

# NOTE: webhook.py and webhook_forwarder.py disabled - moved to Soma.Ingress
# from .routers.webhook_forwarder import router as webhook_forwarder_router
# from .routers.webhook import router as webhook_router
from .observability.logging import get_logger
from ingest_llm_as.processors.conversation_ingestor import ConversationIngestor
from ingest_llm_as.processors.terminal_processor import TerminalProcessor

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup/shutdown of background tasks and resources.
    """
    # Startup
    logger.info("Initializing InGest-LLM services...")
    logger.info("SERVICE RELOAD TRIGGERED - TIMESTAMP: CHECK")

    settings = get_settings()
    logger.info(f"DEBUG: raw_db_url={settings.raw_db_url}")
    logger.info(f"DEBUG: neo4j_uri={settings.neo4j_uri}")

    # Track tasks
    app.state.bg_tasks = []

    try:
        # 1. Start Conversation Ingestor
        conv_ingestor = ConversationIngestor()
        app.state.bg_tasks.append(asyncio.create_task(conv_ingestor.start()))
        app.state.conv_ingestor = conv_ingestor

        # 2. Start Terminal Processor
        term_processor = TerminalProcessor()
        app.state.bg_tasks.append(asyncio.create_task(term_processor.start()))
        app.state.term_processor = term_processor

        logger.info("[WORKHORSE] InGest-LLM processors started.")
    except Exception as e:
        logger.error(f"CRITICAL STARTUP ERROR: {e}", exc_info=True)
        raise e

    yield

    # Shutdown
    logger.info("Shutting down InGest-LLM Workhorse services...")

    if hasattr(app.state, "conv_ingestor"):
        await app.state.conv_ingestor.stop()
    if hasattr(app.state, "term_processor"):
        await app.state.term_processor.stop()

    for task in app.state.bg_tasks:
        task.cancel()

    # Wait for all tasks to complete cancellation
    await asyncio.gather(*app.state.bg_tasks, return_exceptions=True)
    logger.info("Services stopped.")


def create_app() -> FastAPI:
    """Create the FastAPI application.

    Observability integrations are intentionally removed for now.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="A microservice for ingesting data into the ApexSigma ecosystem.",
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Configure CORS
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Cortex dev (legacy)
            "http://localhost:6001",  # Cortex (current)
            "http://127.0.0.1:6001",  # Cortex (IP)
            "http://localhost:3000",  # Alternative dev
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Include API routers
    app.include_router(ingestion_router)
    app.include_router(repository_router)
    app.include_router(ecosystem_router)
    app.include_router(analysis_router)
    app.include_router(graph_parser_router)
    app.include_router(vitals_router)
    app.include_router(config_router)  # TN-CTX-203: Configuration management
    app.include_router(omega_ingest_router)
    app.include_router(eod_logs_router)
    # NOTE: Webhook routers disabled - moved to Soma.Ingress on Port 8000
    # app.include_router(webhook_forwarder_router)
    # app.include_router(webhook_router)

    @app.get("/", response_model=dict)
    def read_root():
        """Root endpoint that returns a welcome message."""
        current = get_settings()
        return {
            "message": f"Welcome to the {current.app_name} service!",
            "version": current.app_version,
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/health", response_model=HealthResponse)
    def health_check():
        """Health check endpoint.

        Note: observability fields are intentionally omitted/disabled.
        """
        current = get_settings()
        return HealthResponse(
            service=current.app_name,
            version=current.app_version,
            dependencies={
                "memOS.as": f"configured: {current.memos_base_url}",
            },
        )

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("ingest_llm_as.main:app", host="127.0.0.1", port=8766, reload=True)
