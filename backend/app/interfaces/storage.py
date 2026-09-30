from abc import ABC, abstractmethod
from typing import BinaryIO

from fastapi import UploadFile


class BaseStorageService(ABC):
    @abstractmethod
    def upload_file(self, upload_file: UploadFile | BinaryIO, folder: str, filename: str) -> str:
        """Persist a file and return its stored key or URL."""

    @abstractmethod
    def generate_signed_url(self, object_key: str, expires_in: int = 900) -> str:
        """Return a time-limited URL for a private stored object."""

    @abstractmethod
    def delete_file(self, object_key: str) -> None:
        """Delete a stored object."""
