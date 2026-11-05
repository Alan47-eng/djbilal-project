from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import auth, schemas
from ..database import get_session
from ..dependencies import get_storage_service
from ..interfaces import BaseStorageService
from ..models import Album, Track, User
from ..utils import (
    IMAGE_EXTENSIONS,
    MAX_COVER_UPLOAD_BYTES,
    build_storage_name,
    validate_upload_data,
    validate_upload_file,
)
from .dependencies import require_admin

router = APIRouter(prefix="/albums", tags=["albums"])


@router.post("/cover-upload")
async def upload_album_cover(
    cover_file: UploadFile = File(...),
    current_user: User = Depends(auth.get_current_user),
    storage_service: BaseStorageService = Depends(get_storage_service),
) -> dict[str, str]:
    require_admin(current_user)
    validate_upload_file(
        cover_file, IMAGE_EXTENSIONS, MAX_COVER_UPLOAD_BYTES, "Cover image"
    )
    try:
        content = await cover_file.read(MAX_COVER_UPLOAD_BYTES + 1)
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded cover image could not be read; please retry the upload",
        ) from exc
    finally:
        await cover_file.close()

    validate_upload_data(
        cover_file.filename,
        len(content),
        IMAGE_EXTENSIONS,
        MAX_COVER_UPLOAD_BYTES,
        "Cover image",
    )
    filename = build_storage_name(cover_file.filename or "")
    cover_url = await storage_service.upload_file(content, "covers", filename)
    return {"cover_image_url": cover_url}


@router.get("", response_model=list[schemas.AlbumResponse])
async def list_albums(session: AsyncSession = Depends(get_session)) -> list[Album]:
    result = await session.execute(select(Album).order_by(Album.release_date.desc(), Album.id.desc()))
    return list(result.scalars().all())


@router.post(
    "",
    response_model=schemas.AlbumResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_album(
    payload: schemas.AlbumCreate,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Album:
    require_admin(current_user)
    album = Album(**payload.model_dump())
    session.add(album)
    await session.commit()
    await session.refresh(album)
    return album


@router.put("/{album_id}", response_model=schemas.AlbumResponse)
async def update_album(
    album_id: int,
    payload: schemas.AlbumUpdate,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Album:
    require_admin(current_user)
    album = await session.get(Album, album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(album, field, value)
    await session.commit()
    await session.refresh(album)
    return album


@router.delete("/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_album(
    album_id: int,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    require_admin(current_user)
    album = await session.get(Album, album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found")

    tracks = await session.execute(select(Track).where(Track.album_id == album_id))
    for track in tracks.scalars():
        track.album_id = None
    await session.delete(album)
    await session.commit()
