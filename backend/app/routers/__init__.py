from .auth import router as auth_router
from .albums import router as albums_router
from .media import router as media_router
from .password_reset import router as password_reset_router
from .profile import router as profile_router
from .system import router as system_router
from .shopier import router as shopier_router
from .tracks import router as tracks_router

__all__ = [
    "auth_router",
    "albums_router",
    "media_router",
    "password_reset_router",
    "profile_router",
    "system_router",
    "shopier_router",
    "tracks_router",
]
