import pytest
import httpx

from app.adapters.lemon_squeezy import LemonSqueezyService


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_checkout_retries_transient_network_error(monkeypatch):
    monkeypatch.setenv("LEMON_SQUEEZY_API_KEY", "test-api-key")
    monkeypatch.setenv("LEMON_SQUEEZY_STORE_ID", "store-123")
    calls = []

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers, json):
            calls.append(json)
            if len(calls) == 1:
                raise httpx.ConnectError("temporary network failure")
            return FakeResponse(200, {"data": {"attributes": {"url": "https://checkout.test/retry"}}})

    monkeypatch.setattr("app.adapters.lemon_squeezy.httpx.AsyncClient", FakeAsyncClient)

    result = await LemonSqueezyService(max_attempts=2, retry_delay=0).create_checkout_session(
        variant_quantities=[{"variant_id": 101, "quantity": 1}],
        custom_data={"track_id": "1"},
    )

    assert result == "https://checkout.test/retry"
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_checkout_uses_fallback_when_provider_omits_url(monkeypatch):
    monkeypatch.setenv("LEMON_SQUEEZY_API_KEY", "test-api-key")
    monkeypatch.setenv("LEMON_SQUEEZY_STORE_ID", "store-123")

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers, json):
            return FakeResponse(200, {"data": {"attributes": {}}})

    monkeypatch.setattr("app.adapters.lemon_squeezy.httpx.AsyncClient", FakeAsyncClient)

    result = await LemonSqueezyService(max_attempts=1, retry_delay=0).create_checkout_session(
        variant_quantities=[{"variant_id": 101, "quantity": 1}],
        custom_data={"track_id": "1"},
        email="buyer@example.com",
        fallback_url="https://checkout.test/fallback",
    )

    assert result.startswith("https://checkout.test/fallback?")
    assert "checkout%5Bcustom%5D%5Btrack_id%5D=1" in result
