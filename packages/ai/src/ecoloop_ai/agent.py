"""Public entry point for the EcoLoop AI LangGraph agent."""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, ConfigDict

from ecoloop_ai.config import AiAgentConfig
from ecoloop_ai.graph import build_agent_graph
from ecoloop_ai.memory import AgentMemoryManager
from ecoloop_ai.models import AgentRequest, OptimizationReport
from ecoloop_ai.nodes import (
    AnalyzerNode,
    CriticNode,
    PlannerNode,
    ReportNode,
    ToolExecutorNode,
)
from ecoloop_ai.planner import Planner
from ecoloop_ai.prompts import PromptLibrary
from ecoloop_ai.reasoner import Reasoner
from ecoloop_ai.state import AgentState
from ecoloop_ai.tools import McpToolClient
from ecoloop_common.exceptions import ApplicationError


class AgentRunResult(BaseModel):
    """Final result returned from one AI agent execution."""

    model_config = ConfigDict(frozen=True)

    final_state: AgentState
    report: OptimizationReport


class EcoLoopAgent:
    """Production-oriented LangGraph agent that uses only MCP tools."""

    def __init__(
        self,
        graph: CompiledStateGraph[Any, Any, Any, Any],
        config: AiAgentConfig,
        memory_manager: AgentMemoryManager,
    ) -> None:
        """Initialize the agent with a compiled graph and immutable config."""
        self._graph = graph
        self._config = config
        self._memory_manager = memory_manager

    @classmethod
    def from_dependencies(
        cls,
        *,
        config: AiAgentConfig,
        tool_client: McpToolClient,
        chat_model: BaseChatModel | None = None,
        prompts: PromptLibrary | None = None,
        memory_manager: AgentMemoryManager | None = None,
    ) -> EcoLoopAgent:
        """Construct the production agent from injected model and MCP dependencies."""
        prompt_library = prompts or PromptLibrary()
        memory = memory_manager or AgentMemoryManager()
        model = chat_model or config.create_chat_model()
        planner = Planner(
            model,
            prompt_library,
            tool_client,
            structured_output_method=config.ollama.structured_output_method,
        )
        reasoner = Reasoner(
            model,
            prompt_library,
            structured_output_method=config.ollama.structured_output_method,
        )
        graph = build_agent_graph(
            planner_node=PlannerNode(planner),
            tool_node=ToolExecutorNode(tool_client, memory),
            analyzer_node=AnalyzerNode(reasoner, memory),
            critic_node=CriticNode(reasoner),
            report_node=ReportNode(reasoner),
        )
        return cls(graph=graph, config=config, memory_manager=memory)

    def run(self, request: AgentRequest) -> AgentRunResult:
        """Execute one LangGraph optimization loop and return the final report."""
        memory = self._memory_manager.initialize(request)
        initial_state = AgentState.from_request(
            request,
            memory=memory,
            default_max_iterations=self._config.loop.max_iterations,
        )
        recursion_limit = max(
            25,
            initial_state.max_iterations * self._config.loop.recursion_limit_multiplier,
        )
        raw_state = self._graph.invoke(
            initial_state.model_dump(mode="python"),
            config={"recursion_limit": recursion_limit},
        )
        final_state = AgentState.model_validate(raw_state)
        if final_state.final_report is None:
            raise ApplicationError("The AI agent terminated without producing a final report.")

        return AgentRunResult(
            final_state=final_state,
            report=final_state.final_report,
        )


__all__ = ["AgentRunResult", "EcoLoopAgent"]
