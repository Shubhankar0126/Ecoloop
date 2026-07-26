"""Shared normalization helpers used by EnergyPlus output parsers."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_energyplus.domain.models import (
    ComfortMetrics,
    EnergyMetrics,
    HVACMetrics,
    SimulationMetrics,
    SimulationMetricValue,
    SummaryEntry,
    SummaryTable,
    WeatherMetrics,
    ZoneMetrics,
)

_MONTHLY_KEYWORDS = ("monthly",)
_ANNUAL_KEYWORDS = ("annual", "end uses", "utility performance")
_NON_ZONE_KEYS = {"environment", "facility", "site", "whole building"}
_TEMPERATURE_ALIASES = ("zone mean air temperature", "zone air temperature")
_HUMIDITY_ALIASES = ("zone air relative humidity", "zone mean air humidity")
_PMV_ALIASES = ("fanger model pmv", "thermal comfort pmv", "zone thermal comfort pmv")
_PPD_ALIASES = ("fanger model ppd", "thermal comfort ppd", "zone thermal comfort ppd")
_WEATHER_TEMPERATURE_ALIASES = (
    "site outdoor air drybulb temperature",
    "outdoor dry bulb temperature",
    "outdoor drybulb temperature",
)
_WEATHER_HUMIDITY_ALIASES = (
    "site outdoor air relative humidity",
    "outdoor relative humidity",
)
_TOTAL_SITE_ENERGY_ALIASES = ("total site energy", "facility total site energy")
_ELECTRICITY_ALIASES = ("electricity consumption", "electricity")
_HEATING_ALIASES = ("heating energy", "heating")
_COOLING_ALIASES = ("cooling energy", "cooling")
_HVAC_ALIASES = ("hvac energy", "total hvac")
_EQUIPMENT_ALIASES = ("equipment loads", "equipment load", "equipment")
_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


class ParsedSeries(BaseModel):
    """A normalized numeric series extracted from a parser-specific artifact."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    key: str | None = None
    unit: str | None = None
    frequency: str | None = None
    values: tuple[float, ...] = ()
    source_table: str | None = None
    source_artifact: str | None = None


class SummaryCell(BaseModel):
    """One normalized summary cell extracted from an EnergyPlus artifact."""

    model_config = ConfigDict(frozen=True)

    table_name: str = Field(min_length=1)
    row_name: str = Field(min_length=1)
    column_name: str = Field(min_length=1)
    value: float | int | str | bool
    unit: str | None = None
    report_name: str | None = None
    source_artifact: str | None = None


@dataclass(frozen=True)
class _MetricExtraction:
    """Internal normalized metric source used during parser assembly."""

    value: float
    unit: str | None
    source_table: str | None
    source_artifact: str | None


