"""Planning logic for selecting the next MCP tool call."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from ecoloop_ai.models import PlannerDecision
from ecoloop_ai.prompts import PromptLibrary, render_prompt_json
from ecoloop_ai.state import AgentState
from ecoloop_ai.tools import McpToolClient
from ecoloop_common.exceptions import InfrastructureError


class Planner:
    """Use the configured chat model to pick the next MCP tool call."""

    def __init__(
        self,
        model: BaseChatModel,
        prompts: PromptLibrary,
        tool_client: McpToolClient,
        *,
        structured_output_method: str,
    ) -> None:
        """Initialize the planner with injected model, prompts, and MCP discovery."""
        self._model = model
        self._prompts = prompts
        self._tool_client = tool_client
        self._structured_output_method = structured_output_method

    def plan(self, state: AgentState) -> PlannerDecision:
        """Generate the next structured plan and tool call."""
        available_tools = self._tool_client.list_tools()
        if not available_tools:
            raise InfrastructureError("No MCP tools are available for agent planning.")

        prompt_value = self._prompts.planner_prompt().invoke(
            {
                "system_prompt": self._prompts.system_prompt(),
                "goal": render_prompt_json(state.goal),
                "conversation": render_prompt_json(state.conversation),
                "building_context": render_prompt_json(state.memory.building_context),
                "previous_optimizations": render_prompt_json(
                    state.memory.previous_optimizations
                ),
                "available_tools": render_prompt_json(available_tools),
                "simulation_history": render_prompt_json(state.simulation_history),
                "latest_analysis": render_prompt_json(state.latest_analysis),
                "latest_critique": render_prompt_json(state.latest_critique),
                "latest_tool_execution": render_prompt_json(state.latest_tool_execution),
            }
        )
        structured_model = self._model.with_structured_output(
            PlannerDecision,
            method=self._structured_output_method,
        )
        response = structured_model.invoke(prompt_value)
        return PlannerDecision.model_validate(response)


__all__ = ["Planner"]
