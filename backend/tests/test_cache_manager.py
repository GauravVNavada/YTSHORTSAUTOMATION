"""
Tests for cache_manager.py — SQLite cache for sheet data.

Uses an in-memory database for speed and isolation.
"""
import asyncio
import pytest
import pytest_asyncio

from backend.core.cache_manager import CacheManager
from backend.core.models import Genre, GenreConfig


@pytest_asyncio.fixture
async def cache(tmp_path):
    """Create a fresh in-memory cache for each test."""
    db_path = tmp_path / "test_cache.db"
    mgr = CacheManager(db_path=db_path)
    await mgr.initialize()
    yield mgr
    await mgr.close()


@pytest.fixture
def sample_genres():
    """Two test genres."""
    return [
        Genre(
            genre_id="scary_stories",
            display_name="Scary Stories & Mysteries",
            icon="👻",
            difficulty="Easy",
            is_active=True,
        ),
        Genre(
            genre_id="psychology",
            display_name="Psychology & Human Behavior",
            icon="🧠",
            difficulty="Medium",
            is_active=True,
        ),
    ]


@pytest.fixture
def sample_configs():
    """Two test genre configs."""
    return [
        GenreConfig(
            genre_id="scary_stories",
            tts_voice="en-US-Neural2-D",
            tts_rate=0.88,
            tts_pitch=-2.0,
            layout="split_screen",
            caption_preset="horror_red",
            music_mood="dark_ambient",
        ),
        GenreConfig(
            genre_id="psychology",
            tts_voice="en-US-Neural2-F",
            tts_rate=0.95,
            tts_pitch=0.0,
            layout="full_image",
            caption_preset="clean_pro",
            music_mood="chill",
        ),
    ]


# ─── Cache Initialization ─────────────────────────────

@pytest.mark.asyncio
async def test_cache_initializes(cache):
    """Cache should create tables without error."""
    genres = await cache.get_genres()
    assert genres == []


@pytest.mark.asyncio
async def test_empty_cache_is_stale(cache):
    """Empty cache should always be considered stale."""
    assert await cache.is_stale()


@pytest.mark.asyncio
async def test_empty_cache_age_is_inf(cache):
    """Empty cache should report infinite age."""
    age = await cache.cache_age_hours()
    assert age == float("inf")


# ─── Genre Storage & Retrieval ─────────────────────────

@pytest.mark.asyncio
async def test_store_and_read_genres(cache, sample_genres):
    """Should store and retrieve genres correctly."""
    await cache.store_genres(sample_genres)
    genres = await cache.get_genres()
    assert len(genres) == 2
    assert genres[0].genre_id in ("psychology", "scary_stories")


@pytest.mark.asyncio
async def test_genres_replace_on_store(cache, sample_genres):
    """Storing genres again should replace the old data."""
    await cache.store_genres(sample_genres)
    await cache.store_genres([sample_genres[0]])  # Only first genre
    genres = await cache.get_genres()
    assert len(genres) == 1


@pytest.mark.asyncio
async def test_cache_not_stale_after_store(cache, sample_genres):
    """Cache should not be stale immediately after storing."""
    await cache.store_genres(sample_genres)
    assert not await cache.is_stale()


@pytest.mark.asyncio
async def test_cache_age_near_zero_after_store(cache, sample_genres):
    """Cache age should be near zero right after storing."""
    await cache.store_genres(sample_genres)
    age = await cache.cache_age_hours()
    assert age < 0.1  # Less than 6 minutes


@pytest.mark.asyncio
async def test_last_refresh_iso_after_store(cache, sample_genres):
    """Last refresh ISO should be set after storing."""
    await cache.store_genres(sample_genres)
    iso = await cache.last_refresh_iso()
    assert iso is not None
    assert "T" in iso  # ISO format has T separator


# ─── Genre Config ──────────────────────────────────────

@pytest.mark.asyncio
async def test_store_and_read_config(cache, sample_configs):
    """Should store and retrieve genre config."""
    await cache.store_genre_configs(sample_configs)
    cfg = await cache.get_genre_config("scary_stories")
    assert cfg is not None
    assert cfg.tts_rate == 0.88
    assert cfg.layout == "split_screen"


@pytest.mark.asyncio
async def test_config_not_found(cache):
    """Should return None for non-existent genre config."""
    cfg = await cache.get_genre_config("nonexistent")
    assert cfg is None


# ─── Reference Scripts ─────────────────────────────────

@pytest.mark.asyncio
async def test_store_and_read_scripts(cache):
    """Should store and retrieve reference scripts."""
    scripts = [
        {
            "full script / transcript": "You wake up at 3 AM...",
            "hook type": "question",
            "score: overall": "8",
        },
        {
            "full script / transcript": "In 1987, a family...",
            "hook type": "time_reference",
            "score: overall": "9",
        },
    ]
    await cache.store_reference_scripts(
        "scary_stories", "Genre 2", scripts
    )
    result = await cache.get_reference_scripts("scary_stories")
    assert len(result) == 2
    # Should be ordered by quality_score DESC
    assert result[0]["quality_score"] >= result[1]["quality_score"]


@pytest.mark.asyncio
async def test_scripts_limit(cache):
    """Should respect the limit parameter."""
    scripts = [
        {
            "full script / transcript": f"Script {i}...",
            "score: overall": str(i),
        }
        for i in range(10)
    ]
    await cache.store_reference_scripts(
        "scary_stories", "Genre 2", scripts
    )
    result = await cache.get_reference_scripts("scary_stories", limit=3)
    assert len(result) == 3


@pytest.mark.asyncio
async def test_scripts_empty_genre(cache):
    """Should return empty list for genre with no scripts."""
    result = await cache.get_reference_scripts("nonexistent")
    assert result == []
