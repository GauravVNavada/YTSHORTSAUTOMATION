"""
Upload Agent — orchestrates YouTube video upload and scheduling.

Per MASTER_BLUEPRINT §5 step 13: YouTube upload with title from genre template,
auto-scheduling based on best posting time, and AI disclosure.

Input: VideoResult (from Visual Agent)
Output: UploadResult (video_id, URL, scheduled time)
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

from backend.core.config import config
from backend.core.exceptions import UploadError
from backend.core.logger import get_logger
from backend.core.models import VideoResult
from backend.services.youtube_service import YouTubeService

logger = get_logger(__name__)

# Best posting times (UTC hours) by day of week — from analytics research
# Mon=0, Sun=6
_BEST_HOURS_UTC = {
    0: [14, 17, 20],   # Monday
    1: [14, 17, 20],   # Tuesday
    2: [14, 17, 21],   # Wednesday
    3: [12, 15, 18],   # Thursday
    4: [10, 14, 17],   # Friday
    5: [9, 12, 15],    # Saturday
    6: [10, 14, 18],   # Sunday
}


class UploadResult:
    """Result of a YouTube upload."""

    def __init__(
        self, video_id: str, url: str, title: str,
        uploaded_at: str, scheduled_for: str = "",
    ):
        self.video_id = video_id
        self.url = url
        self.title = title
        self.uploaded_at = uploaded_at
        self.scheduled_for = scheduled_for


class UploadAgent:
    """Handles video upload to YouTube with smart scheduling.

    Args:
        youtube_service: Injected YouTube API service.
    """

    def __init__(self, youtube_service: YouTubeService):
        self._youtube = youtube_service

    async def upload(
        self, video_result: VideoResult, schedule: str = "now",
    ) -> UploadResult:
        """Upload a video to YouTube.

        Args:
            video_result: VideoResult from Visual Agent.
            schedule: "now" | "next_best" | ISO datetime.

        Returns:
            UploadResult with video ID and URL.
        """
        title = video_result.title
        description = _add_ai_disclosure(video_result.description)
        tags = video_result.hashtags

        # Resolve schedule
        scheduled_for = _resolve_schedule(schedule)

        # Retry upload
        last_error = None
        for attempt in range(config.max_retries):
            try:
                video_id = await self._youtube.upload_video(
                    video_path=video_result.video_path,
                    title=title, description=description, tags=tags,
                )
                url = f"https://youtube.com/shorts/{video_id}"
                now = datetime.now(timezone.utc).isoformat()

                logger.info("Upload complete", extra={"extra_data": {
                    "video_id": video_id, "attempt": attempt + 1,
                    "url": url, "scheduled_for": scheduled_for,
                }})

                return UploadResult(
                    video_id=video_id, url=url, title=title,
                    uploaded_at=now, scheduled_for=scheduled_for,
                )
            except UploadError as exc:
                last_error = exc
                logger.warning(f"Upload attempt {attempt + 1} failed: {exc}")
                if attempt < config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        raise UploadError(
            f"Upload failed after {config.max_retries} attempts",
            details=str(last_error),
        )


def _resolve_schedule(schedule: str) -> str:
    """Resolve schedule string to an ISO datetime.

    Per MASTER_BLUEPRINT §5 step 13: auto-scheduling based on
    best posting time from analytics.

    Args:
        schedule: "now" | "next_best" | ISO datetime string.

    Returns:
        ISO datetime string for the scheduled time.
    """
    if schedule == "now":
        return datetime.now(timezone.utc).isoformat()

    if schedule == "next_best":
        return _find_next_best_time().isoformat()

    # Assume ISO datetime
    try:
        datetime.fromisoformat(schedule)
        return schedule
    except ValueError:
        return datetime.now(timezone.utc).isoformat()


def _find_next_best_time() -> datetime:
    """Find the next best posting time based on analytics.

    Returns:
        Next best posting datetime (UTC).
    """
    now = datetime.now(timezone.utc)
    # Check today and next 7 days
    for day_offset in range(8):
        check_date = now + timedelta(days=day_offset)
        day = check_date.weekday()
        hours = _BEST_HOURS_UTC.get(day, [14])

        for hour in hours:
            candidate = check_date.replace(
                hour=hour, minute=0, second=0, microsecond=0,
            )
            if candidate > now + timedelta(minutes=30):
                return candidate

    # Fallback: tomorrow at 14:00 UTC
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)


def _add_ai_disclosure(description: str) -> str:
    """Add AI disclosure per MASTER_BLUEPRINT §5 step 13."""
    disclosure = "\n\n---\nCreated with AI assistance"
    if disclosure.strip() not in description:
        return description + disclosure
    return description
