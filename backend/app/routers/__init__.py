from .auth import router as auth_router
from .media import router as media_router
from .password_reset import router as password_reset_router
from .purchases import router as purchases_router
from .system import router as system_router
from .tracks import router as tracks_router
from .webhooks import router as webhooks_router

__all__ = [
    "auth_router",
    "media_router",
    "password_reset_router",
    "purchases_router",
    "system_router",
    "tracks_router",
    "webhooks_router",
]
