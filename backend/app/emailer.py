import logging
import os
from typing import TypedDict, cast

import resend

logger = logging.getLogger(__name__)

_EmailPayload = TypedDict(
    "_EmailPayload",
    {"from": str, "to": list[str], "subject": str, "html": str},
)

resend.api_key = os.getenv("RESEND_API_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
_configured_from_email = os.getenv("FROM_EMAIL")
if not _configured_from_email:
    logger.warning("FROM_EMAIL is not set; using Resend's onboarding sender")
FROM_EMAIL = _configured_from_email or "onboarding@resend.dev"


def _validate_resend_api_key() -> None:
    api_key = resend.api_key or ""
    has_quotes = '"' in api_key or "'" in api_key
    has_bearer_prefix = api_key.lower().startswith("bearer ")
    has_whitespace = any(character.isspace() for character in api_key)

    if not api_key:
        logger.critical(
            "CRITICAL ERROR: RESEND_API_KEY is not set in environment variables!"
        )
        raise RuntimeError("RESEND_API_KEY is not configured")
    if (
        not api_key.startswith("re_")
        or has_whitespace
        or has_quotes
        or has_bearer_prefix
    ):
        raise RuntimeError(
            "RESEND_API_KEY must contain only the raw Resend key, without quotes or a Bearer prefix"
        )


def _send_email(
    payload: _EmailPayload, email: str, purpose: str
) -> None:
    _validate_resend_api_key()
    try:
        resend.Emails.send(cast(resend.Emails.SendParams, payload))
    except Exception:
        logger.exception("Resend %s failed for %s", purpose, email)
        raise


def send_password_reset_email(email: str, token: str) -> None:
    reset_url = f"{FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
    payload: _EmailPayload = {
        "from": FROM_EMAIL,
        "to": [email],
        "subject": "DJ Bilal — Şifre Sıfırlama",
        "html": f"""
        <p>Merhaba,</p>
        <p>Şifrenizi sıfırlamak için aşağıdaki bağlantıya tıklayın. Bu bağlantı 1 saat içinde geçersiz olacaktır.</p>
        <p><a href="{reset_url}">Şifremi Sıfırla</a></p>
        <p>Eğer bu isteği siz yapmadıysanız, bu e-postayı görmezden gelin.</p>
        """,
    }
    _send_email(payload, email, "password reset email")


def send_email_verification_code(email: str, code: str) -> None:
    payload: _EmailPayload = {
        "from": FROM_EMAIL,
        "to": [email],
        "subject": "DJ Bilal — E-posta Doğrulama Kodu",
        "html": (
            "<p>Merhaba,</p>"
            "<p>Hesabınızı doğrulamak için aşağıdaki kodu kullanın. "
            "Kod 15 dakika içinde geçersiz olacaktır.</p>"
            f'<p style="font-size:32px;font-weight:bold;letter-spacing:8px">{code}</p>'
            "<p>Bu isteği siz yapmadıysanız bu e-postayı yok sayabilirsiniz.</p>"
        ),
    }
    _send_email(payload, email, "verification email")
