"""Reusable base type for immutable domain events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Immutable record describing something that happened in the domain."""

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        """Ensure event timestamps are always timezone-aware."""
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("DomainEvent.occurred_at must be timezone-aware.")

    @property
    def event_name(self) -> str:
        """Return the concrete event type name for logging and tracing."""
        return type(self).__name__
