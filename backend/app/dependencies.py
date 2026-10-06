from fastapi import Depends

from .adapters import GumroadService, R2StorageService
from .interfaces import BaseStorageService
from .services import PurchaseService, TrackService


def get_storage_service() -> BaseStorageService:
    return R2StorageService()


def get_gumroad_service() -> GumroadService:
    return GumroadService()


def get_track_service(
    storage_service: BaseStorageService = Depends(get_storage_service),
) -> TrackService:
    return TrackService(storage_service=storage_service)


def get_purchase_service(
    gumroad_service: GumroadService = Depends(get_gumroad_service),
    track_service: TrackService = Depends(get_track_service),
) -> PurchaseService:
    return PurchaseService(
        gumroad_service=gumroad_service,
        track_service=track_service,
    )
