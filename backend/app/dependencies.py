from fastapi import Depends

from .adapters import R2StorageService
from .interfaces import BaseStorageService
from .services import TrackService


def get_storage_service() -> BaseStorageService:
    return R2StorageService()


def get_track_service(
    storage_service: BaseStorageService = Depends(get_storage_service),
) -> TrackService:
    return TrackService(storage_service=storage_service)
