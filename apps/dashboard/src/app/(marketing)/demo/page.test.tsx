import React from "react";
import { render, screen } from "@testing-library/react";

import DemoRoute from "@/app/(marketing)/demo/page";

describe("DemoRoute", () => {
  it("renders the placeholder demo experience", () => {
    render(<DemoRoute />);

    expect(screen.getByText("EcoLoop AI walkthrough")).toBeInTheDocument();
    expect(screen.getByText(/placeholder page reserves the production demo surface/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /launch dashboard/i })).toHaveAttribute(
      "href",
      "/dashboard"
    );
  });
});
