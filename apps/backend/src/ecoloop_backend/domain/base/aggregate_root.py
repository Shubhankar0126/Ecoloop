"""Aggregate root abstraction for backend domain models."""

from __future__ import annotations

from collections.abc import Hashable

from ecoloop_backend.domain.base.entity import Entity
from ecoloop_common.events.domain_event import DomainEvent


class AggregateRoot[EntityIdT: Hashable](Entity[EntityIdT]):
    """Entity base class that records pending domain events."""

    __slots__ = ("_pending_events",)

    def __init__(self, entity_id: EntityIdT) -> None:
        """Initialize the aggregate root and its pending event queue."""
        super().__init__(entity_id)
        self._pending_events: list[DomainEvent] = []

    @property
    def domain_events(self) -> tuple[DomainEvent, ...]:
        """Return an immutable snapshot of currently pending domain events."""
        return tuple(self._pending_events)

    def record_event(self, event: DomainEvent) -> None:
        """Record a new domain event for later publication."""
        self._pending_events.append(event)

    def pull_domain_events(self) -> tuple[DomainEvent, ...]:
        """Return and clear all currently pending domain events."""
        events = tuple(self._pending_events)
        self._pending_events.clear()
        return events
