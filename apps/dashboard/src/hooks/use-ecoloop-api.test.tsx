import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";

import {
  useBuildingDetailsQuery,
  useRunSimulationMutation,
  useSimulationDetailsQuery
} from "@/hooks/use-ecoloop-api";
import {
  buildingDetailFixture,
  simulationDetailFixture,
  simulationListFixture
} from "@/test/fixtures";

const apiMocks = vi.hoisted(() => ({
  createBuilding: vi.fn(),
  generateReport: vi.fn(),
  getBuilding: vi.fn(),
  getSimulation: vi.fn(),
  listBuildings: vi.fn(),
  listSimulations: vi.fn(),
  runAiChat: vi.fn(),
  runSimulation: vi.fn()
}));

vi.mock("@/lib/api/client", () => ({
  ecoloopApi: apiMocks
}));

async function flushPromises() {
  await Promise.resolve();
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });

  return {
    queryClient,
    wrapper: ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
  };
}

describe("useEcoLoopApi hooks", () => {
  beforeEach(() => {
    apiMocks.getBuilding.mockReset();
    apiMocks.getSimulation.mockReset();
    apiMocks.runSimulation.mockReset();
  });

  it("loads one building detail only when a building id is present", async () => {
    apiMocks.getBuilding.mockResolvedValue(buildingDetailFixture);

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useBuildingDetailsQuery(buildingDetailFixture.building_id), {
      wrapper
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiMocks.getBuilding).toHaveBeenCalledWith(buildingDetailFixture.building_id);
  });

  it("loads simulation details for the listed simulation ids", async () => {
    apiMocks.getSimulation.mockResolvedValue(simulationDetailFixture);

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useSimulationDetailsQuery(simulationListFixture.items), {
      wrapper
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiMocks.getSimulation).toHaveBeenCalledTimes(simulationListFixture.items.length);
  });

  it("invalidates building and simulation queries after a run", async () => {
    apiMocks.runSimulation.mockResolvedValue(simulationDetailFixture);

    const { queryClient, wrapper } = createWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useRunSimulationMutation(), { wrapper });

    act(() => {
      result.current.mutate({
        idf_path: simulationDetailFixture.idf_path,
        epw_path: simulationDetailFixture.epw_path
      });
    });

    await flushPromises();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["simulations"] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["buildings"] });
  });
});
