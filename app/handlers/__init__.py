from app.handlers.start import router as start_router
from app.handlers.handlers import router as hand_router
from app.handlers.prices import router as prices_router

routers = [start_router, prices_router, hand_router]

__all__ = ["routers"]