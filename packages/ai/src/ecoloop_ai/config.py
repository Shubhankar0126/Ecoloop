"""Configuration models for the EcoLoop AI agent package."""

from __future__ import annotations

from typing import Literal

from langchain_ollama import ChatOllama
from pydantic import BaseModel, ConfigDict, Field


class OllamaSettings(BaseModel):
    """Runtime configuration for the Ollama-hosted Qwen chat model."""

    model_config = ConfigDict(frozen=True)

    base_url: str = "http://localhost:11434"
    model: str = "qwen3"
    temperature: float = Field(default=0.1, ge=0, le=2)
    num_ctx: int | None = Field(default=8192, ge=1)
    num_predict: int | None = Field(default=1024, ge=1)
    top_p: float | None = Field(default=0.9, ge=0, le=1)
    seed: int | None = None
    reasoning: bool | str | None = None
    validate_model_on_init: bool = False
    structured_output_method: Literal["function_calling", "json_mode", "json_schema"] = (
        "json_schema"
    )


class AgentLoopSettings(BaseModel):
    """Execution policy for the LangGraph planning loop."""

    model_config = ConfigDict(frozen=True)

    max_iterations: int = Field(default=3, ge=1, le=20)
    recursion_limit_multiplier: int = Field(default=6, ge=2, le=20)


class AiAgentConfig(BaseModel):
    """Top-level configuration contract for the EcoLoop AI agent."""

    model_config = ConfigDict(frozen=True)

    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    loop: AgentLoopSettings = Field(default_factory=AgentLoopSettings)

    def create_chat_model(self) -> ChatOllama:
        """Build the default ChatOllama instance for structured agent reasoning."""
        return ChatOllama(
            model=self.ollama.model,
            base_url=self.ollama.base_url,
            temperature=self.ollama.temperature,
            num_ctx=self.ollama.num_ctx,
            num_predict=self.ollama.num_predict,
            top_p=self.ollama.top_p,
            seed=self.ollama.seed,
            reasoning=self.ollama.reasoning,
            validate_model_on_init=self.ollama.validate_model_on_init,
        )


__all__ = ["AgentLoopSettings", "AiAgentConfig", "OllamaSettings"]
