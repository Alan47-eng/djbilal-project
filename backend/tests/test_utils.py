import io

import pytest
from fastapi import HTTPException, status
from starlette.datastructures import UploadFile

from app.utils import (
    build_storage_name,
    save_upload_file,
    validate_upload_data,
    validate_upload_file,
)


def test_build_storage_name_sanitizes_filename():
    name = build_storage_name(r"..\..\my track?.mp3")

    assert name.endswith(".mp3")
    assert "/" not in name
    assert "\\" not in name
    assert ".." not in name


def test_validate_upload_file_rejects_unsupported_extension():
    upload = type("Upload", (), {"filename": "track.exe"})()

    with pytest.raises(HTTPException) as exc_info:
        validate_upload_file(upload, {".mp3"}, 1024, "Track file")

    assert exc_info.value.status_code == 400


def test_validate_upload_file_does_not_consume_or_close_content():
    upload = UploadFile(filename="track.mp3", file=io.BytesIO(b"audio bytes"))
    upload.file.seek(4)

    validate_upload_file(upload, {".mp3"}, 1024, "Track file")

    assert not upload.file.closed
    assert upload.file.tell() == 4


def test_validate_upload_data_uses_content_too_large_status():
    with pytest.raises(HTTPException) as exc_info:
        validate_upload_data("track.mp3", 4, {".mp3"}, 3, "Track file")

    assert exc_info.value.status_code == status.HTTP_413_CONTENT_TOO_LARGE


@pytest.mark.asyncio
async def test_save_upload_file_streams_and_persists(tmp_path):
    upload = UploadFile(filename="track.mp3", file=io.BytesIO(b"hello world"))
    destination = tmp_path / "track.mp3"

    await save_upload_file(upload, destination, max_bytes=1024)

    assert destination.read_bytes() == b"hello world"


@pytest.mark.asyncio
async def test_save_upload_file_rejects_oversized_payload(tmp_path):
    upload = UploadFile(filename="track.mp3", file=io.BytesIO(b"abcd"))
    destination = tmp_path / "track.mp3"

    with pytest.raises(HTTPException) as exc_info:
        await save_upload_file(upload, destination, max_bytes=3)

    assert exc_info.value.status_code == 413
    assert not destination.exists()
