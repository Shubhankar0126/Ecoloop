from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Final

from ecoloop_backend.infrastructure.config import Settings
from ecoloop_backend.infrastructure.request_context import get_request_id

_RESERVED_LOG_RECORD_FIELDS: Final[set[str]] = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}


class JsonFormatter(logging.Formatter):
    def __init__(self, *, service_name: str, environment: str) -> None:
        super().__init__()
        self._service_name = service_name
        self._environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self._service_name,
            "environment": self._environment,
            "request_id": getattr(record, "request_id", None) or get_request_id(),
        }
        payload.update(self._extra_fields(record))

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=self._default_serializer)

    def _extra_fields(self, record: logging.LogRecord) -> dict[str, object]:
        extra_fields: dict[str, object] = {}
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_FIELDS or key.startswith("_"):
                continue
            extra_fields[key] = value

        return extra_fields

    @staticmethod
    def _default_serializer(value: object) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter(
            service_name=settings.app.name,
            environment=settings.app.environment.value,
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.logging.level.value)

    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
