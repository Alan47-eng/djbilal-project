import os
from resend import Resend

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
FROM_EMAIL = os.getenv("FROM_EMAIL", "no-reply@djbilal.com")

client = Resend(RESEND_API_KEY) if RESEND_API_KEY else None


def send_password_reset_email(email: str, token: str) -> None:
    """Send a password reset email using Resend.

    Constructs a frontend reset link and sends a simple HTML email.
    If RESEND_API_KEY is not configured, this is a no-op (useful for local dev).
    """
    if client is None:
        # In dev environments without an API key, do nothing.
        return

    reset_url = f"{FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
    subject = "DJ Bilal — Şifre Sıfırlama"
    html = f"""
    <p>Merhaba,</p>
    <p>Şifrenizi sıfırlamak için aşağıdaki bağlantıya tıklayın. Bu bağlantı 1 saat içinde geçersiz olacaktır.</p>
    <p><a href=\"{reset_url}\">Şifremi Sıfırla</a></p>
    <p>Eğer bu isteği siz yapmadıysanız, bu e-postayı görmezden gelin.</p>
    """

    # Resend client expects a dict payload
    client.emails.send({
        "from": FROM_EMAIL,
        "to": [email],
        "subject": subject,
        "html": html,
    })
