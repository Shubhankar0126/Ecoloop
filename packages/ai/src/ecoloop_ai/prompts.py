"""Prompt templates and prompt serialization helpers for the AI agent."""

from __future__ import annotations

import json
from enum import Enum

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel


def _to_jsonable(value: object) -> object:
    """Convert supported Python and Pydantic values into JSON-safe prompt data."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}

    if isinstance(value, tuple | list):
        return [_to_jsonable(item) for item in value]

    return value


def render_prompt_json(value: object) -> str:
    """Serialize state fragments into stable JSON for prompt injection."""
    return json.dumps(_to_jsonable(value), indent=2, sort_keys=True)


class PromptLibrary:
    """Own the system and role-specific prompt templates for the graph."""

    def system_prompt(self) -> str:
        """Return the shared system instruction for all agent roles."""
        return (
            "You are EcoLoop AI's optimization brain. "
            "You must reason carefully, stay within the provided building context, "
            "and use only the available MCP tools. "
            "Never assume direct access to EnergyPlus internals, files, or hidden services. "
            "Favor conservative, traceable recommendations grounded in tool outputs."
        )

    def planner_prompt(self) -> ChatPromptTemplate:
        """Return the prompt template for planning the next tool action."""
        return ChatPromptTemplate.from_messages(
            [
                ("system", "{system_prompt}"),
                (
                    "human",
                    (
                        "Plan the next single MCP tool call.\n\n"
                        "Goal:\n{goal}\n\n"
                        "Conversation:\n{conversation}\n\n"
                        "Building context:\n{building_context}\n\n"
                        "Previous optimizations:\n{previous_optimizations}\n\n"
                        "Available MCP tools:\n{available_tools}\n\n"
                        "Simulation history:\n{simulation_history}\n\n"
                        "Latest analysis:\n{latest_analysis}\n\n"
                        "Latest critique:\n{latest_critique}\n\n"
                        "Latest tool execution:\n{latest_tool_execution}\n\n"
                        "Select exactly one allowed MCP tool and provide its arguments. "
                        "Use only information already present in the context or prior tool outputs."
                    ),
                ),
            ]
        )

    def analyzer_prompt(self) -> ChatPromptTemplate:
        """Return the prompt template for analyzing the latest tool result."""
        return ChatPromptTemplate.from_messages(
            [
                ("system", "{system_prompt}"),
                (
                    "human",
                    (
                        "Analyze the latest tool execution and determine whether the "
                        "goal is met.\n\n"
                        "Goal:\n{goal}\n\n"
                        "Current plan:\n{current_plan}\n\n"
                        "Latest tool execution:\n{latest_tool_execution}\n\n"
                        "Latest simulation result:\n{latest_simulation_result}\n\n"
                        "Simulation history:\n{simulation_history}\n\n"
                        "Conversation:\n{conversation}\n\n"
                        "Provide factual findings, a concise summary, and whether the objective "
                        "has been achieved."
                    ),
                ),
            ]
        )

    def critic_prompt(self) -> ChatPromptTemplate:
        """Return the prompt template for critiquing an incomplete plan."""
        return ChatPromptTemplate.from_messages(
            [
                ("system", "{system_prompt}"),
                (
                    "human",
                    (
                        "Critique the current optimization attempt and propose a better focus "
                        "for the next planning iteration.\n\n"
                        "Goal:\n{goal}\n\n"
                        "Current plan:\n{current_plan}\n\n"
                        "Latest analysis:\n{latest_analysis}\n\n"
                        "Latest tool execution:\n{latest_tool_execution}\n\n"
                        "Simulation history:\n{simulation_history}\n\n"
                        "Messages:\n{messages}\n\n"
                        "Identify the most useful next-line improvements without inventing "
                        "new tools or direct EnergyPlus access."
                    ),
                ),
            ]
        )

    def report_prompt(self) -> ChatPromptTemplate:
        """Return the prompt template for the final optimization report."""
        return ChatPromptTemplate.from_messages(
            [
                ("system", "{system_prompt}"),
                (
                    "human",
                    (
                        "Write the final optimization report.\n\n"
                        "Goal:\n{goal}\n\n"
                        "Goal achieved:\n{goal_achieved}\n\n"
                        "Iterations used:\n{iteration_count}\n\n"
                        "Simulation history:\n{simulation_history}\n\n"
                        "Latest analysis:\n{latest_analysis}\n\n"
                        "Latest critique:\n{latest_critique}\n\n"
                        "Messages:\n{messages}\n\n"
                        "Latest simulation result:\n{latest_simulation_result}\n\n"
                        "Summarize what happened, what the results show, and what actions should "
                        "be taken next."
                    ),
                ),
            ]
        )


__all__ = ["PromptLibrary", "render_prompt_json"]
