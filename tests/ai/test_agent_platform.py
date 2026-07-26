from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest
from langchain_core.language_models.chat_models import BaseChatModel

from ecoloop_ai import (
    AgentMemoryManager,
    AgentRequest,
    AgentState,
    AgentToolName,
    AiAgentConfig,
    AnalysisResult,
    BuildingContext,
    ConversationRole,
    ConversationTurn,
    CriticResult,
    EcoLoopAgent,
    OptimizationReport,
    PlannedToolCall,
    PlannerDecision,
    PlanStep,
    ToolCatalogEntry,
    ToolExecutionRecord,
    UserGoal,
)
from ecoloop_ai.graph import route_after_analysis
from ecoloop_ai.models import MessageKind, SimulationHistoryEntry
from ecoloop_ai.nodes.tool_node import ToolExecutorNode
from ecoloop_ai.planner import Planner
from ecoloop_ai.prompts import PromptLibrary, render_prompt_json
from ecoloop_ai.reasoner import Reasoner
from ecoloop_common.exceptions import ApplicationError, InfrastructureError
from ecoloop_energyplus import (
    ComfortMetrics,
    EnergyMetrics,
    HVACMetrics,
    SimulationMetadata,
    SimulationMetrics,
    SimulationResult,
    SimulationSpec,
    SimulationStatus,
    ValidationResult,
    WeatherMetrics,
    ZoneMetrics,
)


class FakeRunnable:
    """Minimal structured runnable used by the fake chat model."""

    def __init__(self, responses: list[object], invocations: list[object]) -> None:
        self._responses = responses
        self._invocations = invocations

    def invoke(self, prompt_value: object) -> object:
        self._invocations.append(prompt_value)
        if not self._responses:
            raise AssertionError("No fake model response was configured.")

        return self._responses.pop(0)


class FakeStructuredChatModel:
    """A tiny fake that mimics `with_structured_output` for tests."""

    def __init__(self, responses: dict[type[Any], Sequence[object]]) -> None:
        self._responses = {schema: list(items) for schema, items in responses.items()}
        self.invocations: dict[str, list[object]] = {}

    def with_structured_output(self, schema: type[object], **_: Any) -> FakeRunnable:
        queue = self._responses.setdefault(schema, [])
        invocations = self.invocations.setdefault(schema.__name__, [])
        return FakeRunnable(queue, invocations)


class FakeToolClient:
    """Queue-based MCP client fake for graph tests."""

    def __init__(
        self,
        *,
        catalog: tuple[ToolCatalogEntry, ...],
        records: tuple[ToolExecutionRecord, ...],
    ) -> None:
        self._catalog = catalog
        self._records = list(records)
        self.calls: list[tuple[AgentToolName, dict[str, Any]]] = []

    def list_tools(self) -> tuple[ToolCatalogEntry, ...]:
        return self._catalog

    def call_tool(
        self,
        tool_name: AgentToolName,
        arguments: dict[str, Any],
    ) -> ToolExecutionRecord:
        self.calls.append((tool_name, arguments))
        if not self._records:
            raise AssertionError("No fake tool record was configured.")

        return self._records.pop(0)


class EmptyToolClient:
    """MCP client fake that returns an empty tool catalog."""

    def list_tools(self) -> tuple[ToolCatalogEntry, ...]:
        return ()

    def call_tool(
        self,
        tool_name: AgentToolName,
        arguments: dict[str, Any],
    ) -> ToolExecutionRecord:
        raise AssertionError(f"Unexpected tool call: {tool_name} {arguments}")


class StubGraph:
    """Minimal graph stub used to cover agent termination safeguards."""

    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def invoke(self, *args: object, **kwargs: object) -> dict[str, object]:
        del args, kwargs
        return self._payload


def _spec(tmp_path: Path) -> SimulationSpec:
    return SimulationSpec(
        idf_path=tmp_path / "building.idf",
        epw_path=tmp_path / "weather.epw",
        timeout_seconds=90,
        parallel_jobs=1,
    )


