import logging
import sys
import structlog
from app.core.config import settings

def _inject_correlation_id(logger, method_name, event_dict):
    """
    Reads the correlation ID from contextvars (from correlation middleware)
    and attaches it to the log record.
    """
    try:
        from app.middleware.correlation import get_correlation_id
        cid = get_correlation_id()
        if cid:
            event_dict["correlation_id"] = cid
    except Exception:
        pass
    return event_dict

def setup_logging():
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _inject_correlation_id,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.ENVIRONMENT == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        processor=processors[-1]
    ))

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)

    # Silence verbose libs
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)

setup_logging()
logger = structlog.get_logger("api-gateway")
