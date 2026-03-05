"""
Tests for the Pipeline Orchestrator — state machine, parallel fetch, recovery.

Uses mocked agents (no real API calls per testing rules).
"""
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.core.cache_manager import CacheManager
from backend.core.models import (
    GenreConfig,
    PipelineStage,
    PipelineState,
    ScriptOutput,
    AudioBundle,
    AssetBundle,
    VideoResult,
    WordTimestamp,
    ImageCue,
    SfxCue,
)
from backend.pipeline.orchestrator import Orchestrator


# ─── Mock Factories ───────────────────────────────────

def _mock_script_output():
    """Create a realistic ScriptOutput for testing."""
    return ScriptOutput(
        title="Test Title",
        narration=(
            "Did you know that a family in Connecticut bought their dream home "
            "only to discover that the previous owner had sealed an entire room "
            "behind a brick wall? When construction workers finally broke through "
            "they found a child bedroom that had not been touched in forty years. "
            "The bed was still made. Toys were still on the floor. And on the wall "
            "someone had scratched the words she can hear you over and over again. "
            "The family moved out three days later. To this day no one knows who "
            "the room belonged to. And the house? It is still for sale."
        ),
        hook_line="Did you know",
        word_count=108,
        estimated_duration=52,
        description="Test description",
        hashtags=["#test"],
        image_cues=[
            ImageCue(keyword="dark room", timestamp_hint="start", mood="eerie"),
        ],
        sfx_cues=[
            SfxCue(trigger_word="sealed", sfx_type="door_creak",
                   timestamp_hint="during"),
        ],
    )


def _mock_asset_bundle():
    return AssetBundle(
        image_paths=["/tmp/img1.jpg", "/tmp/img2.jpg"],
        sfx_paths=["/tmp/door.wav"],
        music_path="/tmp/music.mp3",
    )


def _mock_audio_bundle():
    return AudioBundle(
        audio_path="/tmp/narration.wav",
        narration_path="/tmp/narration.wav",
        duration_ms=5000,
        word_timestamps=[
            WordTimestamp(word="Did", start_ms=0, end_ms=300),
            WordTimestamp(word="you", start_ms=300, end_ms=500),
        ],
    )


def _mock_video_result(job_id="test_001"):
    return VideoResult(
        job_id=job_id,
        video_path="/tmp/final.mp4",
        title="Test Title",
        duration_seconds=5,
        genre_id="scary_stories",
    )


# ─── Fixtures ─────────────────────────────────────────

@pytest_asyncio.fixture
async def cache(tmp_path):
    """Fresh cache with scary_stories genre config."""
    mgr = CacheManager(db_path=tmp_path / "test.db")
    await mgr.initialize()
    await mgr.store_genre_configs([
        GenreConfig(
            genre_id="scary_stories",
            tts_voice="en-US-Neural2-D",
            tts_rate=0.88,
            tts_pitch=-2.0,
            layout="split_screen",
            caption_preset="horror_red",
            music_mood="dark_ambient",
        ),
    ])
    # Mock get_recent_scripts so dedup doesn't interfere
    async def _empty(*a, **k):
        return []
    mgr.get_recent_scripts = _empty
    yield mgr
    await mgr.close()


class MockUploadResult:
    def __init__(self):
        self.video_id = "abc123"
        self.url = "https://youtube.com/shorts/abc123"
        self.title = "Test"
        self.uploaded_at = "2026-03-05T00:00:00"
        self.scheduled_for = ""


def _make_orchestrator(cache):
    """Create Orchestrator with fully mocked agents."""
    script = AsyncMock()
    script.generate = AsyncMock(return_value=_mock_script_output())

    asset = AsyncMock()
    asset.generate = AsyncMock(return_value=_mock_asset_bundle())

    audio = AsyncMock()
    audio.generate = AsyncMock(return_value=_mock_audio_bundle())

    visual = AsyncMock()
    visual.generate = AsyncMock(return_value=_mock_video_result())

    upload = AsyncMock()
    upload.upload = AsyncMock(return_value=MockUploadResult())

    return Orchestrator(
        script_agent=script,
        asset_agent=asset,
        audio_agent=audio,
        visual_agent=visual,
        upload_agent=upload,
        cache=cache,
    )


# ─── Full Pipeline Tests ──────────────────────────────

@pytest.mark.asyncio
async def test_full_pipeline_completes(cache):
    """Full pipeline should reach COMPLETE state."""
    orch = _make_orchestrator(cache)
    state = await orch.generate("scary_stories")
    assert state.state == PipelineStage.COMPLETE
    assert state.script_output is not None
    assert state.video_path is not None


