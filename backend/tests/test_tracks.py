import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas import TrackCreate, TrackResponse, TrackUpdate, calculate_discounted_price


class TestTrackCreate:
    """Test suite for TrackCreate schema validation"""

    def test_valid_track_creation(self):
        """Test successful TrackCreate with valid data (happy path)"""
        track = TrackCreate(
            title="Epic Song",
            artist="Amazing Artist",
            price=9.99,
            preview_url="https://example.com/preview.mp3",
            full_file_path="/server/music/track.mp3"
        )
        assert track.title == "Epic Song"
        assert track.artist == "Amazing Artist"
        assert track.price == 9.99
        assert track.preview_url == "https://example.com/preview.mp3"
        assert track.full_file_path == "/server/music/track.mp3"

    def test_track_with_whitespace_trim(self):
        """Test that title and artist are trimmed of whitespace"""
        track = TrackCreate(
            title="  Song Title  ",
            artist="  Artist Name  ",
            price=5.99,
            preview_url="https://example.com/preview.mp3",
            full_file_path="/server/music/track.mp3"
        )
        assert track.title == "Song Title"
        assert track.artist == "Artist Name"

    def test_track_with_zero_price(self):
        """Test that zero price is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            TrackCreate(
                title="Song",
                artist="Artist",
                price=0.0,
                preview_url="https://example.com/preview.mp3",
                full_file_path="/server/music/track.mp3"
            )
        assert "Price must be greater than 0" in str(exc_info.value)

    def test_track_with_negative_price(self):
        """Test that negative price is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            TrackCreate(
                title="Song",
                artist="Artist",
                price=-5.99,
                preview_url="https://example.com/preview.mp3",
                full_file_path="/server/music/track.mp3"
            )
        assert "Price must be greater than 0" in str(exc_info.value)

    def test_track_with_excessive_price(self):
        """Test that excessively high price is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            TrackCreate(
                title="Song",
                artist="Artist",
                price=1000000.00,
                preview_url="https://example.com/preview.mp3",
                full_file_path="/server/music/track.mp3"
            )
        assert "Price cannot exceed 999999.99" in str(exc_info.value)

    def test_track_with_valid_high_price(self):
        """Test that valid high price is accepted"""
        track = TrackCreate(
            title="Expensive Song",
            artist="Premium Artist",
            price=999999.99,
            preview_url="https://example.com/preview.mp3",
            full_file_path="/server/music/track.mp3"
        )
        assert track.price == 999999.99

    def test_track_with_empty_title(self):
        """Test that empty title is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            TrackCreate(
                title="",
                artist="Artist",
                price=9.99,
                preview_url="https://example.com/preview.mp3",
                full_file_path="/server/music/track.mp3"
            )
        assert "Title and artist cannot be empty" in str(exc_info.value)

    def test_track_with_whitespace_only_title(self):
        """Test that title with only whitespace is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            TrackCreate(
                title="   ",
                artist="Artist",
                price=9.99,
                preview_url="https://example.com/preview.mp3",
                full_file_path="/server/music/track.mp3"
            )
        assert "Title and artist cannot be empty" in str(exc_info.value)

    def test_track_with_empty_artist(self):
        """Test that empty artist is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            TrackCreate(
                title="Song",
                artist="",
                price=9.99,
                preview_url="https://example.com/preview.mp3",
                full_file_path="/server/music/track.mp3"
            )
        assert "Title and artist cannot be empty" in str(exc_info.value)

    def test_track_with_empty_preview_url(self):
        """Test that empty preview_url is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            TrackCreate(
                title="Song",
                artist="Artist",
                price=9.99,
                preview_url="",
                full_file_path="/server/music/track.mp3"
            )
        assert "URLs cannot be empty" in str(exc_info.value)

    def test_track_with_empty_full_file_path(self):
        """Test that empty full_file_path is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            TrackCreate(
                title="Song",
                artist="Artist",
                price=9.99,
                preview_url="https://example.com/preview.mp3",
                full_file_path=""
            )
        assert "URLs cannot be empty" in str(exc_info.value)

    def test_track_with_various_url_formats(self):
        """Test that various URL formats are accepted"""
        # HTTPS URL
        track1 = TrackCreate(
            title="Song",
            artist="Artist",
            price=9.99,
            preview_url="https://example.com/preview.mp3",
            full_file_path="/server/music/track.mp3"
        )
        assert track1.preview_url == "https://example.com/preview.mp3"

        # File path
        track2 = TrackCreate(
            title="Song",
            artist="Artist",
            price=9.99,
            preview_url="/cdn/preview.mp3",
            full_file_path="/server/music/track.mp3"
        )
        assert track2.preview_url == "/cdn/preview.mp3"

        # S3-like URL
        track3 = TrackCreate(
            title="Song",
            artist="Artist",
            price=9.99,
            preview_url="s3://bucket/preview.mp3",
            full_file_path="/server/music/track.mp3"
        )
        assert track3.preview_url == "s3://bucket/preview.mp3"

    def test_track_with_missing_field(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError):
            TrackCreate(
                title="Song",
                artist="Artist",
                price=9.99
                # Missing preview_url and full_file_path
            )

    def test_track_with_invalid_price_type(self):
        """Test that non-numeric price is rejected"""
        with pytest.raises(ValidationError):
            TrackCreate(
                title="Song",
                artist="Artist",
                price="not_a_number",
                preview_url="https://example.com/preview.mp3",
                full_file_path="/server/music/track.mp3"
            )


