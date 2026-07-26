import { z } from "zod";

export const problemDetailsSchema = z.object({
  type: z.string(),
  title: z.string(),
  status: z.number(),
  detail: z.string(),
  instance: z.string(),
  error_code: z.string().optional(),
  request_id: z.string().optional(),
  context: z.record(z.unknown()).nullable().optional(),
  errors: z
    .array(
      z.object({
        name: z.string(),
        location: z.string(),
        message: z.string()
      })
    )
    .nullable()
    .optional()
});

export const buildingSummarySchema = z.object({
  building_id: z.string(),
  name: z.string(),
  description: z.string().nullable().optional(),
  timezone: z.string().nullable().optional(),
  created_at: z.string(),
  simulation_count: z.number()
});

export const buildingDetailSchema = buildingSummarySchema.extend({
  baseline_idf_path: z.string().nullable().optional(),
  weather_file_path: z.string().nullable().optional(),
  metadata: z.record(z.string())
});

export const buildingListSchema = z.object({
  count: z.number(),
  items: z.array(buildingSummarySchema)
});

export const simulationStatusSchema = z.enum([
  "pending",
  "validating",
  "queued",
  "running",
  "succeeded",
  "failed",
  "timed_out",
  "cancelled",
  "parse_failed"
]);

const energyMetricsSchema = z.object({
  total_site_energy_kwh: z.number().nullable().optional(),
  electricity_consumption_kwh: z.number().nullable().optional()
});

const hvacMetricsSchema = z.object({
  heating_energy_kwh: z.number().nullable().optional(),
  cooling_energy_kwh: z.number().nullable().optional(),
  hvac_energy_kwh: z.number().nullable().optional(),
  equipment_loads_kwh: z.number().nullable().optional()
});

const comfortMetricsSchema = z.object({
  average_zone_temperature_celsius: z.number().nullable().optional(),
  average_zone_humidity_percent: z.number().nullable().optional(),
  average_pmv: z.number().nullable().optional(),
  average_ppd_percent: z.number().nullable().optional()
});

const zoneMetricSchema = z.object({
  zone_name: z.string(),
  mean_air_temperature_celsius: z.number().nullable().optional(),
  mean_relative_humidity_percent: z.number().nullable().optional(),
  thermal_comfort_pmv: z.number().nullable().optional(),
  thermal_comfort_ppd_percent: z.number().nullable().optional()
});

const simulationMetricsSchema = z.object({
  values: z.record(z.unknown()),
  energy: energyMetricsSchema.nullable().optional(),
  hvac: hvacMetricsSchema.nullable().optional(),
  comfort: comfortMetricsSchema.nullable().optional(),
  weather: z.record(z.unknown()).nullable().optional(),
  zones: z.array(zoneMetricSchema).default([]),
  monthly_summary: z.array(z.unknown()).default([]),
  annual_summary: z.array(z.unknown()).default([])
});

const simulationMetadataSchema = z.object({
  energyplus_version: z.string().nullable().optional(),
  installation_root: z.string().nullable().optional(),
  command_line: z.array(z.string()).default([]),
  exit_code: z.number().nullable().optional(),
  duration_ms: z.number().nullable().optional(),
  idf_checksum: z.string().nullable().optional(),
  epw_checksum: z.string().nullable().optional(),
  hostname: z.string().nullable().optional(),
  started_at: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional()
});

export const simulationResultSchema = z.object({
  simulation_id: z.string(),
  final_status: simulationStatusSchema,
  metrics: simulationMetricsSchema,
  artifacts: z.array(z.unknown()).default([]),
  diagnostics: z.array(z.string()).default([]),
  metadata: simulationMetadataSchema
});

export const simulationSummarySchema = z.object({
  simulation_id: z.string(),
  building_id: z.string().nullable().optional(),
  final_status: simulationStatusSchema,
  created_at: z.string(),
  idf_path: z.string(),
  epw_path: z.string(),
  duration_ms: z.number().nullable().optional(),
  energyplus_version: z.string().nullable().optional(),
  diagnostics_count: z.number()
});

export const simulationDetailSchema = simulationSummarySchema.extend({
  result: simulationResultSchema
});

export const simulationListSchema = z.object({
  count: z.number(),
  items: z.array(simulationSummarySchema)
});

const optimizationReportSchema = z.object({
  executive_summary: z.string(),
  goal_achieved: z.boolean(),
  iterations_used: z.number(),
  key_findings: z.array(z.string()).default([]),
  recommendations: z.array(z.string()).default([]),
  next_actions: z.array(z.string()).default([])
});

export const aiChatResponseSchema = z.object({
  latest_simulation_id: z.string().nullable().optional(),
  report: optimizationReportSchema
});

export const executiveReportSchema = z.object({
  simulation_id: z.string(),
  building_id: z.string().nullable().optional(),
  building_name: z.string().nullable().optional(),
  generated_at: z.string(),
  title: z.string(),
  executive_summary: z.string(),
  final_status: simulationStatusSchema,
  highlights: z.array(z.string()).default([]),
  recommendations: z.array(z.string()).default([]),
  diagnostics: z.array(z.string()).default([])
});

export type ProblemDetails = z.infer<typeof problemDetailsSchema>;
export type BuildingSummary = z.infer<typeof buildingSummarySchema>;
export type BuildingDetail = z.infer<typeof buildingDetailSchema>;
export type BuildingList = z.infer<typeof buildingListSchema>;
export type SimulationSummary = z.infer<typeof simulationSummarySchema>;
export type SimulationDetail = z.infer<typeof simulationDetailSchema>;
export type SimulationList = z.infer<typeof simulationListSchema>;
export type AiChatResponse = z.infer<typeof aiChatResponseSchema>;
export type ExecutiveReport = z.infer<typeof executiveReportSchema>;
