from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..database import test_connection

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/db-check", response_model=None)
async def db_check() -> dict[str, str] | JSONResponse:
    try:
        await test_connection()
        return {"status": "ok", "db": "reachable"}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(exc)})
