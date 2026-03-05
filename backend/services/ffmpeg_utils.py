"""
FFmpeg utilities — command building, transitions, and validation.

Per MASTER_BLUEPRINT §9-12: Ken Burns, xfade transitions,
3 layout modes, crash-proof validation.
"""
import shutil
import subprocess
from pathlib import Path

from backend.core.exceptions import RenderError
from backend.core.logger import get_logger

logger = get_logger(__name__)

# ─── Constants (MASTER_BLUEPRINT §12) ──────────────────
FFMPEG_TIMEOUT = 300
ENCODING = [
    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k",
    "-movflags", "+faststart",
]
MIN_DISK_MB = 500

# Genre → transition mapping (MASTER_BLUEPRINT §9)
GENRE_TRANSITIONS = {
    "scary_stories": "dissolve",
    "history": "dissolve",
    "motivation": "slideleft",
    "tech_ai": "fade",
    "science": "fade",
    "psychology": "circlecrop",
}
XFADE_DURATION = 0.3  # seconds


def find_ffmpeg() -> str:
    """Find FFmpeg binary in PATH."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RenderError(
            "FFmpeg not found in PATH",
            details="Install FFmpeg: https://ffmpeg.org/download.html",
        )
    return ffmpeg


def check_disk_space(path: Path) -> None:
    """Verify minimum free disk space."""
    free_mb = shutil.disk_usage(str(path)).free // (1024 * 1024)
    if free_mb < MIN_DISK_MB:
        raise RenderError(f"Disk space: {free_mb}MB < {MIN_DISK_MB}MB")


def build_ffmpeg_cmd(
    ffmpeg: str, audio_path: str, image_paths: list[str],
    caption_path: str, output_path: str, duration_ms: int,
    genre_id: str = "", layout: str = "full_image",
    gameplay_path: str = "",
) -> list[str]:
    """Build FFmpeg command with xfade transitions and layout modes.

    Args:
        ffmpeg: Path to ffmpeg binary.
        audio_path: Audio file path.
        image_paths: Processed image paths.
        caption_path: ASS caption file path.
        output_path: Output video path.
        duration_ms: Total duration in ms.
        genre_id: Genre for transition selection.
        layout: Layout mode: full_image, split_screen, full_gameplay.
        gameplay_path: Gameplay clip path (for split/full layouts).

    Returns:
        FFmpeg command as list of strings.
    """
    if layout == "full_gameplay" and gameplay_path:
        return _build_gameplay_cmd(
            ffmpeg, audio_path, gameplay_path,
            caption_path, output_path, duration_ms,
        )
    if layout == "split_screen" and gameplay_path:
        return _build_split_cmd(
            ffmpeg, audio_path, image_paths, gameplay_path,
            caption_path, output_path, duration_ms, genre_id,
        )
    return _build_full_image_cmd(
        ffmpeg, audio_path, image_paths,
        caption_path, output_path, duration_ms, genre_id,
    )


def _build_full_image_cmd(
    ffmpeg: str, audio_path: str, image_paths: list[str],
    caption_path: str, output_path: str, duration_ms: int,
    genre_id: str,
) -> list[str]:
    """Full Image layout with Ken Burns + xfade transitions."""
    duration_s = duration_ms / 1000.0
    n = max(len(image_paths), 1)
    img_dur = duration_s / n
    transition = GENRE_TRANSITIONS.get(genre_id, "fade")

    cmd = [ffmpeg, "-y"]
    for img in image_paths:
        cmd.extend(["-loop", "1", "-t", f"{img_dur:.2f}", "-i", img])
    cmd.extend(["-i", audio_path])

    if n > 1:
        parts = []
        for i in range(n):
            parts.append(
                f"[{i}:v]scale=1080:1920:force_original_aspect_ratio="
                f"decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
                f"zoompan=z='min(zoom+0.0008,1.15)'"
                f":d={int(img_dur * 30)}:s=1080x1920:fps=30[v{i}]"
            )
        # Chain xfade transitions between each pair
        prev = "v0"
        for i in range(1, n):
            offset = max(0, img_dur * i - XFADE_DURATION)
            out_label = f"xf{i}" if i < n - 1 else "vbase"
            parts.append(
                f"[{prev}][v{i}]xfade=transition={transition}"
                f":duration={XFADE_DURATION}:offset={offset:.2f}[{out_label}]"
            )
            prev = out_label

        cap_path = caption_path.replace("\\", "/").replace(":", "\\\\:")
        parts.append(f"[vbase]ass='{cap_path}'[vout]")
        cmd.extend(["-filter_complex", ";".join(parts)])
        cmd.extend(["-map", "[vout]", "-map", f"{n}:a"])
    else:
        cap_path = caption_path.replace("\\", "/").replace(":", "\\\\:")
        cmd.extend([
            "-vf",
            f"scale=1080:1920,zoompan=z='min(zoom+0.0008,1.15)'"
            f":d={int(duration_s * 30)}:s=1080x1920:fps=30,"
            f"ass='{cap_path}'",
        ])
        cmd.extend(["-map", "0:v", "-map", "1:a"])

    cmd.extend(["-t", f"{duration_s:.2f}"])
    cmd.extend(ENCODING)
    cmd.append(output_path)
    return cmd


def _build_split_cmd(
    ffmpeg: str, audio_path: str, image_paths: list[str],
    gameplay_path: str, caption_path: str, output_path: str,
    duration_ms: int, genre_id: str,
) -> list[str]:
    """Split Screen: images top 55% + gameplay bottom 45%."""
    duration_s = duration_ms / 1000.0
    n = max(len(image_paths), 1)
    img_dur = duration_s / n

    cmd = [ffmpeg, "-y"]
    for img in image_paths:
        cmd.extend(["-loop", "1", "-t", f"{img_dur:.2f}", "-i", img])
    cmd.extend(["-i", gameplay_path, "-i", audio_path])

    # Build: scale images to top 55%, gameplay to bottom 45%, vstack
    parts = []
    for i in range(n):
        parts.append(f"[{i}:v]scale=1080:1056[top{i}]")
    parts.append(f"[{n}:v]scale=1080:864[bottom]")

    if n > 1:
        for i in range(n):
            parts.append(f"[top{i}][bottom]vstack[combined{i}]")
        concat_in = "".join(f"[combined{i}]" for i in range(n))
        parts.append(f"{concat_in}concat=n={n}:v=1:a=0[vbase]")
    else:
        parts.append(f"[top0][bottom]vstack[vbase]")

    cap_path = caption_path.replace("\\", "/").replace(":", "\\\\:")
    parts.append(f"[vbase]ass='{cap_path}'[vout]")
    cmd.extend(["-filter_complex", ";".join(parts)])
    cmd.extend(["-map", "[vout]", "-map", f"{n + 1}:a"])
    cmd.extend(["-t", f"{duration_s:.2f}"])
    cmd.extend(ENCODING)
    cmd.append(output_path)
    return cmd


def _build_gameplay_cmd(
    ffmpeg: str, audio_path: str, gameplay_path: str,
    caption_path: str, output_path: str, duration_ms: int,
) -> list[str]:
    """Full Gameplay: gameplay 100% + captions overlay."""
    duration_s = duration_ms / 1000.0
    cap_path = caption_path.replace("\\", "/").replace(":", "\\\\:")
    cmd = [ffmpeg, "-y", "-i", gameplay_path, "-i", audio_path]
    cmd.extend([
        "-vf", f"scale=1080:1920,ass='{cap_path}'",
        "-map", "0:v", "-map", "1:a",
        "-t", f"{duration_s:.2f}",
    ])
    cmd.extend(ENCODING)
    cmd.append(output_path)
    return cmd


def ffprobe_duration(video_path: str) -> float:
    """Validate video with ffprobe."""
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
        raise RenderError("ffprobe validation failed")
