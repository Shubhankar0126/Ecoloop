from __future__ import annotations

from dataclasses import dataclass

from ecoloop_backend.domain.base.aggregate_root import AggregateRoot
from ecoloop_backend.domain.base.entity import Entity
from ecoloop_common.events.domain_event import DomainEvent


class Building(Entity[str]):
    """Test-only entity used to verify identity semantics."""


class Campus(Entity[str]):
    """Test-only entity used to verify type-safe identity comparison."""


class Portfolio(AggregateRoot[str]):
    """Test-only aggregate root used to verify event handling."""


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioUpdated(DomainEvent):
    portfolio_id: str


def test_entity_compares_by_identity_and_type() -> None:
    assert Building("building-001") == Building("building-001")
    assert Building("building-001") != Building("building-002")
    assert Building("shared-id") != Campus("shared-id")
    assert hash(Building("building-001")) == hash(Building("building-001"))


def test_aggregate_root_records_and_pulls_domain_events() -> None:
    aggregate = Portfolio("portfolio-001")
    event = PortfolioUpdated(portfolio_id="portfolio-001")

    aggregate.record_event(event)

    assert aggregate.domain_events == (event,)
    assert aggregate.pull_domain_events() == (event,)
    assert not aggregate.domain_events
