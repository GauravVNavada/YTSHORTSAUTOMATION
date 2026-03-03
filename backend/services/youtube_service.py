"""
YouTube Service — wraps YouTube Data API v3 for video uploads.

Handles OAuth2 authentication, video upload with resumable protocol,
and metadata setting (title, description, tags, category).
"""
import asyncio
from pathlib import Path
from typing import Optional

from backend.core.config import config
from backend.core.exceptions import UploadError, AuthError
from backend.core.logger import get_logger

logger = get_logger(__name__)


class YouTubeService:
    """Wraps the YouTube Data API v3.

    Args:
        credentials_path: Path to OAuth2 credentials JSON.
    """

    def __init__(self, credentials_path: str = ""):
        self._creds_path = credentials_path
        self._service = None  # Lazy-initialized

    def _get_service(self):
        """Initialize the YouTube API service.

        Returns:
            YouTube API resource object.

        Raises:
            AuthError: If credentials are invalid.
        """
        if self._service:
            return self._service

        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials

            if not self._creds_path:
                raise AuthError(
                    "YouTube credentials not configured",
                    details="Set up OAuth2 credentials in settings",
                )

            creds = Credentials.from_authorized_user_file(
                self._creds_path
            )
            self._service = build("youtube", "v3", credentials=creds)
            return self._service
        except AuthError:
            raise
        except Exception as exc:
            raise AuthError(
                f"YouTube auth failed: {exc}",
                details=str(exc),
            )

    async def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        category_id: int = 22,
        privacy: str = "public",
    ) -> str:
        """Upload a video to YouTube.

        Uses resumable uploads via MediaFileUpload.

        Args:
            video_path: Path to the video file.
            title: Video title (max 100 chars).
            description: Video description.
            tags: Video tags/hashtags.
            category_id: YouTube category (22 = People & Blogs).
            privacy: Privacy status (public/unlisted/private).

        Returns:
            YouTube video ID.

        Raises:
            UploadError: If upload fails.
        """
        if not Path(video_path).exists():
            raise UploadError(
                f"Video file not found: {video_path}",
            )

        try:
            from googleapiclient.http import MediaFileUpload

            service = self._get_service()

            body = {
                "snippet": {
                    "title": title[:100],
                    "description": description,
                    "tags": tags[:30],
                    "categoryId": str(category_id),
                },
                "status": {
                    "privacyStatus": privacy,
                    "selfDeclaredMadeForKids": False,
                },
            }

            media = MediaFileUpload(
                video_path,
                mimetype="video/mp4",
                resumable=True,
                chunksize=256 * 1024,
            )

            request = service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            # Resumable upload loop
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.debug(f"Upload progress: {progress}%")

            video_id = response.get("id", "")
            logger.info(
                "Video uploaded",
                extra={"extra_data": {
                    "video_id": video_id,
                    "title": title[:50],
                }},
            )
            return video_id

        except (AuthError, UploadError):
            raise
        except Exception as exc:
            raise UploadError(
                f"YouTube upload failed: {exc}",
                details=str(exc),
            )

    async def get_quota_usage(self) -> dict:
        """Check current YouTube API quota usage.

        Returns:
            Dict with quota info.
        """
        # YouTube Data API quota: 10,000 units/day
        # Upload = 1,600 units → ~6 uploads/day
        return {
            "daily_limit": 10000,
            "upload_cost": 1600,
            "max_uploads_per_day": 6,
        }
