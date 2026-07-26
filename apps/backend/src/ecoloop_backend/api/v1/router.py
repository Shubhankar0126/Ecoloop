"""Aggregate router for the version 1 backend API surface."""

from fastapi import APIRouter

from ecoloop_backend.api.v1.routers.ai import router as ai_router
from ecoloop_backend.api.v1.routers.buildings import router as buildings_router
from ecoloop_backend.api.v1.routers.health import router as health_router
from ecoloop_backend.api.v1.routers.reports import router as reports_router
from ecoloop_backend.api.v1.routers.simulations import router as simulations_router

router = APIRouter()
router.include_router(health_router)
router.include_router(buildings_router)
router.include_router(simulations_router)
router.include_router(ai_router)
router.include_router(reports_router)

__all__ = ["router"]
