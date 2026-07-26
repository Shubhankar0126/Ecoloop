"""Framework-independent shared primitives for EcoLoop AI."""

from ecoloop_common.events.domain_event import DomainEvent
from ecoloop_common.value_objects.value_object import ValueObject

__all__ = ["DomainEvent", "ValueObject", "__version__"]

__version__ = "0.1.0"
