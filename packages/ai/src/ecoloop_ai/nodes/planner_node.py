"""Planner node for the EcoLoop AI LangGraph workflow."""

from __future__ import annotations

from ecoloop_ai.models import AgentMessage, MessageKind
from ecoloop_ai.planner import Planner
from ecoloop_ai.state import AgentState


class PlannerNode:
    """Create the next structured plan and tool selection."""

    def __init__(self, planner: Planner) -> None:
        """Initialize the node with the planner service."""
        self._planner = planner

    def __call__(self, state: AgentState) -> dict[str, object]:
        """Plan the next MCP tool call and update internal messages."""
        decision = self._planner.plan(state)
        return {
            "current_plan": decision,
            "messages": (
                *state.messages,
                AgentMessage(
                    kind=MessageKind.PLAN,
                    content=decision.plan_summary,
                ),
            ),
        }


__all__ = ["PlannerNode"]
