import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import {
  AboutStoryPage,
  ArchitectureStoryPage,
  FeatureHighlightsPage,
  LandingPage
} from "@/components/marketing/marketing-pages";

describe("marketing pages", () => {
  it("renders the landing page hero and developer section", () => {
    render(<LandingPage />);

    expect(
      screen.getByText(/optimize commercial buildings with simulation-backed intelligence/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /launch dashboard/i })).toHaveAttribute(
      "href",
      "/dashboard"
    );
    expect(screen.getByRole("link", { name: /watch demo/i })).toHaveAttribute("href", "/demo");
    expect(screen.getByText("Shubhankar Pandey")).toBeInTheDocument();
    expect(screen.getByText("Designed & Developed by Shubhankar Pandey")).toBeInTheDocument();
  });

  it("renders the feature overview page", () => {
    render(<FeatureHighlightsPage />);

    expect(screen.getByText(/premium product surface/i)).toBeInTheDocument();
    expect(screen.getByText("Landing Narrative")).toBeInTheDocument();
    expect(screen.getByText("Workspace Analytics")).toBeInTheDocument();
  });

  it("renders the architecture story page and updates the selected detail", async () => {
    const user = userEvent.setup();
    render(<ArchitectureStoryPage />);

    expect(
      screen.getByText(/product layer respects every backend boundary/i)
    ).toBeInTheDocument();
    expect(screen.getByText("REST Contract")).toBeInTheDocument();

    const energyPlusButton = screen.getByText("EnergyPlus").closest("button");
    expect(energyPlusButton).not.toBeNull();

    await user.click(energyPlusButton!);

    expect(
      screen.getByText(/no fabricated metrics or bypassed execution paths are allowed here/i)
    ).toBeInTheDocument();
  });

  it("renders the about page and creator attribution", () => {
    render(<AboutStoryPage />);

    expect(screen.getByText(/sustainable building operations/i)).toBeInTheDocument();
    expect(screen.getByText("Shubhankar Pandey")).toBeInTheDocument();
    expect(screen.getByText("Designed & Developed by Shubhankar Pandey")).toBeInTheDocument();
  });
});