class TestTrackResponse:
    """Test suite for TrackResponse schema"""

    def test_track_response_contains_required_fields(self):
        """Test that TrackResponse has all required fields"""
        response = TrackResponse(
            id=1,
            title="Song",
            artist="Artist",
            price=9.99,
            preview_url="https://example.com/preview.mp3",
            created_at=datetime.now()
        )
        assert response.id == 1
        assert response.title == "Song"
        assert response.artist == "Artist"
        assert response.price == 9.99
        assert response.preview_url == "https://example.com/preview.mp3"
        assert isinstance(response.created_at, datetime)

    def test_track_response_no_full_file_path(self):
        """Test that TrackResponse schema does NOT include full_file_path (security)"""
        response_dict = TrackResponse(
            id=1,
            title="Song",
            artist="Artist",
            price=9.99,
            preview_url="https://example.com/preview.mp3",
            created_at=datetime.now()
        ).model_dump()
        
        assert "full_file_path" not in response_dict
        assert "preview_url" in response_dict


class TestTrackUpdate:
    """Test suite for TrackUpdate schema"""

    def test_track_update_accepts_price_only(self):
        track = TrackUpdate(price=12.5)
        assert track.price == 12.5

    def test_track_update_rejects_invalid_category(self):
        with pytest.raises(ValueError):
            TrackUpdate(category="invalid")

    def test_track_update_rejects_negative_price(self):
        with pytest.raises(ValueError):
            TrackUpdate(price=-1)


class TestCalculateDiscountedPrice:
    """Test suite for calculate_discounted_price function"""

    def test_no_discount(self):
        """Test calculation with 0% discount (happy path)"""
        result = calculate_discounted_price(100.0, 0)
        assert result == 100.0

    def test_fifty_percent_discount(self):
        """Test calculation with 50% discount"""
        result = calculate_discounted_price(100.0, 50)
        assert result == 50.0

    def test_full_discount(self):
        """Test calculation with 100% discount"""
        result = calculate_discounted_price(100.0, 100)
        assert result == 0.0

    def test_ten_percent_discount(self):
        """Test calculation with 10% discount"""
        result = calculate_discounted_price(9.99, 10)
        assert result == 8.99

    def test_discount_with_rounding(self):
        """Test that result is properly rounded to 2 decimal places"""
        result = calculate_discounted_price(10.00, 33)
        # 10 * 0.67 = 6.7
        assert result == 6.7
        
        result = calculate_discounted_price(9.99, 25)
        # 9.99 * 0.75 = 7.4925 → 7.49
        assert result == 7.49

    def test_small_price_discount(self):
        """Test discount on small price"""
        result = calculate_discounted_price(1.0, 50)
        assert result == 0.5

    def test_large_price_discount(self):
        """Test discount on large price"""
        result = calculate_discounted_price(999999.99, 50)
        assert result == 499999.99

    def test_fractional_discount_percent(self):
        """Test discount with fractional percentage"""
        result = calculate_discounted_price(100.0, 5.5)
        assert result == 94.5

    def test_negative_price_raises_error(self):
        """Test that negative price raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            calculate_discounted_price(-100.0, 10)
        assert "Price must be greater than 0" in str(exc_info.value)

    def test_zero_price_raises_error(self):
        """Test that zero price raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            calculate_discounted_price(0.0, 10)
        assert "Price must be greater than 0" in str(exc_info.value)

    def test_negative_discount_raises_error(self):
        """Test that negative discount raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            calculate_discounted_price(100.0, -5)
        assert "Discount percentage must be between 0 and 100" in str(exc_info.value)

    def test_discount_exceeds_100_raises_error(self):
        """Test that discount > 100% raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            calculate_discounted_price(100.0, 105)
        assert "Discount percentage must be between 0 and 100" in str(exc_info.value)

    def test_discount_exactly_100_is_valid(self):
        """Test that 100% discount is valid"""
        result = calculate_discounted_price(100.0, 100)
        assert result == 0.0

    def test_discount_exactly_0_is_valid(self):
        """Test that 0% discount is valid"""
        result = calculate_discounted_price(100.0, 0)
        assert result == 100.0

    def test_very_small_price_with_discount(self):
        """Test discount on very small price"""
        result = calculate_discounted_price(0.01, 50)
        assert result == 0.01  # 0.01 * 0.5 = 0.005 rounds to 0.01


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_track_with_special_characters_in_title(self):
        """Test track with special characters in title"""
        track = TrackCreate(
            title="Song & Artist's #1 Hit!",
            artist="Artist/Band (Official)",
            price=9.99,
            preview_url="https://example.com/preview.mp3",
            full_file_path="/server/music/track.mp3"
        )
        assert track.title == "Song & Artist's #1 Hit!"
        assert track.artist == "Artist/Band (Official)"

    def test_track_with_unicode_characters(self):
        """Test track with Unicode characters"""
        track = TrackCreate(
            title="Müzik 音楽 موسيقى",
            artist="Artiste Française",
            price=9.99,
            preview_url="https://example.com/preview.mp3",
            full_file_path="/server/music/track.mp3"
        )
        assert "Müzik" in track.title
        assert "Artiste Française" == track.artist

    def test_track_with_very_long_title(self):
        """Test track with very long title (within string limit)"""
        long_title = "A" * 255  # Max field length
        track = TrackCreate(
            title=long_title,
            artist="Artist",
            price=9.99,
            preview_url="https://example.com/preview.mp3",
            full_file_path="/server/music/track.mp3"
        )
        assert len(track.title) == 255

    def test_discount_with_very_small_percentage(self):
        """Test discount with very small percentage"""
        result = calculate_discounted_price(100.0, 0.01)
        assert result == 99.99

    def test_multiple_validations_fail(self):
        """Test that first validation error is caught"""
        with pytest.raises(ValidationError):
            TrackCreate(
                title="",  # Empty
                artist="",  # Empty
                price=-10,  # Negative
                preview_url="",  # Empty
                full_file_path=""  # Empty
            )
