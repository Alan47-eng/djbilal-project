from abc import ABC, abstractmethod
from typing import TypedDict

from ..json_types import JSONObject


class WebhookEvent(TypedDict):
    successful: bool
    custom_data: dict[str, str]


class BasePaymentGateway(ABC):
    @abstractmethod
    async def create_checkout_session(
        self,
        *,
        variant_quantities: list[dict[str, int]],
        custom_data: dict[str, str],
        email: str | None = None,
        custom_price: int | None = None,
        fallback_url: str | None = None,
    ) -> str:
        """Create a provider checkout session and return its redirect URL."""

    @abstractmethod
    def verify_webhook(self, raw_body: bytes, signature: str | None) -> bool:
        """Verify a provider webhook signature."""

    @abstractmethod
    def handle_webhook_event(self, payload: JSONObject) -> WebhookEvent:
        """Normalize a provider event for application-level processing."""
