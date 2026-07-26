"""Backend service for AI chat requests routed through the frozen agent package."""

from __future__ import annotations

from logging import Logger

from ecoloop_ai import AgentRequest, EcoLoopAgent
from ecoloop_backend.api.v1.schemas.ai import AiChatRequest, AiChatResponse


class AiChatService:
    """Bridge backend AI chat requests into the shared LangGraph agent."""

    def __init__(self, *, agent: EcoLoopAgent, logger: Logger) -> None:
        """Initialize the service with the injected AI agent dependency."""
        self._agent = agent
        self._logger = logger

    def run_chat(self, request: AiChatRequest) -> AiChatResponse:
        """Execute one AI chat request and return the final normalized report."""
        self._logger.info(
            "AI chat execution started",
            extra={
                "event": "ai_chat_started",
                "objective": request.goal.objective,
                "max_iterations": request.max_iterations,
            },
        )
        result = self._agent.run(
            AgentRequest(
                goal=request.goal,
                conversation=request.conversation,
                building_context=request.building_context,
                previous_optimizations=request.previous_optimizations,
                max_iterations=request.max_iterations,
            )
        )
        latest_simulation = result.final_state.latest_simulation_result
        response = AiChatResponse(
            latest_simulation_id=(
                None if latest_simulation is None else latest_simulation.simulation_id
            ),
            report=result.report,
        )
        self._logger.info(
            "AI chat execution completed",
            extra={
                "event": "ai_chat_completed",
                "goal_achieved": result.report.goal_achieved,
                "iterations_used": result.report.iterations_used,
                "latest_simulation_id": (
                    str(response.latest_simulation_id) if response.latest_simulation_id else None
                ),
            },
        )
        return response


__all__ = ["AiChatService"]
