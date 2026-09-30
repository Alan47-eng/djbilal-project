import pytest

from app import config


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        ("https://djbilal.com", ["https://djbilal.com"]),
        ('"https://djbilal.com/"', ["https://djbilal.com"]),
        ("[https://djbilal.com]", ["https://djbilal.com"]),
        (
            "[https://djbilal.com](https://djbilal.com)",
            ["https://djbilal.com"],
        ),
        (
            '["https://djbilal.com", "https://www.djbilal.com"]',
            ["https://djbilal.com", "https://www.djbilal.com"],
        ),
    ],
)
def test_parse_frontend_origins_normalizes_wrappers(
    monkeypatch: pytest.MonkeyPatch,
    configured: str,
    expected: list[str],
) -> None:
    monkeypatch.setattr(config, "IS_PRODUCTION", True)

    assert config.parse_frontend_origins(configured) == expected


@pytest.mark.parametrize(
    "configured",
    [
        "http://djbilal.com",
        "https://djbilal.com/app",
        "https://*.djbilal.com",
        "[https://djbilal.com](https://attacker.example)",
    ],
)
def test_parse_frontend_origins_rejects_invalid_production_origins(
    monkeypatch: pytest.MonkeyPatch,
    configured: str,
) -> None:
    monkeypatch.setattr(config, "IS_PRODUCTION", True)

    with pytest.raises(RuntimeError):
        config.parse_frontend_origins(configured)
