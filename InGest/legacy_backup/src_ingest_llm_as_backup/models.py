"""
Pydantic models for the InGest-LLM.as ingestion pipeline.

This module defines the data models used for:
- Ingestion requests and responses
- Integration with memOS.as
- Validation and error handling
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class ContentType(str, Enum):
    """Supported content types for ingestion."""

    TEXT = "text"
    CODE = "code"
    DOCUMENTATION = "documentation"
    MARKDOWN = "markdown"
    JSON = "json"


class SourceType(str, Enum):
    """Source types for ingested content."""

    MANUAL = "manual"
    API = "api"
    UPLOAD = "upload"
    WEB_SCRAPE = "web_scrape"
    REPOSITORY = "repository"


class IngestionMetadata(BaseModel):
    """Metadata associated with ingested content."""

    source: SourceType
    content_type: ContentType
    source_url: Optional[str] = Field(
        None, description="Original URL or path if applicable"
    )
    author: Optional[str] = Field(None, description="Content author if known")
    title: Optional[str] = Field(None, description="Content title or identifier")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @field_validator("tags")
    def validate_tags(cls, v):
        """Ensure tags are non-empty strings."""
        return [tag.strip() for tag in v if tag and tag.strip()]


class IngestionRequest(BaseModel):
    """Request model for text ingestion."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=1_000_000,
        description="Content to ingest",
    )
    metadata: IngestionMetadata
    chunk_size: Optional[int] = Field(
        None, ge=100, le=10000, description="Optional chunking size"
    )
    process_async: bool = Field(False, description="Whether to process asynchronously")

    @field_validator("content")
    def validate_content(cls, v):
        """Ensure content is not empty after stripping."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Content cannot be empty or whitespace only")
        return stripped


class MemoryTier(str, Enum):
    """Memory tiers in memOS.as."""

    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryStorageRequest(BaseModel):
    """Request model for storing data in memOS.as memory system."""

    content: str
    memory_tier: MemoryTier
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    relationships: List[Dict[str, Any]] = Field(default_factory=list)


class MemoryStorageResponse(BaseModel):
    """Response from memOS.as memory storage."""

    success: bool
    tier: int
    message: str
    memory_id: Optional[int] = None  # Optional, sometimes not returned

    @property
    def memory_tier(self) -> MemoryTier:
        """Convert numeric tier to MemoryTier enum."""
        tier_mapping = {
            1: MemoryTier.WORKING,
            # Align tier 2 to PROCEDURAL to match current memOS/InGest routing
            2: MemoryTier.PROCEDURAL,
            3: MemoryTier.SEMANTIC,
        }
        return tier_mapping.get(self.tier, MemoryTier.SEMANTIC)


class ProcessingStatus(str, Enum):
    """Status of ingestion processing."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestionResult(BaseModel):
    """Individual ingestion result for content chunk."""

    chunk_id: UUID = Field(default_factory=uuid4)
    memory_id: Optional[int] = (
        None  # Changed from UUID to int to match memOS.as response
    )
    memory_tier: MemoryTier
    content_hash: str
    chunk_size: int
    status: ProcessingStatus
    error_message: Optional[str] = None


class IngestionResponse(BaseModel):
    """Response model for ingestion requests."""

    ingestion_id: UUID = Field(default_factory=uuid4)
    status: ProcessingStatus
    total_chunks: int = Field(ge=1)
    results: List[IngestionResult] = Field(default_factory=list)
    processing_time_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    message: str = Field(default="Ingestion initiated successfully")

    # Rely on Pydantic/FastAPI default serialization for UUID and datetime


class ValidationError(BaseModel):
    """Validation error details."""

    field: str
    message: str
    value: Any = None


class IngestionError(BaseModel):
    """Error response for ingestion failures."""

    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    validation_errors: List[ValidationError] = Field(default_factory=list)
    ingestion_id: Optional[UUID] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Rely on Pydantic/FastAPI default serialization for UUID and datetime


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = "ok"
    service: str = "InGest-LLM.as"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dependencies: Dict[str, Any] = Field(default_factory=dict)
    metrics_enabled: Optional[bool] = None
    tracing_enabled: Optional[bool] = None
    logging_structured: Optional[bool] = None

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}


# Repository Ingestion Models


class RepositorySource(str, Enum):
    """Source types for repository ingestion."""

    LOCAL_PATH = "local_path"
    GIT_URL = "git_url"
    GITHUB_URL = "github_url"
    UPLOADED_ZIP = "uploaded_zip"


