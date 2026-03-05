"""
Tests for the Asset Agent — image fetching, SFX resolution, music selection.

Uses mocked APIs (no real network calls per testing rules).
"""
import pytest
import pytest_asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock

from backend.agents.asset_agent import (
    AssetAgent,
    _create_genre_fallback,
)
from backend.core.models import (
    AssetBundle,
    ImageCue,
    SfxCue,
    GenreConfig,
)
from backend.services.image_service import (
    ImageResult,
    _get_extension,
)


# ─── ImageResult Tests ────────────────────────────────

def test_image_result_score_high_res():
    """High-res Pexels image should score well."""
    result = ImageResult(
        url="https://example.com/photo.jpg",
        source="pexels",
        width=1920,
        height=1080,
        description="A scary dark room",
        query="scary dark room",
    )
    assert result.score_for("scary dark room") >= 40


def test_image_result_score_low_res():
    """Low-res image with no description should score low."""
    result = ImageResult(
        url="https://example.com/small.jpg",
        source="pixabay",
        width=400,
        height=300,
        query="test",
    )
    assert result.score_for("test") < 40


# ─── URL Extension Tests ──────────────────────────────

def test_extension_jpg():
    """Should extract .jpg extension."""
    assert _get_extension("https://example.com/img.jpg") == ".jpg"


def test_extension_png():
    """Should extract .png extension."""
    assert _get_extension("https://example.com/img.png") == ".png"


def test_extension_with_params():
    """Should ignore query parameters."""
    url = "https://example.com/img.webp?w=800&h=600"
    assert _get_extension(url) == ".webp"


def test_extension_no_ext():
    """Should default to .jpg when no extension found."""
    assert _get_extension("https://example.com/image") == ".jpg"


# ─── Fallback Image Tests ─────────────────────────────

def test_create_fallback_image(tmp_path):
    """Should create a fallback image file."""
    path = _create_genre_fallback(tmp_path, "test.jpg", "scary_stories", "eerie")
    assert Path(path).exists()
    assert Path(path).stat().st_size > 0


def test_fallback_image_unknown_mood(tmp_path):
    """Unknown mood should use default dark color."""
    path = _create_genre_fallback(tmp_path, "test.jpg", "unknown", "happy")
    assert Path(path).exists()


# ─── Asset Agent Tests ─────────────────────────────────

@pytest.fixture
def sample_cues():
    """Sample image and SFX cues."""
    images = [
        ImageCue(keyword="dark house", timestamp_hint="start", mood="eerie"),
        ImageCue(keyword="old door", timestamp_hint="after line 2", mood="dark"),
        ImageCue(keyword="ghost", timestamp_hint="climax", mood="horror"),
    ]
    sfx = [
        SfxCue(trigger_word="door", sfx_type="door_creak", timestamp_hint="during"),
    ]
    return images, sfx


@pytest.fixture
def genre_config():
    """Test genre config."""
    return GenreConfig(
        genre_id="scary_stories",
        music_mood="dark_ambient",
        layout="split_screen",
    )


@pytest.mark.asyncio
async def test_generate_returns_asset_bundle(
    tmp_path, monkeypatch, sample_cues, genre_config
):
    """Asset agent should return valid AssetBundle."""
    monkeypatch.setattr(
        "backend.agents.asset_agent.config",
        type("Config", (), {
            "data_dir": tmp_path,
            "assets_dir": tmp_path / "assets",
        })(),
    )
    # Create assets dirs
    (tmp_path / "assets" / "sfx").mkdir(parents=True)
    (tmp_path / "assets" / "music").mkdir(parents=True)

    # Mock all image searches to return empty (fall to Tier 7)
    with patch("backend.agents.asset_agent.search_pexels",
               new_callable=AsyncMock, return_value=[]), \
         patch("backend.agents.asset_agent.search_pixabay",
               new_callable=AsyncMock, return_value=[]), \
         patch("backend.agents.asset_agent.search_duckduckgo",
               new_callable=AsyncMock, return_value=[]), \
         patch("backend.agents.asset_agent.search_wikimedia",
               new_callable=AsyncMock, return_value=[]):
            agent = AssetAgent()
            images, sfx = sample_cues
            result = await agent.generate(
                images, sfx, genre_config, "test_001"
            )

    assert isinstance(result, AssetBundle)
    assert len(result.image_paths) == 3  # All 3 fallbacks
    assert result.music_path is None  # No music files exist


