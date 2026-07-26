from __future__ import annotations

from dataclasses import dataclass

from ecoloop_common.value_objects.value_object import ValueObject


@dataclass(eq=False, frozen=True, slots=True)
class Temperature(ValueObject):
    celsius: int

    def _comparison_values(self) -> tuple[object, ...]:
        return (self.celsius,)


@dataclass(eq=False, frozen=True, slots=True)
class Humidity(ValueObject):
    percentage: int

    def _comparison_values(self) -> tuple[object, ...]:
        return (self.percentage,)


def test_value_object_compares_by_value_and_type() -> None:
    assert Temperature(22) == Temperature(22)
    assert Temperature(22) != Temperature(24)
    assert Temperature(22) != Humidity(22)


def test_value_object_hashes_and_exposes_tuple_representation() -> None:
    value_object = Temperature(22)

    assert value_object.as_tuple() == (22,)
    assert hash(value_object) == hash(Temperature(22))
