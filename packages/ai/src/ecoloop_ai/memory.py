"""Immutable memory models and update helpers for the EcoLoop AI agent."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ecoloop_ai.models import (
    AgentRequest,
    BuildingContext,
    ConversationTurn,
    PreviousOptimization,
    SimulationHistoryEntry,
)


class AgentMemory(BaseModel):
    """Conversation and optimization memory available to each graph step."""

    model_config = ConfigDict(frozen=True)

    conversation_history: tuple[ConversationTurn, ...] = ()
    simulation_history: tuple[SimulationHistoryEntry, ...] = ()
    previous_optimizations: tuple[PreviousOptimization, ...] = ()
    building_context: BuildingContext | None = None

    @classmethod
    def from_request(cls, request: AgentRequest) -> AgentMemory:
        """Initialize memory from the public agent request."""
        return cls(
            conversation_history=request.conversation,
            simulation_history=(),
            previous_optimizations=request.previous_optimizations,
            building_context=request.building_context,
        )


class AgentMemoryManager:
    """Pure helper methods for producing updated immutable memory snapshots."""

    def initialize(self, request: AgentRequest) -> AgentMemory:
        """Create the initial agent memory snapshot."""
        return AgentMemory.from_request(request)

    def with_conversation(
        self,
        memory: AgentMemory,
        conversation: tuple[ConversationTurn, ...],
    ) -> AgentMemory:
        """Replace the conversation history stored in memory."""
        return memory.model_copy(update={"conversation_history": conversation})

    def record_simulation(
        self,
        memory: AgentMemory,
        entry: SimulationHistoryEntry,
    ) -> AgentMemory:
        """Append one simulation entry to memory."""
        return memory.model_copy(
            update={"simulation_history": (*memory.simulation_history, entry)}
        )

    def replace_last_simulation(
        self,
        memory: AgentMemory,
        entry: SimulationHistoryEntry,
    ) -> AgentMemory:
        """Update the most recent simulation entry while preserving history order."""
        if not memory.simulation_history:
            return memory

        return memory.model_copy(
            update={"simulation_history": (*memory.simulation_history[:-1], entry)}
        )


__all__ = ["AgentMemory", "AgentMemoryManager"]
