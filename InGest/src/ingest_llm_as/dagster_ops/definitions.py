"""Dagster Definitions - Entry point for Soma InGest pipelines.

Run with: dagster dev -m ingest_llm_as.dagster_ops.definitions
"""

from dagster import (
    Definitions,
    ScheduleDefinition,
    define_asset_job,
    EnvVar,
)

from .assets.memory_builder import memory_builder
from .assets.vector_indexer import vector_indexer
from .sensors.poison_pill_sensor import poison_pill_sensor
from .sensors.raw_lake_sensor import raw_lake_sensor
from .resources import (
    PostgresResource,
    RedisResource,
    LanceDBResource,
    OllamaResource,
    OmegaKGClient,
)


all_assets = [memory_builder, vector_indexer]

memory_pipeline_job = define_asset_job(
    name="memory_pipeline",
    selection="*",
    description="Full SimpleMem pipeline: compression → indexing",
)

memory_pipeline_schedule = ScheduleDefinition(
    job=memory_pipeline_job,
    cron_schedule="*/5 * * * *",
    default_status="RUNNING",
)

defs = Definitions(
    assets=all_assets,
    sensors=[poison_pill_sensor, raw_lake_sensor],
    schedules=[memory_pipeline_schedule],
    jobs=[memory_pipeline_job],
    resources={
        "postgres": PostgresResource(
            host=EnvVar("POSTGRES_HOST").get_value() or "localhost",
            port=int(EnvVar("POSTGRES_PORT").get_value() or "5432"),
            user=EnvVar("POSTGRES_USER").get_value() or "postgres",
            password=EnvVar("POSTGRES_PASSWORD").get_value() or "postgres",
            database=EnvVar("POSTGRES_DB").get_value() or "soma_data",
        ),
        "redis": RedisResource(
            url=EnvVar("REDIS_URL").get_value() or "redis://localhost:6379/0",
        ),
        "lancedb": LanceDBResource(
            uri=EnvVar("LANCEDB_URI").get_value() or "D:/docker-data/LanceDB",
            table_name=EnvVar("LANCEDB_TABLE").get_value() or "soma_memories",
        ),
        "ollama": OllamaResource(
            base_url=EnvVar("OLLAMA_BASE_URL").get_value()
            or "http://model-runner.docker.internal",
            embedding_model=EnvVar("OLLAMA_MODEL").get_value()
            or "qwen3-embedding:0.6B-F16",
        ),
        "omegakg": OmegaKGClient(
            base_url=EnvVar("OMEGAKG_API_URL").get_value() or "http://localhost:8765",
        ),
    },
)