class RepositoryIngestionRequest(BaseModel):
    """Request model for Python repository ingestion."""

    repository_source: RepositorySource
    source_path: str = Field(
        ...,
        description="Path to local directory, Git URL, or GitHub repository",
    )
    include_patterns: List[str] = Field(
        default=["**/*.py"], description="Glob patterns for files to include"
    )
    exclude_patterns: List[str] = Field(
        default=[
            "**/__pycache__/**",
            "**/.git/**",
            "**/venv/**",
            "**/env/**",
            "**/.venv/**",
            "**/node_modules/**",
            "**/*.pyc",
            "**/.pytest_cache/**",
            "**/build/**",
            "**/dist/**",
            "**/.tox/**",
        ],
        description="Glob patterns for files/directories to exclude",
    )
    max_file_size: int = Field(
        default=1_000_000,  # 1MB
        ge=1,
        le=10_000_000,  # 10MB max
        description="Maximum file size in bytes",
    )
    max_files: int = Field(
        default=1000,
        ge=1,
        le=5000,
        description="Maximum number of files to process",
    )
    process_async: bool = Field(
        default=True,
        description="Whether to process repository asynchronously",
    )
    metadata: IngestionMetadata

    @field_validator("source_path")
    def validate_source_path(cls, v, values):
        """Validate the source path based on repository source."""
        repository_source = values.data.get("repository_source")

        if repository_source == RepositorySource.LOCAL_PATH:
            # Validate local path exists
            path = Path(v)
            if not path.exists():
                raise ValueError(f"Local path does not exist: {v}")
            if not path.is_dir():
                raise ValueError(f"Path is not a directory: {v}")

        elif repository_source in [
            RepositorySource.GIT_URL,
            RepositorySource.GITHUB_URL,
        ]:
            # Basic URL validation
            if not v.startswith(("http://", "https://", "git://")):
                raise ValueError(f"Invalid URL format: {v}")

        return v

    @field_validator("include_patterns")
    def validate_include_patterns(cls, v):
        """Ensure at least one include pattern."""
        if not v:
            raise ValueError("At least one include pattern is required")
        return v


class FileProcessingResult(BaseModel):
    """Result of processing a single file."""

    file_path: str
    relative_path: str
    file_size: int
    status: ProcessingStatus
    elements_extracted: int = 0
    chunks_created: int = 0
    embeddings_generated: int = 0
    processing_time_ms: int = 0
    complexity_score: float = 0.0
    error_message: Optional[str] = None
    memory_ids: List[UUID] = Field(default_factory=list)


class RepositoryProcessingSummary(BaseModel):
    """Summary of repository processing results."""

    total_files_found: int
    total_files_processed: int
    total_files_skipped: int
    total_files_failed: int

    total_elements_extracted: int
    total_chunks_created: int
    total_embeddings_generated: int

    total_processing_time_ms: int
    average_complexity: float

    file_type_distribution: Dict[str, int] = Field(default_factory=dict)
    element_type_distribution: Dict[str, int] = Field(default_factory=dict)

    largest_files: List[Dict[str, Any]] = Field(default_factory=list)
    most_complex_files: List[Dict[str, Any]] = Field(default_factory=list)

    processing_errors: List[str] = Field(default_factory=list)


class RepositoryIngestionResponse(BaseModel):
    """Response model for repository ingestion requests."""

    ingestion_id: UUID = Field(default_factory=uuid4)
    repository_path: str
    status: ProcessingStatus

    # File discovery results
    files_discovered: int = 0
    files_to_process: int = 0

    # Processing results (populated when complete)
    files_processed: List[FileProcessingResult] = Field(default_factory=list)
    processing_summary: Optional[RepositoryProcessingSummary] = None

    # Timing information
    discovery_time_ms: int = 0
    processing_time_ms: Optional[int] = None
    total_time_ms: Optional[int] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    message: str = Field(default="Repository ingestion initiated")

    # Rely on Pydantic/FastAPI default serialization for UUID and datetime


class RepositoryAnalysisRequest(BaseModel):
    """Request for analyzing an already ingested repository."""

    ingestion_id: UUID
    analysis_type: str = Field(
        default="comprehensive",
        pattern="^(summary|complexity|dependencies|comprehensive)$",
    )


class RepositoryAnalysisResponse(BaseModel):
    """Response for repository analysis."""

    ingestion_id: UUID
    analysis_type: str

    # Code structure analysis
    total_lines_of_code: int = 0
    code_to_comment_ratio: float = 0.0
    average_function_complexity: float = 0.0

    # Architecture insights
    module_dependencies: Dict[str, List[str]] = Field(default_factory=dict)
    class_hierarchy: Dict[str, List[str]] = Field(default_factory=dict)

    # Quality metrics
    documentation_coverage: float = (
        0.0  # Percentage of functions/classes with docstrings
    )
    test_coverage_estimate: float = 0.0  # Based on test file presence

    # Recommendations
    optimization_suggestions: List[str] = Field(default_factory=list)
    refactoring_opportunities: List[str] = Field(default_factory=list)

    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # Rely on Pydantic/FastAPI default serialization for UUID and datetime
