"""HTTP error response models for the FastAPI backend."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

PROBLEM_JSON_MEDIA_TYPE = "application/problem+json"


class InvalidParameter(BaseModel):
    """RFC 7807 extension describing a single invalid request parameter."""

    model_config = ConfigDict(frozen=True)

    name: str
    location: str
    message: str


class ProblemDetails(BaseModel):
    """RFC 7807-compatible problem details payload."""

    model_config = ConfigDict(frozen=True)

    type: str
    title: str
    status: int
    detail: str
    instance: str
    error_code: str | None = None
    request_id: str | None = None
    context: dict[str, Any] | None = None
    errors: list[InvalidParameter] | None = None
