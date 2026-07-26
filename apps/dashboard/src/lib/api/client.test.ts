import { ecoloopApi } from "@/lib/api/client";
import {
  aiChatResponseFixture,
  buildingDetailFixture,
  buildingListFixture,
  executiveReportFixture,
  simulationDetailFixture,
  simulationListFixture
} from "@/test/fixtures";

function createJsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}

describe("ecoloopApi", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("parses the building and simulation endpoints", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(createJsonResponse(buildingListFixture))
      .mockResolvedValueOnce(createJsonResponse(buildingDetailFixture))
      .mockResolvedValueOnce(createJsonResponse(simulationListFixture))
      .mockResolvedValueOnce(createJsonResponse(simulationDetailFixture))
      .mockResolvedValueOnce(createJsonResponse(aiChatResponseFixture))
      .mockResolvedValueOnce(createJsonResponse(executiveReportFixture));

    await expect(ecoloopApi.listBuildings()).resolves.toEqual(buildingListFixture);
    await expect(ecoloopApi.getBuilding(buildingDetailFixture.building_id)).resolves.toEqual(
      buildingDetailFixture
    );
    await expect(ecoloopApi.listSimulations()).resolves.toEqual(simulationListFixture);
    await expect(
      ecoloopApi.getSimulation(simulationDetailFixture.simulation_id)
    ).resolves.toEqual(simulationDetailFixture);
    await expect(ecoloopApi.runAiChat({ goal: {} })).resolves.toEqual(aiChatResponseFixture);
    await expect(
      ecoloopApi.generateReport({ simulation_id: simulationDetailFixture.simulation_id })
    ).resolves.toEqual(executiveReportFixture);
  });

  it("raises ApiError with problem details payloads", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      createJsonResponse(
        {
          type: "https://ecoloop.ai/problems/validation",
          title: "Validation failed",
          status: 400,
          detail: "One or more fields are invalid.",
          instance: "/api/v1/buildings",
          error_code: "invalid_request",
          request_id: "req-123"
        },
        400
      )
    );

    await expect(ecoloopApi.listBuildings()).rejects.toMatchObject({
      name: "ApiError",
      status: 400,
      problem: expect.objectContaining({
        detail: "One or more fields are invalid.",
        error_code: "invalid_request"
      })
    });
  });

  it("falls back to a generic API error when the response is not problem+json", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response("upstream failure", {
        status: 503,
        headers: { "Content-Type": "text/plain" }
      })
    );

    await expect(ecoloopApi.listSimulations()).rejects.toEqual(
      expect.objectContaining({
        name: "ApiError",
        message: "The EcoLoop API request failed.",
        status: 503,
        problem: null
      })
    );
  });
});
