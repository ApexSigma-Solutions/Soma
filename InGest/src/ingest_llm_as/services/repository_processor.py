"""
Repository processing service for Python project ingestion.

This module handles the discovery, processing, and analysis of Python repositories
including file discovery, batch processing, and comprehensive analysis.
"""

import asyncio
import time
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import fnmatch

from ..models import (
    RepositoryIngestionRequest,
    RepositoryIngestionResponse,
    FileProcessingResult,
    RepositoryProcessingSummary,
    ProcessingStatus,
    RepositorySource,
    MemoryTier,
)
from ..utils.content_processor import ContentProcessor
from ..services.memos_client import get_memos_client, MemOSClient
from ..services.progress_logger import get_progress_logger
from ..observability.logging import get_logger
from ..observability.langfuse_client import get_langfuse_client
from ..config import settings

logger = get_logger(__name__)


@dataclass
class DiscoveredFile:
    """Represents a discovered file in the repository."""

    absolute_path: Path
    relative_path: Path
    size_bytes: int
    is_python: bool = False
    should_process: bool = True
    skip_reason: Optional[str] = None


class RepositoryProcessor:
    """
    Processes Python repositories for comprehensive code analysis and ingestion.

    Handles file discovery, filtering, batch processing, and analysis generation
    with full observability and error handling.
    """

    def __init__(self):
        """Initialize the repository processor."""
        self.logger = get_logger(__name__)
        self.langfuse_client = get_langfuse_client()
        self.content_processor = ContentProcessor(
            enable_embeddings=settings.embedding_enabled
        )
        self.progress_logger = get_progress_logger()

    async def process_repository(
        self, request: RepositoryIngestionRequest
    ) -> RepositoryIngestionResponse:
        """
        Process a Python repository comprehensively.

        Args:
            request: Repository ingestion request

        Returns:
            RepositoryIngestionResponse: Processing results and analysis
        """
        start_time = time.time()

        # Create Langfuse trace for repository processing
        trace_id = None
        if self.langfuse_client.enabled:
            trace_id = self.langfuse_client.create_trace(
                name="repository_ingestion",
                metadata={
                    "repository_source": request.repository_source.value,
                    "source_path": request.source_path,
                    "max_files": request.max_files,
                    "max_file_size": request.max_file_size,
                    "process_async": request.process_async,
                    "include_patterns": request.include_patterns,
                    "exclude_patterns": request.exclude_patterns,
                },
                tags=["repository", "ingestion", request.repository_source.value],
                input_data={
                    "repository_source": request.repository_source.value,
                    "source_path": request.source_path,
                    "max_files": request.max_files,
                    "include_patterns": request.include_patterns[
                        :3
                    ],  # First 3 patterns
                    "exclude_patterns": request.exclude_patterns[
                        :5
                    ],  # First 5 patterns
                },
            )

        response = RepositoryIngestionResponse(
            repository_path=request.source_path, status=ProcessingStatus.PROCESSING
        )

        # Start progress logging
        await self.progress_logger.start_ingestion_logging(
            str(response.ingestion_id), request
        )

        try:
            # Step 1: Prepare repository (clone/download if needed)
            repo_path = await self._prepare_repository(request, trace_id)

            # Step 2: Discover files
            discovery_start = time.time()
            discovered_files = await self._discover_files(repo_path, request, trace_id)
            discovery_time = int((time.time() - discovery_start) * 1000)

            response.files_discovered = len(discovered_files)
            response.files_to_process = len(
                [f for f in discovered_files if f.should_process]
            )
            response.discovery_time_ms = discovery_time

            # Log discovery completion
            await self.progress_logger.log_discovery_complete(
                str(response.ingestion_id),
                response.files_discovered,
                response.files_to_process,
                discovery_time,
            )

            self.logger.info(
                f"Repository discovery complete: {response.files_discovered} files found, "
                f"{response.files_to_process} to process"
            )

            # Step 3: Process files
            if request.process_async:
                # Start async processing and return immediately
                asyncio.create_task(
                    self._process_files_async(
                        discovered_files, request, response, trace_id
                    )
                )
                response.status = ProcessingStatus.PENDING
                response.message = f"Repository processing started: {response.files_to_process} files queued"
            else:
                # Process synchronously
                await self._process_files_sync(
                    discovered_files, request, response, trace_id
                )
                response.status = ProcessingStatus.COMPLETED
                response.completed_at = response.created_at
                response.total_time_ms = int((time.time() - start_time) * 1000)
                response.message = f"Repository processing completed: {len(response.files_processed)} files processed"

                # Generate code structure analysis
                structure_analysis = (
                    await self.progress_logger.generate_code_structure_analysis(
                        str(repo_path), response.files_processed
                    )
                )

                # Log completion with structure analysis
                await self.progress_logger.log_ingestion_complete(
                    str(response.ingestion_id), response, structure_analysis
                )

            # Record successful initiation in Langfuse
            if self.langfuse_client.enabled and trace_id:
                self.langfuse_client.client.trace(
                    id=trace_id,
                    output={
                        "repository_prepared": True,
                        "files_discovered": response.files_discovered,
                        "files_to_process": response.files_to_process,
                        "discovery_time_ms": discovery_time,
                        "processing_mode": "async" if request.process_async else "sync",
                        "ingestion_id": str(response.ingestion_id),
                    },
                )

                # Score repository complexity
                complexity_score = min(
                    1.0, response.files_to_process / 100
                )  # Normalize file count
                self.langfuse_client.score_trace(
                    trace_id=trace_id,
                    name="repository_complexity",
                    value=complexity_score,
                    comment=f"Repository with {response.files_to_process} Python files",
                )

            return response

        except Exception as e:
            self.logger.error(f"Repository processing failed: {e}")

            # Log error in progress tracking
            await self.progress_logger.log_ingestion_error(
                str(response.ingestion_id), str(e), "processing"
            )

            # Record error in Langfuse
            if self.langfuse_client.enabled and trace_id:
                self.langfuse_client.client.trace(
                    id=trace_id,
                    output={
                        "success": False,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

                self.langfuse_client.score_trace(
                    trace_id=trace_id,
                    name="repository_complexity",
                    value=0.0,
                    comment=f"Processing failed: {str(e)}",
                )

            response.status = ProcessingStatus.FAILED
            response.message = f"Repository processing failed: {str(e)}"
            return response

    async def _prepare_repository(
        self, request: RepositoryIngestionRequest, trace_id: Optional[str] = None
    ) -> Path:
        """
        Prepare repository for processing (clone if needed).

        Args:
            request: Repository ingestion request
            trace_id: Optional Langfuse trace ID

        Returns:
            Path: Local path to repository
        """
        if request.repository_source == RepositorySource.LOCAL_PATH:
            return Path(request.source_path)

        elif request.repository_source in [
            RepositorySource.GIT_URL,
            RepositorySource.GITHUB_URL,
        ]:
            # Clone repository to temporary directory
            temp_dir = Path(tempfile.mkdtemp(prefix="repo_ingest_"))

            try:
                # Use git clone
                result = subprocess.run(
                    [
                        "git",
                        "clone",
                        "--depth",
                        "1",
                        request.source_path,
                        str(temp_dir),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                )

                if result.returncode != 0:
                    raise RuntimeError(f"Git clone failed: {result.stderr}")

                self.logger.info(f"Successfully cloned repository to {temp_dir}")

                # Record successful clone in Langfuse
                if self.langfuse_client.enabled and trace_id:
                    self.langfuse_client.client.generation(
                        trace_id=trace_id,
                        name="git_clone",
                        model="git",
                        input={"repository_url": request.source_path},
                        output={"temp_directory": str(temp_dir), "success": True},
                    )

                return temp_dir

            except subprocess.TimeoutExpired:
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise RuntimeError("Git clone timed out after 5 minutes")
            except Exception as e:
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise RuntimeError(f"Failed to clone repository: {e}")

        else:
            raise ValueError(
                f"Unsupported repository source: {request.repository_source}"
            )

    async def _discover_files(
        self,
        repo_path: Path,
        request: RepositoryIngestionRequest,
        trace_id: Optional[str] = None,
    ) -> List[DiscoveredFile]:
        """
        Discover and filter files in the repository.

        Args:
            repo_path: Path to repository
            request: Repository ingestion request
            trace_id: Optional Langfuse trace ID

        Returns:
            List[DiscoveredFile]: Discovered files with processing decisions
        """
        discovered_files = []

        # Walk through all files in repository
        for file_path in repo_path.rglob("*"):
            if not file_path.is_file():
                continue

            try:
                relative_path = file_path.relative_to(repo_path)
                size_bytes = file_path.stat().st_size

                discovered_file = DiscoveredFile(
                    absolute_path=file_path,
                    relative_path=relative_path,
                    size_bytes=size_bytes,
                    is_python=file_path.suffix == ".py",
                )

                # Apply filtering logic
                should_process, skip_reason = self._should_process_file(
                    relative_path, size_bytes, request
                )

                discovered_file.should_process = should_process
                discovered_file.skip_reason = skip_reason

                discovered_files.append(discovered_file)

                # Limit discovery if we hit max files
                if (
                    len([f for f in discovered_files if f.should_process])
                    >= request.max_files
                ):
                    self.logger.warning(
                        f"Hit max files limit ({request.max_files}), stopping discovery"
                    )
                    break

            except Exception as e:
                self.logger.warning(f"Error processing file {file_path}: {e}")
                continue

        # Log discovery results
        total_files = len(discovered_files)
        python_files = len([f for f in discovered_files if f.is_python])
        files_to_process = len([f for f in discovered_files if f.should_process])

        self.logger.info(
            f"File discovery: {total_files} total, {python_files} Python, "
            f"{files_to_process} to process"
        )

        # Record discovery metrics in Langfuse
        if self.langfuse_client.enabled and trace_id:
            self.langfuse_client.client.generation(
                trace_id=trace_id,
                name="file_discovery",
                model="filesystem_walker",
                input={"repository_path": str(repo_path)},
                output={
                    "total_files": total_files,
                    "python_files": python_files,
                    "files_to_process": files_to_process,
                    "discovery_efficiency": files_to_process / total_files
                    if total_files > 0
                    else 0,
                },
            )

        return discovered_files

    def _should_process_file(
        self, relative_path: Path, size_bytes: int, request: RepositoryIngestionRequest
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if a file should be processed.

        Args:
            relative_path: Relative path to file
            size_bytes: File size in bytes
            request: Repository ingestion request

        Returns:
            Tuple[bool, Optional[str]]: (should_process, skip_reason)
        """
        path_str = str(relative_path)

        # Check size limits
        if size_bytes > request.max_file_size:
            return False, f"File too large: {size_bytes} > {request.max_file_size}"

        if size_bytes == 0:
            return False, "Empty file"

        # Check exclude patterns first
        for pattern in request.exclude_patterns:
            if fnmatch.fnmatch(path_str, pattern):
                return False, f"Excluded by pattern: {pattern}"

        # Check include patterns
        included = False
        for pattern in request.include_patterns:
            if fnmatch.fnmatch(path_str, pattern):
                included = True
                break

        if not included:
            return False, f"Not matched by include patterns: {request.include_patterns}"

        return True, None

    async def _process_files_sync(
        self,
        discovered_files: List[DiscoveredFile],
        request: RepositoryIngestionRequest,
        response: RepositoryIngestionResponse,
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Process files synchronously.

        Args:
            discovered_files: Files to process
            request: Repository ingestion request
            response: Response object to update
            trace_id: Optional Langfuse trace ID
        """
        processing_start = time.time()

        files_to_process = [f for f in discovered_files if f.should_process]

        # Get memOS client
        memos_client = get_memos_client()

        # Process files in batches for better performance
        batch_size = 10
        for i in range(0, len(files_to_process), batch_size):
            batch = files_to_process[i : i + batch_size]

            # Process batch concurrently
            batch_tasks = []
            for file in batch:
                task = self._process_single_file(file, request, memos_client, trace_id)
                batch_tasks.append(task)

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Process results
            for file, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    self.logger.error(
                        f"Error processing {file.relative_path}: {result}"
                    )
                    file_result = FileProcessingResult(
                        file_path=str(file.absolute_path),
                        relative_path=str(file.relative_path),
                        file_size=file.size_bytes,
                        status=ProcessingStatus.FAILED,
                        error_message=str(result),
                    )
                else:
                    file_result = result

                response.files_processed.append(file_result)

                # Log individual file progress
                await self.progress_logger.log_file_processing_progress(
                    str(response.ingestion_id),
                    str(file.relative_path),
                    len(response.files_processed),
                    len(files_to_process),
                    file_result,
                )

            # Log progress
            processed_count = len(response.files_processed)
            self.logger.info(
                f"Processed batch: {processed_count}/{len(files_to_process)} files"
            )

        # Generate processing summary
        processing_time = int((time.time() - processing_start) * 1000)
        response.processing_time_ms = processing_time
        response.processing_summary = self._generate_processing_summary(
            response.files_processed, processing_time
        )

        self.logger.info(
            f"Repository processing completed: {len(response.files_processed)} files, "
            f"{processing_time}ms"
        )

    async def _process_files_async(
        self,
        discovered_files: List[DiscoveredFile],
        request: RepositoryIngestionRequest,
        response: RepositoryIngestionResponse,
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Process files asynchronously in background.

        Args:
            discovered_files: Files to process
            request: Repository ingestion request
            response: Response object to update
            trace_id: Optional Langfuse trace ID
        """
        # TODO: Implement async processing with status tracking
        # For now, delegate to sync processing
        await self._process_files_sync(discovered_files, request, response, trace_id)

    async def _process_single_file(
        self,
        file: DiscoveredFile,
        request: RepositoryIngestionRequest,
        memos_client: MemOSClient,
        trace_id: Optional[str] = None,
    ) -> FileProcessingResult:
        """
        Process a single file.

        Args:
            file: File to process
            request: Repository ingestion request
            memos_client: memOS client
            trace_id: Optional Langfuse trace ID

        Returns:
            FileProcessingResult: Processing result
        """
        start_time = time.time()

        try:
            # Read file content
            with open(file.absolute_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Process with AST parser if Python file
            if file.is_python:
                processing_result = (
                    await self.content_processor.process_python_code_with_embeddings(
                        source_code=content,
                        file_path=str(file.relative_path),
                        content_type="code",
                    )
                )
            else:
                # Process as regular text
                processing_result = (
                    await self.content_processor.process_content_with_embeddings(
                        content=content, content_type="text"
                    )
                )

            # Store chunks in memOS
            memory_ids = []
            chunks = processing_result["chunks"]
            embeddings = processing_result["embeddings"]

            for i, chunk in enumerate(chunks):
                try:
                    embedding = embeddings[i] if i < len(embeddings) else None

                    # Create metadata for this chunk
                    chunk_metadata = {
                        "file_path": str(file.relative_path),
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "file_size": file.size_bytes,
                        "repository_ingestion_id": str(
                            request.metadata.custom_fields.get("ingestion_id", "")
                        ),
                        **request.metadata.model_dump(),
                    }

                    # Store in memOS
                    storage_response = await memos_client.store_memory(
                        content=chunk,
                        memory_tier=MemoryTier.PROCEDURAL
                        if file.is_python
                        else MemoryTier.SEMANTIC,
                        metadata=chunk_metadata,
                        embedding=embedding,
                    )

                    if (
                        hasattr(storage_response, "memory_id")
                        and storage_response.memory_id
                    ):
                        memory_ids.append(storage_response.memory_id)

                except Exception as e:
                    self.logger.warning(
                        f"Failed to store chunk {i} for {file.relative_path}: {e}"
                    )

            processing_time = int((time.time() - start_time) * 1000)

            # Calculate complexity (for Python files)
            complexity_score = 0.0
            elements_extracted = 0

            if file.is_python and "parsing_result" in processing_result:
                parsing_result = processing_result["parsing_result"]
                elements_extracted = parsing_result["total_elements"]

                # Calculate average complexity
                if "code_elements" in processing_result:
                    complexities = [
                        elem.complexity_score
                        for elem in processing_result["code_elements"]
                        if hasattr(elem, "complexity_score")
                    ]
                    if complexities:
                        complexity_score = sum(complexities) / len(complexities)

            return FileProcessingResult(
                file_path=str(file.absolute_path),
                relative_path=str(file.relative_path),
                file_size=file.size_bytes,
                status=ProcessingStatus.COMPLETED,
                elements_extracted=elements_extracted,
                chunks_created=len(chunks),
                embeddings_generated=sum(1 for emb in embeddings if emb is not None),
                processing_time_ms=processing_time,
                complexity_score=complexity_score,
                memory_ids=memory_ids,
            )

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            self.logger.error(f"Error processing file {file.relative_path}: {e}")

            return FileProcessingResult(
                file_path=str(file.absolute_path),
                relative_path=str(file.relative_path),
                file_size=file.size_bytes,
                status=ProcessingStatus.FAILED,
                processing_time_ms=processing_time,
                error_message=str(e),
            )

    def _generate_processing_summary(
        self, file_results: List[FileProcessingResult], total_processing_time_ms: int
    ) -> RepositoryProcessingSummary:
        """
        Generate comprehensive processing summary.

        Args:
            file_results: Results from file processing
            total_processing_time_ms: Total processing time

        Returns:
            RepositoryProcessingSummary: Comprehensive summary
        """
        # Basic counts
        total_files_processed = len(file_results)
        successful_files = [
            r for r in file_results if r.status == ProcessingStatus.COMPLETED
        ]
        failed_files = [r for r in file_results if r.status == ProcessingStatus.FAILED]

        # Aggregate metrics
        total_elements = sum(r.elements_extracted for r in successful_files)
        total_chunks = sum(r.chunks_created for r in successful_files)
        total_embeddings = sum(r.embeddings_generated for r in successful_files)

        # Complexity analysis
        complexities = [
            r.complexity_score for r in successful_files if r.complexity_score > 0
        ]
        avg_complexity = sum(complexities) / len(complexities) if complexities else 0.0

        # File type distribution
        file_type_dist = defaultdict(int)
        for result in file_results:
            extension = Path(result.relative_path).suffix or "no_extension"
            file_type_dist[extension] += 1

        # Find largest and most complex files
        largest_files = sorted(
            [{"path": r.relative_path, "size": r.file_size} for r in successful_files],
            key=lambda x: x["size"],
            reverse=True,
        )[:10]

        most_complex_files = sorted(
            [
                {"path": r.relative_path, "complexity": r.complexity_score}
                for r in successful_files
                if r.complexity_score > 0
            ],
            key=lambda x: x["complexity"],
            reverse=True,
        )[:10]

        # Collect errors
        processing_errors = [r.error_message for r in failed_files if r.error_message][
            :20
        ]  # Limit to 20 errors

        return RepositoryProcessingSummary(
            total_files_found=total_files_processed,  # This is files processed, not found
            total_files_processed=len(successful_files),
            total_files_skipped=0,  # Would need to track skipped files separately
            total_files_failed=len(failed_files),
            total_elements_extracted=total_elements,
            total_chunks_created=total_chunks,
            total_embeddings_generated=total_embeddings,
            total_processing_time_ms=total_processing_time_ms,
            average_complexity=avg_complexity,
            file_type_distribution=dict(file_type_dist),
            element_type_distribution={},  # Could aggregate element types from AST results
            largest_files=largest_files,
            most_complex_files=most_complex_files,
            processing_errors=processing_errors,
        )


# Global repository processor instance
_repository_processor: Optional[RepositoryProcessor] = None


def get_repository_processor() -> RepositoryProcessor:
    """
    Get the global repository processor instance.

    Returns:
        RepositoryProcessor: Configured processor instance
    """
    global _repository_processor
    if _repository_processor is None:
        _repository_processor = RepositoryProcessor()
    return _repository_processor
