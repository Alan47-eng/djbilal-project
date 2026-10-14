from io import BytesIO
from threading import get_ident

import pytest

from app.adapters.r2_storage import R2StorageService


@pytest.mark.asyncio
async def test_upload_file_offloads_boto_upload_using_bytes(monkeypatch):
    main_thread_id = get_ident()
    upload_calls = []

    class FakeS3Client:
        def upload_fileobj(self, file_obj, bucket, key):
            upload_calls.append((file_obj.read(), bucket, key, get_ident()))

    monkeypatch.setattr(
        R2StorageService,
        "get_config",
        staticmethod(
            lambda: {
                "account_id": "account",
                "access_key_id": "access",
                "secret_access_key": "secret",
                "bucket_name": "bucket",
                "public_url": "https://cdn.example.com",
            }
        ),
    )
    monkeypatch.setattr(
        R2StorageService, "_client", staticmethod(lambda: FakeS3Client())
    )
    result = await R2StorageService().upload_file(b"audio bytes", "previews", "track.mp3")

    assert result == "https://cdn.example.com/previews/track.mp3"
    assert upload_calls[0][:3] == (b"audio bytes", "bucket", "previews/track.mp3")
    assert upload_calls[0][3] != main_thread_id


@pytest.mark.asyncio
async def test_upload_file_accepts_independent_bytes_io_stream(monkeypatch):
    upload_calls = []

    class FakeS3Client:
        def upload_fileobj(self, file_obj, bucket, key):
            upload_calls.append((file_obj.read(), bucket, key))

    monkeypatch.setattr(
        R2StorageService,
        "get_config",
        staticmethod(
            lambda: {
                "account_id": "account",
                "access_key_id": "access",
                "secret_access_key": "secret",
                "bucket_name": "bucket",
                "public_url": "https://cdn.example.com",
            }
        ),
    )
    monkeypatch.setattr(
        R2StorageService, "_client", staticmethod(lambda: FakeS3Client())
    )
    content = BytesIO(b"audio bytes")
    content.seek(4)
    result = await R2StorageService().upload_file(content, "tracks", "track.mp3")

    assert result == "tracks/track.mp3"
    assert upload_calls == [(b"audio bytes", "bucket", "tracks/track.mp3")]


@pytest.mark.asyncio
async def test_local_upload_fallback_offloads_file_copy(monkeypatch, tmp_path):
    monkeypatch.setattr("app.adapters.r2_storage.UPLOAD_ROOT", tmp_path)
    monkeypatch.setattr(
        R2StorageService,
        "get_config",
        staticmethod(lambda: {"account_id": None, "bucket_name": None}),
    )
    monkeypatch.setattr(R2StorageService, "_client", staticmethod(lambda: None))
    result = await R2StorageService().upload_file(
        BytesIO(b"local audio"), "tracks", "track.mp3"
    )

    assert result == "/media/tracks/track.mp3"
    assert (tmp_path / "tracks" / "track.mp3").read_bytes() == b"local audio"
