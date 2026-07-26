import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { BuildingsPage } from "@/components/workspace/buildings-page";
import { buildingDetailFixture, buildingListFixture } from "@/test/fixtures";

const hookMocks = vi.hoisted(() => ({
  useBuildingDetailsQuery: vi.fn(),
  useBuildingsQuery: vi.fn(),
  useCreateBuildingMutation: vi.fn()
}));

vi.mock("@/hooks/use-ecoloop-api", () => hookMocks);

describe("BuildingsPage", () => {
  beforeEach(() => {
    hookMocks.useBuildingsQuery.mockReturnValue({
      data: buildingListFixture,
      isLoading: false,
      isError: false
    });
    hookMocks.useBuildingDetailsQuery.mockReturnValue({
      data: buildingDetailFixture,
      isLoading: false
    });
    hookMocks.useCreateBuildingMutation.mockReturnValue({
      isPending: false,
      mutateAsync: vi.fn().mockResolvedValue(buildingDetailFixture)
    });
  });

  it("renders building cards and selected building details", async () => {
    const user = userEvent.setup();
    render(<BuildingsPage />);

    await user.click(screen.getByRole("button", { name: /hq office tower/i }));

    expect(screen.getByText("Baseline IDF")).toBeInTheDocument();
    expect(screen.getByText("portfolio: north-region")).toBeInTheDocument();
  });

  it("filters buildings and submits the create form", async () => {
    const user = userEvent.setup();
    const mutation = {
      isPending: false,
      mutateAsync: vi.fn().mockResolvedValue(buildingDetailFixture)
    };

    hookMocks.useCreateBuildingMutation.mockReturnValue(mutation);
    render(<BuildingsPage />);

    await user.type(screen.getByPlaceholderText("Search buildings..."), "missing");
    expect(screen.getByText("No buildings found")).toBeInTheDocument();

    await user.clear(screen.getByPlaceholderText("Search buildings..."));
    await user.type(screen.getByLabelText(/building name/i), "New Tower");
    await user.type(
      screen.getByLabelText(/metadata/i),
      "portfolio: west-region\nbuilding_type: lab"
    );
    await user.click(screen.getByRole("button", { name: /create building/i }));

    await waitFor(() => expect(mutation.mutateAsync).toHaveBeenCalled());
  });
});
