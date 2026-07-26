from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pytest

from ecoloop_common.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class BuildingInspected(DomainEvent):
    building_id: str


def test_domain_event_generates_identity_name_and_timestamp() -> None:
    event = BuildingInspected(building_id="building-001")

    assert event.event_id
    assert event.event_name == "BuildingInspected"
    assert event.occurred_at.tzinfo is not None
    assert event.occurred_at.utcoffset() is not None


def test_domain_event_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        BuildingInspected(
            building_id="building-001",
            occurred_at=datetime.now(),
        )
