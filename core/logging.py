"""Structured logging configuration for PulseStream."""

import logging
import sys
from typing import Any, Dict

import structlog
from structlog.typing import FilteringBoundLogger


def configure_logging(log_level: str = "INFO", log_format: str = "json") -> FilteringBoundLogger:
    """Configure structured logging with structlog."""
    
    # Set log level
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Configure structlog
    if log_format.lower() == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            renderer,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Get logger
    logger = structlog.get_logger()
    
    return logger


def get_logger(name: str) -> FilteringBoundLogger:
    """Get a named logger instance."""
    return structlog.get_logger(name)


class LoggingMixin:
    """Mixin to add logging capabilities to classes."""
    
    @property
    def logger(self) -> FilteringBoundLogger:
        """Get logger for this class."""
        return get_logger(self.__class__.__name__)


def log_function_call(func_name: str, **kwargs: Any) -> Dict[str, Any]:
    """Create a consistent log entry for function calls."""
    return {
        "event": "function_call",
        "function": func_name,
        **kwargs,
    }


def log_api_request(method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
    """Create a consistent log entry for API requests."""
    return {
        "event": "api_request",
        "method": method,
        "path": path,
        **kwargs,
    }


def log_database_operation(operation: str, table: str, **kwargs: Any) -> Dict[str, Any]:
    """Create a consistent log entry for database operations."""
    return {
        "event": "database_operation",
        "operation": operation,
        "table": table,
        **kwargs,
    }


def log_celery_task(task_name: str, **kwargs: Any) -> Dict[str, Any]:
    """Create a consistent log entry for Celery tasks."""
    return {
        "event": "celery_task",
        "task": task_name,
        **kwargs,
    }
