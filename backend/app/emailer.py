import logging
import os
from typing import TypedDict, cast
from urllib.parse import quote, urlsplit

import resend

logger = logging.getLogger(__name__)

_DEFAULT_FRONTEND_URL = "http://localhost:3000"
_INVALID_FRONTEND_URL_FALLBACK = "https://dj-bilal.com"

_EmailPayload = TypedDict(
    "_EmailPayload",
    {"from": str, "to": list[str], "subject": str, "html": str},
)

resend.api_key = os.getenv("RESEND_API_KEY")
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


def _get_frontend_url() -> str:
    frontend_url = os.getenv("FRONTEND_URL", _DEFAULT_FRONTEND_URL).strip()
    try:
        parsed_url = urlsplit(frontend_url)
        _ = parsed_url.port
        if (
            parsed_url.scheme not in {"http", "https"}
            or not parsed_url.netloc
            or not parsed_url.hostname
            or parsed_url.username
            or parsed_url.password
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise ValueError("FRONTEND_URL must be an absolute HTTP(S) URL")
    except ValueError:
        logger.error("FRONTEND_URL is invalid; using the production frontend URL")
        return _INVALID_FRONTEND_URL_FALLBACK
    return frontend_url.rstrip("/")


def _email_language(lang: str) -> str:
    return "ar" if lang == "ar" else "en"


def send_password_reset_email(email: str, token: str, lang: str = "en") -> None:
    language = _email_language(lang)
    reset_url = f"{_get_frontend_url()}/reset-password?token={quote(token, safe='')}"
    if language == "ar":
        subject = "DJ Bilal — إعادة تعيين كلمة المرور"
        body = (
            '<p dir="rtl" lang="ar">مرحبًا،</p>'
            '<p dir="rtl" lang="ar">انقر على الرابط أدناه لإعادة تعيين كلمة المرور. '
            "ستنتهي صلاحية هذا الرابط خلال ساعة واحدة.</p>"
            f'<p dir="rtl" lang="ar"><a href="{reset_url}">إعادة تعيين كلمة المرور</a></p>'
            '<p dir="rtl" lang="ar">إذا لم تطلب ذلك، فتجاهل هذه الرسالة.</p>'
        )
    else:
        subject = "DJ Bilal — Password Reset"
        body = (
            "<p>Hello,</p>"
            "<p>Use the link below to reset your password. "
            "This link will expire in one hour.</p>"
            f'<p><a href="{reset_url}">Reset my password</a></p>'
            "<p>If you did not request this, you can ignore this email.</p>"
        )
    payload: _EmailPayload = {
        "from": FROM_EMAIL,
        "to": [email],
        "subject": subject,
        "html": body,
    }
    _send_email(payload, email, "password reset email")


def send_email_verification_code(email: str, code: str, lang: str = "en") -> None:
    if _email_language(lang) == "ar":
        subject = "DJ Bilal — رمز التحقق من البريد الإلكتروني"
        body = (
            '<p dir="rtl" lang="ar">مرحبًا،</p>'
            '<p dir="rtl" lang="ar">استخدم الرمز أدناه للتحقق من حسابك. '
            "ستنتهي صلاحية الرمز خلال 15 دقيقة.</p>"
            f'<p dir="rtl" lang="ar" style="font-size:32px;font-weight:bold;letter-spacing:8px">{code}</p>'
            '<p dir="rtl" lang="ar">إذا لم تطلب ذلك، فتجاهل هذه الرسالة.</p>'
        )
    else:
        subject = "DJ Bilal — Email Verification Code"
        body = (
            "<p>Hello,</p>"
            "<p>Use the code below to verify your account. "
            "The code will expire in 15 minutes.</p>"
            f'<p style="font-size:32px;font-weight:bold;letter-spacing:8px">{code}</p>'
            "<p>If you did not request this, you can ignore this email.</p>"
        )
    payload: _EmailPayload = {
        "from": FROM_EMAIL,
        "to": [email],
        "subject": subject,
        "html": body,
    }
    _send_email(payload, email, "verification email")
