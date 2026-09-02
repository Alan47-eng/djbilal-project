import re
from pydantic import BaseModel, EmailStr, field_validator, model_validator, ConfigDict
from datetime import datetime

PAID_TRACK_CATEGORIES = {"edit", "remix"}
FREE_TRACK_CATEGORIES = {"remix", "simple-pack", "vst"}
ALL_TRACK_CATEGORIES = PAID_TRACK_CATEGORIES | FREE_TRACK_CATEGORIES

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str):
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("Password must contain at least one letter and one number")
        return value

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None):
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Full name cannot be empty")
        if len(normalized) > 255:
            raise ValueError("Full name is too long")
        return normalized

class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class TrackCreate(BaseModel):
    title: str
    artist: str
    price: float
    cover_image_url: str | None = None
    checkout_url: str | None = None
    lemon_variant_id: int | None = None
    preview_url: str
    full_file_path: str
    is_free: bool = False
    free_download_url: str | None = None
    category: str = "edit"

    @field_validator('title', 'artist')
    @classmethod
    def title_artist_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Title and artist cannot be empty')
        return v.strip()

    @field_validator('price')
    @classmethod
    def price_must_be_valid(cls, v):
        if v < 0:
            raise ValueError('Price must be greater than 0')
        if v > 999999.99:
            raise ValueError('Price cannot exceed 999999.99')
        return v

    @model_validator(mode='after')
    def validate_price_by_type(self):
        if not self.is_free and self.price <= 0:
            raise ValueError('Price must be greater than 0 for paid tracks')
        return self

    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str):
        normalized = v.strip().lower()
        if normalized not in ALL_TRACK_CATEGORIES:
            raise ValueError('Category must be one of: edit, remix, simple-pack, vst')
        return normalized

    @model_validator(mode='after')
    def validate_category_by_type(self):
        if self.is_free and self.category == "edit":
            self.category = "remix"
        if self.is_free and self.category not in FREE_TRACK_CATEGORIES:
            raise ValueError('Free tracks must use category: remix, simple-pack, or vst')
        if not self.is_free and self.category not in PAID_TRACK_CATEGORIES:
            raise ValueError('Paid tracks must use category: edit or remix')
        return self

    @field_validator('lemon_variant_id')
    @classmethod
    def validate_lemon_variant_id(cls, value):
        if value is None:
            return value
        if value <= 0:
            raise ValueError('Lemon variant ID must be a positive integer')
        return value

    @field_validator('cover_image_url', 'checkout_url', 'preview_url', 'full_file_path', 'free_download_url')
    @classmethod
    def urls_not_empty(cls, v):
        if v is None:
            return v
        if not v.strip():
            raise ValueError('URLs cannot be empty')
        return v.strip()

class TrackUpdate(BaseModel):
    title: str | None = None
    artist: str | None = None
    price: float | None = None
    cover_image_url: str | None = None
    checkout_url: str | None = None
    lemon_variant_id: int | None = None
    preview_url: str | None = None
    is_free: bool | None = None
    free_download_url: str | None = None
    category: str | None = None

    @field_validator('title', 'artist')
    @classmethod
    def title_artist_not_empty(cls, v):
        if v is None:
            return v
        if not v or not v.strip():
            raise ValueError('Title and artist cannot be empty')
        return v.strip()

    @field_validator('price')
    @classmethod
    def price_must_be_valid(cls, v):
        if v is None:
            return v
        if v < 0:
            raise ValueError('Price must be greater than 0')
        if v > 999999.99:
            raise ValueError('Price cannot exceed 999999.99')
        return v

    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str | None):
        if v is None:
            return v
        normalized = v.strip().lower()
        if normalized not in ALL_TRACK_CATEGORIES:
            raise ValueError('Category must be one of: edit, remix, simple-pack, vst')
        return normalized

    @field_validator('lemon_variant_id')
    @classmethod
    def validate_lemon_variant_id(cls, value):
        if value is None:
            return value
        if value <= 0:
            raise ValueError('Lemon variant ID must be a positive integer')
        return value

    @field_validator('cover_image_url', 'checkout_url', 'preview_url', 'free_download_url')
    @classmethod
    def urls_not_empty(cls, v):
        if v is None:
            return v
        if not v.strip():
            raise ValueError('URLs cannot be empty')
        return v.strip()


class TrackResponse(BaseModel):
    id: int
    title: str
    artist: str
    price: float
    cover_image_url: str | None = None
    checkout_url: str | None = None
    lemon_variant_id: int | None = None
    preview_url: str
    is_free: bool = False
    free_download_url: str | None = None
    category: str = "edit"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseDetail(BaseModel):
    id: int
    track_id: int
    track_title: str
    track_artist: str
    cover_image_url: str | None = None
    download_url: str
    license_pdf_url: str
    license_type: str | None = None
    purchased_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DownloadResponse(BaseModel):
    track_id: int
    full_file_path: str
    download_url: str

    model_config = ConfigDict(from_attributes=True)


class CartCheckoutRequest(BaseModel):
    track_ids: list[int]

    @field_validator("track_ids")
    @classmethod
    def validate_track_ids(cls, values: list[int]):
        if not values:
            raise ValueError("track_ids cannot be empty")
        unique_ids = []
        seen = set()
        for track_id in values:
            if track_id <= 0:
                raise ValueError("track_ids must contain positive integers")
            if track_id not in seen:
                seen.add(track_id)
                unique_ids.append(track_id)
        return unique_ids

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
