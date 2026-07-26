"""EnergyPlus-specific exception taxonomy."""

from __future__ import annotations

from ecoloop_common.exceptions import ConfigurationError, InfrastructureError, ValidationError


class EnergyPlusError(InfrastructureError):
    """Base exception for EnergyPlus platform failures."""

    default_message = "The EnergyPlus platform failed."
    error_code = "energyplus.error"


class EnergyPlusConfigurationError(ConfigurationError):
    """Raised when EnergyPlus platform configuration is invalid."""

    default_message = "EnergyPlus platform configuration is invalid."
    error_code = "energyplus.configuration_error"


class EnergyPlusNotInstalledError(EnergyPlusError):
    """Raised when no supported EnergyPlus installation can be found."""

    default_message = "EnergyPlus is not installed."
    error_code = "energyplus.not_installed"


class EnergyPlusVersionUnsupportedError(EnergyPlusError):
    """Raised when a discovered EnergyPlus installation is unsupported."""

    default_message = "The discovered EnergyPlus version is unsupported."
    error_code = "energyplus.version_unsupported"


class InvalidSimulationInputError(ValidationError):
    """Base exception for invalid simulation input artifacts or options."""

    default_message = "The EnergyPlus simulation input is invalid."
    error_code = "energyplus.invalid_input"


class InvalidIDFError(InvalidSimulationInputError):
    """Raised when an IDF input file is invalid."""

    default_message = "The EnergyPlus IDF file is invalid."
    error_code = "energyplus.invalid_idf"


class InvalidWeatherFileError(InvalidSimulationInputError):
    """Raised when a weather input file is invalid."""

    default_message = "The EnergyPlus weather file is invalid."
    error_code = "energyplus.invalid_weather_file"


class SimulationError(EnergyPlusError):
    """Base exception for simulation execution failures."""

    default_message = "The EnergyPlus simulation failed."
    error_code = "energyplus.simulation_error"


class SimulationFailedError(SimulationError):
    """Raised when EnergyPlus completes with a failed simulation outcome."""

    default_message = "EnergyPlus reported a failed simulation run."
    error_code = "energyplus.simulation_failed"


class SimulationTimeoutError(SimulationFailedError):
    """Raised when a simulation exceeds its configured timeout."""

    default_message = "The EnergyPlus simulation timed out."
    error_code = "energyplus.simulation_timeout"


class OutputParseError(EnergyPlusError):
    """Raised when EnergyPlus output artifacts cannot be parsed."""

    default_message = "EnergyPlus output parsing failed."
    error_code = "energyplus.output_parse_error"


EnergyPlusNotInstalled = EnergyPlusNotInstalledError
EnergyPlusVersionUnsupported = EnergyPlusVersionUnsupportedError
InvalidSimulationInput = InvalidSimulationInputError
InvalidIDF = InvalidIDFError
InvalidWeatherFile = InvalidWeatherFileError
SimulationFailed = SimulationFailedError
SimulationTimeout = SimulationTimeoutError
