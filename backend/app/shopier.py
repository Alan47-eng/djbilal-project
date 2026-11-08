"""Shopier signature helpers based on the supplied PHP integration sample."""

import base64
import hashlib
import hmac


def _signature(secret: str, message: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def checkout_signature(
    secret: str,
    random_nr: str,
    platform_order_id: str,
    total_order_value: str,
    currency: int,
) -> str:
    message = f"{random_nr}{platform_order_id}{total_order_value}{currency}"
    return _signature(secret, message)


def callback_signature(secret: str, random_nr: str, platform_order_id: str) -> str:
    return _signature(secret, f"{random_nr}{platform_order_id}")


def verify_callback_signature(
    secret: str,
    random_nr: str,
    platform_order_id: str,
    provided_signature: str,
) -> bool:
    expected = callback_signature(secret, random_nr, platform_order_id)
    return hmac.compare_digest(expected, provided_signature)