@pytest.mark.asyncio
async def test_pipeline_calls_all_agents(cache):
    """Should call every agent exactly once."""
    orch = _make_orchestrator(cache)
    state = await orch.generate("scary_stories")
    orch._script.generate.assert_called_once()
    orch._asset.generate.assert_called_once()
    orch._audio.generate.assert_called_once()
    orch._visual.generate.assert_called_once()
    orch._upload.upload.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_parallel_fetch(cache):
    """Asset + Audio should run in parallel (both called)."""
    orch = _make_orchestrator(cache)
    state = await orch.generate("scary_stories")
    # Both should have been called
    assert orch._asset.generate.call_count == 1
    assert orch._audio.generate.call_count == 1
    # Parallel timing should be recorded
    assert "parallel_fetch" in state.stage_timings


@pytest.mark.asyncio
async def test_pipeline_records_stage_timings(cache):
    """Should record timing for each stage."""
    orch = _make_orchestrator(cache)
    state = await orch.generate("scary_stories")
    assert "script" in state.stage_timings
    assert "parallel_fetch" in state.stage_timings
    assert "video_render" in state.stage_timings
    assert "upload" in state.stage_timings


@pytest.mark.asyncio
async def test_pipeline_job_id_format(cache):
    """Job ID should contain genre and UUID hex."""
    orch = _make_orchestrator(cache)
    state = await orch.generate("scary_stories")
    assert state.job_id.startswith("scary_stories_")
    assert len(state.job_id) > len("scary_stories_")


# ─── Progress Callback Tests ─────────────────────────

@pytest.mark.asyncio
async def test_progress_callback_fires(cache):
    """Progress callback should be called multiple times."""
    events = []

    async def on_progress(stage, pct, msg):
        events.append((stage, pct, msg))

    orch = _make_orchestrator(cache)
    await orch.generate("scary_stories", on_progress=on_progress)
    assert len(events) >= 4  # At least one per stage


@pytest.mark.asyncio
async def test_no_progress_callback_ok(cache):
    """Pipeline should work without progress callback."""
    orch = _make_orchestrator(cache)
    state = await orch.generate("scary_stories")
    assert state.state == PipelineStage.COMPLETE


# ─── State Persistence Tests ─────────────────────────

@pytest.mark.asyncio
async def test_state_persisted_to_db(cache):
    """State should be saved to SQLite during pipeline."""
    orch = _make_orchestrator(cache)
    state = await orch.generate("scary_stories")

    # Load from DB
    loaded = await cache.load_pipeline_state(state.job_id)
    assert loaded is not None
    assert loaded.job_id == state.job_id
    assert loaded.state == PipelineStage.COMPLETE


@pytest.mark.asyncio
async def test_list_recent_jobs(cache):
    """Should list jobs from the DB."""
    orch = _make_orchestrator(cache)
    await orch.generate("scary_stories")
    await orch.generate("scary_stories")

    jobs = await cache.list_recent_jobs(limit=10)
    assert len(jobs) >= 2


# ─── Failure Tests ────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_fails_on_script_error(cache):
    """Should transition to FAILED if script agent crashes."""
    orch = _make_orchestrator(cache)
    orch._script.generate = AsyncMock(
        side_effect=Exception("Gemini down"),
    )

    from backend.core.exceptions import PipelineError
    with pytest.raises(PipelineError, match="Gemini down"):
        await orch.generate("scary_stories")


@pytest.mark.asyncio
async def test_failed_state_persisted(cache):
    """Failed state should be saved to DB."""
    orch = _make_orchestrator(cache)
    orch._script.generate = AsyncMock(
        side_effect=Exception("API error"),
    )

    from backend.core.exceptions import PipelineError
    try:
        await orch.generate("scary_stories")
    except PipelineError:
        pass

    # Check that at least one job exists with FAILED state
    jobs = await cache.list_recent_jobs()
    failed = [j for j in jobs if j.state == PipelineStage.FAILED]
    assert len(failed) >= 1


# ─── Custom Mode Tests ───────────────────────────────

@pytest.mark.asyncio
async def test_custom_mode_passes_topic(cache):
    """Custom mode should pass topic to script agent."""
    orch = _make_orchestrator(cache)
    await orch.generate(
        "scary_stories", mode="custom",
        custom_topic="A haunted lighthouse",
    )
    call_kwargs = orch._script.generate.call_args
    assert call_kwargs[1].get("custom_topic") == "A haunted lighthouse"
    assert call_kwargs[1].get("mode") == "custom"
