"""Lightweight domain base abstractions for the EcoLoop backend."""

from ecoloop_backend.domain.base.aggregate_root import AggregateRoot
from ecoloop_backend.domain.base.entity import Entity

__all__ = ["AggregateRoot", "Entity"]
