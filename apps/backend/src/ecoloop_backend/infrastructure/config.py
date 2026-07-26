from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ecoloop_ai import AiAgentConfig
from ecoloop_energyplus import EnergyPlusPlatformConfig, OutputSettings


class AppEnvironment(StrEnum):
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AppSettings(BaseModel):
    name: str = "ecoloop-backend"
    version: str = "0.1.0"
    environment: AppEnvironment = AppEnvironment.LOCAL
    debug: bool = False


class ApiSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    base_path: str = "/api/v1"


class LoggingSettings(BaseModel):
    level: LogLevel = LogLevel.INFO
    access_logger_name: str = "ecoloop.access"
    application_logger_name: str = "ecoloop.application"


def _default_energyplus_output_root() -> Path:
    """Return the default absolute output root for local simulation artifacts."""
    return (Path.cwd() / "runtime" / "energyplus").resolve()


def _default_energyplus_platform_config() -> EnergyPlusPlatformConfig:
    """Build the default EnergyPlus platform configuration for the backend."""
    return EnergyPlusPlatformConfig(
        output=OutputSettings(root_directory=_default_energyplus_output_root())
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ECOLOOP_",
        env_nested_delimiter="__",
        extra="ignore",
        frozen=True,
    )

    app: AppSettings = Field(default_factory=AppSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    energyplus_platform: EnergyPlusPlatformConfig = Field(
        default_factory=_default_energyplus_platform_config
    )
    ai_agent: AiAgentConfig = Field(default_factory=AiAgentConfig)


def load_settings() -> Settings:
    return Settings()
