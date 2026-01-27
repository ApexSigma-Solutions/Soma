"""
Content processing utilities for text ingestion.

This module provides utilities for processing, chunking, and preparing
content for storage in the memOS.as memory system.
"""

import re
import logging
import time
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

from ..config import settings
from ..services.vectorizer import generate_content_embedding
from ..parsers.python_ast_parser import PythonASTParser
from ..observability.langfuse_client import get_langfuse_client

logger = logging.getLogger(__name__)


class ContentProcessor:
    """
    Handles content processing and chunking for ingestion.

    Provides methods to clean, validate, and chunk content
    for optimal storage in different memory tiers with embedding generation.
    """

    def __init__(self, chunk_size: int = None, enable_embeddings: bool = None):
        """
        Initialize content processor.

        Args:
            chunk_size: Maximum size for content chunks
            enable_embeddings: Whether to generate embeddings for content
        """
        self.chunk_size = chunk_size or settings.default_chunk_size
        self.max_chunk_size = 10000  # Hard limit
        self.min_chunk_size = 100  # Minimum viable chunk
        self.enable_embeddings = (
            enable_embeddings
            if enable_embeddings is not None
            else settings.embedding_enabled
        )

    def clean_content(self, content: str) -> str:
        """
        Clean and normalize content for processing.

        Args:
            content: Raw content string

        Returns:
            str: Cleaned content
        """
        # Strip whitespace
        cleaned = content.strip()

        # Normalize whitespace (multiple spaces/newlines to single)
        cleaned = re.sub(r"\s+", " ", cleaned)

        # Remove control characters except newlines and tabs
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", cleaned)

        return cleaned

    async def process_pdf_content(
        self, file_content: bytes, filename: str
    ) -> Dict[str, Any]:
        """
        Extract text from PDF content using PyMuPDF.

        Args:
            file_content: Raw PDF bytes
            filename: Original filename

        Returns:
            Dict containing processed content and metadata
        """
        import fitz  # PyMuPDF

        start_time = time.time()
        text_content = []
        metadata = {"page_count": 0, "author": "", "title": "", "subject": ""}

        try:
            with fitz.open(stream=file_content, filetype="pdf") as doc:
                metadata["page_count"] = len(doc)
                metadata.update(doc.metadata)

                for page in doc:
                    text_content.append(page.get_text())

            full_text = "\n\n".join(text_content)

            # Process as standard content
            return await self.process_content_with_embeddings(
                content=full_text, content_type="documentation", detected_type="pdf"
            )

        except Exception as e:
            logger.error(f"PDF processing failed for {filename}: {e}")
            raise ValueError(f"Failed to process PDF: {str(e)}")

    def chunk_content(self, content: str, chunk_size: int = None) -> List[str]:
        """
        Split content into optimally-sized chunks.

        Uses intelligent chunking that tries to preserve:
        - Sentence boundaries
        - Paragraph boundaries
        - Code block boundaries

        Args:
            content: Content to chunk
            chunk_size: Override default chunk size

        Returns:
            List[str]: List of content chunks
        """
        target_size = chunk_size or self.chunk_size

        # For small content, return as single chunk
        if len(content) <= target_size:
            return [content]

        chunks = []
        remaining = content

        while remaining and len(remaining) > target_size:
            # Find optimal split point
            chunk, remaining = self._find_optimal_split(remaining, target_size)

            if chunk:
                chunks.append(chunk.strip())

            # Safety check to prevent infinite loops
            if len(chunks) > settings.max_chunks_per_request:
                logger.warning(
                    f"Hit max chunks limit ({settings.max_chunks_per_request})"
                )
                break

        # Add final chunk if remaining content
        if remaining and remaining.strip():
            chunks.append(remaining.strip())

        return [chunk for chunk in chunks if len(chunk) >= self.min_chunk_size]

    def _find_optimal_split(self, content: str, target_size: int) -> Tuple[str, str]:
        """
        Find optimal split point for content chunking.

        Tries to split at natural boundaries in order of preference:
        1. Double newline (paragraph boundary)
        2. Single newline + sentence end
        3. Sentence boundary (. ! ?)
        4. Word boundary
        5. Character boundary (fallback)

        Args:
            content: Content to split
            target_size: Target chunk size

        Returns:
            Tuple[str, str]: (chunk, remaining_content)
        """
        if len(content) <= target_size:
            return content, ""

        # Define search window (look back from target size)
        search_start = max(0, target_size - 200)
        search_end = min(len(content), target_size + 100)
        search_text = content[search_start:search_end]

        # Try paragraph boundary first
        paragraph_matches = list(re.finditer(r"\n\s*\n", search_text))
        if paragraph_matches:
            split_pos = search_start + paragraph_matches[-1].end()
            return content[:split_pos], content[split_pos:]

        # Try sentence boundary at line end
        sentence_line_matches = list(re.finditer(r"[.!?]\s*\n", search_text))
        if sentence_line_matches:
            split_pos = search_start + sentence_line_matches[-1].end()
            return content[:split_pos], content[split_pos:]

        # Try sentence boundary
        sentence_matches = list(re.finditer(r"[.!?]\s+", search_text))
        if sentence_matches:
            split_pos = search_start + sentence_matches[-1].end()
            return content[:split_pos], content[split_pos:]

        # Try word boundary
        word_matches = list(re.finditer(r"\s+", search_text))
        if word_matches:
            split_pos = search_start + word_matches[-1].start()
            return content[:split_pos], content[split_pos:]

        # Fallback: hard split at target size
        return content[:target_size], content[target_size:]

    def extract_metadata_from_content(self, content: str) -> dict:
        """
        Extract implicit metadata from content structure.

        Args:
            content: Content to analyze

        Returns:
            dict: Extracted metadata
        """
        metadata = {}

        # Basic content statistics
        metadata["word_count"] = len(content.split())
        metadata["char_count"] = len(content)
        metadata["line_count"] = content.count("\n") + 1

        # Try to detect content patterns
        if self._looks_like_code(content):
            metadata["detected_type"] = "code"
        elif self._looks_like_markdown(content):
            metadata["detected_type"] = "markdown"
        elif self._looks_like_json(content):
            metadata["detected_type"] = "json"
        else:
            metadata["detected_type"] = "text"

        # Extract potential title (first line if it looks like a title)
        lines = content.split("\n")
        if lines:
            first_line = lines[0].strip()
            if (
                len(first_line) < 100
                and not first_line.endswith(".")
                and len(first_line.split()) <= 10
            ):
                metadata["potential_title"] = first_line

        return metadata

    def _looks_like_code(self, content: str) -> bool:
        """Check if content appears to be code."""
        code_indicators = [
            "def ",
            "function ",
            "class ",
            "import ",
            "from ",
            "#!/",
            "<?",
            "<!--",
            "{",
            "}",
            "()",
            "=>",
            "console.log",
            "print(",
            "System.out",
        ]
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in code_indicators)

    def _looks_like_markdown(self, content: str) -> bool:
        """Check if content appears to be Markdown."""
        md_indicators = ["# ", "## ", "### ", "- ", "* ", "```", "[", "]("]
        return any(indicator in content for indicator in md_indicators)

    def _looks_like_json(self, content: str) -> bool:
        """Check if content appears to be JSON."""
        stripped = content.strip()
        return (stripped.startswith("{") and stripped.endswith("}")) or (
            stripped.startswith("[") and stripped.endswith("]")
        )

    async def generate_embeddings_for_chunks(
        self, chunks: List[str], content_type: str, detected_type: str = None
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for content chunks using LM Studio.

        Implements TASK-IG-16: Integrate the vectorizer service into the main
        ingestion flow with live calls to local models.

        Args:
            chunks: List of content chunks to embed
            content_type: Content type for model selection
            detected_type: Auto-detected content type

        Returns:
            List[Optional[List[float]]]: Embeddings for each chunk (None if generation fails)
        """
        if not self.enable_embeddings or not settings.lm_studio_enabled:
            logger.debug("Embedding generation disabled, returning None embeddings")
            return [None] * len(chunks)

        embeddings = []

        for i, chunk in enumerate(chunks):
            try:
                embedding = await generate_content_embedding(
                    content=chunk,
                    content_type=content_type,
                    detected_type=detected_type,
                )
                embeddings.append(embedding)

                if embedding:
                    logger.debug(f"Generated embedding for chunk {i + 1}/{len(chunks)}")
                else:
                    logger.warning(
                        f"Failed to generate embedding for chunk {i + 1}/{len(chunks)}"
                    )

            except Exception as e:
                logger.error(f"Error generating embedding for chunk {i + 1}: {e}")
                embeddings.append(None)

        success_count = sum(1 for emb in embeddings if emb is not None)
        logger.info(f"Generated {success_count}/{len(chunks)} embeddings successfully")

        return embeddings

    async def process_content_with_embeddings(
        self, content: str, content_type: str, detected_type: str = None
    ) -> Dict[str, Any]:
        """
        Process content with chunking and embedding generation.

        Args:
            content: Raw content to process
            content_type: Content type for processing
            detected_type: Auto-detected content type

        Returns:
            Dict[str, Any]: Processing results with chunks and embeddings
        """
        # Clean and chunk content
        cleaned_content = self.clean_content(content)
        chunks = self.chunk_content(cleaned_content)

        # Extract metadata
        content_metadata = self.extract_metadata_from_content(cleaned_content)

        # Generate embeddings
        embeddings = await self.generate_embeddings_for_chunks(
            chunks=chunks,
            content_type=content_type,
            detected_type=detected_type or content_metadata.get("detected_type"),
        )

        return {
            "cleaned_content": cleaned_content,
            "chunks": chunks,
            "embeddings": embeddings,
            "content_metadata": content_metadata,
            "processing_stats": {
                "original_size": len(content),
                "cleaned_size": len(cleaned_content),
                "chunk_count": len(chunks),
                "embeddings_generated": sum(1 for emb in embeddings if emb is not None),
                "embedding_enabled": self.enable_embeddings,
            },
        }

    async def process_python_code_with_embeddings(
        self,
        source_code: str,
        file_path: Optional[str] = None,
        content_type: str = "code",
    ) -> Dict[str, Any]:
        """
        Process Python source code using AST parsing and generate embeddings.

        Args:
            source_code: Python source code to process
            file_path: Optional file path for context
            content_type: Content type (default: "code")

        Returns:
            Dict[str, Any]: Processing results with code elements and embeddings
        """
        langfuse_client = get_langfuse_client()
        start_time = time.time()

        # Create Langfuse trace for Python AST processing
        trace_id = None
        if langfuse_client.enabled:
            trace_id = langfuse_client.create_trace(
                name="python_ast_processing",
                metadata={
                    "file_path": file_path,
                    "content_type": content_type,
                    "source_length": len(source_code),
                    "source_lines": len(source_code.split("\n")),
                    "embedding_enabled": self.enable_embeddings,
                },
                tags=["ast", "python", "code_processing", content_type],
                input_data={
                    "file_path": file_path,
                    "content_type": content_type,
                    "source_length": len(source_code),
                    "source_lines": len(source_code.split("\n")),
                    "source_preview": source_code[:200] + "..."
                    if len(source_code) > 200
                    else source_code,
                },
            )

        try:
            # Parse Python code using AST parser
            ast_start_time = time.time()
            ast_parser = PythonASTParser()
            parsing_result = ast_parser.parse_source(source_code, file_path)
            ast_duration = time.time() - ast_start_time

            if not parsing_result.success:
                logger.warning(
                    f"AST parsing failed for {file_path or 'source'}: {parsing_result.errors}"
                )

                # Record AST parsing failure in Langfuse
                if langfuse_client.enabled and trace_id:
                    langfuse_client.client.trace(
                        id=trace_id,
                        output={
                            "ast_parsing_success": False,
                            "ast_errors": parsing_result.errors,
                            "fallback_to_text_processing": True,
                            "ast_duration_ms": int(ast_duration * 1000),
                        },
                    )

                    langfuse_client.score_trace(
                        trace_id=trace_id,
                        name="ast_parsing_success",
                        value=0.0,
                        comment=f"AST parsing failed: {parsing_result.errors}",
                    )

                # Fallback to regular text processing
                return await self.process_content_with_embeddings(
                    source_code, content_type
                )

            # Record successful AST parsing
            if langfuse_client.enabled and trace_id:
                langfuse_client.client.generation(
                    trace_id=trace_id,
                    name="ast_parsing",
                    model="python_ast_parser",
                    input={
                        "source_code_length": len(source_code),
                        "file_path": file_path,
                    },
                    output={
                        "elements_extracted": parsing_result.element_count,
                        "function_count": parsing_result.function_count,
                        "class_count": parsing_result.class_count,
                        "total_lines": parsing_result.total_lines,
                        "processing_time_ms": parsing_result.processing_time_ms,
                    },
                )

            # Convert code elements to searchable content chunks
            chunking_start_time = time.time()
            code_chunks = []
            code_elements_metadata = []

            for element in parsing_result.elements:
                # Generate searchable content for the element
                searchable_content = element.to_searchable_content()
                code_chunks.append(searchable_content)

                # Create metadata for this code element
                element_metadata = {
                    "element_type": element.element_type.value,
                    "name": element.name,
                    "qualified_name": element.qualified_name,
                    "line_start": element.line_start,
                    "line_end": element.line_end,
                    "complexity_score": element.complexity_score,
                    "decorators": element.decorators,
                    "parent_class": element.parent_class,
                    "dependencies": element.dependencies,
                    "tags": list(element.tags),
                    "content_hash": element.content_hash,
                    "has_docstring": bool(element.docstring),
                    "signature": element.signature,
                }
                code_elements_metadata.append(element_metadata)

            chunking_duration = time.time() - chunking_start_time

            # Generate embeddings for code elements
            embedding_start_time = time.time()
            embeddings = await self.generate_embeddings_for_chunks(
                chunks=code_chunks,
                content_type="code",  # Use "code" type for embedding model selection
                detected_type="python",
            )
            embedding_duration = time.time() - embedding_start_time

            # Calculate processing statistics
            total_elements = len(parsing_result.elements)
            function_count = len(
                [
                    e
                    for e in parsing_result.elements
                    if "function" in e.element_type.value
                ]
            )
            class_count = len(
                [e for e in parsing_result.elements if e.element_type.value == "class"]
            )
            total_duration = time.time() - start_time

            # Record comprehensive processing results in Langfuse
            if langfuse_client.enabled and trace_id:
                langfuse_client.client.trace(
                    id=trace_id,
                    output={
                        "success": True,
                        "ast_parsing_success": True,
                        "total_elements": total_elements,
                        "function_count": function_count,
                        "class_count": class_count,
                        "total_lines": parsing_result.total_lines,
                        "chunks_generated": len(code_chunks),
                        "embeddings_generated": sum(
                            1 for emb in embeddings if emb is not None
                        ),
                        "processing_times": {
                            "ast_duration_ms": int(ast_duration * 1000),
                            "chunking_duration_ms": int(chunking_duration * 1000),
                            "embedding_duration_ms": int(embedding_duration * 1000),
                            "total_duration_ms": int(total_duration * 1000),
                        },
                        "efficiency_metrics": {
                            "elements_per_second": total_elements / total_duration
                            if total_duration > 0
                            else 0,
                            "lines_per_second": parsing_result.total_lines
                            / total_duration
                            if total_duration > 0
                            else 0,
                            "chars_per_second": len(source_code) / total_duration
                            if total_duration > 0
                            else 0,
                        },
                    },
                )

                # Score AST parsing success
                langfuse_client.score_trace(
                    trace_id=trace_id,
                    name="ast_parsing_success",
                    value=1.0,
                    comment=f"Successfully extracted {total_elements} elements from Python code",
                )

                # Score processing efficiency
                elements_per_second = (
                    total_elements / total_duration if total_duration > 0 else 0
                )
                efficiency_score = min(
                    1.0, elements_per_second / 10
                )  # Normalize to reasonable processing speed

                langfuse_client.score_trace(
                    trace_id=trace_id,
                    name="python_processing_efficiency",
                    value=efficiency_score,
                    comment=f"Processing: {elements_per_second:.1f} elements/s, {total_elements} total elements",
                )

                # Track code complexity insights
                avg_complexity = (
                    sum(e.complexity_score for e in parsing_result.elements)
                    / total_elements
                    if total_elements > 0
                    else 0
                )
                complexity_score = max(
                    0.0, min(1.0, 1.0 - (avg_complexity / 20))
                )  # Inverse complexity score

                langfuse_client.score_trace(
                    trace_id=trace_id,
                    name="code_complexity_score",
                    value=complexity_score,
                    comment=f"Average complexity: {avg_complexity:.1f}, Max complexity detected",
                )

            return {
                "cleaned_content": source_code,  # Keep original source for code
                "chunks": code_chunks,
                "embeddings": embeddings,
                "code_elements": parsing_result.elements,
                "code_elements_metadata": code_elements_metadata,
                "parsing_result": {
                    "success": parsing_result.success,
                    "total_elements": total_elements,
                    "function_count": function_count,
                    "class_count": class_count,
                    "total_lines": parsing_result.total_lines,
                    "processing_time_ms": parsing_result.processing_time_ms,
                    "errors": parsing_result.errors,
                    "warnings": parsing_result.warnings,
                },
                "content_metadata": {
                    "detected_type": "python",
                    "file_path": file_path,
                    "total_elements": total_elements,
                    "function_count": function_count,
                    "class_count": class_count,
                },
                "processing_stats": {
                    "original_size": len(source_code),
                    "cleaned_size": len(source_code),
                    "chunk_count": len(code_chunks),
                    "embeddings_generated": sum(
                        1 for emb in embeddings if emb is not None
                    ),
                    "embedding_enabled": self.enable_embeddings,
                    "ast_parsing_success": parsing_result.success,
                    "total_duration_ms": int(total_duration * 1000),
                    "ast_duration_ms": int(ast_duration * 1000),
                    "embedding_duration_ms": int(embedding_duration * 1000),
                },
            }

        except Exception as e:
            logger.error(f"Error in Python code processing: {e}")

            # Record processing error in Langfuse
            if langfuse_client.enabled and trace_id:
                langfuse_client.client.trace(
                    id=trace_id,
                    output={
                        "success": False,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "fallback_to_text_processing": True,
                        "duration_before_error_ms": int(
                            (time.time() - start_time) * 1000
                        ),
                    },
                )

                langfuse_client.score_trace(
                    trace_id=trace_id,
                    name="python_processing_efficiency",
                    value=0.0,
                    comment=f"Processing failed: {str(e)}",
                )

            # Fallback to regular text processing
            return await self.process_content_with_embeddings(source_code, content_type)

    def detect_content_type(self, content: str, file_path: Optional[str] = None) -> str:
        """
        Detect content type from content and file path.

        Args:
            content: Content to analyze
            file_path: Optional file path for extension-based detection

        Returns:
            str: Detected content type
        """
        langfuse_client = get_langfuse_client()
        start_time = time.time()

        # Create Langfuse trace for content type detection
        trace_id = None
        if langfuse_client.enabled:
            trace_id = langfuse_client.create_trace(
                name="content_type_detection",
                metadata={
                    "file_path": file_path,
                    "content_length": len(content),
                    "has_file_path": file_path is not None,
                    "detection_strategy": "hybrid_file_extension_and_content",
                },
                tags=["content_detection", "type_classification"],
                input_data={
                    "file_path": file_path,
                    "content_length": len(content),
                    "content_preview": content[:100] + "..."
                    if len(content) > 100
                    else content,
                },
            )

        detected_type = "text"  # Default
        detection_method = "default"
        confidence_score = 0.3
        indicators_found = []

        # File extension based detection
        if file_path:
            file_path_lower = file_path.lower()
            if file_path_lower.endswith(".py"):
                detected_type = "python"
                detection_method = "file_extension"
                confidence_score = 0.9
                indicators_found.append("python_extension")
            elif file_path_lower.endswith((".md", ".markdown")):
                detected_type = "markdown"
                detection_method = "file_extension"
                confidence_score = 0.9
                indicators_found.append("markdown_extension")
            elif file_path_lower.endswith((".json",)):
                detected_type = "json"
                detection_method = "file_extension"
                confidence_score = 0.9
                indicators_found.append("json_extension")
            elif file_path_lower.endswith((".txt",)):
                detected_type = "text"
                detection_method = "file_extension"
                confidence_score = 0.8
                indicators_found.append("text_extension")

        # Content-based detection (if no file extension match or low confidence)
        if confidence_score < 0.8:
            content_lower = content.lower().strip()

            # Check for Python code patterns
            python_indicators = [
                "def ",
                "class ",
                "import ",
                "from ",
                "__init__",
                "if __name__",
                "print(",
                "self.",
                "return ",
                "yield ",
            ]
            python_matches = [ind for ind in python_indicators if ind in content_lower]
            if python_matches:
                detected_type = "python"
                detection_method = "content_analysis"
                confidence_score = min(0.9, 0.5 + len(python_matches) * 0.1)
                indicators_found.extend(python_matches)

            # Check for JSON
            elif content_lower.startswith(("{", "[")):
                try:
                    import json

                    json.loads(content)
                    detected_type = "json"
                    detection_method = "content_validation"
                    confidence_score = 0.95
                    indicators_found.append("valid_json_structure")
                except json.JSONDecodeError:
                    indicators_found.append("json_like_start_but_invalid")

            # Check for Markdown
            elif any(
                pattern in content for pattern in ["# ", "## ", "### ", "```", "*", "-"]
            ):
                markdown_patterns = ["# ", "## ", "### ", "```", "*", "-"]
                markdown_matches = [p for p in markdown_patterns if p in content]
                if markdown_matches:
                    detected_type = "markdown"
                    detection_method = "content_analysis"
                    confidence_score = min(0.8, 0.4 + len(markdown_matches) * 0.1)
                    indicators_found.extend(markdown_matches)

        detection_duration = time.time() - start_time

        # Record detection results in Langfuse
        if langfuse_client.enabled and trace_id:
            langfuse_client.client.trace(
                id=trace_id,
                output={
                    "detected_type": detected_type,
                    "detection_method": detection_method,
                    "confidence_score": confidence_score,
                    "indicators_found": indicators_found,
                    "detection_duration_ms": int(detection_duration * 1000),
                    "file_extension_used": file_path is not None,
                    "content_analysis_performed": detection_method
                    in ["content_analysis", "content_validation"],
                },
            )

            # Score detection confidence
            langfuse_client.score_trace(
                trace_id=trace_id,
                name="content_type_confidence",
                value=confidence_score,
                comment=f"Detected {detected_type} using {detection_method} with {len(indicators_found)} indicators",
            )

            # Score detection method effectiveness
            method_score = (
                1.0
                if detection_method == "file_extension"
                else 0.8
                if detection_method == "content_validation"
                else 0.6
            )
            langfuse_client.score_trace(
                trace_id=trace_id,
                name="detection_method_reliability",
                value=method_score,
                comment=f"Method: {detection_method}, Confidence: {confidence_score:.2f}",
            )

        return detected_type


def create_ingestion_metadata(
    original_metadata: dict,
    chunk_index: int = 0,
    total_chunks: int = 1,
    processing_info: dict = None,
) -> dict:
    """
    Create comprehensive metadata for memory storage.

    Args:
        original_metadata: Original request metadata
        chunk_index: Index of this chunk (0-based)
        total_chunks: Total number of chunks
        processing_info: Additional processing information

    Returns:
        dict: Complete metadata for memOS.as storage
    """
    metadata = {
        # Original metadata
        **original_metadata,
        # Processing metadata
        "ingestion_timestamp": datetime.utcnow().isoformat(),
        "chunk_info": {
            "index": chunk_index,
            "total": total_chunks,
            "is_chunked": total_chunks > 1,
        },
        "processor_version": "1.0.0",
        # Service metadata
        "ingested_by": "InGest-LLM.as",
        "service_version": settings.app_version,
    }

    # Add processing info if provided
    if processing_info:
        metadata["processing"] = processing_info

    return metadata
