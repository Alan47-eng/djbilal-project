from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .. import auth, schemas
from ..database import get_session
from ..dependencies import get_purchase_service, get_storage_service, get_track_service
from ..interfaces import BaseStorageService
from ..models import Track, User
from ..services import TrackService, PurchaseService
from ..utils import (
    is_r2_object_key,
    normalize_media_url,
    resolve_uploaded_file_path,
)
from .dependencies import require_admin

router = APIRouter(prefix="/tracks", tags=["tracks"])


def _track_response(track: Track) -> schemas.TrackResponse:
    return schemas.TrackResponse.model_validate(
        {
            "id": track.id,
            "title": track.title,
            "artist": track.artist,
            "price": track.price,
            "cover_image_url": normalize_media_url(track.cover_image_url),
            "external_product_id": track.external_product_id,
            "preview_url": normalize_media_url(track.preview_url),
            "is_free": track.is_free,
            "free_download_url": normalize_media_url(track.free_download_url),
            "category": track.category,
            "created_at": track.created_at,
        }
    )


@router.post("", response_model=schemas.TrackResponse)
async def create_track(
    track: schemas.TrackCreate,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
    track_service: TrackService = Depends(get_track_service),
) -> Track:
    require_admin(current_user)
    return await track_service.create_track(session, track)


@router.post("/upload", response_model=schemas.TrackResponse)
async def upload_track(
    title: str = Form(...),
    artist: str = Form(...),
    category: str = Form(...),
    price: float | None = Form(None),
    external_product_id: str | None = Form(None),
    is_free: bool = Form(False),
    free_download_url: str | None = Form(None),
    track_file: UploadFile = File(...),
    preview_file: UploadFile = File(...),
    cover_file: UploadFile | None = File(None),
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
    track_service: TrackService = Depends(get_track_service),
) -> Track:
    require_admin(current_user)
    return await track_service.upload_track(
        session=session,
        title=title,
        artist=artist,
        category=category,
        price=price,
        external_product_id=external_product_id,
        is_free=is_free,
        free_download_url=free_download_url,
        track_file=track_file,
        preview_file=preview_file,
        cover_file=cover_file,
    )


@router.put("/{track_id}", response_model=schemas.TrackResponse)
async def update_track(
    track_id: int,
    track_update: schemas.TrackUpdate,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
    track_service: TrackService = Depends(get_track_service),
) -> schemas.TrackResponse:
    require_admin(current_user)
    track = await track_service.update_track(session, track_id, track_update)
    return _track_response(track)


@router.delete("/{track_id}")
async def delete_track(
    track_id: int,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
    track_service: TrackService = Depends(get_track_service),
) -> dict[str, int | str]:
    require_admin(current_user)
    await track_service.delete_track(session, track_id)
    return {"status": "deleted", "track_id": track_id}


@router.get("", response_model=list[schemas.TrackResponse])
async def list_tracks(
    session: AsyncSession = Depends(get_session),
    track_service: TrackService = Depends(get_track_service),
) -> list[schemas.TrackResponse]:
    tracks = await track_service.get_all_tracks(session)
    return [_track_response(track) for track in tracks]


@router.get("/{track_id}", response_model=schemas.TrackResponse)
async def get_track(
    track_id: int,
    session: AsyncSession = Depends(get_session),
    track_service: TrackService = Depends(get_track_service),
) -> schemas.TrackResponse:
    track = await track_service.get_track(session, track_id)
    return _track_response(track)


@router.get("/{track_id}/free-download", response_model=schemas.DownloadResponse)
async def free_download_track(
    track_id: int,
    session: AsyncSession = Depends(get_session),
    track_service: TrackService = Depends(get_track_service),
) -> schemas.DownloadResponse:
    track = await track_service.get_track(session, track_id)
    if not track.is_free:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This track is not available for free download",
        )
    download_url = normalize_media_url(track.free_download_url) or normalize_media_url(
        track.full_file_path
    )
    return schemas.DownloadResponse.model_validate(
        {
            "track_id": track.id,
            "full_file_path": normalize_media_url(track.full_file_path),
            "download_url": download_url,
        }
    )


@router.get("/{track_id}/free-download-file")
async def free_download_track_file(
    track_id: int,
    session: AsyncSession = Depends(get_session),
    track_service: TrackService = Depends(get_track_service),
) -> FileResponse:
    track = await track_service.get_track(session, track_id)
    if not track.is_free:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This track is not available for free download",
        )
    file_path = resolve_uploaded_file_path(track.full_file_path, "tracks")
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream",
    )


@router.post("/{track_id}/checkout")
async def create_checkout(
    track_id: int,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
    track_service: TrackService = Depends(get_track_service),
) -> dict[str, int | str]:
    return await track_service.create_checkout(session, track_id, current_user)


@router.get("/{track_id}/download", response_model=schemas.DownloadResponse)
async def download_track(
    track_id: int,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
    track_service: TrackService = Depends(get_track_service),
    purchase_service: PurchaseService = Depends(get_purchase_service),
    storage_service: BaseStorageService = Depends(get_storage_service),
) -> schemas.DownloadResponse:
    track = await track_service.get_track(session, track_id)
    if not await purchase_service.can_download(session, current_user.id, track_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must purchase this track before downloading it",
        )

    if is_r2_object_key(track.full_file_path):
        return schemas.DownloadResponse.model_validate(
            {
                "track_id": track.id,
                "full_file_path": track.full_file_path,
                "download_url": storage_service.generate_signed_url(track.full_file_path),
            }
        )

    download_url = normalize_media_url(track.full_file_path)
    return schemas.DownloadResponse.model_validate(
        {
            "track_id": track.id,
            "full_file_path": download_url,
            "download_url": download_url,
        }
    )


@router.get("/{track_id}/download-file", response_model=None)
async def download_track_file(
    track_id: int,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
    track_service: TrackService = Depends(get_track_service),
    purchase_service: PurchaseService = Depends(get_purchase_service),
    storage_service: BaseStorageService = Depends(get_storage_service),
) -> FileResponse | RedirectResponse:
    track = await track_service.get_track(session, track_id)
    if not await purchase_service.can_download(session, current_user.id, track_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must purchase this track before downloading it",
        )

    if is_r2_object_key(track.full_file_path):
        return RedirectResponse(
            url=storage_service.generate_signed_url(track.full_file_path),
            status_code=302,
        )

    file_path = resolve_uploaded_file_path(track.full_file_path, "tracks")
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream",
    )
