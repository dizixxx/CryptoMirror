from app.handlers.start import router as start_router
from app.handlers.prices import router as prices_router
from app.handlers.portfolio import router as portfolio_router
from app.handlers.help import router as help_router
from app.handlers.sell import router as sell_router
from app.handlers.buy import router as buy_router
from app.handlers.balance import router as balance_router

routers = [start_router, prices_router, buy_router, portfolio_router, help_router, sell_router, balance_router]

__all__ = ["routers"]