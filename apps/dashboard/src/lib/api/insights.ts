import type { BuildingList } from "@/lib/api/schemas";

type SimulationAnalytics = {
  created_at: string;
  simulation_id: string;
  result: {
    diagnostics?: string[];
    metrics: {
      comfort?: {
        average_ppd_percent?: number | null;
        average_zone_humidity_percent?: number | null;
        average_zone_temperature_celsius?: number | null;
      } | null;
      energy?: {
        electricity_consumption_kwh?: number | null;
        total_site_energy_kwh?: number | null;
      } | null;
      hvac?: {
        cooling_energy_kwh?: number | null;
        equipment_loads_kwh?: number | null;
        heating_energy_kwh?: number | null;
        hvac_energy_kwh?: number | null;
      } | null;
    };
  };
};

export function getTotalEnergySaved(simulations: SimulationAnalytics[]) {
  const values = simulations
    .map((simulation) => simulation.result.metrics.energy?.total_site_energy_kwh ?? null)
    .filter((value): value is number => value !== null);

  if (values.length < 2) {
    return 0;
  }

  return Math.max(...values) - Math.min(...values);
}

export function getAverageComfortScore(simulations: SimulationAnalytics[]) {
  const ppdValues = simulations
    .map((simulation) => simulation.result.metrics.comfort?.average_ppd_percent ?? null)
    .filter((value): value is number => value !== null);

  if (ppdValues.length === 0) {
    return 0;
  }

  const averagePpd = ppdValues.reduce((total, value) => total + value, 0) / ppdValues.length;
  return Math.max(0, 100 - averagePpd);
}

export function getEstimatedCarbonReduction(simulations: SimulationAnalytics[]) {
  return getTotalEnergySaved(simulations) * 0.42;
}

export function createEnergyTrendData(simulations: SimulationAnalytics[]) {
  return [...simulations]
    .sort((left, right) => left.created_at.localeCompare(right.created_at))
    .map((simulation) => ({
      name: new Date(simulation.created_at).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric"
      }),
      energy: simulation.result.metrics.energy?.total_site_energy_kwh ?? 0,
      electricity: simulation.result.metrics.energy?.electricity_consumption_kwh ?? 0
    }));
}

export function createHvacUsageData(simulations: SimulationAnalytics[]) {
  return simulations.slice(0, 6).map((simulation) => ({
    name: simulation.simulation_id.slice(0, 8),
    heating: simulation.result.metrics.hvac?.heating_energy_kwh ?? 0,
    cooling: simulation.result.metrics.hvac?.cooling_energy_kwh ?? 0,
    equipment: simulation.result.metrics.hvac?.equipment_loads_kwh ?? 0
  }));
}

export function createComfortChartData(simulations: SimulationAnalytics[]) {
  return simulations.slice(0, 6).map((simulation) => ({
    name: simulation.simulation_id.slice(0, 8),
    temperature: simulation.result.metrics.comfort?.average_zone_temperature_celsius ?? 0,
    humidity: simulation.result.metrics.comfort?.average_zone_humidity_percent ?? 0,
    score: Math.max(
      0,
      100 - (simulation.result.metrics.comfort?.average_ppd_percent ?? 100)
    )
  }));
}

export function buildDashboardSummary(buildings: BuildingList, simulations: SimulationAnalytics[]) {
  return {
    totalBuildings: buildings.count,
    totalSimulations: simulations.length,
    energySaved: getTotalEnergySaved(simulations),
    comfortScore: getAverageComfortScore(simulations),
    carbonReduction: getEstimatedCarbonReduction(simulations)
  };
}

export function compareSimulations(
  baseline: SimulationAnalytics,
  candidate: SimulationAnalytics
) {
  const baselineEnergy = baseline.result.metrics.energy?.total_site_energy_kwh ?? 0;
  const candidateEnergy = candidate.result.metrics.energy?.total_site_energy_kwh ?? 0;
  const baselineHvac = baseline.result.metrics.hvac?.hvac_energy_kwh ?? 0;
  const candidateHvac = candidate.result.metrics.hvac?.hvac_energy_kwh ?? 0;
  const baselineComfort = baseline.result.metrics.comfort?.average_ppd_percent ?? 0;
  const candidateComfort = candidate.result.metrics.comfort?.average_ppd_percent ?? 0;

  return {
    energyDelta: candidateEnergy - baselineEnergy,
    hvacDelta: candidateHvac - baselineHvac,
    comfortDelta: candidateComfort - baselineComfort
  };
}
