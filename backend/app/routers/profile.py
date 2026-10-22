from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from .. import auth
from ..database import get_session
from ..dependencies import get_storage_service
from ..interfaces import BaseStorageService
from ..models import ProfilePhoto, User
from ..utils import IMAGE_EXTENSIONS, build_storage_name, validate_upload_data
from .dependencies import require_admin

router = APIRouter(prefix="/profile", tags=["profile"])
MAX_PROFILE_PHOTO_BYTES = 10 * 1024 * 1024


@router.get("/photo")
async def get_profile_photo(
    session: AsyncSession = Depends(get_session),
) -> dict[str, str | None]:
    photo = await session.get(ProfilePhoto, 1)
    return {"image_url": photo.image_url if photo else None}


@router.post("/photo")
async def upload_profile_photo(
    photo: UploadFile = File(...),
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
    storage_service: BaseStorageService = Depends(get_storage_service),
) -> dict[str, str]:
    require_admin(current_user)
    content = await photo.read(MAX_PROFILE_PHOTO_BYTES + 1)
    validate_upload_data(
        photo.filename,
        len(content),
        IMAGE_EXTENSIONS,
        MAX_PROFILE_PHOTO_BYTES,
        "Profile photo",
    )
    if len(content) > MAX_PROFILE_PHOTO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Profile photo exceeds the maximum size of {MAX_PROFILE_PHOTO_BYTES} bytes",
        )

    filename = build_storage_name(photo.filename or "profile-photo")
    image_url = await storage_service.upload_file(content, "profile", filename)
    profile_photo = await session.get(ProfilePhoto, 1)
    if profile_photo is None:
        profile_photo = ProfilePhoto(id=1, image_url=image_url)
        session.add(profile_photo)
    else:
        profile_photo.image_url = image_url
    await session.commit()
    return {"image_url": image_url}
