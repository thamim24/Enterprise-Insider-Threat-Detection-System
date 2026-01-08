"""API routes module"""
from .auth import router as auth_router
from .events import router as events_router
from .documents import router as documents_router
from .alerts import router as alerts_router
from .reports import router as reports_router
from .ml_status import router as ml_router

__all__ = [
    "auth_router",
    "events_router",
    "documents_router",
    "alerts_router",
    "reports_router",
    "ml_router"
]
