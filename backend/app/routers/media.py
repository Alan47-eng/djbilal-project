from fastapi import APIRouter
from fastapi.staticfiles import StaticFiles

from ..utils import UPLOAD_ROOT

router = APIRouter()
router.mount("/media", StaticFiles(directory=str(UPLOAD_ROOT)), name="media")
