from io import BytesIO
from threading import get_ident

import pytest
from starlette.datastructures import UploadFile

from app.adapters.r2_storage import R2StorageService


@pytest.mark.asyncio
async def test_upload_file_offloads_boto_upload_using_buffered_bytes(monkeypatch):
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
    upload = UploadFile(file=BytesIO(b"audio bytes"), filename="track.mp3")

    result = await R2StorageService().upload_file(upload, "previews", "track.mp3")

    assert result == "https://cdn.example.com/previews/track.mp3"
    assert upload_calls[0][:3] == (b"audio bytes", "bucket", "previews/track.mp3")
    assert upload_calls[0][3] != main_thread_id
    assert upload.file.tell() == len(b"audio bytes")


@pytest.mark.asyncio
async def test_upload_uses_buffer_even_if_request_file_closes_before_boto_runs(monkeypatch):
    upload_calls = []

    class FakeS3Client:
        def upload_fileobj(self, file_obj, bucket, key):
            upload_calls.append((file_obj.read(), bucket, key))

    async def close_request_file_then_run_in_threadpool(function, *args):
        upload.file.close()
        from asyncio import to_thread

        return await to_thread(function, *args)

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
    monkeypatch.setattr(
        "app.adapters.r2_storage.run_in_threadpool",
        close_request_file_then_run_in_threadpool,
    )
    upload = UploadFile(file=BytesIO(b"audio bytes"), filename="track.mp3")

    result = await R2StorageService().upload_file(upload, "tracks", "track.mp3")

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
    upload = UploadFile(file=BytesIO(b"local audio"), filename="track.mp3")

    result = await R2StorageService().upload_file(upload, "tracks", "track.mp3")

    assert result == "/media/tracks/track.mp3"
    assert (tmp_path / "tracks" / "track.mp3").read_bytes() == b"local audio"
    assert upload.file.tell() == len(b"local audio")
