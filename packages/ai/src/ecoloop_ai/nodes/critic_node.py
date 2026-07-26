"""Critic node for the EcoLoop AI LangGraph workflow."""

from __future__ import annotations

from ecoloop_ai.models import AgentMessage, MessageKind
from ecoloop_ai.reasoner import Reasoner
from ecoloop_ai.state import AgentState


class CriticNode:
    """Critique an incomplete attempt before the next planning iteration."""

    def __init__(self, reasoner: Reasoner) -> None:
        """Initialize the node with the structured reasoning service."""
        self._reasoner = reasoner

    def __call__(self, state: AgentState) -> dict[str, object]:
        """Generate a critique and store it in state for the next loop."""
        critique = self._reasoner.critique(state)
        return {
            "latest_critique": critique,
            "messages": (
                *state.messages,
                AgentMessage(
                    kind=MessageKind.CRITIQUE,
                    content=critique.summary,
                ),
            ),
        }


__all__ = ["CriticNode"]
