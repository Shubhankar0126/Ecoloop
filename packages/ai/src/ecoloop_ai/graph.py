"""LangGraph assembly for the EcoLoop AI planning loop."""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ecoloop_ai.nodes import (
    AnalyzerNode,
    CriticNode,
    PlannerNode,
    ReportNode,
    ToolExecutorNode,
)
from ecoloop_ai.state import AgentState


def build_agent_graph(
    *,
    planner_node: PlannerNode,
    tool_node: ToolExecutorNode,
    analyzer_node: AnalyzerNode,
    critic_node: CriticNode,
    report_node: ReportNode,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Build and compile the LangGraph workflow for the agent loop."""
    workflow = StateGraph(AgentState)
    workflow.add_node("planner", planner_node)
    workflow.add_node("tool_executor", tool_node)
    workflow.add_node("analyzer", analyzer_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("report", report_node)

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "tool_executor")
    workflow.add_edge("tool_executor", "analyzer")
    workflow.add_conditional_edges(
        "analyzer",
        route_after_analysis,
        {
            "critic": "critic",
            "report": "report",
        },
    )
    workflow.add_edge("critic", "planner")
    workflow.add_edge("report", END)

    return workflow.compile()


def route_after_analysis(state: AgentState) -> Literal["critic", "report"]:
    """Route to critique or reporting based on progress and loop limits."""
    if state.goal_achieved or state.iteration_count >= state.max_iterations:
        return "report"

    return "critic"


__all__ = ["build_agent_graph", "route_after_analysis"]
