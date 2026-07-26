import { ZodType } from "zod";

import {
  aiChatResponseSchema,
  buildingDetailSchema,
  buildingListSchema,
  executiveReportSchema,
  problemDetailsSchema,
  simulationDetailSchema,
  simulationListSchema,
  type ProblemDetails
} from "@/lib/api/schemas";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly problem: ProblemDetails | null;

  constructor(message: string, status: number, problem: ProblemDetails | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.problem = problem;
  }
}

async function parseError(response: Response) {
  try {
    const payload = await response.json();
    return problemDetailsSchema.safeParse(payload).success ? payload : null;
  } catch {
    return null;
  }
}

async function request<T>(
  path: string,
  schema: ZodType<T>,
  init?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    const problem = await parseError(response);
    throw new ApiError(problem?.detail ?? "The EcoLoop API request failed.", response.status, problem);
  }

  const json = await response.json();
  return schema.parse(json);
}

export const ecoloopApi = {
  listBuildings: () => request("/buildings", buildingListSchema),
  getBuilding: (buildingId: string) => request(`/buildings/${buildingId}`, buildingDetailSchema),
  createBuilding: (body: unknown) =>
    request("/buildings", buildingDetailSchema, {
      method: "POST",
      body: JSON.stringify(body)
    }),
  listSimulations: () => request("/simulations", simulationListSchema),
  getSimulation: (simulationId: string) =>
    request(`/simulations/${simulationId}`, simulationDetailSchema),
  runSimulation: (body: unknown) =>
    request("/simulations", simulationDetailSchema, {
      method: "POST",
      body: JSON.stringify(body)
    }),
  runAiChat: (body: unknown) =>
    request("/ai/chat", aiChatResponseSchema, {
      method: "POST",
      body: JSON.stringify(body)
    }),
  generateReport: (body: unknown) =>
    request("/reports", executiveReportSchema, {
      method: "POST",
      body: JSON.stringify(body)
    })
};
