from fastapi import Depends

from .adapters import LemonSqueezyService, R2StorageService
from .interfaces import BasePaymentGateway, BaseStorageService
from .services import PurchaseService, TrackService


def get_storage_service() -> BaseStorageService:
    return R2StorageService()


def get_payment_gateway() -> BasePaymentGateway:
    return LemonSqueezyService()


def get_track_service(
    storage_service: BaseStorageService = Depends(get_storage_service),
    payment_gateway: BasePaymentGateway = Depends(get_payment_gateway),
) -> TrackService:
    return TrackService(
        storage_service=storage_service,
        payment_gateway=payment_gateway,
    )


def get_purchase_service(
    payment_gateway: BasePaymentGateway = Depends(get_payment_gateway),
    track_service: TrackService = Depends(get_track_service),
) -> PurchaseService:
    return PurchaseService(
        payment_gateway=payment_gateway,
        track_service=track_service,
    )
