import type {
  AiChatResponse,
  BuildingDetail,
  BuildingList,
  ExecutiveReport,
  SimulationDetail,
  SimulationList,
  SimulationSummary
} from "@/lib/api/schemas";

type SimulationFixtureOptions = {
  buildingId?: string | null;
  comfortPpd?: number;
  cooling?: number;
  createdAt?: string;
  durationMs?: number;
  electricity?: number;
  equipment?: number;
  finalStatus?: SimulationDetail["final_status"];
  heating?: number;
  hvac?: number;
  humidity?: number;
  id?: string;
  siteEnergy?: number;
  temperature?: number;
};

export function createBuildingDetail(
  overrides: Partial<BuildingDetail> = {}
): BuildingDetail {
  return {
    building_id: "11111111-1111-1111-1111-111111111111",
    name: "HQ Office Tower",
    description: "Primary commercial office baseline for dashboard analytics.",
    timezone: "Asia/Kolkata",
    created_at: "2026-07-26T10:15:00Z",
    simulation_count: 2,
    baseline_idf_path: "C:/ecoloop/buildings/hq-office.idf",
    weather_file_path: "C:/ecoloop/weather/IND_Delhi.421820_IWEC.epw",
    metadata: {
      portfolio: "north-region",
      building_type: "office"
    },
    ...overrides
  };
}

export const buildingDetailFixture = createBuildingDetail();

export const buildingListFixture: BuildingList = {
  count: 1,
  items: [
    {
      building_id: buildingDetailFixture.building_id,
      name: buildingDetailFixture.name,
      description: buildingDetailFixture.description,
      timezone: buildingDetailFixture.timezone,
      created_at: buildingDetailFixture.created_at,
      simulation_count: buildingDetailFixture.simulation_count
    }
  ]
};

export function createSimulationDetail(
  options: SimulationFixtureOptions = {}
): SimulationDetail {
  const id = options.id ?? "22222222-2222-2222-2222-222222222222";
  const buildingId = options.buildingId ?? buildingDetailFixture.building_id;

  return {
    simulation_id: id,
    building_id: buildingId,
    final_status: options.finalStatus ?? "succeeded",
    created_at: options.createdAt ?? "2026-07-26T10:20:00Z",
    idf_path: "C:/ecoloop/buildings/hq-office.idf",
    epw_path: "C:/ecoloop/weather/IND_Delhi.421820_IWEC.epw",
    duration_ms: options.durationMs ?? 41234,
    energyplus_version: "24.2.0",
    diagnostics_count: 1,
    result: {
      simulation_id: id,
      final_status: options.finalStatus ?? "succeeded",
      metrics: {
        values: {},
        energy: {
          total_site_energy_kwh: options.siteEnergy ?? 15420.6,
          electricity_consumption_kwh: options.electricity ?? 9630.2
        },
        hvac: {
          heating_energy_kwh: options.heating ?? 2410.4,
          cooling_energy_kwh: options.cooling ?? 3188.1,
          hvac_energy_kwh: options.hvac ?? 5598.5,
          equipment_loads_kwh: options.equipment ?? 744.0
        },
        comfort: {
          average_zone_temperature_celsius: options.temperature ?? 23.4,
          average_zone_humidity_percent: options.humidity ?? 48.2,
          average_pmv: 0.1,
          average_ppd_percent: options.comfortPpd ?? 9.8
        },
        weather: null,
        zones: [],
        monthly_summary: [],
        annual_summary: []
      },
      artifacts: [],
      diagnostics: ["Expected EnergyPlus output artifact was not produced: eplusout.eso."],
      metadata: {
        energyplus_version: "24.2.0",
        installation_root: "C:/EnergyPlusV24-2-0",
        command_line: ["energyplus", "-w", "C:/ecoloop/weather/IND_Delhi.421820_IWEC.epw"],
        exit_code: 0,
        duration_ms: options.durationMs ?? 41234,
        idf_checksum: "abc123",
        epw_checksum: "def456",
        hostname: "ecoloop-runner",
        started_at: "2026-07-26T10:20:00Z",
        completed_at: "2026-07-26T10:20:41Z"
      }
    }
  };
}

export const simulationDetailFixture = createSimulationDetail();

export function createSimulationSummary(
  options: SimulationFixtureOptions = {}
): SimulationSummary {
  const detail = createSimulationDetail(options);

  return {
    simulation_id: detail.simulation_id,
    building_id: detail.building_id,
    final_status: detail.final_status,
    created_at: detail.created_at,
    idf_path: detail.idf_path,
    epw_path: detail.epw_path,
    duration_ms: detail.duration_ms,
    energyplus_version: detail.energyplus_version,
    diagnostics_count: detail.diagnostics_count
  };
}

export const simulationListFixture: SimulationList = {
  count: 2,
  items: [
    createSimulationSummary(),
    createSimulationSummary({
      id: "33333333-3333-3333-3333-333333333333",
      createdAt: "2026-07-27T09:20:00Z",
      siteEnergy: 14800,
      electricity: 9020,
      hvac: 5200,
      heating: 2200,
      cooling: 2800,
      equipment: 700,
      comfortPpd: 7.6,
      temperature: 22.8
    })
  ]
};

export const simulationDetailsFixture: SimulationDetail[] = [
  createSimulationDetail(),
  createSimulationDetail({
    id: "33333333-3333-3333-3333-333333333333",
    createdAt: "2026-07-27T09:20:00Z",
    siteEnergy: 14800,
    electricity: 9020,
    hvac: 5200,
    heating: 2200,
    cooling: 2800,
    equipment: 700,
    comfortPpd: 7.6,
    temperature: 22.8
  })
];

export const aiChatResponseFixture: AiChatResponse = {
  latest_simulation_id: simulationDetailFixture.simulation_id,
  report: {
    executive_summary:
      "Cooling energy was reduced while keeping comfort within the requested band.",
    goal_achieved: true,
    iterations_used: 2,
    key_findings: [
      "Cooling energy dropped by 6.1% versus the baseline.",
      "Average PMV remained near neutral during occupied hours."
    ],
    recommendations: [
      "Adopt the revised HVAC weekday schedule as the next candidate baseline."
    ],
    next_actions: ["Validate the same schedule under a second representative weather file."]
  }
};

export const executiveReportFixture: ExecutiveReport = {
  simulation_id: simulationDetailFixture.simulation_id,
  building_id: buildingDetailFixture.building_id,
  building_name: buildingDetailFixture.name,
  generated_at: "2026-07-26T10:30:00Z",
  title: "Executive summary for the HQ baseline run",
  executive_summary:
    "The baseline office simulation completed successfully and produced normalized energy and comfort metrics for dashboard consumption.",
  final_status: "succeeded",
  highlights: [
    "Total site energy: 15420.60 kWh",
    "Electricity consumption: 9630.20 kWh"
  ],
  recommendations: ["Use this run as the reference baseline for future comparison reports."],
  diagnostics: ["Expected EnergyPlus output artifact was not produced: eplusout.eso."]
};
