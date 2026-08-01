from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserRead(BaseModel):
    id: int
    email: EmailStr
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TrackCreate(BaseModel):
    title: str
    artist: str
    price: float
    cover_image_url: str | None = None
    checkout_url: str | None = None
    preview_url: str
    full_file_path: str

    @field_validator('title', 'artist')
    @classmethod
    def title_artist_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Title and artist cannot be empty')
        return v.strip()

    @field_validator('price')
    @classmethod
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be greater than 0')
        if v > 999999.99:
            raise ValueError('Price cannot exceed 999999.99')
        return v

    @field_validator('cover_image_url', 'checkout_url', 'preview_url', 'full_file_path')
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
    preview_url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DownloadResponse(BaseModel):
    track_id: int
    full_file_path: str
    download_url: str

    model_config = ConfigDict(from_attributes=True)

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