def _result(identifier: str) -> SimulationResult:
    return SimulationResult(
        simulation_id=UUID(identifier),
        final_status=SimulationStatus.SUCCEEDED,
        metrics=SimulationMetrics(
            energy=EnergyMetrics(
                total_site_energy_kwh=900.0,
                electricity_consumption_kwh=500.0,
            ),
            hvac=HVACMetrics(
                heating_energy_kwh=120.0,
                cooling_energy_kwh=180.0,
                hvac_energy_kwh=300.0,
                equipment_loads_kwh=80.0,
            ),
            comfort=ComfortMetrics(
                average_zone_temperature_celsius=22.0,
                average_zone_humidity_percent=45.0,
                average_pmv=0.2,
                average_ppd_percent=8.0,
            ),
            weather=WeatherMetrics(
                average_outdoor_dry_bulb_celsius=31.0,
                average_outdoor_relative_humidity_percent=55.0,
            ),
            zones=(
                ZoneMetrics(
                    zone_name="ZONE ONE",
                    mean_air_temperature_celsius=22.0,
                ),
            ),
        ),
        diagnostics=("Simulation completed.",),
        metadata=SimulationMetadata(
            energyplus_version="25.1.0",
            command_line=("energyplus",),
            exit_code=0,
            duration_ms=500,
            started_at=datetime(2026, 7, 26, 9, 0, tzinfo=UTC),
            completed_at=datetime(2026, 7, 26, 9, 1, tzinfo=UTC),
        ),
    )


def _goal() -> UserGoal:
    return UserGoal(
        objective="Reduce total site energy while preserving comfort.",
        success_criteria=("Lower total site energy than the baseline.",),
    )


def _catalog() -> tuple[ToolCatalogEntry, ...]:
    return (
        ToolCatalogEntry(
            name=AgentToolName.SIMULATE_BUILDING.value,
            description="Run a simulation.",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        ),
        ToolCatalogEntry(
            name=AgentToolName.VALIDATE_SIMULATION.value,
            description="Validate one simulation.",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        ),
    )


