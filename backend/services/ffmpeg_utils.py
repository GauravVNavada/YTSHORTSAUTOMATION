"""
FFmpeg utilities — command building and validation helpers.

Separated from visual_agent.py to keep both files under 300 lines
per DEVELOPMENT_CONTRACT §2.
"""
import shutil
import subprocess
from pathlib import Path

from backend.core.exceptions import RenderError
from backend.core.logger import get_logger

logger = get_logger(__name__)

# ─── Constants (MASTER_BLUEPRINT §12) ──────────────────
FFMPEG_TIMEOUT = 300       # 5-minute hard timeout
ENCODING = [
    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k",
    "-movflags", "+faststart",
]
MIN_DISK_MB = 500


def find_ffmpeg() -> str:
    """Find FFmpeg binary in PATH.

    Returns:
        Path to ffmpeg executable.

    Raises:
        RenderError: If FFmpeg not found.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RenderError(
            "FFmpeg not found in PATH",
            details="Install FFmpeg: https://ffmpeg.org/download.html",
        )
    return ffmpeg


def check_disk_space(path: Path) -> None:
    """Verify minimum free disk space.

    Args:
        path: Directory to check.

    Raises:
        RenderError: If insufficient disk space.
    """
    free_mb = shutil.disk_usage(str(path)).free // (1024 * 1024)
    if free_mb < MIN_DISK_MB:
        raise RenderError(
            f"Insufficient disk space: {free_mb}MB < {MIN_DISK_MB}MB",
        )


def build_ffmpeg_cmd(
    ffmpeg: str,
    audio_path: str,
    image_paths: list[str],
    caption_path: str,
    output_path: str,
    duration_ms: int,
) -> list[str]:
    """Build the FFmpeg command for video rendering.

    Creates a slideshow from images + audio + captions with
    Ken Burns zoompan effect per MASTER_BLUEPRINT §9.

    Args:
        ffmpeg: Path to ffmpeg binary.
        audio_path: Path to audio file.
        image_paths: Processed image paths.
        caption_path: Path to ASS caption file.
        output_path: Path for output video.
        duration_ms: Total duration in milliseconds.

    Returns:
        FFmpeg command as list of strings.
    """
    duration_s = duration_ms / 1000.0
    img_count = max(len(image_paths), 1)
    img_duration = duration_s / img_count

    cmd = [ffmpeg, "-y"]

    # Input images as loops
    for img in image_paths:
        cmd.extend([
            "-loop", "1", "-t", f"{img_duration:.2f}", "-i", img,
        ])

    # Input audio
    cmd.extend(["-i", audio_path])

    # Build filter graph
    if len(image_paths) > 1:
        filter_parts = []
        for i in range(len(image_paths)):
            filter_parts.append(
                f"[{i}:v]scale=1080:1920:force_original_aspect_ratio="
                f"decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
                f"zoompan=z='min(zoom+0.0008,1.15)'"
                f":d={int(img_duration * 30)}"
                f":s=1080x1920:fps=30[v{i}]"
            )
        concat_in = "".join(f"[v{i}]" for i in range(len(image_paths)))
        filter_parts.append(
            f"{concat_in}concat=n={len(image_paths)}:v=1:a=0[vbase]"
        )
        filter_parts.append(f"[vbase]ass='{caption_path}'[vout]")
        cmd.extend(["-filter_complex", ";".join(filter_parts)])
        cmd.extend([
            "-map", "[vout]",
            "-map", f"{len(image_paths)}:a",
        ])
    else:
        cmd.extend([
            "-vf",
            f"scale=1080:1920,zoompan=z='min(zoom+0.0008,1.15)'"
            f":d={int(duration_s * 30)}:s=1080x1920:fps=30,"
            f"ass='{caption_path}'",
        ])
        cmd.extend(["-map", "0:v", "-map", "1:a"])

    cmd.extend(["-t", f"{duration_s:.2f}"])
    cmd.extend(ENCODING)
    cmd.append(output_path)

    return cmd


def ffprobe_duration(video_path: str) -> float:
    """Validate video output with ffprobe.

    Args:
        video_path: Path to the rendered video.

    Returns:
        Duration in seconds.

    Raises:
        RenderError: If video is invalid.
    """
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        logger.warning("ffprobe not found, skipping validation")
        return 0.0

    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries",
             "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1",
             video_path],
            capture_output=True, text=True, timeout=10,
        )
        duration = float(result.stdout.strip())
        if duration < 1.0:
            raise RenderError("Rendered video too short (<1s)")
        return duration
    except (ValueError, subprocess.TimeoutExpired):
        raise RenderError(
            "ffprobe validation failed",
            details="Output video may be corrupt",
        )
