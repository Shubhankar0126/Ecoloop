"""Reusable base type for lightweight immutable value objects."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ValueObject(ABC):
    """Base class for immutable objects compared entirely by their values.

    Dataclass-based subclasses should set ``eq=False`` so this implementation
    remains the single source of truth for equality and hashing behavior.
    """

    __slots__ = ()

    @abstractmethod
    def _comparison_values(self) -> tuple[object, ...]:
        """Return the ordered values that define equality for the object."""

    def as_tuple(self) -> tuple[object, ...]:
        """Expose the canonical value tuple used for equality and hashing."""
        return self._comparison_values()

    def __eq__(self, other: object) -> bool:
        """Compare value objects by type and canonical value tuple."""
        if type(self) is not type(other):
            return False

        assert isinstance(other, ValueObject)
        return self.as_tuple() == other.as_tuple()

    def __hash__(self) -> int:
        """Hash the value object by type and canonical value tuple."""
        return hash((type(self), self.as_tuple()))
