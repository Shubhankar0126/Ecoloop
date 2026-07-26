from __future__ import annotations

from ecoloop_common.exceptions import ConfigurationError, InfrastructureError, ValidationError
from ecoloop_energyplus.domain.exceptions import (
    EnergyPlusConfigurationError,
    EnergyPlusError,
    EnergyPlusNotInstalled,
    EnergyPlusNotInstalledError,
    EnergyPlusVersionUnsupported,
    EnergyPlusVersionUnsupportedError,
    InvalidIDF,
    InvalidIDFError,
    InvalidSimulationInput,
    InvalidSimulationInputError,
    InvalidWeatherFile,
    InvalidWeatherFileError,
    OutputParseError,
    SimulationError,
    SimulationFailed,
    SimulationFailedError,
    SimulationTimeout,
    SimulationTimeoutError,
)


def test_energyplus_exception_hierarchy_is_consistent() -> None:
    assert issubclass(EnergyPlusError, InfrastructureError)
    assert issubclass(EnergyPlusConfigurationError, ConfigurationError)
    assert issubclass(EnergyPlusNotInstalledError, EnergyPlusError)
    assert issubclass(EnergyPlusVersionUnsupportedError, EnergyPlusError)
    assert issubclass(InvalidSimulationInputError, ValidationError)
    assert issubclass(InvalidIDFError, InvalidSimulationInputError)
    assert issubclass(InvalidWeatherFileError, InvalidSimulationInputError)
    assert issubclass(SimulationError, EnergyPlusError)
    assert issubclass(SimulationFailedError, SimulationError)
    assert issubclass(SimulationTimeoutError, SimulationFailedError)
    assert issubclass(OutputParseError, EnergyPlusError)


def test_public_aliases_preserve_requested_exception_names() -> None:
    assert EnergyPlusNotInstalled is EnergyPlusNotInstalledError
    assert EnergyPlusVersionUnsupported is EnergyPlusVersionUnsupportedError
    assert InvalidSimulationInput is InvalidSimulationInputError
    assert InvalidIDF is InvalidIDFError
    assert InvalidWeatherFile is InvalidWeatherFileError
    assert SimulationFailed is SimulationFailedError
    assert SimulationTimeout is SimulationTimeoutError


def test_energyplus_exception_codes_are_stable() -> None:
    assert EnergyPlusNotInstalled().error_code == "energyplus.not_installed"
    assert InvalidIDF().error_code == "energyplus.invalid_idf"
    assert SimulationTimeout().error_code == "energyplus.simulation_timeout"
    assert OutputParseError().error_code == "energyplus.output_parse_error"
