from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from ecoloop_backend.domain.health import HealthReport, HealthStatus

type Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class HealthService:
    def __init__(
        self,
        *,
        service_name: str,
        environment: str,
        version: str,
        logger: logging.Logger,
        clock: Clock = utc_now,
    ) -> None:
        self._service_name = service_name
        self._environment = environment
        self._version = version
        self._logger = logger
        self._clock = clock

    def live(self) -> HealthReport:
        report = self._build_report()
        self._logger.info("Liveness check completed", extra={"event": "health_live"})
        return report

    def ready(self) -> HealthReport:
        report = self._build_report()
        self._logger.info("Readiness check completed", extra={"event": "health_ready"})
        return report

    def _build_report(self) -> HealthReport:
        return HealthReport(
            status=HealthStatus.OK,
            service=self._service_name,
            environment=self._environment,
            version=self._version,
            checked_at=self._clock(),
        )
