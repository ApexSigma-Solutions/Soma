"""
Graph Parser API Endpoint for CortexBridge InGest-LLMs Engine.

Provides REST API endpoint for parsing text into Knowledge Graphs
using DocumentParser with Spacy Transformers and NLTK.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from fastapi import (
    APIRouter,
    HTTPException,
    UploadFile,
    File as FastAPIFile,
    Form,
    File,
)
from pydantic import BaseModel, Field

from ingest_llm_as.parsers.document_parser import DocumentParser, ExtractionMode
from ingest_llm_as.services.file_loader_service import FileLoaderService
from src.shared.pulse_emitter import get_pulse_emitter
from src.shared.system_health import SystemHealth

logger = logging.getLogger(__name__)

# Create router for graph parser endpoints
router = APIRouter(prefix="/graph", tags=["Graph Parser"])

# Parser cache: model_name -> DocumentParser instance
_parsers: Dict[str, DocumentParser] = {}


class ParseRequest(BaseModel):
    """Request model for text parsing."""

    text: str = Field(..., description="Text content to parse")
    extraction_mode: Optional[ExtractionMode] = Field(
        default=ExtractionMode.NER_ONLY,
        description="Entity extraction mode (ner_only, svo, hybrid)",
    )
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Optional configuration for parsing behavior"
    )


class ParseResponse(BaseModel):
    """Response model containing parsed Knowledge Graph."""

    metadata: Dict[str, Any] = Field(description="Metadata about the parsing operation")
    nodes: list[Dict[str, Any]] = Field(
        description="List of extracted nodes (entities)"
    )
    edges: list[Dict[str, Any]] = Field(
        description="List of extracted relationships (edges)"
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(description="Service status")
    model_loaded: bool = Field(description="Whether NLP model is loaded")
    model_name: str = Field(description="Name of loaded Spacy model")


def get_parser(model_name: str | None = None) -> DocumentParser:
    """
    Get or create parser instance for the specified model.
    Defaults to 'en_core_web_sm' if not specified or available.

    Args:
        model_name: Specific spacy model name (e.g., 'en_core_web_trf')

    Returns:
        DocumentParser instance
    """
    global _parsers

    # Default fallback
    target_model = model_name or "en_core_web_sm"

    if target_model not in _parsers:
        try:
            logger.info(f"Initializing DocumentParser with model: {target_model}")
            parser = DocumentParser(model_name=target_model)
            _parsers[target_model] = parser
            logger.info(f"DocumentParser ({target_model}) initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize parser for {target_model}: {e}")
            # Fallback to existing if any
            if _parsers:
                fallback = next(iter(_parsers.values()))
                logger.warning(f"Falling back to loaded parser: {fallback.model_name}")
                return fallback
            raise RuntimeError(f"Parser initialization failed: {e}")

    return _parsers[target_model]


@router.post("/parse", response_model=ParseResponse, tags=["nlp", "graph"])
async def parse_text(request: ParseRequest) -> ParseResponse:
    """
    Parse text into a Knowledge Graph structure.

    Args:
        request: ParseRequest containing text and optional config.
                 Config can contain 'model_name'.

    Returns:
        ParseResponse with nodes and edges
    """
    try:
        model_name = request.config.get("model_name")
        parser = get_parser(model_name)

        text_length = len(request.text)
        logger.info(
            "Parsing text (%s chars) with model %s", text_length, parser.model_name
        )

        # Warn about large documents
        if text_length > 50000:
            logger.warning(
                f"Large document detected ({text_length} chars). "
                "This may take 30+ seconds. Consider chunking."
            )

        # Parse text using DocumentParser with specified mode
        extraction_mode = request.extraction_mode or ExtractionMode.NER_ONLY
        result = await parser.parse(request.text, extraction_mode=extraction_mode)

        # Add processing time warning to metadata if document is large
        if text_length > 10000:
            result["metadata"]["warning"] = (
                f"Large document ({text_length} chars) - "
                "processing may take 10-30s. Increase client timeout if needed."
            )

        result["metadata"]["model_used"] = parser.model_name

        logger.info(
            "✅ Parsed into %s nodes and %s edges",
            len(result["nodes"]),
            len(result["edges"]),
        )

        return ParseResponse(
            metadata=result["metadata"],
            nodes=result["nodes"],
            edges=result["edges"],
        )

    except Exception as e:
        logger.error("❌ Parsing failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")


@router.post(
    "/parse/file", response_model=ParseResponse, tags=["nlp", "graph", "file-upload"]
)
async def parse_file(
    file: UploadFile = FastAPIFile(
        ..., description="Document file to parse (TXT, MD, PDF, DOCX)"
    ),
    model_name: str = Form(
        None, description="Spacy model to use (e.g., en_core_web_trf)"
    ),
    extraction_mode: ExtractionMode = Form(
        ExtractionMode.NER_ONLY,
        description="Entity extraction mode (ner_only, svo, hybrid)",
    ),
) -> ParseResponse:
    """
    Parse uploaded file into a Knowledge Graph structure.

    Args:
        file: Uploaded file object
        model_name: Optional model selection (Form field)

    Returns:
        ParseResponse with nodes and edges
    """
    try:
        # Read file content
        content_bytes = await file.read()
        filename = file.filename or "unknown"

        logger.info(
            f"Processing uploaded file: {filename} ({len(content_bytes)} bytes) Model: {model_name}"
        )

        # Rewind file for FileLoaderService if used
        await file.seek(0)

        # Use new FileLoaderService to extract text
        try:
            # Re-wrap bytes not trivial, rely on FileLoaderService taking UploadFile
            # Since we read it, we must seek(0) which we did.
            extracted_text = await FileLoaderService.process_file(file)
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            raise HTTPException(status_code=422, detail=f"Text extraction failed: {e}")

        if not extracted_text or not extracted_text.strip():
            raise HTTPException(
                status_code=422,
                detail=f"Could not extract text from file '{filename}'.",
            )

        text_length = len(extracted_text)
        logger.info("Extracted %s characters from %s", text_length, filename)

        # Parse extracted text
        parser = get_parser(model_name)

        if text_length > 50000:
            logger.warning(
                f"Large document detected ({text_length} chars). "
                "This may take 30+ seconds. Consider chunking."
            )

        result = await parser.parse(extracted_text, extraction_mode=extraction_mode)

        # Add filename to metadata
        result["metadata"]["source_file"] = filename
        result["metadata"]["file_size_bytes"] = len(content_bytes)
        result["metadata"]["extracted_text_length"] = text_length
        result["metadata"]["model_used"] = parser.model_name

        # Add processing time warning if document is large
        if text_length > 10000:
            result["metadata"]["warning"] = (
                f"Large document ({text_length} chars) - "
                "processing may take 10-30s. Increase client timeout if needed."
            )

        logger.info(
            "✅ Parsed %s into %s nodes and %s edges",
            filename,
            len(result["nodes"]),
            len(result["edges"]),
        )

        return ParseResponse(
            metadata=result["metadata"],
            nodes=result["nodes"],
            edges=result["edges"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ File parsing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File parsing failed: {str(e)}")


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    Checks status of default/active parsers.
    """
    try:
        # Check if any parser is loaded, or try to load default
        parser = get_parser()  # Defaults to sm if none

        model_loaded = parser.nlp is not None
        status = "ready" if model_loaded else "error"

        return HealthResponse(
            status=status,
            model_loaded=model_loaded,
            model_name=parser.model_name if model_loaded else "not_loaded",
        )

    except Exception as e:
        logger.error("❌ Health check failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.post("/upload/digest")
async def digest_document(file: UploadFile = File(...), persist: bool = Form(False)):
    """
    1. Checks System Health (Metal).
    2. Digests File (Stomach).
    3. Emits Pulse event (Nervous System).
    4. Returns Text (Nutrients).
    """

    # 1. Check Metal
    if not SystemHealth.is_healthy():
        raise HTTPException(
            status_code=503,
            detail="System Overloaded. RAM usage too high for ingestion.",
        )

    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    filename = file.filename or "unknown"
    file_size_kb = round(file.size / 1024, 2) if file.size else 0

    # 2. Digest with timing
    start_time = time.perf_counter()
    try:
        await file.seek(0)
        raw_text = await FileLoaderService.process_file(file)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    duration_seconds = round(time.perf_counter() - start_time, 3)

    # 3. Emit Pulse (Gastric Signaling)
    vitals = SystemHealth.check_vitals()
    pulse = get_pulse_emitter()
    try:
        pulse.emit_digestion_complete(
            filename=filename,
            duration_seconds=duration_seconds,
            ram_percent=vitals.get("ram_percent", 0),
            model="FileLoaderService",  # This endpoint uses FileLoaderService
            file_size_kb=file_size_kb,
            character_count=len(raw_text),
        )
        logger.info(f"🫀 Pulse emitted for {filename} digestion complete")
    except Exception as pulse_error:
        # Pulse failure should not break the main flow
        logger.warning(f"⚠️ Failed to emit pulse for {filename}: {pulse_error}")

    # 4. Response
    return {
        "status": "success",
        "filename": filename,
        "file_size_kb": file_size_kb,
        "system_vitals": vitals,
        "character_count": len(raw_text),
        "preview": raw_text[:500] + "...",
        "processing_duration_sec": duration_seconds,
    }
