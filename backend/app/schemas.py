import re
import math
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

PAID_TRACK_CATEGORIES = {"edit", "remix"}
FREE_TRACK_CATEGORIES = {"remix", "simple-pack", "vst"}
ALL_TRACK_CATEGORIES = PAID_TRACK_CATEGORIES | FREE_TRACK_CATEGORIES


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserCreate(DTO):
    email: EmailStr
    password: str
    full_name: str | None = None
    lang: Literal["en", "ar"] = "en"

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("Password must contain at least one letter and one number")
        return value

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Full name cannot be empty")
        if len(normalized) > 255:
            raise ValueError("Full name is too long")
        return normalized

class UserRead(DTO):
    id: int
    email: EmailStr
    full_name: str | None = None
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class UserRoleUpdate(DTO):
    role: Literal["user", "admin"]


class TokenResponse(DTO):
    access_token: str
    token_type: str

class LoginRequest(DTO):
    email: EmailStr
    password: str


class PasswordResetRequest(DTO):
    email: EmailStr
    lang: Literal["en", "ar"] = "en"


class EmailVerificationRequest(DTO):
    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$")


class EmailVerificationResendRequest(DTO):
    original_email: EmailStr
    email: EmailStr
    lang: Literal["en", "ar"] = "en"


class PasswordResetConfirm(DTO):
    token: str
    new_password: str


class AlbumCreate(DTO):
    title: str
    cover_image_url: str | None = None
    release_date: date | None = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Album title cannot be empty")
        return value.strip()

    @field_validator("cover_image_url")
    @classmethod
    def cover_url_not_empty(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Cover image URL cannot be empty")
        return value.strip() if value is not None else None


class AlbumUpdate(DTO):
    title: str | None = None
    cover_image_url: str | None = None
    release_date: date | None = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Album title cannot be empty")
        return value.strip() if value is not None else None

    @field_validator("cover_image_url")
    @classmethod
    def cover_url_not_empty(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Cover image URL cannot be empty")
        return value.strip() if value is not None else None


class AlbumResponse(DTO):
    id: int
    title: str
    cover_image_url: str | None = None
    release_date: date | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class TrackCreate(DTO):
    title: str
    artist: str
    price: float
    cover_image_url: str | None = None
    album_id: int | None = None
    preview_url: str
    full_file_path: str
    is_free: bool = False
    free_download_url: str | None = None
    category: str = "edit"

    @field_validator('title', 'artist')
    @classmethod
    def title_artist_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Title and artist cannot be empty')
        return v.strip()

    @field_validator('price')
    @classmethod
    def price_must_be_valid(cls, v: float) -> float:
        if not math.isfinite(v) or v < 0:
            raise ValueError('Price must be greater than 0')
        if v > 999999.99:
            raise ValueError('Price cannot exceed 999999.99')
        return v

    @model_validator(mode='after')
    def validate_price_by_type(self) -> "TrackCreate":
        if not self.is_free and self.price <= 0:
            raise ValueError('Price must be greater than 0 for paid tracks')
        return self

    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        normalized = v.strip().lower()
        if normalized not in ALL_TRACK_CATEGORIES:
            raise ValueError('Category must be one of: edit, remix, simple-pack, vst')
        return normalized

    @field_validator("album_id")
    @classmethod
    def validate_album_id(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("album_id must be a positive integer")
        return value

    @model_validator(mode='after')
    def validate_category_by_type(self) -> "TrackCreate":
        if self.is_free and self.category == "edit":
            self.category = "remix"
        if self.is_free and self.category not in FREE_TRACK_CATEGORIES:
            raise ValueError('Free tracks must use category: remix, simple-pack, or vst')
        if not self.is_free and self.category not in PAID_TRACK_CATEGORIES:
            raise ValueError('Paid tracks must use category: edit or remix')
        return self

    @field_validator('cover_image_url', 'preview_url', 'full_file_path', 'free_download_url')
    @classmethod
    def urls_not_empty(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.strip():
            raise ValueError('URLs cannot be empty')
        return v.strip()

class TrackUpdate(DTO):
    title: str | None = None
    artist: str | None = None
    price: float | None = None
    cover_image_url: str | None = None
    album_id: int | None = None
    preview_url: str | None = None
    is_free: bool | None = None
    free_download_url: str | None = None
    category: str | None = None

    @field_validator('title', 'artist')
    @classmethod
    def title_artist_not_empty(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v or not v.strip():
            raise ValueError('Title and artist cannot be empty')
        return v.strip()

    @field_validator('price')
    @classmethod
    def price_must_be_valid(cls, v: float | None) -> float | None:
        if v is None:
            return v
        if not math.isfinite(v) or v < 0:
            raise ValueError('Price must be greater than 0')
        if v > 999999.99:
            raise ValueError('Price cannot exceed 999999.99')
        return v

    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v is None:
            return v
        normalized = v.strip().lower()
        if normalized not in ALL_TRACK_CATEGORIES:
            raise ValueError('Category must be one of: edit, remix, simple-pack, vst')
        return normalized

    @field_validator("album_id")
    @classmethod
    def validate_album_id(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("album_id must be a positive integer")
        return value

    @field_validator('cover_image_url', 'preview_url', 'free_download_url')
    @classmethod
    def urls_not_empty(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.strip():
            raise ValueError('URLs cannot be empty')
        return v.strip()


class TrackResponse(DTO):
    id: int
    title: str
    artist: str
    price: float
    cover_image_url: str | None = None
    album_id: int | None = None
    preview_url: str
    is_free: bool = False
    free_download_url: str | None = None
    category: str = "edit"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")

class DownloadResponse(DTO):
    track_id: int
    full_file_path: str
    download_url: str

    model_config = ConfigDict(from_attributes=True, extra="forbid")


def calculate_discounted_price(price: float, discount_percent: float) -> float:
    """
    Calculate discounted price.
    
    Args:
        price: Original price (must be > 0)
        discount_percent: Discount percentage (0-100)
        
    Returns:
        Discounted price rounded to 2 decimal places
        
    Raises:
        ValueError: If inputs are invalid
    """
    if price <= 0:
        raise ValueError('Price must be greater than 0')
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError('Discount percentage must be between 0 and 100')
    
    discounted = price * (1 - discount_percent / 100)
    return round(discounted, 2)
