"""Report node for the EcoLoop AI LangGraph workflow."""

from __future__ import annotations

from ecoloop_ai.models import AgentMessage, MessageKind
from ecoloop_ai.reasoner import Reasoner
from ecoloop_ai.state import AgentState


class ReportNode:
    """Build the final optimization report after graph termination."""

    def __init__(self, reasoner: Reasoner) -> None:
        """Initialize the node with the structured reasoning service."""
        self._reasoner = reasoner

    def __call__(self, state: AgentState) -> dict[str, object]:
        """Generate the final report and append it to internal messages."""
        report = self._reasoner.build_report(state)
        return {
            "final_report": report,
            "messages": (
                *state.messages,
                AgentMessage(
                    kind=MessageKind.REPORT,
                    content=report.executive_summary,
                ),
            ),
        }


__all__ = ["ReportNode"]
