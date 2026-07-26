"""REST router for AI-driven optimization chat interactions."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ecoloop_backend.api.error_models import ProblemDetails
from ecoloop_backend.api.v1.dependencies import get_ai_chat_service
from ecoloop_backend.api.v1.schemas.ai import AiChatRequest, AiChatResponse
from ecoloop_backend.api.v1.services import AiChatService

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post(
    "/chat",
    response_model=AiChatResponse,
    summary="Run AI chat",
    description=(
        "Execute one AI optimization request through the frozen LangGraph agent "
        "and return the final structured report."
    ),
    responses={
        400: {
            "model": ProblemDetails,
            "description": "The AI request payload failed validation.",
        },
        500: {
            "model": ProblemDetails,
            "description": "The AI agent could not complete the requested workflow.",
        },
        503: {
            "model": ProblemDetails,
            "description": "A required infrastructure dependency was unavailable.",
        },
    },
)
def run_ai_chat(
    request: AiChatRequest,
    ai_chat_service: Annotated[AiChatService, Depends(get_ai_chat_service)],
) -> AiChatResponse:
    """Run one AI chat workflow and return the final report payload."""
    return ai_chat_service.run_chat(request)


__all__ = ["router"]
