import pytest

from app import emailer


@pytest.mark.parametrize(
    ("lang", "subject", "copy"),
    [
        ("en", "Password Reset", "Reset my password"),
        ("ar", "إعادة تعيين كلمة المرور", "إعادة تعيين كلمة المرور"),
    ],
)
def test_password_reset_email_uses_valid_frontend_url_and_language(
    monkeypatch, lang, subject, copy
):
    sent = []
    monkeypatch.setenv("FRONTEND_URL", "https://dj-bilal.com/")
    monkeypatch.setattr(
        emailer, "_send_email", lambda payload, email, purpose: sent.append(payload)
    )

    emailer.send_password_reset_email("user@example.com", "reset token", lang=lang)

    assert subject in sent[0]["subject"]
    assert (
        'href="https://dj-bilal.com/reset-password?token=reset%20token"'
        in sent[0]["html"]
    )
    assert copy in sent[0]["html"]


def test_password_reset_email_falls_back_when_frontend_url_is_malformed(monkeypatch):
    sent = []
    monkeypatch.setenv("FRONTEND_URL", "http:///reset-password")
    monkeypatch.setattr(
        emailer, "_send_email", lambda payload, email, purpose: sent.append(payload)
    )

    emailer.send_password_reset_email("user@example.com", "token")

    assert "https://dj-bilal.com/reset-password?token=token" in sent[0]["html"]
    assert "http:///reset-password" not in sent[0]["html"]


@pytest.mark.parametrize(
    ("lang", "subject", "copy"),
    [
        ("en", "Email Verification Code", "verify your account"),
        ("ar", "رمز التحقق من البريد الإلكتروني", "للتحقق من حسابك"),
    ],
)
def test_verification_email_uses_requested_language(monkeypatch, lang, subject, copy):
    sent = []
    monkeypatch.setattr(
        emailer, "_send_email", lambda payload, email, purpose: sent.append(payload)
    )

    emailer.send_email_verification_code("user@example.com", "123456", lang=lang)

    assert subject in sent[0]["subject"]
    assert copy in sent[0]["html"]
    assert "123456" in sent[0]["html"]