def test_agent_completes_on_first_successful_iteration(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    result = _result("00000000-0000-0000-0000-000000000101")
    planner_response = PlannerDecision(
        plan_summary="Run the candidate simulation.",
        steps=(
            PlanStep(
                description="Execute the candidate simulation.",
                expected_outcome="Produce a normalized simulation result.",
            ),
        ),
        selected_tool=PlannedToolCall(
            tool_name=AgentToolName.SIMULATE_BUILDING,
            arguments={"spec": spec.model_dump(mode="json")},
            rationale="We need the candidate performance metrics.",
        ),
        expected_outcome="A completed simulation result for analysis.",
    )
    analysis_response = AnalysisResult(
        summary="The candidate meets the energy objective.",
        goal_achieved=True,
        findings=("Total site energy is lower than the baseline target.",),
        recommended_actions=("Proceed with the candidate recommendation.",),
    )
    report_response = OptimizationReport(
        executive_summary="The optimization goal was achieved in one iteration.",
        goal_achieved=True,
        iterations_used=1,
        key_findings=("Energy usage improved while comfort remained acceptable.",),
        recommendations=("Adopt the candidate operating profile.",),
        next_actions=("Validate the change in the live control loop.",),
    )
    model = FakeStructuredChatModel(
        {
            PlannerDecision: [planner_response],
            AnalysisResult: [analysis_response],
            OptimizationReport: [report_response],
        }
    )
    tool_client = FakeToolClient(
        catalog=_catalog(),
        records=(
            ToolExecutionRecord(
                tool_name=AgentToolName.SIMULATE_BUILDING.value,
                arguments={"spec": spec.model_dump(mode="json")},
                success=True,
                structured_output=result.model_dump(mode="json"),
                content_text=result.model_dump_json(),
            ),
        ),
    )
    request = AgentRequest(
        goal=_goal(),
        conversation=(
            ConversationTurn(
                role=ConversationRole.USER,
                content="Optimize the candidate schedule.",
            ),
        ),
        building_context=BuildingContext(
            building_name="HQ Tower",
            available_simulations={"candidate": spec},
            current_simulation_key="candidate",
        ),
    )
    agent = EcoLoopAgent.from_dependencies(
        config=AiAgentConfig(),
        tool_client=tool_client,
        chat_model=cast(BaseChatModel, model),
    )

    run_result = agent.run(request)

    assert run_result.report.goal_achieved is True
    assert run_result.final_state.goal_achieved is True
    assert run_result.final_state.iteration_count == 1
    assert len(run_result.final_state.simulation_history) == 1
    assert run_result.final_state.latest_simulation_result == result
    assert run_result.final_state.memory.simulation_history[0].analysis_summary == (
        "The candidate meets the energy objective."
    )
    assert tool_client.calls == [
        (AgentToolName.SIMULATE_BUILDING, {"spec": spec.model_dump(mode="json")})
    ]


def test_agent_retries_until_max_iterations(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    result = _result("00000000-0000-0000-0000-000000000102")
    planner_responses = [
        PlannerDecision(
            plan_summary="Validate the simulation input first.",
            steps=(
                PlanStep(
                    description="Run validation.",
                    expected_outcome="Confirm that the candidate spec is runnable.",
                ),
            ),
            selected_tool=PlannedToolCall(
                tool_name=AgentToolName.VALIDATE_SIMULATION,
                arguments={"spec": spec.model_dump(mode="json")},
                rationale="Validation should precede execution.",
            ),
            expected_outcome="A validation result.",
        ),
        PlannerDecision(
            plan_summary="Run the validated simulation.",
            steps=(
                PlanStep(
                    description="Execute the simulation.",
                    expected_outcome="Produce a candidate simulation result.",
                ),
            ),
            selected_tool=PlannedToolCall(
                tool_name=AgentToolName.SIMULATE_BUILDING,
                arguments={"spec": spec.model_dump(mode="json")},
                rationale="Execution is required after validation.",
            ),
            expected_outcome="A normalized simulation result.",
        ),
    ]
    analysis_responses = [
        AnalysisResult(
            summary="Validation succeeded, but the objective is still unproven.",
            goal_achieved=False,
            findings=("No execution data is available yet.",),
            recommended_actions=("Run the simulation next.",),
        ),
        AnalysisResult(
            summary="The candidate still does not meet the stated objective.",
            goal_achieved=False,
            findings=("Energy use remains above the desired target.",),
            recommended_actions=("Revisit the control hypothesis.",),
        ),
    ]
    report_response = OptimizationReport(
        executive_summary="The optimization loop stopped at the iteration limit.",
        goal_achieved=False,
        iterations_used=2,
        key_findings=("The current candidate is still underperforming.",),
        recommendations=("Try a revised operating schedule.",),
        next_actions=("Prepare a new candidate for the next run.",),
    )
    critic_response = CriticResult(
        summary="The next plan should move from validation into execution.",
        improvement_hypotheses=("Execution data is needed for a meaningful assessment.",),
        revised_focus=("Run the validated candidate simulation.",),
    )
    model = FakeStructuredChatModel(
        {
            PlannerDecision: planner_responses,
            AnalysisResult: analysis_responses,
            CriticResult: [critic_response],
            OptimizationReport: [report_response],
        }
    )
    tool_client = FakeToolClient(
        catalog=_catalog(),
        records=(
            ToolExecutionRecord(
                tool_name=AgentToolName.VALIDATE_SIMULATION.value,
                arguments={"spec": spec.model_dump(mode="json")},
                success=True,
                structured_output=ValidationResult.success().model_dump(mode="json"),
                content_text=ValidationResult.success().model_dump_json(),
            ),
            ToolExecutionRecord(
                tool_name=AgentToolName.SIMULATE_BUILDING.value,
                arguments={"spec": spec.model_dump(mode="json")},
                success=True,
                structured_output=result.model_dump(mode="json"),
                content_text=result.model_dump_json(),
            ),
        ),
    )
    request = AgentRequest(
        goal=_goal(),
        building_context=BuildingContext(
            available_simulations={"candidate": spec},
            current_simulation_key="candidate",
        ),
        max_iterations=2,
    )
    agent = EcoLoopAgent.from_dependencies(
        config=AiAgentConfig(),
        tool_client=tool_client,
        chat_model=cast(BaseChatModel, model),
    )

    run_result = agent.run(request)

    assert run_result.final_state.goal_achieved is False
    assert run_result.final_state.iteration_count == 2
    assert len(run_result.final_state.simulation_history) == 1
    assert run_result.final_state.latest_critique == critic_response
    assert run_result.report.goal_achieved is False
    assert route_after_analysis(run_result.final_state) == "report"


def test_planner_requires_available_tools(tmp_path: Path) -> None:
    state = AgentState.from_request(
        AgentRequest(
            goal=_goal(),
            building_context=BuildingContext(available_simulations={"candidate": _spec(tmp_path)}),
        ),
        memory=AgentMemoryManager().initialize(
            AgentRequest(
                goal=_goal(),
                building_context=BuildingContext(
                    available_simulations={"candidate": _spec(tmp_path)}
                ),
            )
        ),
        default_max_iterations=3,
    )
    planner = Planner(
        cast(BaseChatModel, FakeStructuredChatModel({PlannerDecision: []})),
        PromptLibrary(),
        EmptyToolClient(),
        structured_output_method="json_schema",
    )

    with pytest.raises(InfrastructureError, match="No MCP tools are available"):
        planner.plan(state)


def test_tool_executor_requires_current_plan(tmp_path: Path) -> None:
    request = AgentRequest(goal=_goal(), building_context=BuildingContext())
    memory = AgentMemoryManager().initialize(request)
    state = AgentState.from_request(request, memory=memory, default_max_iterations=3)
    node = ToolExecutorNode(FakeToolClient(catalog=_catalog(), records=()), AgentMemoryManager())

    with pytest.raises(ApplicationError, match="without an active plan"):
        node(state)


def test_agent_raises_if_graph_finishes_without_report() -> None:
    request = AgentRequest(goal=_goal())
    memory_manager = AgentMemoryManager()
    initial_state = AgentState.from_request(
        request,
        memory=memory_manager.initialize(request),
        default_max_iterations=3,
    )
    payload = initial_state.model_dump(mode="python")
    agent = EcoLoopAgent(
        graph=cast(Any, StubGraph(payload)),
        config=AiAgentConfig(),
        memory_manager=memory_manager,
    )

    with pytest.raises(ApplicationError, match="without producing a final report"):
        agent.run(request)


def test_reasoner_and_prompt_helpers_render_expected_content(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    request = AgentRequest(
        goal=_goal(),
        conversation=(
            ConversationTurn(role=ConversationRole.USER, content="Run a quick review."),
        ),
        building_context=BuildingContext(available_simulations={"candidate": spec}),
    )
    memory_manager = AgentMemoryManager()
    state = AgentState.from_request(
        request,
        memory=memory_manager.initialize(request),
        default_max_iterations=3,
    )
    model = FakeStructuredChatModel(
        {
            AnalysisResult: [
                AnalysisResult(
                    summary="No execution has occurred yet.",
                    goal_achieved=False,
                )
            ],
            CriticResult: [
                CriticResult(
                    summary="A simulation run is still needed.",
                )
            ],
            OptimizationReport: [
                OptimizationReport(
                    executive_summary="The run is incomplete.",
                    goal_achieved=False,
                    iterations_used=0,
                )
            ],
        }
    )
    reasoner = Reasoner(
        cast(BaseChatModel, model),
        PromptLibrary(),
        structured_output_method="json_schema",
    )

    analysis = reasoner.analyze(state)
    critique = reasoner.critique(state.model_copy(update={"latest_analysis": analysis}))
    report = reasoner.build_report(
        state.model_copy(
            update={
                "latest_analysis": analysis,
                "latest_critique": critique,
            }
        )
    )

    assert analysis.goal_achieved is False
    assert critique.summary == "A simulation run is still needed."
    assert report.executive_summary == "The run is incomplete."
    assert "candidate" in render_prompt_json(request.building_context)


def test_config_creates_chat_ollama_and_route_helper(tmp_path: Path) -> None:
    config = AiAgentConfig()
    model = config.create_chat_model()
    request = AgentRequest(goal=_goal(), building_context=BuildingContext())
    state = AgentState.from_request(
        request,
        memory=AgentMemoryManager().initialize(request),
        default_max_iterations=3,
    )
    completed_state = state.model_copy(update={"goal_achieved": True})
    critic_state = state.model_copy(
        update={
            "iteration_count": 1,
            "latest_analysis": AnalysisResult(
                summary="More work is needed.",
                goal_achieved=False,
            ),
        }
    )

    assert model.model == "qwen3"
    assert route_after_analysis(completed_state) == "report"
    assert route_after_analysis(critic_state) == "critic"
    assert critic_state.max_iterations == 3


def test_memory_manager_update_helpers(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    request = AgentRequest(
        goal=_goal(),
        conversation=(ConversationTurn(role=ConversationRole.USER, content="Hello"),),
        building_context=BuildingContext(available_simulations={"candidate": spec}),
    )
    manager = AgentMemoryManager()
    memory = manager.initialize(request)
    entry = SimulationHistoryEntry(
        simulation_result=_result("00000000-0000-0000-0000-000000000103")
    )
    updated_memory = manager.record_simulation(memory, entry)
    replaced_entry = SimulationHistoryEntry(
        simulation_result=entry.simulation_result,
        analysis_summary="Reviewed.",
        goal_achieved=False,
    )

    assert updated_memory.conversation_history == request.conversation
    assert len(updated_memory.simulation_history) == 1
    assert manager.replace_last_simulation(memory, entry) == memory
    replaced_memory = manager.replace_last_simulation(updated_memory, replaced_entry)
    assert replaced_memory.simulation_history[-1] == replaced_entry
    assert manager.with_conversation(memory, request.conversation).conversation_history == (
        request.conversation
    )


def test_graph_messages_capture_internal_reasoning(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    result = _result("00000000-0000-0000-0000-000000000104")
    model = FakeStructuredChatModel(
        {
            PlannerDecision: [
                PlannerDecision(
                    plan_summary="Simulate the building.",
                    selected_tool=PlannedToolCall(
                        tool_name=AgentToolName.SIMULATE_BUILDING,
                        arguments={"spec": spec.model_dump(mode="json")},
                        rationale="Execution is required.",
                    ),
                    expected_outcome="A simulation result.",
                )
            ],
            AnalysisResult: [
                AnalysisResult(
                    summary="The simulation is complete.",
                    goal_achieved=True,
                )
            ],
            OptimizationReport: [
                OptimizationReport(
                    executive_summary="The loop completed successfully.",
                    goal_achieved=True,
                    iterations_used=1,
                )
            ],
        }
    )
    tool_client = FakeToolClient(
        catalog=_catalog(),
        records=(
            ToolExecutionRecord(
                tool_name=AgentToolName.SIMULATE_BUILDING.value,
                arguments={"spec": spec.model_dump(mode="json")},
                success=True,
                structured_output=result.model_dump(mode="json"),
            ),
        ),
    )
    agent = EcoLoopAgent.from_dependencies(
        config=AiAgentConfig(),
        tool_client=tool_client,
        chat_model=cast(BaseChatModel, model),
    )

    run_result = agent.run(
        AgentRequest(
            goal=_goal(),
            building_context=BuildingContext(available_simulations={"candidate": spec}),
        )
    )

    assert [message.kind for message in run_result.final_state.messages] == [
        MessageKind.PLAN,
        MessageKind.TOOL,
        MessageKind.ANALYSIS,
        MessageKind.REPORT,
    ]