class MetricNormalizer:
    """Convert parser-neutral series and summary cells into domain metrics."""

    def build_metrics(
        self,
        *,
        series: tuple[ParsedSeries, ...] = (),
        summary_cells: tuple[SummaryCell, ...] = (),
    ) -> SimulationMetrics:
        """Build normalized domain metrics from generic parser outputs."""
        summary_tables = self.build_summary_tables(summary_cells)
        monthly_summary = tuple(
            table
            for table in summary_tables
            if self._contains_keywords(
                f"{table.report_name or ''} {table.name}",
                _MONTHLY_KEYWORDS,
            )
        )
        annual_summary = tuple(
            table
            for table in summary_tables
            if self._contains_keywords(
                f"{table.report_name or ''} {table.name}",
                _ANNUAL_KEYWORDS,
            )
        )

        energy_sources = {
            "total_site_energy_kwh": self._first_metric(
                summary_cells=summary_cells,
                summary_aliases=_TOTAL_SITE_ENERGY_ALIASES,
                series=series,
                series_aliases=_TOTAL_SITE_ENERGY_ALIASES,
                energy=True,
            ),
            "electricity_consumption_kwh": self._first_metric(
                summary_cells=summary_cells,
                summary_aliases=_ELECTRICITY_ALIASES,
                series=series,
                series_aliases=_ELECTRICITY_ALIASES,
                energy=True,
            ),
        }
        hvac_sources = {
            "heating_energy_kwh": self._first_metric(
                summary_cells=summary_cells,
                summary_aliases=_HEATING_ALIASES,
                series=series,
                series_aliases=_HEATING_ALIASES,
                energy=True,
            ),
            "cooling_energy_kwh": self._first_metric(
                summary_cells=summary_cells,
                summary_aliases=_COOLING_ALIASES,
                series=series,
                series_aliases=_COOLING_ALIASES,
                energy=True,
            ),
            "hvac_energy_kwh": self._first_metric(
                summary_cells=summary_cells,
                summary_aliases=_HVAC_ALIASES,
                series=series,
                series_aliases=_HVAC_ALIASES,
                energy=True,
            ),
            "equipment_loads_kwh": self._first_metric(
                summary_cells=summary_cells,
                summary_aliases=_EQUIPMENT_ALIASES,
                series=series,
                series_aliases=_EQUIPMENT_ALIASES,
                energy=True,
            ),
        }
        zones = self._build_zone_metrics(series)
        comfort = self._build_comfort_metrics(zones)
        weather = self._build_weather_metrics(series)

        energy = self._build_energy_metrics(energy_sources)
        hvac = self._build_hvac_metrics(hvac_sources)
        values = self._build_flat_values(
            energy=energy,
            energy_sources=energy_sources,
            hvac=hvac,
            hvac_sources=hvac_sources,
            comfort=comfort,
            weather=weather,
            zones=zones,
        )

        return SimulationMetrics(
            values=values,
            energy=energy,
            hvac=hvac,
            comfort=comfort,
            weather=weather,
            zones=zones,
            monthly_summary=monthly_summary,
            annual_summary=annual_summary,
        )

    def build_summary_tables(
        self,
        summary_cells: tuple[SummaryCell, ...],
    ) -> tuple[SummaryTable, ...]:
        """Group normalized summary cells into reusable domain tables."""
        grouped_entries: dict[tuple[str, str | None], list[SummaryEntry]] = {}

        for cell in summary_cells:
            key = (cell.table_name, cell.report_name)
            grouped_entries.setdefault(key, []).append(
                SummaryEntry(
                    row_name=cell.row_name,
                    column_name=cell.column_name,
                    value=cell.value,
                    unit=cell.unit,
                    source_table=cell.table_name,
                    source_artifact=cell.source_artifact,
                )
            )

        return tuple(
            SummaryTable(name=table_name, report_name=report_name, entries=tuple(entries))
            for (table_name, report_name), entries in grouped_entries.items()
        )

    @staticmethod
    def coerce_scalar(raw_value: str) -> float | int | str | bool:
        """Convert raw scalar text into a normalized Python value."""
        normalized_value = raw_value.strip()
        lowered = normalized_value.casefold()

        if lowered == "true":
            return True

        if lowered == "false":
            return False

        try:
            integer_value = int(normalized_value)
        except ValueError:
            integer_value = None

        if integer_value is not None and normalized_value == str(integer_value):
            return integer_value

        try:
            return float(normalized_value)
        except ValueError:
            return normalized_value

    def _build_energy_metrics(
        self,
        sources: dict[str, _MetricExtraction | None],
    ) -> EnergyMetrics | None:
        """Build normalized energy metrics when at least one value is available."""
        if all(source is None for source in sources.values()):
            return None

        return EnergyMetrics(
            total_site_energy_kwh=(
                sources["total_site_energy_kwh"].value
                if sources["total_site_energy_kwh"] is not None
                else None
            ),
            electricity_consumption_kwh=(
                sources["electricity_consumption_kwh"].value
                if sources["electricity_consumption_kwh"] is not None
                else None
            ),
        )

    def _build_hvac_metrics(
        self,
        sources: dict[str, _MetricExtraction | None],
    ) -> HVACMetrics | None:
        """Build normalized HVAC metrics when at least one value is available."""
        if all(source is None for source in sources.values()):
            return None

        return HVACMetrics(
            heating_energy_kwh=(
                sources["heating_energy_kwh"].value
                if sources["heating_energy_kwh"] is not None
                else None
            ),
            cooling_energy_kwh=(
                sources["cooling_energy_kwh"].value
                if sources["cooling_energy_kwh"] is not None
                else None
            ),
            hvac_energy_kwh=(
                sources["hvac_energy_kwh"].value
                if sources["hvac_energy_kwh"] is not None
                else None
            ),
            equipment_loads_kwh=(
                sources["equipment_loads_kwh"].value
                if sources["equipment_loads_kwh"] is not None
                else None
            ),
        )

    def _build_zone_metrics(self, series: tuple[ParsedSeries, ...]) -> tuple[ZoneMetrics, ...]:
        """Build per-zone metrics from normalized time-series data."""
        zone_series: dict[str, dict[str, float | None]] = {}

        for item in series:
            zone_name = self._series_zone_name(item)
            if zone_name is None:
                continue

            zone_metrics = zone_series.setdefault(
                zone_name,
                {
                    "mean_air_temperature_celsius": None,
                    "mean_relative_humidity_percent": None,
                    "thermal_comfort_pmv": None,
                    "thermal_comfort_ppd_percent": None,
                },
            )
            average_value = self._average(item.values)
            if average_value is None:
                continue

            if self._series_matches(item, _TEMPERATURE_ALIASES):
                zone_metrics["mean_air_temperature_celsius"] = average_value
            elif self._series_matches(item, _HUMIDITY_ALIASES):
                zone_metrics["mean_relative_humidity_percent"] = average_value
            elif self._series_matches(item, _PMV_ALIASES):
                zone_metrics["thermal_comfort_pmv"] = average_value
            elif self._series_matches(item, _PPD_ALIASES):
                zone_metrics["thermal_comfort_ppd_percent"] = average_value

        return tuple(
            ZoneMetrics(zone_name=zone_name, **values)
            for zone_name, values in sorted(zone_series.items())
            if any(value is not None for value in values.values())
        )

    def _build_comfort_metrics(self, zones: tuple[ZoneMetrics, ...]) -> ComfortMetrics | None:
        """Build aggregated comfort metrics from normalized zone metrics."""
        if not zones:
            return None

        temperatures = tuple(
            zone.mean_air_temperature_celsius
            for zone in zones
            if zone.mean_air_temperature_celsius is not None
        )
        humidities = tuple(
            zone.mean_relative_humidity_percent
            for zone in zones
            if zone.mean_relative_humidity_percent is not None
        )
        pmv_values = tuple(
            zone.thermal_comfort_pmv for zone in zones if zone.thermal_comfort_pmv is not None
        )
        ppd_values = tuple(
            zone.thermal_comfort_ppd_percent
            for zone in zones
            if zone.thermal_comfort_ppd_percent is not None
        )

        if not any((temperatures, humidities, pmv_values, ppd_values)):
            return None

        return ComfortMetrics(
            average_zone_temperature_celsius=self._average(temperatures),
            average_zone_humidity_percent=self._average(humidities),
            average_pmv=self._average(pmv_values),
            average_ppd_percent=self._average(ppd_values),
        )

    def _build_weather_metrics(
        self,
        series: tuple[ParsedSeries, ...],
    ) -> WeatherMetrics | None:
        """Build aggregated weather metrics from environment-level series."""
        weather_temperature = self._first_series_average(series, _WEATHER_TEMPERATURE_ALIASES)
        weather_humidity = self._first_series_average(series, _WEATHER_HUMIDITY_ALIASES)
        if weather_temperature is None and weather_humidity is None:
            return None

        return WeatherMetrics(
            average_outdoor_dry_bulb_celsius=weather_temperature,
            average_outdoor_relative_humidity_percent=weather_humidity,
        )

    def _build_flat_values(
        self,
        *,
        energy: EnergyMetrics | None,
        energy_sources: dict[str, _MetricExtraction | None],
        hvac: HVACMetrics | None,
        hvac_sources: dict[str, _MetricExtraction | None],
        comfort: ComfortMetrics | None,
        weather: WeatherMetrics | None,
        zones: tuple[ZoneMetrics, ...],
    ) -> dict[str, SimulationMetricValue]:
        """Build the canonical flat metric mapping used by earlier Sprint 2A contracts."""
        values: dict[str, SimulationMetricValue] = {}
        self._add_scalar_value(
            values,
            key="energy.total_site_energy_kwh",
            value=energy.total_site_energy_kwh if energy is not None else None,
            unit="kWh",
            source=energy_sources["total_site_energy_kwh"],
        )
        self._add_scalar_value(
            values,
            key="energy.electricity_consumption_kwh",
            value=energy.electricity_consumption_kwh if energy is not None else None,
            unit="kWh",
            source=energy_sources["electricity_consumption_kwh"],
        )
        self._add_scalar_value(
            values,
            key="hvac.heating_energy_kwh",
            value=hvac.heating_energy_kwh if hvac is not None else None,
            unit="kWh",
            source=hvac_sources["heating_energy_kwh"],
        )
        self._add_scalar_value(
            values,
            key="hvac.cooling_energy_kwh",
            value=hvac.cooling_energy_kwh if hvac is not None else None,
            unit="kWh",
            source=hvac_sources["cooling_energy_kwh"],
        )
        self._add_scalar_value(
            values,
            key="hvac.hvac_energy_kwh",
            value=hvac.hvac_energy_kwh if hvac is not None else None,
            unit="kWh",
            source=hvac_sources["hvac_energy_kwh"],
        )
        self._add_scalar_value(
            values,
            key="hvac.equipment_loads_kwh",
            value=hvac.equipment_loads_kwh if hvac is not None else None,
            unit="kWh",
            source=hvac_sources["equipment_loads_kwh"],
        )
        self._add_scalar_value(
            values,
            key="comfort.average_zone_temperature_celsius",
            value=(
                comfort.average_zone_temperature_celsius if comfort is not None else None
            ),
            unit="C",
        )
        self._add_scalar_value(
            values,
            key="comfort.average_zone_humidity_percent",
            value=comfort.average_zone_humidity_percent if comfort is not None else None,
            unit="%",
        )
        self._add_scalar_value(
            values,
            key="comfort.average_pmv",
            value=comfort.average_pmv if comfort is not None else None,
            unit=None,
        )
        self._add_scalar_value(
            values,
            key="comfort.average_ppd_percent",
            value=comfort.average_ppd_percent if comfort is not None else None,
            unit="%",
        )
        self._add_scalar_value(
            values,
            key="weather.average_outdoor_dry_bulb_celsius",
            value=(
                weather.average_outdoor_dry_bulb_celsius if weather is not None else None
            ),
            unit="C",
        )
        self._add_scalar_value(
            values,
            key="weather.average_outdoor_relative_humidity_percent",
            value=(
                weather.average_outdoor_relative_humidity_percent
                if weather is not None
                else None
            ),
            unit="%",
        )

        for zone in zones:
            slug = self._slugify(zone.zone_name)
            self._add_scalar_value(
                values,
                key=f"zone.{slug}.mean_air_temperature_celsius",
                value=zone.mean_air_temperature_celsius,
                unit="C",
            )
            self._add_scalar_value(
                values,
                key=f"zone.{slug}.mean_relative_humidity_percent",
                value=zone.mean_relative_humidity_percent,
                unit="%",
            )
            self._add_scalar_value(
                values,
                key=f"zone.{slug}.thermal_comfort_pmv",
                value=zone.thermal_comfort_pmv,
                unit=None,
            )
            self._add_scalar_value(
                values,
                key=f"zone.{slug}.thermal_comfort_ppd_percent",
                value=zone.thermal_comfort_ppd_percent,
                unit="%",
            )

        return values

    def _add_scalar_value(
        self,
        values: dict[str, SimulationMetricValue],
        *,
        key: str,
        value: float | int | str | bool | None,
        unit: str | None,
        source: _MetricExtraction | None = None,
    ) -> None:
        """Add one canonical flat metric value when a value is present."""
        if value is None:
            return

        values[key] = SimulationMetricValue(
            value=value,
            unit=unit,
            source_artifact=source.source_artifact if source is not None else None,
            source_table=source.source_table if source is not None else None,
        )

    def _first_metric(
        self,
        *,
        summary_cells: tuple[SummaryCell, ...],
        summary_aliases: tuple[str, ...],
        series: tuple[ParsedSeries, ...],
        series_aliases: tuple[str, ...],
        energy: bool,
    ) -> _MetricExtraction | None:
        """Extract the first available summary or series metric for one semantic field."""
        summary_metric = self._first_summary_metric(summary_cells, summary_aliases, energy=energy)
        if summary_metric is not None:
            return summary_metric

        return self._sum_series_metric(series, series_aliases, energy=energy)

    def _first_summary_metric(
        self,
        summary_cells: tuple[SummaryCell, ...],
        aliases: tuple[str, ...],
        *,
        energy: bool,
    ) -> _MetricExtraction | None:
        """Extract the first matching numeric metric from summary cells."""
        for cell in summary_cells:
            if not self._cell_matches(cell, aliases):
                continue

            numeric_value = self._as_float(cell.value)
            if numeric_value is None:
                continue

            normalized_value = (
                self._energy_to_kwh(numeric_value, cell.unit)
                if energy
                else numeric_value
            )
            if normalized_value is None:
                continue

            return _MetricExtraction(
                value=normalized_value,
                unit="kWh" if energy else cell.unit,
                source_table=cell.table_name,
                source_artifact=cell.source_artifact,
            )

        return None

    def _sum_series_metric(
        self,
        series: tuple[ParsedSeries, ...],
        aliases: tuple[str, ...],
        *,
        energy: bool,
    ) -> _MetricExtraction | None:
        """Aggregate one semantic metric from matching numeric series."""
        matched_series = tuple(item for item in series if self._series_matches(item, aliases))
        if not matched_series:
            return None

        aggregated_values: list[float] = []
        for item in matched_series:
            for raw_value in item.values:
                normalized_value = (
                    self._energy_to_kwh(raw_value, item.unit) if energy else raw_value
                )
                if normalized_value is not None:
                    aggregated_values.append(normalized_value)

        if not aggregated_values:
            return None

        first_match = matched_series[0]
        return _MetricExtraction(
            value=(
                sum(aggregated_values)
                if energy
                else self._average(tuple(aggregated_values)) or 0.0
            ),
            unit="kWh" if energy else first_match.unit,
            source_table=first_match.source_table,
            source_artifact=first_match.source_artifact,
        )

    def _first_series_average(
        self,
        series: tuple[ParsedSeries, ...],
        aliases: tuple[str, ...],
    ) -> float | None:
        """Return the first average value for one semantic series family."""
        for item in series:
            if self._series_matches(item, aliases):
                return self._average(item.values)

        return None

    def _cell_matches(self, cell: SummaryCell, aliases: tuple[str, ...]) -> bool:
        """Determine whether one summary cell matches a semantic alias set."""
        haystack = " ".join(
            (
                cell.table_name,
                cell.report_name or "",
                cell.row_name,
                cell.column_name,
            )
        )
        return self._contains_keywords(haystack, aliases)

    def _series_matches(self, series: ParsedSeries, aliases: tuple[str, ...]) -> bool:
        """Determine whether one numeric series matches a semantic alias set."""
        haystack = " ".join((series.key or "", series.name, series.source_table or ""))
        return self._contains_keywords(haystack, aliases)

    def _series_zone_name(self, series: ParsedSeries) -> str | None:
        """Return a zone name for one series when the key appears to be zone-specific."""
        key = series.key or self._extract_key_from_name(series.name)
        if key is None:
            return None

        normalized_key = key.strip()
        if not normalized_key:
            return None

        if normalized_key.casefold() in _NON_ZONE_KEYS:
            return None

        return normalized_key

    @staticmethod
    def _extract_key_from_name(name: str) -> str | None:
        """Extract a key prefix from names that embed a colon-delimited object name."""
        if ":" not in name:
            return None

        key, _, _ = name.partition(":")
        return key.strip() or None

    @staticmethod
    def _contains_keywords(text: str, keywords: tuple[str, ...]) -> bool:
        """Check whether a text contains any semantic keyword alias."""
        normalized_text = text.casefold()
        return any(keyword in normalized_text for keyword in keywords)

    @staticmethod
    def _average(values: tuple[float, ...]) -> float | None:
        """Return the arithmetic mean for a sequence of numeric values."""
        if not values:
            return None

        return sum(values) / len(values)

    @staticmethod
    def _as_float(value: float | int | str | bool) -> float | None:
        """Convert a normalized scalar into a float when possible."""
        if isinstance(value, bool):
            return 1.0 if value else 0.0

        if isinstance(value, int | float):
            return float(value)

        try:
            return float(value)
        except ValueError:
            return None

    @staticmethod
    def _energy_to_kwh(value: float, unit: str | None) -> float | None:
        """Convert common EnergyPlus energy units to kWh."""
        if unit is None:
            return value

        normalized_unit = unit.strip().casefold().replace(" ", "")
        conversions = {
            "kwh": 1.0,
            "wh": 1 / 1000,
            "mwh": 1000.0,
            "j": 1 / 3_600_000,
            "kj": 1 / 3600,
            "mj": 1 / 3.6,
            "gj": 277.77777777777777,
            "btu": 0.00029307107,
            "kbtu": 0.29307107,
        }
        factor = conversions.get(normalized_unit)
        if factor is None:
            return None

        return value * factor

    @staticmethod
    def _slugify(value: str) -> str:
        """Build a stable slug for a zone metric key."""
        normalized_value = _SLUG_PATTERN.sub("_", value.casefold()).strip("_")
        return normalized_value or "zone"


__all__ = [
    "MetricNormalizer",
    "ParsedSeries",
    "SummaryCell",
]
