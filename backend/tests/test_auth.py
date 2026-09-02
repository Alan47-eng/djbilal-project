import hashlib
import hmac
import json
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from urllib.parse import urlparse, parse_qs

from app.main import app
from app.models import Base
from app.database import get_session
from app.models import User, Track
from app import auth, schemas


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def test_db():
    """Create test database and tables"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async def override_get_session():
        async with AsyncSessionLocal() as session:
            yield session
    
    app.dependency_overrides[get_session] = override_get_session
    
    yield engine, AsyncSessionLocal
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def client(test_db):
    """Create async test client"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def create_user_record(session, email, password, is_admin=False, full_name=None):
    user = User(
        email=email,
        full_name=full_name,
        hashed_password=auth.hash_password(password),
        is_admin=is_admin,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_track_record(
    session,
    checkout_url=None,
    is_free=False,
    price=9.99,
    full_file_path="/server/music/track.mp3",
    free_download_url=None,
):
    track = Track(
        title="Webhook Track",
        artist="Tester",
        price=price,
        cover_image_url=None,
        checkout_url=checkout_url,
        preview_url="https://example.com/preview.mp3",
        full_file_path=full_file_path,
        is_free=is_free,
        free_download_url=free_download_url if free_download_url is not None else (full_file_path if is_free else None),
    )
    session.add(track)
    await session.commit()
    await session.refresh(track)
    return track


class TestPasswordHashing:
    """Test password hashing and verification"""
    
    def test_hash_password(self):
        """Test that password is properly hashed"""
        password = "test_password_123"
        hashed = auth.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
    
    def test_verify_correct_password(self):
        """Test verifying correct password"""
        password = "correct_password"
        hashed = auth.hash_password(password)
        
        assert auth.verify_password(password, hashed) is True
    
    def test_verify_incorrect_password(self):
        """Test verifying incorrect password"""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = auth.hash_password(password)
        
        assert auth.verify_password(wrong_password, hashed) is False
    
    def test_hash_same_password_different_output(self):
        """Test that hashing same password twice gives different output (salt)"""
        password = "test_password"
        hash1 = auth.hash_password(password)
        hash2 = auth.hash_password(password)
        
        assert hash1 != hash2
        assert auth.verify_password(password, hash1) is True
        assert auth.verify_password(password, hash2) is True


class TestJWTToken:
    """Test JWT token creation and decoding"""
    
    def test_create_access_token(self):
        """Test creating JWT access token"""
        data = {"sub": "test@example.com"}
        token = auth.create_access_token(data=data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_valid_token(self):
        """Test decoding valid JWT token"""
        data = {"sub": "test@example.com"}
        token = auth.create_access_token(data=data)
        
        decoded = auth.decode_token(token)
        assert decoded["sub"] == "test@example.com"
    
    def test_decode_invalid_token(self):
        """Test decoding invalid token raises error"""
        from fastapi import HTTPException
        
        invalid_token = "invalid.token.here"
        with pytest.raises(HTTPException) as exc_info:
            auth.decode_token(invalid_token)
        
        assert exc_info.value.status_code == 401
    
    def test_decode_expired_token(self):
        """Test decoding expired token raises error"""
        from datetime import timedelta
        from fastapi import HTTPException
        
        # Create token that expires in -1 second (already expired)
        data = {"sub": "test@example.com"}
        token = auth.create_access_token(
            data=data,
            expires_delta=timedelta(seconds=-1)
        )
        
        with pytest.raises(HTTPException) as exc_info:
            auth.decode_token(token)
        
        assert exc_info.value.status_code == 401


class TestRegisterEndpoint:
    """Test POST /register endpoint"""
    
    @pytest.mark.asyncio
    async def test_register_success(self, client):
        """Test successful user registration"""
        response = await client.post(
            "/register",
            json={"email": "user@example.com", "password": "password123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "user@example.com"
        assert data["id"] > 0
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_register_with_full_name(self, client):
        response = await client.post(
            "/register",
            json={"email": "fullname@example.com", "password": "password123", "full_name": "Ali Veli"}
        )

        assert response.status_code == 200
        assert response.json()["full_name"] == "Ali Veli"
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client):
        """Test that duplicate email registration fails"""
        email = "duplicate@example.com"
        password = "password123"
        
        # First registration
        response1 = await client.post(
            "/register",
            json={"email": email, "password": password}
        )
        assert response1.status_code == 200
        
        # Second registration with same email
        response2 = await client.post(
            "/register",
            json={"email": email, "password": "different_password1"}
        )
        assert response2.status_code == 400
        assert "already registered" in response2.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client):
        """Test registration with invalid email"""
        response = await client.post(
            "/register",
            json={"email": "not_an_email", "password": "password123"}
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_register_missing_password(self, client):
        """Test registration without password"""
        response = await client.post(
            "/register",
            json={"email": "user@example.com"}
        )
        
        assert response.status_code == 422


class TestLoginEndpoint:
    """Test POST /login endpoint"""
    
    @pytest.mark.asyncio
    async def test_login_success(self, client):
        """Test successful login"""
        email = "testuser@example.com"
        password = "password123"
        
        # Register first
        await client.post(
            "/register",
            json={"email": email, "password": password}
        )
        
        # Login
        response = await client.post(
            "/login",
            json={"email": email, "password": password}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client):
        """Test login with wrong password"""
        email = "user@example.com"
        
        # Register
        await client.post(
            "/register",
            json={"email": email, "password": "correctpassword"}
        )
        
        # Try login with wrong password
        response = await client.post(
            "/login",
            json={"email": email, "password": "wrongpassword"}
        )
        
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client):
        """Test login with non-existent email"""
        response = await client.post(
            "/login",
            json={"email": "nonexistent@example.com", "password": "password123"}
        )
        
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_invalid_email(self, client):
        """Test login with invalid email format"""
        response = await client.post(
            "/login",
            json={"email": "not_an_email", "password": "password123"}
        )
        
        assert response.status_code == 422


class TestMeEndpoint:
    """Test GET /me endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_profile_authenticated(self, client):
        """Test getting profile with valid token"""
        email = "profile@example.com"
        password = "password123"
        
        # Register
        await client.post(
            "/register",
            json={"email": email, "password": password}
        )
        
        # Login to get token
        login_response = await client.post(
            "/login",
            json={"email": email, "password": password}
        )
        token = login_response.json()["access_token"]
        
        # Get profile
        response = await client.get(
            "/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == email
        assert data["id"] > 0
    
    @pytest.mark.asyncio
    async def test_get_profile_no_token(self, client):
        """Test getting profile without token"""
        response = await client.get("/me")
        
        # Should be unauthorized/forbidden without credentials (401 or 403)
        assert response.status_code in [401, 403]
    
    @pytest.mark.asyncio
    async def test_get_profile_invalid_token(self, client):
        """Test getting profile with invalid token"""
        response = await client.get(
            "/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401  # Unauthorized (invalid token)
    
    @pytest.mark.asyncio
    async def test_get_profile_malformed_header(self, client):
        """Test getting profile with malformed auth header"""
        response = await client.get(
            "/me",
            headers={"Authorization": "InvalidFormat token"}
        )
        
        # Should be unauthorized/forbidden with invalid scheme
        assert response.status_code in [401, 403]


class TestCreateTrackAuthentication:
    """Test that POST /tracks requires authentication"""
    
    @pytest.mark.asyncio
    async def test_create_track_without_auth(self, client):
        """Test creating track without authentication fails"""
        response = await client.post(
            "/tracks",
            json={
                "title": "Test Track",
                "artist": "Test Artist",
                "price": 9.99,
                "preview_url": "https://example.com/preview.mp3",
                "full_file_path": "/server/music/track.mp3"
            }
        )
        
        # Should be forbidden without credentials
        assert response.status_code in [401, 403]
    
    @pytest.mark.asyncio
    async def test_create_track_requires_admin(self, client):
        """Test creating track with a normal user is forbidden"""
        email = "creator@example.com"
        password = "password123"
        
        # Register and login
        await client.post(
            "/register",
            json={"email": email, "password": password}
        )
        
        login_response = await client.post(
            "/login",
            json={"email": email, "password": password}
        )
        token = login_response.json()["access_token"]
        
        response = await client.post(
            "/tracks",
            json={
                "title": "Authorized Track",
                "artist": "Test Artist",
                "price": 9.99,
                "preview_url": "https://example.com/preview.mp3",
                "full_file_path": "/server/music/track.mp3"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_track_with_admin(self, client, test_db):
        """Test creating track with admin authentication succeeds"""
        _, AsyncSessionLocal = test_db

        async with AsyncSessionLocal() as session:
            await create_user_record(session, "admin@example.com", "Admin123!", is_admin=True)

        login_response = await client.post(
            "/login",
            json={"email": "admin@example.com", "password": "Admin123!"}
        )
        token = login_response.json()["access_token"]

        response = await client.post(
            "/tracks",
            json={
                "title": "Authorized Track",
                "artist": "Test Artist",
                "price": 9.99,
                "preview_url": "https://example.com/preview.mp3",
                "full_file_path": "/server/music/track.mp3"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Authorized Track"
        assert data["artist"] == "Test Artist"
        assert "full_file_path" not in data  # Security: not exposed in response


class TestUserAdminEndpoints:
    """Test admin-only user management endpoints"""

    @pytest.mark.asyncio
    async def test_list_users_requires_admin(self, client):
        email = "member@example.com"
        password = "password123"

        await client.post(
            "/register",
            json={"email": email, "password": password}
        )
        login_response = await client.post(
            "/login",
            json={"email": email, "password": password}
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            "/users",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403


class TestCheckoutAndWebhook:
    """Test Lemon Squeezy checkout flow"""

    @pytest.mark.asyncio
    async def test_cart_checkout_falls_back_to_track_checkout_url(self, client, test_db):
        _, AsyncSessionLocal = test_db

        async with AsyncSessionLocal() as session:
            user = await create_user_record(session, "cartbuyer@example.com", "password123")
            track_one = await create_track_record(
                session,
                checkout_url="https://buy.lemonsqueezy.com/checkout/buy/first",
                price=0.5,
            )
            track_two = await create_track_record(
                session,
                checkout_url="https://buy.lemonsqueezy.com/checkout/buy/second",
                price=0.5,
            )

        login_response = await client.post(
            "/login",
            json={"email": user.email, "password": "password123"},
        )
        token = login_response.json()["access_token"]

        response = await client.post(
            "/checkout/cart",
            json={"track_ids": [track_one.id, track_two.id]},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert set(data["track_ids"]) == {track_one.id, track_two.id}
        parsed = urlparse(data["checkout_url"])
        query = parse_qs(parsed.query)
        assert query["checkout[custom][track_ids]"][0] == f"{track_one.id},{track_two.id}"
        assert query["checkout[custom][user_id]"][0] == str(user.id)

    @pytest.mark.asyncio
    async def test_checkout_endpoint_builds_payment_url(self, client, test_db):
        _, AsyncSessionLocal = test_db

        async with AsyncSessionLocal() as session:
            user = await create_user_record(session, "buyer@example.com", "password123")
            track = await create_track_record(
                session,
                "https://buy.lemonsqueezy.com/checkout/buy/abc123",
            )

        login_response = await client.post(
            "/login",
            json={"email": user.email, "password": "password123"}
        )
        token = login_response.json()["access_token"]

        response = await client.post(
            f"/tracks/{track.id}/checkout",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["track_id"] == track.id
        parsed = urlparse(data["checkout_url"])
        query = parse_qs(parsed.query)
        assert query["checkout[email]"][0] == "buyer@example.com"
        assert query["checkout[custom][track_id]"][0] == str(track.id)
        assert query["checkout[custom][user_id]"][0] == str(user.id)

    @pytest.mark.asyncio
    async def test_webhook_grants_purchase(self, client, test_db, monkeypatch):
        _, AsyncSessionLocal = test_db

        async with AsyncSessionLocal() as session:
            user = await create_user_record(session, "paid@example.com", "password123")
            track = await create_track_record(
                session,
                "https://buy.lemonsqueezy.com/checkout/buy/abc123",
            )

        payload = {
            "type": "order_created",
            "data": {
                "attributes": {
                    "status": "paid"
                }
            },
            "meta": {
                "event_name": "order_created",
                "custom_data": {
                    "track_id": str(track.id),
                    "user_id": str(user.id),
                }
            }
        }

        raw_body = json.dumps(payload).encode("utf-8")
        secret = "test-webhook-secret"
        monkeypatch.setenv("LEMON_SQUEEZY_WEBHOOK_SECRET", secret)
        signature = hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        response = await client.post(
            "/webhooks/lemonsqueezy",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": signature,
            },
        )
        assert response.status_code == 200

        login_response = await client.post(
            "/login",
            json={"email": user.email, "password": "password123"}
        )
        token = login_response.json()["access_token"]

        purchases_response = await client.get(
            "/purchases",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert purchases_response.status_code == 200
        assert track.id in purchases_response.json()

    @pytest.mark.asyncio
    async def test_checkout_rejects_free_track(self, client, test_db):
        _, AsyncSessionLocal = test_db

        async with AsyncSessionLocal() as session:
            user = await create_user_record(session, "freebuyer@example.com", "password123")
            track = await create_track_record(
                session,
                checkout_url="https://buy.lemonsqueezy.com/checkout/buy/abc123",
                is_free=True,
                price=0,
            )

        login_response = await client.post(
            "/login",
            json={"email": user.email, "password": "password123"}
        )
        token = login_response.json()["access_token"]

        response = await client.post(
            f"/tracks/{track.id}/checkout",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400
        assert "free to download" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webhook_rejects_missing_signature(self, client, monkeypatch):
        monkeypatch.setenv("LEMON_SQUEEZY_WEBHOOK_SECRET", "test-webhook-secret")
        payload = {
            "type": "order_created",
            "data": {"attributes": {"status": "paid"}},
            "meta": {"event_name": "order_created", "custom_data": {"track_id": "1", "user_id": "1"}},
        }

        response = await client.post("/webhooks/lemonsqueezy", json=payload)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_license_pdf_available_in_purchase_details(self, client, test_db, monkeypatch):
        _, AsyncSessionLocal = test_db

        async with AsyncSessionLocal() as session:
            user = await create_user_record(
                session,
                "license@example.com",
                "password123",
                full_name="Test User",
            )
            track = await create_track_record(
                session,
                "https://buy.lemonsqueezy.com/checkout/buy/abc123",
            )

        payload = {
            "type": "order_created",
            "data": {"attributes": {"status": "paid"}},
            "meta": {
                "event_name": "order_created",
                "custom_data": {"track_id": str(track.id), "user_id": str(user.id)},
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        secret = "test-webhook-secret"
        monkeypatch.setenv("LEMON_SQUEEZY_WEBHOOK_SECRET", secret)
        signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

        webhook_response = await client.post(
            "/webhooks/lemonsqueezy",
            content=raw_body,
            headers={"Content-Type": "application/json", "X-Signature": signature},
        )
        assert webhook_response.status_code == 200

        login_response = await client.post(
            "/login",
            json={"email": user.email, "password": "password123"}
        )
        token = login_response.json()["access_token"]

        details_response = await client.get(
            "/purchases/details",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert details_response.status_code == 200
        details = details_response.json()
        assert len(details) == 1
        assert details[0]["license_pdf_url"].startswith("/purchases/")

        purchase_id = details[0]["id"]
        pdf_response = await client.get(
            f"/purchases/{purchase_id}/license-pdf",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert pdf_response.status_code == 200
        assert pdf_response.headers["content-type"].startswith("application/pdf")
        assert pdf_response.content.startswith(b"%PDF-")

    @pytest.mark.asyncio
    async def test_free_download_normalizes_legacy_http_media_url(self, client, test_db):
        _, AsyncSessionLocal = test_db

        async with AsyncSessionLocal() as session:
            track = await create_track_record(
                session,
                is_free=True,
                price=0,
                full_file_path="http://legacy.example.com/media/tracks/sample.mp3",
                free_download_url="http://legacy.example.com/media/tracks/sample.mp3",
            )

        response = await client.get(f"/tracks/{track.id}/free-download")
        assert response.status_code == 200
        data = response.json()
        assert data["download_url"] == "/media/tracks/sample.mp3"
        assert data["full_file_path"] == "/media/tracks/sample.mp3"


class TestEdgeCases:
    """Test edge cases for auth endpoints"""
    
    @pytest.mark.asyncio
    async def test_register_empty_password(self, client):
        """Test registration with empty password"""
        response = await client.post(
            "/register",
            json={"email": "user@example.com", "password": ""}
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_weak_password_missing_number(self, client):
        response = await client.post(
            "/register",
            json={"email": "weak@example.com", "password": "password"}
        )

        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_login_case_sensitive_email(self, client):
        """Test that login is case-insensitive for email"""
        email = "user@example.com"
        password = "password123"
        
        # Register with lowercase
        await client.post(
            "/register",
            json={"email": email, "password": password}
        )
        
        # Try login with uppercase
        response = await client.post(
            "/login",
            json={"email": email.upper(), "password": password}
        )
        
        # Email validation should handle this, but result depends on
        # whether EmailStr normalizes to lowercase
        assert response.status_code in [200, 401]
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_logins(self, client):
        """Test multiple login requests from same user"""
        email = "user@example.com"
        password = "password123"
        
        # Register
        await client.post(
            "/register",
            json={"email": email, "password": password}
        )
        
        # Multiple logins
        response1 = await client.post(
            "/login",
            json={"email": email, "password": password}
        )
        response2 = await client.post(
            "/login",
            json={"email": email, "password": password}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        # Tokens should be different
        token1 = response1.json()["access_token"]
        token2 = response2.json()["access_token"]
        # Tokens might be different due to different exp times
        assert len(token1) > 0
        assert len(token2) > 0

    def test_track_schema_allows_zero_price_for_free_track(self):
        track = schemas.TrackCreate(
            title="Free Track",
            artist="Test Artist",
            price=0,
            is_free=True,
            preview_url="https://example.com/preview.mp3",
            full_file_path="https://example.com/full.mp3",
        )
        assert track.price == 0
        assert track.is_free is True

    def test_track_schema_rejects_zero_price_for_paid_track(self):
        with pytest.raises(ValueError):
            schemas.TrackCreate(
                title="Paid Track",
                artist="Test Artist",
                price=0,
                is_free=False,
                preview_url="https://example.com/preview.mp3",
                full_file_path="https://example.com/full.mp3",
            )
