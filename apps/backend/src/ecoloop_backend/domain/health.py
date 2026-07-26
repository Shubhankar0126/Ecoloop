from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class HealthStatus(StrEnum):
    OK = "ok"


@dataclass(frozen=True, slots=True)
class HealthReport:
    status: HealthStatus
    service: str
    environment: str
    version: str
    checked_at: datetime
