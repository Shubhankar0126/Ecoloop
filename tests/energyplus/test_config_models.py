from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from ecoloop_energyplus.config.models import (
    EnergyPlusPlatformConfig,
    EnergyPlusSettings,
    OutputSettings,
    SimulationSettings,
)


def test_energyplus_settings_defaults_support_discovery() -> None:
    settings = EnergyPlusSettings()

    assert settings.enabled is True
    assert settings.validate_on_startup is True
    assert settings.discover_on_path is True
    assert settings.installation_roots == ()
    assert settings.executable_path is None


def test_simulation_settings_reject_invalid_ranges() -> None:
    with pytest.raises(ValidationError, match="default_timeout_seconds"):
        SimulationSettings(
            default_timeout_seconds=7200,
            maximum_timeout_seconds=3600,
        )

    with pytest.raises(ValidationError, match="default_parallel_jobs"):
        SimulationSettings(
            default_parallel_jobs=3,
            maximum_parallel_jobs=2,
        )


def test_output_settings_require_absolute_root_directory() -> None:
    with pytest.raises(ValidationError, match="root_directory must be an absolute path"):
        OutputSettings(root_directory=Path("relative-output"))


def test_platform_config_composes_section_models() -> None:
    output = OutputSettings(root_directory=Path("C:/ecoloop/energyplus/output"))
    config = EnergyPlusPlatformConfig(output=output)

    assert config.output == output
    assert isinstance(config.energyplus, EnergyPlusSettings)
    assert isinstance(config.simulation, SimulationSettings)
