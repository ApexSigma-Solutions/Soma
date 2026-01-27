"""
End-to-End Distributed Tracing for InGest-LLM.as - ApexSigma Data Ingestion Service

This module implements comprehensive E2E tracing for the InGest-LLM service in the ApexSigma ecosystem.
Handles data ingestion, processing pipelines, LLM interactions, and cross-service agent coordination.
"""

import uuid
from typing import Dict, Any, Optional
from contextlib import contextmanager

from opentelemetry import trace, baggage
from opentelemetry.trace import Status, StatusCode
from opentelemetry.propagate import extract, inject
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.propagators.jaeger import JaegerPropagator
from opentelemetry.propagators.b3 import B3MultiFormat, B3SingleFormat
from opentelemetry.propagators.composite import CompositePropagator
from fastapi import Request, Response
from structlog import get_logger

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)

# Composite propagator for maximum compatibility
propagator = CompositePropagator(
    [
        TraceContextTextMapPropagator(),
        B3MultiFormat(),
        B3SingleFormat(),
        JaegerPropagator(),
        W3CBaggagePropagator(),
    ]
)


class InGestE2ETracing:
    """End-to-end distributed tracing for InGest-LLM.as service."""

    def __init__(self):
        self.service_name = "ingest-llm.as"
        self.service_version = "1.0.0"

    def extract_request_context(self, request: Request) -> Dict[str, Any]:
        """Extract tracing context from incoming HTTP request."""
        headers = dict(request.headers)

        # Extract OpenTelemetry context
        context = extract(headers)

        # Extract ApexSigma correlation headers
        correlation_id = headers.get("x-apexsigma-correlation-id")
        workflow_id = headers.get("x-apexsigma-workflow-id")
        agent_chain = headers.get("x-apexsigma-agent-chain", "")

        return {
            "context": context,
            "correlation_id": correlation_id,
            "workflow_id": workflow_id,
            "agent_chain": agent_chain,
            "source_service": headers.get("x-apexsigma-source-service"),
            "request_id": headers.get("x-request-id", str(uuid.uuid4())),
        }

    def inject_response_context(
        self, response: Response, correlation_id: str, workflow_id: Optional[str] = None
    ):
        """Inject tracing context into outgoing HTTP response."""
        carrier = {}
        inject(carrier)

        # Add OpenTelemetry headers
        for key, value in carrier.items():
            response.headers[key] = value

        # Add ApexSigma correlation headers
        response.headers["x-apexsigma-correlation-id"] = correlation_id
        if workflow_id:
            response.headers["x-apexsigma-workflow-id"] = workflow_id
        response.headers["x-apexsigma-service"] = self.service_name

    @contextmanager
    def trace_data_ingestion(
        self,
        data_source: str,
        ingestion_type: str,
        correlation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        record_count: Optional[int] = None,
    ):
        """Trace data ingestion operations (file, stream, batch)."""
        span_name = f"ingest.data.{ingestion_type}"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Set standard attributes
                span.set_attribute("service.name", self.service_name)
                span.set_attribute("service.version", self.service_version)
                span.set_attribute("operation.name", ingestion_type)
                span.set_attribute("data.source", data_source)
                span.set_attribute("ingestion.type", ingestion_type)

                if record_count is not None:
                    span.set_attribute("data.record_count", record_count)

                # Set ApexSigma correlation attributes
                if correlation_id:
                    span.set_attribute("apexsigma.correlation_id", correlation_id)
                    baggage.set_baggage("correlation_id", correlation_id)

                if workflow_id:
                    span.set_attribute("apexsigma.workflow_id", workflow_id)
                    baggage.set_baggage("workflow_id", workflow_id)

                # Set baggage for cross-service propagation
                baggage.set_baggage("service", self.service_name)
                baggage.set_baggage("operation", ingestion_type)
                baggage.set_baggage("data_source", data_source)

                logger.info(
                    "Data ingestion started",
                    data_source=data_source,
                    ingestion_type=ingestion_type,
                    record_count=record_count,
                    correlation_id=correlation_id,
                    trace_id=format(span.get_span_context().trace_id, "032x"),
                )

                yield span

                span.set_status(Status(StatusCode.OK))
                logger.info(
                    "Data ingestion completed successfully",
                    data_source=data_source,
                    ingestion_type=ingestion_type,
                    correlation_id=correlation_id,
                )

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error(
                    "Data ingestion failed",
                    data_source=data_source,
                    ingestion_type=ingestion_type,
                    correlation_id=correlation_id,
                    error=str(e),
                )
                raise

    @contextmanager
    def trace_llm_interaction(
        self,
        model_name: str,
        operation: str,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        correlation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ):
        """Trace LLM interactions (completion, embedding, fine-tuning)."""
        span_name = f"ingest.llm.{operation}"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Set standard attributes
                span.set_attribute("service.name", self.service_name)
                span.set_attribute("service.version", self.service_version)
                span.set_attribute("operation.name", operation)
                span.set_attribute("llm.model", model_name)
                span.set_attribute("llm.operation", operation)

                if prompt_tokens is not None:
                    span.set_attribute("llm.prompt_tokens", prompt_tokens)
                if completion_tokens is not None:
                    span.set_attribute("llm.completion_tokens", completion_tokens)
                    span.set_attribute(
                        "llm.total_tokens", (prompt_tokens or 0) + completion_tokens
                    )

                # Set ApexSigma correlation attributes
                if correlation_id:
                    span.set_attribute("apexsigma.correlation_id", correlation_id)
                    baggage.set_baggage("correlation_id", correlation_id)

                if workflow_id:
                    span.set_attribute("apexsigma.workflow_id", workflow_id)
                    baggage.set_baggage("workflow_id", workflow_id)

                # Set baggage for cross-service propagation
                baggage.set_baggage("service", self.service_name)
                baggage.set_baggage("llm_model", model_name)
                baggage.set_baggage("llm_operation", operation)

                logger.info(
                    "LLM interaction started",
                    model=model_name,
                    operation=operation,
                    prompt_tokens=prompt_tokens,
                    correlation_id=correlation_id,
                    trace_id=format(span.get_span_context().trace_id, "032x"),
                )

                yield span

                span.set_status(Status(StatusCode.OK))
                logger.info(
                    "LLM interaction completed",
                    model=model_name,
                    operation=operation,
                    completion_tokens=completion_tokens,
                    correlation_id=correlation_id,
                )

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error(
                    "LLM interaction failed",
                    model=model_name,
                    operation=operation,
                    correlation_id=correlation_id,
                    error=str(e),
                )
                raise

    @contextmanager
    def trace_processing_pipeline(
        self,
        pipeline_name: str,
        stage: str,
        batch_size: Optional[int] = None,
        correlation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ):
        """Trace data processing pipeline stages."""
        span_name = f"ingest.pipeline.{pipeline_name}.{stage}"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Set standard attributes
                span.set_attribute("service.name", self.service_name)
                span.set_attribute("service.version", self.service_version)
                span.set_attribute("operation.name", f"pipeline_{stage}")
                span.set_attribute("pipeline.name", pipeline_name)
                span.set_attribute("pipeline.stage", stage)

                if batch_size is not None:
                    span.set_attribute("pipeline.batch_size", batch_size)

                # Set ApexSigma correlation attributes
                if correlation_id:
                    span.set_attribute("apexsigma.correlation_id", correlation_id)
                    baggage.set_baggage("correlation_id", correlation_id)

                if workflow_id:
                    span.set_attribute("apexsigma.workflow_id", workflow_id)
                    baggage.set_baggage("workflow_id", workflow_id)

                # Set baggage for cross-service propagation
                baggage.set_baggage("service", self.service_name)
                baggage.set_baggage("pipeline", pipeline_name)
                baggage.set_baggage("stage", stage)

                logger.info(
                    "Processing pipeline stage started",
                    pipeline=pipeline_name,
                    stage=stage,
                    batch_size=batch_size,
                    correlation_id=correlation_id,
                    trace_id=format(span.get_span_context().trace_id, "032x"),
                )

                yield span

                span.set_status(Status(StatusCode.OK))
                logger.info(
                    "Processing pipeline stage completed",
                    pipeline=pipeline_name,
                    stage=stage,
                    correlation_id=correlation_id,
                )

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error(
                    "Processing pipeline stage failed",
                    pipeline=pipeline_name,
                    stage=stage,
                    correlation_id=correlation_id,
                    error=str(e),
                )
                raise

    @contextmanager
    def trace_vector_operations(
        self,
        operation: str,
        vector_store: str,
        dimension: Optional[int] = None,
        vector_count: Optional[int] = None,
        correlation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ):
        """Trace vector database operations (index, search, upsert)."""
        span_name = f"ingest.vector.{operation}"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Set standard attributes
                span.set_attribute("service.name", self.service_name)
                span.set_attribute("service.version", self.service_version)
                span.set_attribute("operation.name", operation)
                span.set_attribute("vector.store", vector_store)
                span.set_attribute("vector.operation", operation)

                if dimension is not None:
                    span.set_attribute("vector.dimension", dimension)
                if vector_count is not None:
                    span.set_attribute("vector.count", vector_count)

                # Set ApexSigma correlation attributes
                if correlation_id:
                    span.set_attribute("apexsigma.correlation_id", correlation_id)
                    baggage.set_baggage("correlation_id", correlation_id)

                if workflow_id:
                    span.set_attribute("apexsigma.workflow_id", workflow_id)
                    baggage.set_baggage("workflow_id", workflow_id)

                # Set baggage for cross-service propagation
                baggage.set_baggage("service", self.service_name)
                baggage.set_baggage("vector_store", vector_store)
                baggage.set_baggage("vector_operation", operation)

                logger.info(
                    "Vector operation started",
                    operation=operation,
                    vector_store=vector_store,
                    dimension=dimension,
                    vector_count=vector_count,
                    correlation_id=correlation_id,
                    trace_id=format(span.get_span_context().trace_id, "032x"),
                )

                yield span

                span.set_status(Status(StatusCode.OK))
                logger.info(
                    "Vector operation completed",
                    operation=operation,
                    vector_store=vector_store,
                    correlation_id=correlation_id,
                )

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error(
                    "Vector operation failed",
                    operation=operation,
                    vector_store=vector_store,
                    correlation_id=correlation_id,
                    error=str(e),
                )
                raise

    def prepare_outbound_headers(
        self,
        target_service: str,
        correlation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        agent_chain: Optional[str] = None,
    ) -> Dict[str, str]:
        """Prepare headers for outbound HTTP requests to other services."""
        headers = {}

        # Inject OpenTelemetry context
        inject(headers)

        # Add ApexSigma correlation headers
        if correlation_id:
            headers["x-apexsigma-correlation-id"] = correlation_id
        if workflow_id:
            headers["x-apexsigma-workflow-id"] = workflow_id
        if agent_chain:
            headers["x-apexsigma-agent-chain"] = f"{agent_chain}->{self.service_name}"
        else:
            headers["x-apexsigma-agent-chain"] = self.service_name

        headers["x-apexsigma-source-service"] = self.service_name
        headers["x-request-id"] = str(uuid.uuid4())

        logger.debug(
            "Prepared outbound headers",
            target_service=target_service,
            correlation_id=correlation_id,
            headers=list(headers.keys()),
        )

        return headers

    @contextmanager
    def trace_cross_service_call(
        self,
        target_service: str,
        operation: str,
        correlation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ):
        """Trace outbound calls to other ApexSigma services."""
        span_name = f"ingest.outbound.{target_service}.{operation}"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Set standard attributes
                span.set_attribute("service.name", self.service_name)
                span.set_attribute("service.version", self.service_version)
                span.set_attribute("operation.name", operation)
                span.set_attribute("target.service", target_service)
                span.set_attribute("call.direction", "outbound")

                # Set ApexSigma correlation attributes
                if correlation_id:
                    span.set_attribute("apexsigma.correlation_id", correlation_id)

                if workflow_id:
                    span.set_attribute("apexsigma.workflow_id", workflow_id)

                logger.info(
                    "Cross-service call initiated",
                    target_service=target_service,
                    operation=operation,
                    correlation_id=correlation_id,
                    trace_id=format(span.get_span_context().trace_id, "032x"),
                )

                yield span

                span.set_status(Status(StatusCode.OK))
                logger.info(
                    "Cross-service call completed",
                    target_service=target_service,
                    operation=operation,
                    correlation_id=correlation_id,
                )

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error(
                    "Cross-service call failed",
                    target_service=target_service,
                    operation=operation,
                    correlation_id=correlation_id,
                    error=str(e),
                )
                raise


# Global instance
ingest_e2e_tracing = InGestE2ETracing()


def get_ingest_e2e_tracing() -> InGestE2ETracing:
    """Get the global InGest-LLM E2E tracing instance."""
    return ingest_e2e_tracing
