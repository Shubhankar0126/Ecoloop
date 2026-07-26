"""Base entity abstraction for backend domain models."""

from __future__ import annotations

from collections.abc import Hashable


class Entity[EntityIdT: Hashable]:
    """Base class for domain objects whose identity defines equality."""

    __slots__ = ("_id",)

    def __init__(self, entity_id: EntityIdT) -> None:
        """Initialize the entity with its immutable identity."""
        self._id = entity_id

    @property
    def id(self) -> EntityIdT:
        """Return the stable identity of the entity."""
        return self._id

    def same_identity_as(self, other: object) -> bool:
        """Return whether another object represents the same entity identity."""
        return type(self) is type(other) and getattr(other, "id", object()) == self.id

    def __eq__(self, other: object) -> bool:
        """Compare entities by concrete type and identifier."""
        return self.same_identity_as(other)

    def __hash__(self) -> int:
        """Hash entities by concrete type and identifier."""
        return hash((type(self), self.id))
