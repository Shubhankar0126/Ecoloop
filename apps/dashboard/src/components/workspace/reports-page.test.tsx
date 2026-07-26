import React from "react";
import { render, screen } from "@testing-library/react";

import { ReportsPage } from "@/components/workspace/reports-page";
import {
  executiveReportFixture,
  simulationDetailsFixture,
  simulationListFixture
} from "@/test/fixtures";

const hookMocks = vi.hoisted(() => ({
  useGenerateReportMutation: vi.fn(),
  useSimulationDetailsQuery: vi.fn(),
  useSimulationListQuery: vi.fn()
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () =>
    new URLSearchParams("simulationId=22222222-2222-2222-2222-222222222222")
}));

vi.mock("@/hooks/use-ecoloop-api", () => hookMocks);

describe("ReportsPage", () => {
  beforeEach(() => {
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
    hookMocks.useGenerateReportMutation.mockReturnValue({
      isPending: false,
      data: executiveReportFixture,
      mutateAsync: vi.fn()
    });
  });

  it("renders a generated executive report", () => {
    render(<ReportsPage />);

    expect(screen.getByText(executiveReportFixture.title)).toBeInTheDocument();
    expect(screen.getByText("Energy Snapshot")).toBeInTheDocument();
    expect(screen.getByText("Download (Soon)")).toBeDisabled();
  });

  it("renders an error state when simulation data fails", () => {
    hookMocks.useSimulationListQuery.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true
    });
    hookMocks.useSimulationDetailsQuery.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false
    });

    render(<ReportsPage />);

    expect(screen.getByText("Unable to load report data")).toBeInTheDocument();
  });
});
