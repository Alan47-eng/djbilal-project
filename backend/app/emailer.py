import json
import logging
import os
from urllib import request, error

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
FROM_EMAIL = os.getenv("FROM_EMAIL", "onboarding@resend.dev")


def send_password_reset_email(email: str, token: str) -> None:
    """Send a password reset email using Resend's REST API.

    This avoids depending on a specific `resend` SDK version that may not expose
    the `Resend` class in this environment.
    """
    if not RESEND_API_KEY:
        return

    reset_url = f"{FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
    subject = "DJ Bilal — Şifre Sıfırlama"
    html = f"""
    <p>Merhaba,</p>
    <p>Şifrenizi sıfırlamak için aşağıdaki bağlantıya tıklayın. Bu bağlantı 1 saat içinde geçersiz olacaktır.</p>
    <p><a href=\"{reset_url}\">Şifremi Sıfırla</a></p>
    <p>Eğer bu isteği siz yapmadıysanız, bu e-postayı görmezden gelin.</p>
    """

    payload = {
        "from": FROM_EMAIL,
        "to": [email],
        "subject": subject,
        "html": html,
    }

    req = request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=20) as response:
            response.read()
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        logger.warning("Resend email send failed for %s: %s %s", email, exc.code, body)
    except Exception as exc:
        logger.warning("Resend email send exception for %s: %s", email, exc)
