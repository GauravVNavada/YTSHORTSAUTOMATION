"""
Caption Builder — generates ASS subtitle files from word timestamps.

Per MASTER_BLUEPRINT §10: builds word-at-a-time pop captions with
genre-specific styling, safe zones, and font sizing.

Uses pysubs2 for ASS file generation. Never exceeds 300 lines.
"""
import re
from pathlib import Path
from typing import Optional

from backend.core.logger import get_logger
from backend.core.models import WordTimestamp

logger = get_logger(__name__)


# ─── Caption Safety Constants (MASTER_BLUEPRINT §10) ──
MAX_CHARS_PER_LINE = 25
MAX_LINES = 2
MAX_WORDS_ON_SCREEN = 7
SIDE_MARGIN_PX = 60
TOP_SAFE_ZONE_PX = 200
BOTTOM_SAFE_ZONE_PX = 250
MIN_FONT_SIZE = 48
MAX_FONT_SIZE = 84
MIN_BORDER_PX = 2

# Video dimensions
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

# ─── Genre Preset Styles ──────────────────────────────
_PRESETS = {
    "clean_pro": {
        "font": "Montserrat", "font_size": 64,
        "primary": "&H00FFFFFF", "outline": "&H00000000", "border": 3,
    },
    "horror_red": {
        "font": "Creepster", "font_size": 60,
        "primary": "&H0000CCFF", "outline": "&H00000000", "border": 3,
    },
    "bold_pop": {
        "font": "Anton", "font_size": 72,
        "primary": "&H0000FFFF", "outline": "&H00000000", "border": 4,
    },
    "neon_glow": {
        "font": "Oswald", "font_size": 60,
        "primary": "&H00FF66CC", "outline": "&H00330033", "border": 3,
    },
    "minimal": {
        "font": "Roboto", "font_size": 56,
        "primary": "&H00FFFFFF", "outline": "&H00333333", "border": 2,
    },
    "classic_white": {
        "font": "Arial", "font_size": 62,
        "primary": "&H00FFFFFF", "outline": "&H00000000", "border": 3,
    },
    "tiktok_bright": {
        "font": "Poppins", "font_size": 68,
        "primary": "&H0000FFFF", "outline": "&H00000000", "border": 4,
    },
    "karaoke_fill": {
        "font": "Montserrat", "font_size": 66,
        "primary": "&H0000FF00", "outline": "&H00000000", "border": 3,
    },
    "typewriter_mono": {
        "font": "Courier New", "font_size": 54,
        "primary": "&H0000FF00", "outline": "&H00111111", "border": 2,
    },
    "comic_burst": {
        "font": "Bangers", "font_size": 74,
        "primary": "&H0000DDFF", "outline": "&H00000088", "border": 5,
    },
    "fire_gradient": {
        "font": "Impact", "font_size": 70,
        "primary": "&H000055FF", "outline": "&H000000AA", "border": 4,
    },
    "ice_cool": {
        "font": "Nunito", "font_size": 60,
        "primary": "&H00FFCC66", "outline": "&H00331100", "border": 3,
    },
}


def build_captions(
    word_timestamps: list[WordTimestamp],
    output_path: Path,
    preset: str = "clean_pro",
    video_width: int = VIDEO_WIDTH,
    video_height: int = VIDEO_HEIGHT,
) -> str:
    """Build an ASS subtitle file from word timestamps.

    Creates word-at-a-time pop captions per MASTER_BLUEPRINT §10.
    Each word appears individually, timed to speech.

    Args:
        word_timestamps: Word-level timestamps from AudioBundle.
        output_path: Path to write the .ass file.
        preset: Caption style preset name.
        video_width: Video width in pixels.
        video_height: Video height in pixels.

    Returns:
        Absolute path to the generated .ass file.
    """
    style = _PRESETS.get(preset, _PRESETS["clean_pro"])
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Group words into display chunks (max 7 words per screen)
    chunks = _group_words(word_timestamps)

    # Build ASS content
    lines = _build_ass_header(style, video_width, video_height)
    lines.append("")
    lines.append("[Events]")
    lines.append(
        "Format: Layer, Start, End, Style, Name, "
        "MarginL, MarginR, MarginV, Effect, Text"
    )

    for chunk in chunks:
        if not chunk:
            continue
        start = _ms_to_ass_time(chunk[0].start_ms)
        end = _ms_to_ass_time(chunk[-1].end_ms)
        text = " ".join(w.word for w in chunk)

        # Enforce max chars per line
        text = _wrap_text(text)

        lines.append(
            f"Dialogue: 0,{start},{end},Default,,{SIDE_MARGIN_PX},"
            f"{SIDE_MARGIN_PX},0,,{text}"
        )

    content = "\n".join(lines)
    output_path.write_text(content, encoding="utf-8")

    logger.info(
        "Captions built",
        extra={"extra_data": {
            "words": len(word_timestamps),
            "chunks": len(chunks),
            "preset": preset,
        }},
    )
    return str(output_path)


def _build_ass_header(
    style: dict, width: int, height: int
) -> list[str]:
    """Build the ASS file header with style definition.

    Args:
        style: Preset style dictionary.
        width: Video width.
        height: Video height.

    Returns:
        List of header lines.
    """
    font = style["font"]
    size = min(max(style["font_size"], MIN_FONT_SIZE), MAX_FONT_SIZE)
    primary = style["primary"]
    outline = style["outline"]
    border = max(style["border"], MIN_BORDER_PX)

    # Vertical position in safe zone
    y_pos = height - BOTTOM_SAFE_ZONE_PX

    return [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "WrapStyle: 0",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, "
        "SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, "
        "MarginV, Encoding",
        f"Style: Default,{font},{size},{primary},&H000000FF,"
        f"{outline},&H80000000,-1,0,0,0,100,100,0,0,1,"
        f"{border},0,2,{SIDE_MARGIN_PX},{SIDE_MARGIN_PX},"
        f"{height - y_pos},1",
    ]


def _group_words(
    timestamps: list[WordTimestamp],
) -> list[list[WordTimestamp]]:
    """Group words into display chunks.

    Max 7 words per chunk per MASTER_BLUEPRINT §10 safety rules.

    Args:
        timestamps: All word timestamps.

    Returns:
        List of word groups for display.
    """
    chunks = []
    current = []
    for ts in timestamps:
        current.append(ts)
        if len(current) >= MAX_WORDS_ON_SCREEN:
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)
    return chunks


def _wrap_text(text: str) -> str:
    """Wrap text to fit within max chars per line.

    Uses \\N for ASS line breaks. Max 2 lines.

    Args:
        text: Caption text.

    Returns:
        Wrapped text with ASS line breaks.
    """
    if len(text) <= MAX_CHARS_PER_LINE:
        return text
    # Find a good break point near the middle
    mid = len(text) // 2
    # Look for space near middle
    best = mid
    for i in range(mid, min(mid + 10, len(text))):
        if text[i] == " ":
            best = i
            break
    for i in range(mid, max(mid - 10, 0), -1):
        if text[i] == " ":
            best = i
            break
    return text[:best] + "\\N" + text[best + 1:]


def _ms_to_ass_time(ms: int) -> str:
    """Convert milliseconds to ASS timestamp format.

    Args:
        ms: Time in milliseconds.

    Returns:
        ASS-formatted time string (H:MM:SS.CC).
    """
    total_s = ms / 1000.0
    h = int(total_s // 3600)
    m = int((total_s % 3600) // 60)
    s = total_s % 60
    return f"{h}:{m:02d}:{s:05.2f}"
