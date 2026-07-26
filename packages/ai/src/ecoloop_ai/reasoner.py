"""Analysis, critique, and reporting logic for the EcoLoop AI agent."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from ecoloop_ai.models import AnalysisResult, CriticResult, OptimizationReport
from ecoloop_ai.prompts import PromptLibrary, render_prompt_json
from ecoloop_ai.state import AgentState


class Reasoner:
    """Structured reasoning services used by analyzer, critic, and report nodes."""

    def __init__(
        self,
        model: BaseChatModel,
        prompts: PromptLibrary,
        *,
        structured_output_method: str,
    ) -> None:
        """Initialize the reasoning service with the shared chat model."""
        self._model = model
        self._prompts = prompts
        self._structured_output_method = structured_output_method

    def analyze(self, state: AgentState) -> AnalysisResult:
        """Analyze the latest tool execution and current optimization progress."""
        prompt_value = self._prompts.analyzer_prompt().invoke(
            {
                "system_prompt": self._prompts.system_prompt(),
                "goal": render_prompt_json(state.goal),
                "current_plan": render_prompt_json(state.current_plan),
                "latest_tool_execution": render_prompt_json(state.latest_tool_execution),
                "latest_simulation_result": render_prompt_json(state.latest_simulation_result),
                "simulation_history": render_prompt_json(state.simulation_history),
                "conversation": render_prompt_json(state.conversation),
            }
        )
        structured_model = self._model.with_structured_output(
            AnalysisResult,
            method=self._structured_output_method,
        )
        response = structured_model.invoke(prompt_value)
        return AnalysisResult.model_validate(response)

    def critique(self, state: AgentState) -> CriticResult:
        """Critique the current trajectory before the next planning loop."""
        prompt_value = self._prompts.critic_prompt().invoke(
            {
                "system_prompt": self._prompts.system_prompt(),
                "goal": render_prompt_json(state.goal),
                "current_plan": render_prompt_json(state.current_plan),
                "latest_analysis": render_prompt_json(state.latest_analysis),
                "latest_tool_execution": render_prompt_json(state.latest_tool_execution),
                "simulation_history": render_prompt_json(state.simulation_history),
                "messages": render_prompt_json(state.messages),
            }
        )
        structured_model = self._model.with_structured_output(
            CriticResult,
            method=self._structured_output_method,
        )
        response = structured_model.invoke(prompt_value)
        return CriticResult.model_validate(response)

    def build_report(self, state: AgentState) -> OptimizationReport:
        """Produce the final report after termination or goal completion."""
        prompt_value = self._prompts.report_prompt().invoke(
            {
                "system_prompt": self._prompts.system_prompt(),
                "goal": render_prompt_json(state.goal),
                "goal_achieved": state.goal_achieved,
                "iteration_count": state.iteration_count,
                "simulation_history": render_prompt_json(state.simulation_history),
                "latest_analysis": render_prompt_json(state.latest_analysis),
                "latest_critique": render_prompt_json(state.latest_critique),
                "messages": render_prompt_json(state.messages),
                "latest_simulation_result": render_prompt_json(state.latest_simulation_result),
            }
        )
        structured_model = self._model.with_structured_output(
            OptimizationReport,
            method=self._structured_output_method,
        )
        response = structured_model.invoke(prompt_value)
        return OptimizationReport.model_validate(response)


__all__ = ["Reasoner"]
