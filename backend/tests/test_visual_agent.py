"""
Tests for the Visual Agent — caption builder, FFmpeg utils, video rendering.

Uses mocked FFmpeg calls (no real rendering per testing rules).
"""
import pytest
import pytest_asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

from backend.agents.caption_builder import (
    build_captions,
    _ms_to_ass_time,
    _wrap_text,
    _group_words,
)
from backend.agents.visual_agent import VisualAgent
from backend.core.models import (
    AudioBundle,
    AssetBundle,
    GenreConfig,
    VideoResult,
    WordTimestamp,
)
from backend.services.ffmpeg_utils import (
    build_ffmpeg_cmd,
    check_disk_space,
    ENCODING,
)


# ─── Caption Builder Tests ─────────────────────────────

def test_ms_to_ass_time():
    """Should convert milliseconds to ASS time format."""
    assert _ms_to_ass_time(0) == "0:00:00.00"
    assert _ms_to_ass_time(1500) == "0:00:01.50"
    assert _ms_to_ass_time(65000) == "0:01:05.00"


def test_wrap_text_short():
    """Short text should remain unchanged."""
    assert _wrap_text("hello world") == "hello world"


def test_wrap_text_long():
    """Long text should be wrapped with \\N."""
    text = "this is a really long caption text"
    result = _wrap_text(text)
    assert "\\N" in result


def test_group_words_small():
    """Fewer than 7 words should be one chunk."""
    words = [
        WordTimestamp(word="hello", start_ms=0, end_ms=200),
        WordTimestamp(word="world", start_ms=200, end_ms=400),
    ]
    chunks = _group_words(words)
    assert len(chunks) == 1
    assert len(chunks[0]) == 2


def test_group_words_large():
    """More than 7 words should be split into chunks."""
    words = [
        WordTimestamp(word=f"word{i}", start_ms=i * 200, end_ms=(i + 1) * 200)
        for i in range(15)
    ]
    chunks = _group_words(words)
    assert len(chunks) == 3  # 7 + 7 + 1


def test_build_captions_creates_file(tmp_path):
    """Should create a valid .ass file."""
    words = [
        WordTimestamp(word="Did", start_ms=0, end_ms=300),
        WordTimestamp(word="you", start_ms=300, end_ms=500),
        WordTimestamp(word="know", start_ms=500, end_ms=800),
    ]
    output = tmp_path / "captions.ass"
    result = build_captions(words, output)

    assert Path(result).exists()
    content = Path(result).read_text()
    assert "[Script Info]" in content
    assert "[V4+ Styles]" in content
    assert "[Events]" in content
    assert "Dialogue:" in content


def test_build_captions_preset_styles(tmp_path):
    """Different presets should produce different styles."""
    words = [
        WordTimestamp(word="test", start_ms=0, end_ms=500),
    ]
    out1 = tmp_path / "clean.ass"
    out2 = tmp_path / "horror.ass"
    build_captions(words, out1, preset="clean_pro")
    build_captions(words, out2, preset="horror_red")

    c1 = Path(out1).read_text()
    c2 = Path(out2).read_text()
    # They should have different font names
    assert "Montserrat" in c1
    assert "Creepster" in c2


# ─── FFmpeg Utils Tests ────────────────────────────────

def test_build_ffmpeg_cmd_single_image():
    """Single image should use -vf filter."""
    cmd = build_ffmpeg_cmd(
        ffmpeg="ffmpeg",
        audio_path="audio.wav",
        image_paths=["img.jpg"],
        caption_path="caps.ass",
        output_path="out.mp4",
        duration_ms=30000,
    )
    assert cmd[0] == "ffmpeg"
    assert "-vf" in cmd
    assert "out.mp4" in cmd


