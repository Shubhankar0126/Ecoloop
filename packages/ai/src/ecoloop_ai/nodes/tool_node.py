"""Tool execution node for the EcoLoop AI LangGraph workflow."""

from __future__ import annotations

from ecoloop_ai.memory import AgentMemoryManager
from ecoloop_ai.models import AgentMessage, MessageKind, SimulationHistoryEntry
from ecoloop_ai.state import AgentState
from ecoloop_ai.tools import McpToolClient, parse_tool_output
from ecoloop_common.exceptions import ApplicationError
from ecoloop_energyplus import SimulationResult


class ToolExecutorNode:
    """Execute the planner-selected MCP tool and capture its result."""

    def __init__(
        self,
        tool_client: McpToolClient,
        memory_manager: AgentMemoryManager,
    ) -> None:
        """Initialize the node with MCP execution and memory helpers."""
        self._tool_client = tool_client
        self._memory_manager = memory_manager

    def __call__(self, state: AgentState) -> dict[str, object]:
        """Execute the selected tool and persist any simulation output."""
        if state.current_plan is None:
            raise ApplicationError("A tool execution was requested without an active plan.")

        tool_call = state.current_plan.selected_tool
        execution = self._tool_client.call_tool(tool_call.tool_name, tool_call.arguments)

        simulation_history = state.simulation_history
        latest_simulation_result = state.latest_simulation_result
        memory = state.memory
        parsed_output = parse_tool_output(execution)

        if isinstance(parsed_output, SimulationResult):
            latest_simulation_result = parsed_output
            entry = SimulationHistoryEntry(simulation_result=parsed_output)
            simulation_history = (*state.simulation_history, entry)
            memory = self._memory_manager.record_simulation(memory, entry)

        tool_message = self._tool_message(execution)
        return {
            "latest_tool_execution": execution,
            "latest_simulation_result": latest_simulation_result,
            "simulation_history": simulation_history,
            "memory": memory,
            "iteration_count": state.iteration_count + 1,
            "messages": (*state.messages, tool_message),
        }

    def _tool_message(self, execution: object) -> AgentMessage:
        """Render a concise internal message describing the tool outcome."""
        from ecoloop_ai.models import ToolExecutionRecord

        record = ToolExecutionRecord.model_validate(execution)
        if record.success:
            return AgentMessage(
                kind=MessageKind.TOOL,
                content=f"Tool {record.tool_name} completed successfully.",
            )

        error_message = (
            record.error.message
            if record.error is not None
            else "The tool returned an unknown failure."
        )
        return AgentMessage(
            kind=MessageKind.TOOL,
            content=f"Tool {record.tool_name} failed: {error_message}",
        )


__all__ = ["ToolExecutorNode"]
