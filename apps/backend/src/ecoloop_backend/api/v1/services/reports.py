"""Backend service for deterministic executive report generation."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from logging import Logger
from uuid import UUID

from ecoloop_backend.api.v1.schemas.reports import ExecutiveReportResponse, ReportCreateRequest
from ecoloop_backend.api.v1.services.state import BackendRuntimeState
from ecoloop_energyplus import SimulationResult, SimulationStatus

type Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class ExecutiveReportService:
    """Generate deterministic executive reports from stored simulation history."""

    def __init__(
        self,
        *,
        state: BackendRuntimeState,
        logger: Logger,
        clock: Clock | None = None,
    ) -> None:
        """Initialize the service with shared runtime state and logging."""
        self._state = state
        self._logger = logger
        self._clock = clock or _utc_now

    def generate_report(self, request: ReportCreateRequest) -> ExecutiveReportResponse | None:
        """Generate one executive report when the target simulation exists."""
        with self._state.lock:
            simulation = self._state.simulations.get(request.simulation_id)
            building = (
                None
                if simulation is None or simulation.building_id is None
                else self._state.buildings.get(simulation.building_id)
            )

        if simulation is None:
            return None

        response = ExecutiveReportResponse(
            simulation_id=simulation.simulation_id,
            building_id=simulation.building_id,
            building_name=None if building is None else building.name,
            generated_at=self._clock(),
            title=request.title
            or self._default_title(
                simulation.simulation_id,
                None if building is None else building.name,
            ),
            executive_summary=self._build_summary(
                simulation.result,
                None if building is None else building.name,
            ),
            final_status=simulation.final_status,
            highlights=self._build_highlights(simulation.result),
            recommendations=self._build_recommendations(simulation.result),
            diagnostics=simulation.result.diagnostics if request.include_diagnostics else (),
        )
        self._logger.info(
            "Executive report generated",
            extra={
                "event": "executive_report_generated",
                "simulation_id": str(response.simulation_id),
                "building_id": str(response.building_id) if response.building_id else None,
                "final_status": response.final_status.value,
            },
        )
        return response

    def _default_title(self, simulation_id: UUID, building_name: str | None) -> str:
        """Build a stable report title when the caller does not provide one."""
        if building_name is None:
            return f"Executive report for simulation {simulation_id}"

        return f"Executive report for {building_name}"

    def _build_summary(self, result: SimulationResult, building_name: str | None) -> str:
        """Create a concise executive summary from simulation status and metrics."""
        subject = (
            f"The simulation for {building_name}" if building_name is not None else "The simulation"
        )
        status_fragment = result.final_status.value.replace("_", " ")
        summary = f"{subject} completed with status '{status_fragment}'."
        energy = result.metrics.energy
        comfort = result.metrics.comfort

        details: list[str] = []
        if energy is not None and energy.total_site_energy_kwh is not None:
            details.append(f"Total site energy was {energy.total_site_energy_kwh:.2f} kWh.")
        if comfort is not None and comfort.average_zone_temperature_celsius is not None:
            details.append(
                f"Average zone temperature was {comfort.average_zone_temperature_celsius:.2f} C."
            )
        if not details and result.diagnostics:
            details.append("Diagnostics were captured for follow-up review.")

        return " ".join((summary, *details)).strip()

    def _build_highlights(self, result: SimulationResult) -> tuple[str, ...]:
        """Create human-readable highlights from normalized metrics."""
        highlights: list[str] = []
        energy = result.metrics.energy
        hvac = result.metrics.hvac
        comfort = result.metrics.comfort

        if energy is not None and energy.total_site_energy_kwh is not None:
            highlights.append(f"Total site energy: {energy.total_site_energy_kwh:.2f} kWh")
        if energy is not None and energy.electricity_consumption_kwh is not None:
            highlights.append(
                f"Electricity consumption: {energy.electricity_consumption_kwh:.2f} kWh"
            )
        if hvac is not None and hvac.hvac_energy_kwh is not None:
            highlights.append(f"HVAC energy: {hvac.hvac_energy_kwh:.2f} kWh")
        if comfort is not None and comfort.average_zone_temperature_celsius is not None:
            highlights.append(
                f"Average zone temperature: {comfort.average_zone_temperature_celsius:.2f} C"
            )
        if comfort is not None and comfort.average_zone_humidity_percent is not None:
            highlights.append(
                f"Average zone humidity: {comfort.average_zone_humidity_percent:.2f}%"
            )
        if not highlights:
            highlights.append("No normalized simulation metrics were available for this report.")

        return tuple(highlights)

    def _build_recommendations(self, result: SimulationResult) -> tuple[str, ...]:
        """Generate neutral operational recommendations from result completeness and status."""
        recommendations: list[str] = []
        if result.final_status is not SimulationStatus.SUCCEEDED:
            recommendations.append(
                "Review EnergyPlus diagnostics before using this simulation as a planning baseline."
            )
        if not result.metrics.zones:
            recommendations.append(
                "Enable zone-level output variables to improve dashboard analytics and reporting."
            )
        if result.final_status is SimulationStatus.SUCCEEDED and not result.diagnostics:
            recommendations.append(
                "Use this run as the reference baseline for future comparison reports."
            )
        if not recommendations:
            recommendations.append(
                "Review the captured metrics and diagnostics with the building operations team."
            )

        return tuple(recommendations)


__all__ = ["ExecutiveReportService"]
