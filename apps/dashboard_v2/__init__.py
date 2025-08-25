"""Dashboard v2 module for PulseStream - Built alongside existing dashboard."""

from .services import DashboardServiceV2
from .api import router as dashboard_v2_router

__all__ = [
    "DashboardServiceV2",
    "dashboard_v2_router"
]
