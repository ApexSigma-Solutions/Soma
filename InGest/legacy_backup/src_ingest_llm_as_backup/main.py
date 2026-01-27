from fastapi import FastAPI

from .config import get_settings
from .models import HealthResponse
from .api.ingestion import router as ingestion_router
from .api.repository import router as repository_router
from .api.ecosystem import router as ecosystem_router
from .api.analysis import router as analysis_router
from .api.omega_ingest import router as omega_ingest_router

from .routers.eod_logs import router as eod_logs_router

from .observability.logging import get_logger


logger = get_logger(__name__)


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
    )

    # Include API routers
    app.include_router(ingestion_router)
    app.include_router(repository_router)
    app.include_router(ecosystem_router)
    app.include_router(analysis_router)
    app.include_router(omega_ingest_router)
    app.include_router(eod_logs_router)

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
