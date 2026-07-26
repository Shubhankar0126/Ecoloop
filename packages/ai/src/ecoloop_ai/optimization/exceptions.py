"""Optimization-specific exception types."""

from __future__ import annotations

from ecoloop_common.exceptions import ApplicationError, ValidationError


class OptimizationError(ApplicationError):
    """Base exception for optimization engine orchestration failures."""

    default_message = "The optimization engine could not complete the requested operation."
    error_code = "ecoloop.ai.optimization_error"


class OptimizationWorkflowError(OptimizationError):
    """Raised when workflow orchestration cannot advance safely."""

    default_message = "The optimization workflow could not advance."
    error_code = "ecoloop.ai.optimization_workflow_error"


class OptimizationStateError(OptimizationWorkflowError):
    """Raised when an invalid optimization state transition is requested."""

    default_message = "The optimization workflow state is invalid for this operation."
    error_code = "ecoloop.ai.optimization_state_error"


class OptimizationConfigurationError(OptimizationError):
    """Raised when runtime optimization configuration is internally inconsistent."""

    default_message = "The optimization engine configuration is invalid."
    error_code = "ecoloop.ai.optimization_configuration_error"


class OptimizationValidationError(ValidationError):
    """Raised when an optimization request violates a domain validation rule."""

    default_message = "The optimization request is invalid."
    error_code = "ecoloop.ai.optimization_validation_error"


class GoalInterpretationError(OptimizationError):
    """Raised when a natural-language goal cannot be normalized safely."""

    default_message = "The optimization goal could not be interpreted."
    error_code = "ecoloop.ai.goal_interpretation_error"


class ObjectiveResolutionError(OptimizationError):
    """Raised when an optimization objective cannot be resolved or evaluated."""

    default_message = "The optimization objective could not be resolved."
    error_code = "ecoloop.ai.objective_resolution_error"


class HypothesisGenerationError(OptimizationError):
    """Raised when the hypothesis engine cannot produce a valid candidate set."""

    default_message = "The hypothesis engine could not generate valid candidates."
    error_code = "ecoloop.ai.hypothesis_generation_error"


class StrategyResolutionError(OptimizationError):
    """Raised when the configured optimization strategy cannot be resolved."""

    default_message = "The optimization strategy could not be resolved."
    error_code = "ecoloop.ai.strategy_resolution_error"


__all__ = [
    "GoalInterpretationError",
    "HypothesisGenerationError",
    "ObjectiveResolutionError",
    "OptimizationConfigurationError",
    "OptimizationError",
    "OptimizationStateError",
    "OptimizationValidationError",
    "OptimizationWorkflowError",
    "StrategyResolutionError",
]
