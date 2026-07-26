import React from "react";
import { render, screen } from "@testing-library/react";

import { DashboardPage } from "@/components/workspace/dashboard-page";
import {
  buildingListFixture,
  simulationDetailsFixture,
  simulationListFixture
} from "@/test/fixtures";

const hookMocks = vi.hoisted(() => ({
  useBuildingsQuery: vi.fn(),
  useSimulationDetailsQuery: vi.fn(),
  useSimulationListQuery: vi.fn()
}));

vi.mock("@/hooks/use-ecoloop-api", () => hookMocks);

describe("DashboardPage", () => {
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
  });

  it("renders the populated analytics workspace", () => {
    render(<DashboardPage />);

    expect(screen.getByText("Simulation workspace overview")).toBeInTheDocument();
    expect(screen.getByText("Total Buildings")).toBeInTheDocument();
    expect(screen.getByText("Energy Trend")).toBeInTheDocument();
    expect(screen.getByText("Quick Actions")).toBeInTheDocument();
  });

  it("renders the empty state when there are no simulations", () => {
    hookMocks.useSimulationListQuery.mockReturnValue({
      data: { count: 0, items: [] },
      isLoading: false,
      isError: false
    });
    hookMocks.useSimulationDetailsQuery.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false
    });

    render(<DashboardPage />);

    expect(screen.getByText("No simulation history yet")).toBeInTheDocument();
  });
});
