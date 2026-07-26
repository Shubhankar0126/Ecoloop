"""Compatibility wrapper exposing the existing health router in the v1 API package."""

from ecoloop_backend.api.routes.health import router

__all__ = ["router"]
