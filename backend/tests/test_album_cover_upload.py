from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile

from app.interfaces import BaseStorageService
from app.models import User
from app.routers.albums import upload_album_cover


class FakeStorageService(BaseStorageService):
    def __init__(self):
        self.uploaded = None

    async def upload_file(self, content, folder, filename):
        self.uploaded = (content, folder, filename)
        return f"/media/{folder}/{filename}"

    def generate_signed_url(self, object_key, expires_in=900):
        return object_key

    def delete_file(self, object_key):
        return None


@pytest.mark.asyncio
async def test_album_cover_upload_persists_valid_image():
    storage = FakeStorageService()
    result = await upload_album_cover(
        UploadFile(filename="album-cover.png", file=BytesIO(b"image-bytes")),
        User(email="admin@example.com", hashed_password="test-hash", is_admin=True),
        storage,
    )

    assert result["cover_image_url"].startswith("/media/covers/album-cover-")
    assert result["cover_image_url"].endswith(".png")
    assert storage.uploaded[0:2] == (b"image-bytes", "covers")


@pytest.mark.asyncio
async def test_album_cover_upload_rejects_unsupported_file_type():
    with pytest.raises(HTTPException) as error:
        await upload_album_cover(
            UploadFile(filename="cover.svg", file=BytesIO(b"<svg />")),
            User(email="admin@example.com", hashed_password="test-hash", is_admin=True),
            FakeStorageService(),
        )

    assert error.value.status_code == 400
