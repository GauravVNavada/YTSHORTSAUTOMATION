"""
Visual Agent — renders final video using FFmpeg subprocess.

Per MASTER_BLUEPRINT §12: ALL rendering = FFmpeg subprocess. NEVER MoviePy.
Follows crash-proof rendering: temp file → ffprobe validate → atomic rename.

Input: AudioBundle + AssetBundle + GenreConfig
Output: VideoResult (final_video.mp4)
"""
import asyncio
import shutil
from pathlib import Path
from typing import Optional

from backend.agents.caption_builder import build_captions
from backend.core.config import config
from backend.core.exceptions import RenderError
from backend.core.logger import get_logger
from backend.core.models import (
    AudioBundle,
    AssetBundle,
    GenreConfig,
    VideoResult,
)
from backend.services.ffmpeg_utils import (
    find_ffmpeg,
    check_disk_space,
    build_ffmpeg_cmd,
    ffprobe_duration,
    FFMPEG_TIMEOUT,
)

logger = get_logger(__name__)


class VisualAgent:
    """Renders the final video from audio, images, and captions.

    ALL rendering uses FFmpeg subprocess per MASTER_BLUEPRINT §12.
    Never uses MoviePy for compositing.
    """

    async def generate(
        self,
        audio_bundle: AudioBundle,
        asset_bundle: AssetBundle,
        genre_config: GenreConfig,
        job_id: str,
        title: str = "",
        description: str = "",
        hashtags: Optional[list[str]] = None,
    ) -> VideoResult:
        """Render the final video.

        Args:
            audio_bundle: Audio with timestamps from Audio Agent.
            asset_bundle: Images and media from Asset Agent.
            genre_config: Genre visual settings.
            job_id: Unique job identifier.
            title: Video title for metadata.
            description: Video description.
            hashtags: Video hashtags.

        Returns:
            VideoResult with path to final video.

        Raises:
            RenderError: If rendering fails.
        """
        output_dir = config.output_dir / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Safety check 1: Disk space (MASTER_BLUEPRINT §12)
        check_disk_space(output_dir)

        # Safety check 2: FFmpeg available
        ffmpeg = find_ffmpeg()

        # Step 1: Build captions (.ass file)
        caption_path = output_dir / "captions.ass"
        build_captions(
            audio_bundle.word_timestamps,
            caption_path,
            preset=genre_config.caption_preset,
        )

        # Step 2: Preprocess images (resize to 1080×1920)
        processed = await self._preprocess_images(
            asset_bundle.image_paths, output_dir
        )

        # Step 3: Build FFmpeg command
        tmp_path = output_dir / "render.tmp.mp4"
        final_path = output_dir / "final.mp4"

        cmd = build_ffmpeg_cmd(
            ffmpeg=ffmpeg,
            audio_path=audio_bundle.audio_path,
            image_paths=processed,
            caption_path=str(caption_path),
            output_path=str(tmp_path),
            duration_ms=audio_bundle.duration_ms,
            genre_id=genre_config.genre_id,
            layout=genre_config.layout,
            gameplay_path=getattr(asset_bundle, "gameplay_path", "") or "",
        )

        # Step 4: Render with timeout
        await self._run_ffmpeg(cmd)

        # Step 5: Validate output with ffprobe
        duration_s = ffprobe_duration(str(tmp_path))

        # Step 6: Atomic rename (temp → final)
        shutil.move(str(tmp_path), str(final_path))

        logger.info(
            "Video rendered",
            extra={"extra_data": {
                "job_id": job_id,
                "duration_s": duration_s,
                "path": str(final_path),
            }},
        )

        return VideoResult(
            job_id=job_id,
            video_path=str(final_path),
            title=title,
            description=description,
            hashtags=hashtags or [],
            duration_seconds=int(duration_s),
            word_count=len(audio_bundle.word_timestamps),
            genre_id=genre_config.genre_id,
        )

    async def _preprocess_images(
        self, image_paths: list[str], output_dir: Path
    ) -> list[str]:
        """Resize images to 1080×1920 using Pillow.

        Args:
            image_paths: Original image paths.
            output_dir: Directory for processed images.

        Returns:
            List of processed image paths.
        """
        processed = []
        proc_dir = output_dir / "processed"
        proc_dir.mkdir(exist_ok=True)

        for i, path in enumerate(image_paths):
            try:
                from PIL import Image
                img = Image.open(path)
                img = img.resize(
                    (config.video_width, config.video_height),
                    Image.LANCZOS,
                )
                out = proc_dir / f"img_{i:02d}.jpg"
                img.save(str(out), "JPEG", quality=90)
                processed.append(str(out))
            except Exception as exc:
                logger.warning(f"Image preprocess failed: {exc}")
                processed.append(path)
        return processed

    async def _run_ffmpeg(self, cmd: list[str]) -> None:
        """Run FFmpeg subprocess with timeout.

        Args:
            cmd: FFmpeg command list.

        Raises:
            RenderError: If FFmpeg fails or times out.
        """
        logger.info(
            "FFmpeg render starting",
            extra={"extra_data": {
                "cmd_preview": " ".join(cmd[:8]),
            }},
        )
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=FFMPEG_TIMEOUT
            )
            if proc.returncode != 0:
                err_text = stderr.decode()[-500:]
                raise RenderError(
                    f"FFmpeg exited with code {proc.returncode}",
                    details=err_text,
                )
        except asyncio.TimeoutError:
            proc.kill()
            raise RenderError(
                f"FFmpeg timed out after {FFMPEG_TIMEOUT}s",
            )
        except RenderError:
            raise
        except Exception as exc:
            raise RenderError(
                f"FFmpeg execution failed: {exc}",
                details=str(exc),
            )
