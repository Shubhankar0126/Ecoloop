import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AiPage } from "@/components/workspace/ai-page";
import {
  aiChatResponseFixture,
  simulationDetailsFixture,
  simulationListFixture
} from "@/test/fixtures";

const hookMocks = vi.hoisted(() => ({
  useAiChatMutation: vi.fn(),
  useSimulationDetailsQuery: vi.fn(),
  useSimulationListQuery: vi.fn()
}));

vi.mock("@/hooks/use-ecoloop-api", () => hookMocks);

describe("AiPage", () => {
  beforeEach(() => {
    hookMocks.useSimulationListQuery.mockReturnValue({
      data: simulationListFixture
    });
    hookMocks.useSimulationDetailsQuery.mockReturnValue({
      data: simulationDetailsFixture
    });
    hookMocks.useAiChatMutation.mockReturnValue({
      isPending: false,
      data: aiChatResponseFixture,
      mutateAsync: vi.fn().mockResolvedValue(aiChatResponseFixture)
    });
  });

  it("submits a goal and renders the AI response", async () => {
    const user = userEvent.setup();
    render(<AiPage />);

    await user.type(
      screen.getByLabelText(/goal/i),
      "Reduce cooling energy without degrading occupant comfort."
    );
    await user.click(screen.getByRole("button", { name: /ask ecoloop ai/i }));

    await waitFor(() =>
      expect(
        screen.getAllByText(aiChatResponseFixture.report.executive_summary).length
      ).toBeGreaterThanOrEqual(1)
    );

    expect(screen.getByText("Simulation Results")).toBeInTheDocument();
  });
});
