"""
Main routes initialization file.
Combines all route modules into a single router.
"""
from fastapi import APIRouter
from sympy import im

from api.routes import auth_routes
from api.routes import upload_routes
from api.routes import websocket_routes
from api.routes import results_routes
from api.routes import project_routes
from api.routes import elicitation_routes
from api.routes import template_routes
from api.routes import titlePage_router

# Initialize main router
router = APIRouter()

# Include all sub-routers
router.include_router(auth_routes.router)
router.include_router(upload_routes.router)
router.include_router(websocket_routes.router)
router.include_router(results_routes.router)
router.include_router(project_routes.router)
router.include_router(elicitation_routes.router)
router.include_router(template_routes.router)
router.include_router(titlePage_router.router)

__all__ = ["router"]
