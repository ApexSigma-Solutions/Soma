"""
LM Studio embedding service for InGest-LLM.as.

This module encapsulates all interaction with the LM Studio SDK for generating
embeddings using local models (nomic-embed-text, nomic-embed-code).
"""

from typing import List, Optional, Dict, Any
from enum import Enum
import time

import numpy as np
from openai import OpenAI
import httpx

from ..config import settings
from ..observability.logging import get_logger
from ..observability.langfuse_client import get_langfuse_client

logger = get_logger(__name__)


class EmbeddingModelType(str, Enum):
    """Available embedding models in LM Studio/Ollama."""

    TEXT = "bge-m3"  # User specified model
    CODE = "bge-m3"  # Fallback
    GENERAL = "bge-m3"  # Fallback


class VectorizerError(Exception):
    """Base exception for vectorizer errors."""

    pass


class VectorizerConnectionError(VectorizerError):
    """Raised when connection to LM Studio fails."""

    pass


class VectorizerAPIError(VectorizerError):
    """Raised when LM Studio returns an API error."""

    pass


class LMStudioVectorizer:
    """
    LM Studio vectorizer client for generating embeddings.

    Provides seamless integration with LM Studio's OpenAI-compatible API
    to generate embeddings using specialized local models.
    """

    def __init__(self):
        """Initialize the LM Studio vectorizer client."""
        self.base_url = settings.lm_studio_base_url
        self.timeout = settings.lm_studio_timeout
        self.api_key = (
            settings.lm_studio_api_key or "not-needed"
        )  # LM Studio doesn't require real API key

        # Initialize OpenAI client pointed to LM Studio
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
        )

        # Model availability cache
        self._available_models: Optional[List[str]] = None
        self._model_loaded: Optional[str] = None

    async def health_check(self) -> bool:
        """
        Check if LM Studio server is healthy and reachable.

        Returns:
            bool: True if LM Studio is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # LM Studio doesn't have /health, use /models instead (base_url includes /v1)
                response = await client.get(f"{self.base_url}/models")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"LM Studio health check failed: {e}")
            return False

    def get_available_models(self) -> List[str]:
        """
        Get list of available embedding models from LM Studio.

        Returns:
            List[str]: Available model names

        Raises:
            VectorizerConnectionError: If unable to connect to LM Studio
            VectorizerAPIError: If LM Studio returns an error
        """
        try:
            if self._available_models is None:
                models_response = self.client.models.list()
                self._available_models = [model.id for model in models_response.data]
                logger.info(f"Available LM Studio models: {self._available_models}")

            return self._available_models

        except Exception as e:
            logger.error(f"Failed to get available models from LM Studio: {e}")
            raise VectorizerConnectionError(f"Unable to connect to LM Studio: {e}")

    def select_model_for_content(
        self, content_type: str, detected_type: str = None
    ) -> str:
        """
        Select the most appropriate embedding model based on content type.

        Implements TASK-IG-15: Logic to switch between specialized embedding models
        based on the type of content being processed.

        Args:
            content_type: The declared content type (text, code, etc.)
            detected_type: Auto-detected content type from processing

        Returns:
            str: Selected model name
        """
        langfuse_client = get_langfuse_client()

        # Create Langfuse trace for model selection
        trace_id = None
        if langfuse_client.enabled:
            trace_id = langfuse_client.create_trace(
                name="embedding_model_selection",
                metadata={
                    "content_type": content_type,
                    "detected_type": detected_type,
                    "selection_strategy": "content_type_based",
                },
                tags=["embedding", "model_selection", content_type],
                input_data={
                    "content_type": content_type,
                    "detected_type": detected_type,
                },
            )

        available_models = self.get_available_models()
        selected_model = None
        selection_reason = ""

        # Helper for partial matching
        def find_matching_model(target: str) -> Optional[str]:
            # Try exact match
            if target in available_models:
                return target
            # Try partial match (e.g. "bge-m3" matches "bge-m3:567m" or "bge-m3:latest")
            for model in available_models:
                if model.startswith(target) or target in model:
                    return model
            return None

        # Priority selection based on content analysis
        if content_type.lower() in [
            "code",
            "python",
            "javascript",
            "json",
        ] or (detected_type and detected_type.lower() in ["code", "python"]):
            # Prefer code-specialized model
            match = find_matching_model(EmbeddingModelType.CODE.value)
            if match:
                selected_model = match
                selection_reason = "code_specialized_model_available"
                logger.debug(f"Selected {selected_model} for code content")

        # For text, documentation, markdown
        if not selected_model:
            match = find_matching_model(EmbeddingModelType.TEXT.value)
            if match:
                selected_model = match
                selection_reason = "text_specialized_model_available"
                logger.debug(f"Selected {selected_model} for text content")

        # Fallback to first available model
        if not selected_model and available_models:
            selected_model = available_models[0]
            selection_reason = "fallback_to_first_available"
            logger.warning(
                f"Using fallback model {selected_model} for content type {content_type}"
            )

        # Final fallback
        if not selected_model:
            selected_model = EmbeddingModelType.GENERAL.value
            selection_reason = "final_fallback_model"
            logger.warning("No specialized models available, using general model")

        # Update Langfuse trace with selection result
        if langfuse_client.enabled and trace_id:
            langfuse_client.client.trace(
                id=trace_id,
                output={
                    "selected_model": selected_model,
                    "selection_reason": selection_reason,
                    "available_models": available_models,
                },
            )

            # Score the model selection quality
            quality_score = (
                1.0
                if "specialized" in selection_reason
                else 0.5
                if "fallback" in selection_reason
                else 0.3
            )
            langfuse_client.score_trace(
                trace_id=trace_id,
                name="model_selection_quality",
                value=quality_score,
                comment=f"Model selection: {selection_reason}",
            )

        return selected_model

    def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None,
        content_type: str = "text",
        detected_type: str = None,
    ) -> List[float]:
        """
        Generate embedding for the given text using LM Studio.

        Args:
            text: Text content to embed
            model: Specific model to use (auto-selected if None)
            content_type: Content type hint for model selection
            detected_type: Auto-detected content type

        Returns:
            List[float]: Embedding vector

        Raises:
            VectorizerConnectionError: If unable to connect to LM Studio
            VectorizerAPIError: If embedding generation fails
        """
        langfuse_client = get_langfuse_client()
        start_time = time.time()

        # Create Langfuse trace for embedding generation
        trace_id = None
        if langfuse_client.enabled:
            trace_id = langfuse_client.create_trace(
                name="embedding_generation",
                metadata={
                    "content_type": content_type,
                    "detected_type": detected_type,
                    "content_length": len(text),
                    "model_specified": model is not None,
                    "embedding_provider": "lm_studio",
                },
                tags=[
                    "embedding",
                    "generation",
                    content_type,
                    model or "auto_select",
                ],
                input_data={
                    "content_preview": text[:100] + "..." if len(text) > 100 else text,
                    "content_length": len(text),
                    "content_type": content_type,
                    "detected_type": detected_type,
                    "specified_model": model,
                },
            )

        try:
            # Auto-select model if not specified
            if model is None:
                model = self.select_model_for_content(content_type, detected_type)

            logger.debug(
                f"Generating embedding with model {model} for {len(text)} chars"
            )

            # Record model selection in trace
            if langfuse_client.enabled and trace_id:
                langfuse_client.client.generation(
                    trace_id=trace_id,
                    name="model_selection",
                    model=model,
                    input={
                        "content_type": content_type,
                        "detected_type": detected_type,
                    },
                    output={"selected_model": model},
                )

            # Generate embedding using OpenAI-compatible API
            api_start_time = time.time()
            response = self.client.embeddings.create(input=[text], model=model)
            api_duration = time.time() - api_start_time

            embedding = response.data[0].embedding
            total_duration = time.time() - start_time

            logger.debug(
                f"Generated embedding with {len(embedding)} dimensions in {total_duration:.3f}s"
            )

            # Record successful embedding generation in Langfuse
            if langfuse_client.enabled and trace_id:
                langfuse_client.client.trace(
                    id=trace_id,
                    output={
                        "embedding_dimensions": len(embedding),
                        "model_used": model,
                        "api_duration_ms": int(api_duration * 1000),
                        "total_duration_ms": int(total_duration * 1000),
                        "success": True,
                        "tokens_processed": len(text.split()),
                        "chars_per_second": len(text) / total_duration
                        if total_duration > 0
                        else 0,
                    },
                )

                # Score the embedding generation performance
                # Performance score based on speed (chars/second) and dimension consistency
                chars_per_second = (
                    len(text) / total_duration if total_duration > 0 else 0
                )
                expected_dimensions = 768  # Common embedding dimension
                dimension_score = 1.0 if len(embedding) == expected_dimensions else 0.8
                speed_score = min(
                    1.0, chars_per_second / 1000
                )  # Normalize to reasonable speed
                performance_score = (dimension_score + speed_score) / 2

                langfuse_client.score_trace(
                    trace_id=trace_id,
                    name="embedding_performance",
                    value=performance_score,
                    comment=f"Model: {model}, Speed: {chars_per_second:.1f} chars/s, Dims: {len(embedding)}",
                )

                # Add efficiency metrics for model comparison
                langfuse_client.score_trace(
                    trace_id=trace_id,
                    name="embedding_efficiency",
                    value=chars_per_second / 1000,  # Normalized efficiency metric
                    comment=f"Processing efficiency for {model}: {chars_per_second:.1f} chars/second",
                )

            return embedding

        except Exception as e:
            error_msg = f"Failed to generate embedding with LM Studio: {e}"
            logger.error(error_msg)

            # Record error in Langfuse
            if langfuse_client.enabled and trace_id:
                langfuse_client.client.trace(
                    id=trace_id,
                    output={
                        "success": False,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "model_attempted": model,
                        "duration_before_error_ms": int(
                            (time.time() - start_time) * 1000
                        ),
                    },
                )

                # Score as failure
                langfuse_client.score_trace(
                    trace_id=trace_id,
                    name="embedding_performance",
                    value=0.0,
                    comment=f"Failed: {str(e)}",
                )

            if "connection" in str(e).lower():
                raise VectorizerConnectionError(error_msg)
            else:
                raise VectorizerAPIError(error_msg)

    def generate_embeddings_batch(
        self,
        texts: List[str],
        model: Optional[str] = None,
        content_type: str = "text",
        detected_type: str = None,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a single batch.

        Args:
            texts: List of text content to embed
            model: Specific model to use (auto-selected if None)
            content_type: Content type hint for model selection
            detected_type: Auto-detected content type

        Returns:
            List[List[float]]: List of embedding vectors

        Raises:
            VectorizerConnectionError: If unable to connect to LM Studio
            VectorizerAPIError: If embedding generation fails
        """
        langfuse_client = get_langfuse_client()
        start_time = time.time()

        # Calculate batch statistics
        total_chars = sum(len(text) for text in texts)
        avg_text_length = total_chars / len(texts) if texts else 0

        # Create Langfuse trace for batch embedding generation
        trace_id = None
        if langfuse_client.enabled:
            trace_id = langfuse_client.create_trace(
                name="batch_embedding_generation",
                metadata={
                    "content_type": content_type,
                    "detected_type": detected_type,
                    "batch_size": len(texts),
                    "total_chars": total_chars,
                    "avg_text_length": avg_text_length,
                    "model_specified": model is not None,
                    "embedding_provider": "lm_studio",
                },
                tags=[
                    "embedding",
                    "batch",
                    "generation",
                    content_type,
                    f"batch_size_{len(texts)}",
                ],
                input_data={
                    "batch_size": len(texts),
                    "total_chars": total_chars,
                    "avg_text_length": avg_text_length,
                    "content_type": content_type,
                    "detected_type": detected_type,
                    "specified_model": model,
                    "sample_texts": [
                        text[:50] + "..." if len(text) > 50 else text
                        for text in texts[:3]
                    ],
                },
            )

        try:
            # Auto-select model if not specified
            if model is None:
                model = self.select_model_for_content(content_type, detected_type)

            logger.debug(f"Generating {len(texts)} embeddings with model {model}")

            # Generate embeddings using batch API
            api_start_time = time.time()
            response = self.client.embeddings.create(input=texts, model=model)
            api_duration = time.time() - api_start_time

            embeddings = [item.embedding for item in response.data]
            total_duration = time.time() - start_time

            logger.debug(
                f"Generated {len(embeddings)} embeddings in {total_duration:.3f}s"
            )

            # Calculate batch efficiency metrics
            chars_per_second = total_chars / total_duration if total_duration > 0 else 0
            embeddings_per_second = (
                len(embeddings) / total_duration if total_duration > 0 else 0
            )
            avg_embedding_dims = (
                sum(len(emb) for emb in embeddings) / len(embeddings)
                if embeddings
                else 0
            )

            # Record successful batch generation in Langfuse
            if langfuse_client.enabled and trace_id:
                langfuse_client.client.trace(
                    id=trace_id,
                    output={
                        "embeddings_generated": len(embeddings),
                        "avg_embedding_dimensions": avg_embedding_dims,
                        "model_used": model,
                        "api_duration_ms": int(api_duration * 1000),
                        "total_duration_ms": int(total_duration * 1000),
                        "success": True,
                        "batch_efficiency": {
                            "chars_per_second": chars_per_second,
                            "embeddings_per_second": embeddings_per_second,
                            "total_chars_processed": total_chars,
                            "avg_chars_per_embedding": total_chars / len(texts)
                            if texts
                            else 0,
                        },
                    },
                )

                # Score batch processing performance
                # Batch efficiency bonus for processing multiple items efficiently
                batch_efficiency = (
                    embeddings_per_second * 10
                )  # Scale factor for visibility
                batch_score = min(
                    1.0, batch_efficiency / 50
                )  # Normalize to reasonable batch speed

                langfuse_client.score_trace(
                    trace_id=trace_id,
                    name="batch_embedding_performance",
                    value=batch_score,
                    comment=f"Batch: {len(texts)} items, {embeddings_per_second:.1f} emb/s, {chars_per_second:.1f} chars/s",
                )

                # Add batch efficiency comparison metric
                langfuse_client.score_trace(
                    trace_id=trace_id,
                    name="batch_embedding_efficiency",
                    value=embeddings_per_second / 10,  # Normalized efficiency metric
                    comment=f"Batch efficiency for {model}: {embeddings_per_second:.1f} embeddings/second",
                )

                # Track model performance for comparison
                langfuse_client.score_trace(
                    trace_id=trace_id,
                    name=f"model_efficiency_{model.replace('-', '_')}",
                    value=chars_per_second / 1000,
                    comment=f"Model-specific efficiency: {chars_per_second:.1f} chars/second",
                )

            return embeddings

        except Exception as e:
            error_msg = f"Failed to generate batch embeddings with LM Studio: {e}"
            logger.error(error_msg)

            # Record error in Langfuse
            if langfuse_client.enabled and trace_id:
                langfuse_client.client.trace(
                    id=trace_id,
                    output={
                        "success": False,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "model_attempted": model,
                        "batch_size": len(texts),
                        "duration_before_error_ms": int(
                            (time.time() - start_time) * 1000
                        ),
                    },
                )

                # Score as failure
                langfuse_client.score_trace(
                    trace_id=trace_id,
                    name="batch_embedding_performance",
                    value=0.0,
                    comment=f"Batch failed: {str(e)}",
                )

            if "connection" in str(e).lower():
                raise VectorizerConnectionError(error_msg)
            else:
                raise VectorizerAPIError(error_msg)

    def calculate_similarity(
        self, embedding1: List[float], embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            float: Cosine similarity score (0-1)
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norms = np.linalg.norm(vec1) * np.linalg.norm(vec2)

            if norms == 0:
                return 0.0

            similarity = dot_product / norms

            # Ensure result is in [0, 1] range
            return max(0.0, min(1.0, (similarity + 1) / 2))

        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0

    def get_embedding_info(self, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about the embedding model.

        Args:
            model: Model name to get info for

        Returns:
            Dict[str, Any]: Model information
        """
        if model is None:
            model = self.select_model_for_content("text")

        return {
            "model": model,
            "provider": "lm-studio",
            "local": True,
            "available_models": self.get_available_models(),
            "base_url": self.base_url,
        }


# Global vectorizer instance
_vectorizer: Optional[LMStudioVectorizer] = None


def get_vectorizer() -> LMStudioVectorizer:
    """
    Get the global LM Studio vectorizer instance.

    Returns:
        LMStudioVectorizer: Configured vectorizer instance
    """
    global _vectorizer
    if _vectorizer is None:
        _vectorizer = LMStudioVectorizer()
    return _vectorizer


async def generate_content_embedding(
    content: str, content_type: str = "text", detected_type: str = None
) -> Optional[List[float]]:
    """
    Convenience function to generate embedding for content.

    Args:
        content: Text content to embed
        content_type: Content type hint
        detected_type: Auto-detected content type

    Returns:
        Optional[List[float]]: Embedding vector or None if generation fails
    """
    try:
        vectorizer = get_vectorizer()

        # Check if LM Studio is available
        if not await vectorizer.health_check():
            logger.warning("LM Studio not available, skipping embedding generation")
            return None

        return vectorizer.generate_embedding(
            text=content,
            content_type=content_type,
            detected_type=detected_type,
        )

    except Exception as e:
        logger.error(f"Failed to generate content embedding: {e}")
        return None
