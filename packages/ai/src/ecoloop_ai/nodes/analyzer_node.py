"""Analyzer node for the EcoLoop AI LangGraph workflow."""

from __future__ import annotations

from ecoloop_ai.memory import AgentMemoryManager
from ecoloop_ai.models import AgentMessage, AgentToolName, MessageKind, SimulationHistoryEntry
from ecoloop_ai.reasoner import Reasoner
from ecoloop_ai.state import AgentState


class AnalyzerNode:
    """Analyze the latest tool result and update goal progress."""

    def __init__(
        self,
        reasoner: Reasoner,
        memory_manager: AgentMemoryManager,
    ) -> None:
        """Initialize the node with reasoning and memory services."""
        self._reasoner = reasoner
        self._memory_manager = memory_manager

    def __call__(self, state: AgentState) -> dict[str, object]:
        """Analyze the latest tool outcome and synchronize memory."""
        analysis = self._reasoner.analyze(state)
        simulation_history = state.simulation_history
        memory = state.memory

        if (
            state.latest_tool_execution is not None
            and state.latest_tool_execution.success
            and state.latest_tool_execution.tool_name == AgentToolName.SIMULATE_BUILDING.value
            and simulation_history
        ):
            updated_entry = SimulationHistoryEntry(
                simulation_result=simulation_history[-1].simulation_result,
                analysis_summary=analysis.summary,
                goal_achieved=analysis.goal_achieved,
            )
            simulation_history = (*simulation_history[:-1], updated_entry)
            memory = self._memory_manager.replace_last_simulation(memory, updated_entry)

        return {
            "latest_analysis": analysis,
            "goal_achieved": analysis.goal_achieved,
            "simulation_history": simulation_history,
            "memory": memory,
            "messages": (
                *state.messages,
                AgentMessage(
                    kind=MessageKind.ANALYSIS,
                    content=analysis.summary,
                ),
            ),
        }


__all__ = ["AnalyzerNode"]
