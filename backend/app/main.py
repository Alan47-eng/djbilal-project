from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import (
    FRONTEND_ORIGINS,
    IS_PRODUCTION,
    LOCAL_DEV_ORIGIN_REGEX,
)
from .lifecycle import initialize_application
from .rate_limit import limiter
from .routers import (
    auth_router,
    media_router,
    password_reset_router,
    purchases_router,
    system_router,
    tracks_router,
    webhooks_router,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await initialize_application()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_origin_regex=None if IS_PRODUCTION else LOCAL_DEV_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(media_router)
app.include_router(system_router)
app.include_router(auth_router)
app.include_router(password_reset_router)
app.include_router(tracks_router)
app.include_router(purchases_router)
app.include_router(webhooks_router)
