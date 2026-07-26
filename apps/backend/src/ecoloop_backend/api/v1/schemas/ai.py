"""Request and response schemas for AI chat resources."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_ai import (
    BuildingContext,
    ConversationTurn,
    OptimizationReport,
    PreviousOptimization,
    UserGoal,
)

_AI_CHAT_REQUEST_EXAMPLE: dict[str, Any] = {
    "goal": {
        "objective": "Reduce cooling energy without degrading occupant comfort.",
        "success_criteria": [
            "Lower annual cooling energy by at least 5%.",
            "Keep average PMV between -0.5 and 0.5.",
        ],
        "constraints": ["Do not modify weather data."],
        "target_metrics": {"cooling_energy_kwh": 3000.0},
    },
    "conversation": [
        {
            "role": "user",
            "content": (
                "Start from the current office baseline and focus on HVAC schedule changes."
            ),
        }
    ],
    "building_context": {
        "building_name": "HQ Office Tower",
        "available_simulations": {},
        "current_simulation_key": None,
        "notes": ["Office occupancy peaks between 09:00 and 18:00."],
        "constraints": ["Maintain comfort during business hours."],
    },
    "previous_optimizations": [],
    "max_iterations": 3,
}

_AI_CHAT_RESPONSE_EXAMPLE: dict[str, Any] = {
    "latest_simulation_id": "22222222-2222-2222-2222-222222222222",
    "report": {
        "executive_summary": (
            "Cooling energy was reduced while keeping comfort within the requested band."
        ),
        "goal_achieved": True,
        "iterations_used": 2,
        "key_findings": [
            "Cooling energy dropped by 6.1% versus the baseline.",
            "Average PMV remained near neutral during occupied hours.",
        ],
        "recommendations": [
            "Adopt the revised HVAC weekday schedule as the next candidate baseline."
        ],
        "next_actions": ["Validate the same schedule under a second representative weather file."],
    },
}


class AiChatRequest(BaseModel):
    """HTTP contract for one AI-driven optimization conversation turn."""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"example": _AI_CHAT_REQUEST_EXAMPLE},
    )

    goal: UserGoal
    conversation: tuple[ConversationTurn, ...] = ()
    building_context: BuildingContext | None = None
    previous_optimizations: tuple[PreviousOptimization, ...] = ()
    max_iterations: int | None = Field(default=None, ge=1, le=20)


class AiChatResponse(BaseModel):
    """HTTP response payload returned from the AI chat endpoint."""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"example": _AI_CHAT_RESPONSE_EXAMPLE},
    )

    latest_simulation_id: UUID | None = None
    report: OptimizationReport


__all__ = ["AiChatRequest", "AiChatResponse"]