@pytest.mark.asyncio
async def test_sfx_resolution_finds_file(
    tmp_path, monkeypatch
):
    """Should find SFX file in local library."""
    sfx_dir = tmp_path / "assets" / "sfx"
    sfx_dir.mkdir(parents=True)
    # Create a test SFX file
    (sfx_dir / "door_creak.wav").write_bytes(b"fake wav")

    monkeypatch.setattr(
        "backend.agents.asset_agent.config",
        type("Config", (), {
            "data_dir": tmp_path,
            "assets_dir": tmp_path / "assets",
        })(),
    )

    agent = AssetAgent()
    sfx_cues = [
        SfxCue(trigger_word="door", sfx_type="door_creak",
               timestamp_hint="during"),
    ]
    paths = agent._resolve_sfx(sfx_cues)
    assert len(paths) == 1
    assert "door_creak.wav" in paths[0]


@pytest.mark.asyncio
async def test_sfx_resolution_skips_missing(
    tmp_path, monkeypatch
):
    """Should skip SFX cues with no matching file."""
    (tmp_path / "assets" / "sfx").mkdir(parents=True)
    monkeypatch.setattr(
        "backend.agents.asset_agent.config",
        type("Config", (), {
            "data_dir": tmp_path,
            "assets_dir": tmp_path / "assets",
        })(),
    )

    agent = AssetAgent()
    sfx_cues = [
        SfxCue(trigger_word="x", sfx_type="nonexistent",
               timestamp_hint="during"),
    ]
    paths = agent._resolve_sfx(sfx_cues)
    assert paths == []


@pytest.mark.asyncio
async def test_music_selection_by_mood(
    tmp_path, monkeypatch
):
    """Should select music from mood-specific folder."""
    music_dir = tmp_path / "assets" / "music" / "dark_ambient"
    music_dir.mkdir(parents=True)
    (music_dir / "track_01.mp3").write_bytes(b"fake mp3")

    monkeypatch.setattr(
        "backend.agents.asset_agent.config",
        type("Config", (), {
            "assets_dir": tmp_path / "assets",
        })(),
    )

    agent = AssetAgent()
    path = agent._select_music("dark_ambient")
    assert path is not None
    assert "track_01.mp3" in path


@pytest.mark.asyncio
async def test_gameplay_selected_for_split_screen(
    tmp_path, monkeypatch
):
    """Should select gameplay clip for split_screen layout."""
    gameplay_dir = tmp_path / "assets" / "gameplay"
    gameplay_dir.mkdir(parents=True)
    (gameplay_dir / "minecraft.mp4").write_bytes(b"fake mp4")

    monkeypatch.setattr(
        "backend.agents.asset_agent.config",
        type("Config", (), {
            "assets_dir": tmp_path / "assets",
        })(),
    )

    agent = AssetAgent()
    path = agent._select_gameplay("split_screen")
    assert path is not None


@pytest.mark.asyncio
async def test_gameplay_not_selected_for_full_image(
    tmp_path, monkeypatch
):
    """Should NOT select gameplay for full_image layout."""
    monkeypatch.setattr(
        "backend.agents.asset_agent.config",
        type("Config", (), {
            "assets_dir": tmp_path / "assets",
        })(),
    )

    agent = AssetAgent()
    path = agent._select_gameplay("full_image")
    assert path is None
