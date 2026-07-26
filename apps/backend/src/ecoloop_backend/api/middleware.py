from __future__ import annotations

import logging
from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from ecoloop_backend.infrastructure.request_context import reset_request_id, set_request_id


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, logger_name: str) -> None:
        super().__init__(app)
        self._logger = logging.getLogger(logger_name)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        token = set_request_id(request_id)
        started_at = perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            self._logger.exception(
                "Request failed",
                extra={
                    "event": "http_request_failed",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            raise
        finally:
            reset_request_id(token)

        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        self._logger.info(
            "Request completed",
            extra={
                "event": "http_request_completed",
                "request_id": request_id,
                "client_ip": request.client.host if request.client else None,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