def test_build_ffmpeg_cmd_multi_image():
    """Multiple images should use -filter_complex."""
    cmd = build_ffmpeg_cmd(
        ffmpeg="ffmpeg",
        audio_path="audio.wav",
        image_paths=["a.jpg", "b.jpg", "c.jpg"],
        caption_path="caps.ass",
        output_path="out.mp4",
        duration_ms=45000,
    )
    assert "-filter_complex" in cmd
    assert "concat=n=3" in " ".join(cmd)


def test_encoding_settings():
    """Encoding should match MASTER_BLUEPRINT §12."""
    assert "-c:v" in ENCODING
    assert "libx264" in ENCODING
    assert "-preset" in ENCODING
    assert "medium" in ENCODING
    assert "-crf" in ENCODING
    assert "20" in ENCODING


def test_check_disk_space_passes(tmp_path):
    """Should not raise when plenty of space."""
    check_disk_space(tmp_path)  # Should pass silently


# ─── VideoResult Model Tests ──────────────────────────

def test_video_result_model():
    """VideoResult should accept valid data."""
    vr = VideoResult(
        job_id="test_001",
        video_path="/output/final.mp4",
        title="Test Video",
        duration_seconds=45,
        genre_id="scary_stories",
    )
    assert vr.job_id == "test_001"
    assert vr.hashtags == []


# ─── Visual Agent Integration Tests ───────────────────

@pytest.fixture
def mock_audio_bundle(tmp_path):
    """Mock AudioBundle with test audio file."""
    audio_path = tmp_path / "narration.wav"
    audio_path.write_bytes(b"fake wav data")
    return AudioBundle(
        audio_path=str(audio_path),
        narration_path=str(audio_path),
        duration_ms=30000,
        word_timestamps=[
            WordTimestamp(word="test", start_ms=0, end_ms=500),
            WordTimestamp(word="video", start_ms=500, end_ms=1000),
        ],
    )


@pytest.fixture
def mock_asset_bundle(tmp_path):
    """Mock AssetBundle with test images."""
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    # Create simple JPEG files using Pillow
    from PIL import Image
    for i in range(3):
        img = Image.new("RGB", (100, 100), (i * 80, 50, 50))
        img.save(str(img_dir / f"img_{i}.jpg"), "JPEG")

    return AssetBundle(
        image_paths=[
            str(img_dir / f"img_{i}.jpg") for i in range(3)
        ],
        sfx_paths=[],
        music_path=None,
    )


@pytest.fixture
def mock_genre_config():
    """Genre config for visual testing."""
    return GenreConfig(
        genre_id="scary_stories",
        caption_preset="horror_red",
        layout="split_screen",
        music_mood="dark_ambient",
    )


@pytest.mark.asyncio
async def test_visual_agent_generates_result(
    tmp_path, monkeypatch, mock_audio_bundle,
    mock_asset_bundle, mock_genre_config
):
    """Visual agent should return VideoResult.

    Mocks FFmpeg (no real rendering).
    """
    monkeypatch.setattr(
        "backend.agents.visual_agent.config",
        type("Config", (), {
            "output_dir": tmp_path / "output",
            "video_width": 1080,
            "video_height": 1920,
        })(),
    )

    # Mock FFmpeg helpers
    with patch("backend.agents.visual_agent.find_ffmpeg", return_value="ffmpeg"):
        with patch("backend.agents.visual_agent.check_disk_space"):
            with patch("backend.agents.visual_agent.ffprobe_duration", return_value=30.0):
                agent = VisualAgent()
                # Mock _run_ffmpeg to create the tmp file
                async def fake_ffmpeg(cmd):
                    out_path = cmd[-1]
                    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(out_path).write_bytes(b"fake mp4")

                agent._run_ffmpeg = fake_ffmpeg
                result = await agent.generate(
                    mock_audio_bundle,
                    mock_asset_bundle,
                    mock_genre_config,
                    "test_job",
                    title="Test",
                )

    assert isinstance(result, VideoResult)
    assert result.job_id == "test_job"
    assert "final.mp4" in result.video_path
