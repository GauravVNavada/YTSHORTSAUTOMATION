"""
Upload Agent — orchestrates YouTube video upload and scheduling.

Per MASTER_BLUEPRINT §5 step 13: YouTube upload with title from genre template,
auto-scheduling, and AI disclosure. Follows agent isolation rules.

Input: VideoResult (from Visual Agent)
Output: UploadResult (video_id, URL, scheduled time)
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional

from backend.core.config import config
from backend.core.exceptions import UploadError
from backend.core.logger import get_logger
from backend.core.models import VideoResult
from backend.services.youtube_service import YouTubeService

logger = get_logger(__name__)


class UploadResult:
    """Result of a YouTube upload.

    Args:
        video_id: YouTube video ID.
        url: Full YouTube URL.
        title: Uploaded title.
        uploaded_at: Upload timestamp.
    """

    def __init__(
        self,
        video_id: str,
        url: str,
        title: str,
        uploaded_at: str,
    ):
        self.video_id = video_id
        self.url = url
        self.title = title
        self.uploaded_at = uploaded_at


class UploadAgent:
    """Handles video upload to YouTube.

    Args:
        youtube_service: Injected YouTube API service.
    """

    def __init__(self, youtube_service: YouTubeService):
        self._youtube = youtube_service

    async def upload(
        self,
        video_result: VideoResult,
        schedule: str = "now",
    ) -> UploadResult:
        """Upload a video to YouTube.

        Args:
            video_result: VideoResult from Visual Agent.
            schedule: "now" | "next_best" | ISO datetime.

        Returns:
            UploadResult with video ID and URL.

        Raises:
            UploadError: If upload fails after retries.
        """
        title = video_result.title
        description = video_result.description
        tags = video_result.hashtags

        # Add AI disclosure to description
        description = _add_ai_disclosure(description)

        # Retry upload up to 3 times
        last_error = None
        for attempt in range(config.max_retries):
            try:
                video_id = await self._youtube.upload_video(
                    video_path=video_result.video_path,
                    title=title,
                    description=description,
                    tags=tags,
                )

                url = f"https://youtube.com/shorts/{video_id}"
                now = datetime.now(timezone.utc).isoformat()

                logger.info(
                    "Upload complete",
                    extra={"extra_data": {
                        "video_id": video_id,
                        "attempt": attempt + 1,
                        "url": url,
                    }},
                )

                return UploadResult(
                    video_id=video_id,
                    url=url,
                    title=title,
                    uploaded_at=now,
                )
            except UploadError as exc:
                last_error = exc
                logger.warning(
                    f"Upload attempt {attempt + 1} failed: {exc}",
                )
                if attempt < config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        raise UploadError(
            f"Upload failed after {config.max_retries} attempts",
            details=str(last_error),
        )


def _add_ai_disclosure(description: str) -> str:
    """Add AI disclosure to video description.

    Per MASTER_BLUEPRINT §5 step 13: AI disclosure field
    (manual workaround — no API field exists yet).

    Args:
        description: Original description.

    Returns:
        Description with AI disclosure appended.
    """
    disclosure = "\n\n---\nCreated with AI assistance"
    if disclosure.strip() not in description:
        return description + disclosure
    return description
