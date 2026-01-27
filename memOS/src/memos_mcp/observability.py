import logging
import sys
from pathlib import Path

import structlog


def configure_logging(
    service_name: str, log_dir: str | Path, level: str = "INFO"
) -> None:
    """
    Configures structlog and standard logging to output JSON logs to file
    and pretty logs to console.
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Log file path: logs/service_name.json.log
    file_handler = logging.FileHandler(
        log_path / f"{service_name}.json.log", encoding="utf-8"
    )
    file_handler.setLevel(level)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file_handler.stream),
        cache_logger_on_first_use=True,
    )

    # Let's reset root logger
    logging.getLogger().handlers.clear()
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Console Handler (Pretty)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # File Handler (JSON)
    json_file_handler = logging.FileHandler(
        log_path / f"{service_name}.json.log", encoding="utf-8"
    )
    json_file_handler.setLevel(level)

    # Processors shared by both
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # Console formatter
    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Formatter for Console (Pretty)
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(),
        foreign_pre_chain=shared_processors,
    )
    console_handler.setFormatter(console_formatter)

    # Formatter for File (JSON)
    def add_service_name(logger, method_name, event_dict):
        event_dict["service"] = service_name
        return event_dict

    json_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors
        + [add_service_name, structlog.processors.dict_tracebacks],
    )
    json_file_handler.setFormatter(json_formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(json_file_handler)

    # Silence noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING)

    # Set up global exception hook to log unhandled exceptions
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        root_logger.error(
            "Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = handle_exception
