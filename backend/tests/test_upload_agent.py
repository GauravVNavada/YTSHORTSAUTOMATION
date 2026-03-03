"""
Tests for the Upload Agent and YouTube Service.

Uses mocked YouTube API (no real uploads per testing rules).
"""
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock

from backend.agents.upload_agent import (
    UploadAgent,
    UploadResult,
    _add_ai_disclosure,
)
from backend.core.models import VideoResult
from backend.services.youtube_service import YouTubeService


# ─── AI Disclosure Tests ───────────────────────────────

def test_ai_disclosure_added():
    """Should append AI disclosure to description."""
    result = _add_ai_disclosure("Great video!")
    assert "AI assistance" in result


def test_ai_disclosure_not_duplicated():
    """Should not add disclosure twice."""
    text = "Video\n\n---\nCreated with AI assistance"
    result = _add_ai_disclosure(text)
    assert result.count("AI assistance") == 1


# ─── YouTube Service Tests ─────────────────────────────

def test_youtube_service_no_creds():
    """Should raise AuthError without credentials."""
    from backend.core.exceptions import AuthError
    svc = YouTubeService(credentials_path="")
    with pytest.raises(AuthError):
        svc._get_service()


@pytest.mark.asyncio
async def test_youtube_upload_file_missing():
    """Should raise UploadError for missing video file."""
    from backend.core.exceptions import UploadError
    svc = YouTubeService(credentials_path="fake.json")
    with pytest.raises(UploadError):
        await svc.upload_video(
            video_path="/nonexistent/video.mp4",
            title="Test",
            description="Test desc",
            tags=["test"],
        )


@pytest.mark.asyncio
async def test_quota_info():
    """Should return quota details."""
    svc = YouTubeService()
    quota = await svc.get_quota_usage()
    assert quota["daily_limit"] == 10000
    assert quota["max_uploads_per_day"] == 6


# ─── Upload Agent Tests ───────────────────────────────

@pytest.fixture
def mock_youtube_service():
    """Mock YouTube service that returns a fake video ID."""
    svc = MagicMock(spec=YouTubeService)
    svc.upload_video = AsyncMock(return_value="dQw4w9WgXcQ")
    return svc


@pytest.fixture
def sample_video_result(tmp_path):
    """Sample VideoResult for upload testing."""
    video = tmp_path / "final.mp4"
    video.write_bytes(b"fake mp4 data")
    return VideoResult(
        job_id="test_001",
        video_path=str(video),
        title="Scary Short 😨",
        description="Would you stay?",
        hashtags=["#shorts", "#scary"],
        duration_seconds=45,
        genre_id="scary_stories",
    )


@pytest.mark.asyncio
async def test_upload_success(mock_youtube_service, sample_video_result):
    """Should upload and return UploadResult."""
    agent = UploadAgent(mock_youtube_service)
    result = await agent.upload(sample_video_result)

    assert isinstance(result, UploadResult)
    assert result.video_id == "dQw4w9WgXcQ"
    assert "shorts/" in result.url
    assert result.uploaded_at


@pytest.mark.asyncio
async def test_upload_adds_disclosure(mock_youtube_service, sample_video_result):
    """Should add AI disclosure to description."""
    agent = UploadAgent(mock_youtube_service)
    await agent.upload(sample_video_result)

    # Check the description passed to upload_video
    call_args = mock_youtube_service.upload_video.call_args
    desc = call_args.kwargs.get("description", call_args[1].get("description", ""))
    assert "AI assistance" in desc


@pytest.mark.asyncio
async def test_upload_retries_on_failure(sample_video_result):
    """Should retry upload on failure."""
    from backend.core.exceptions import UploadError

    svc = MagicMock(spec=YouTubeService)
    svc.upload_video = AsyncMock(
        side_effect=[UploadError("fail"), "success_id"]
    )
    agent = UploadAgent(svc)
    result = await agent.upload(sample_video_result)

    assert result.video_id == "success_id"
    assert svc.upload_video.call_count == 2


@pytest.mark.asyncio
async def test_upload_fails_after_max_retries(sample_video_result, monkeypatch):
    """Should raise after all retries exhausted."""
    from backend.core.exceptions import UploadError

    svc = MagicMock(spec=YouTubeService)
    svc.upload_video = AsyncMock(side_effect=UploadError("nope"))

    monkeypatch.setattr(
        "backend.agents.upload_agent.config",
        type("Config", (), {"max_retries": 2})(),
    )

    agent = UploadAgent(svc)
    with pytest.raises(UploadError, match="failed after"):
        await agent.upload(sample_video_result)

    assert svc.upload_video.call_count == 2
