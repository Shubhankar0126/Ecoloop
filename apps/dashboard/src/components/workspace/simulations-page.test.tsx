import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SimulationsPage } from "@/components/workspace/simulations-page";
import {
  buildingListFixture,
  simulationDetailsFixture,
  simulationListFixture
} from "@/test/fixtures";

const hookMocks = vi.hoisted(() => ({
  useBuildingsQuery: vi.fn(),
  useRunSimulationMutation: vi.fn(),
  useSimulationDetailsQuery: vi.fn(),
  useSimulationListQuery: vi.fn()
}));

vi.mock("@/hooks/use-ecoloop-api", () => hookMocks);

describe("SimulationsPage", () => {
  beforeEach(() => {
    hookMocks.useBuildingsQuery.mockReturnValue({
      data: buildingListFixture,
      isLoading: false,
      isError: false
    });
    hookMocks.useSimulationListQuery.mockReturnValue({
      data: simulationListFixture,
      isLoading: false,
      isError: false
    });
    hookMocks.useSimulationDetailsQuery.mockReturnValue({
      data: simulationDetailsFixture,
      isLoading: false,
      isError: false
    });
    hookMocks.useRunSimulationMutation.mockReturnValue({
      isPending: false,
      mutateAsync: vi.fn()
    });
  });

  it("renders simulation history and detail views", async () => {
    const user = userEvent.setup();
    render(<SimulationsPage />);

    expect(screen.getByText("Simulation History")).toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: "View" })[0]);
    expect(screen.getByText("Simulation Detail")).toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: /compare/i })[0]);
    await user.click(screen.getAllByRole("button", { name: /compare/i })[1]);
    expect(screen.getByText("Simulation Comparison")).toBeInTheDocument();
  });
});
