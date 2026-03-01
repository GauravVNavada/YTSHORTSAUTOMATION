"""
SSML Builder — converts plain narration text into genre-specific SSML.

Adds prosody profiles, break tags, and word-level <mark> tags for
timestamp extraction from Google Cloud TTS.

Each genre has different pacing, pitch, and emphasis characteristics.
"""
import re
from typing import Optional

from backend.core.models import GenreConfig
from backend.core.logger import get_logger

logger = get_logger(__name__)


# ─── Genre Prosody Profiles ───────────────────────────
# Overrides applied to TTS when genre config has specific moods.
# rate = speaking rate multiplier (1.0 = normal)
# pitch = semitone shift
# break_ms = pause between sentences
_GENRE_PROSODY = {
    "dark_ambient": {"rate": 0.88, "pitch": -2.0, "break_ms": 600},
    "suspense":     {"rate": 0.85, "pitch": -1.5, "break_ms": 700},
    "chill":        {"rate": 0.95, "pitch": 0.0,   "break_ms": 400},
    "upbeat":       {"rate": 1.05, "pitch": 1.0,   "break_ms": 300},
    "neutral":      {"rate": 0.95, "pitch": 0.0,   "break_ms": 400},
    "epic":         {"rate": 0.92, "pitch": -1.0,  "break_ms": 500},
    "dramatic":     {"rate": 0.90, "pitch": -1.5,  "break_ms": 550},
}

# Power words that get emphasis (medium)
_POWER_WORDS = {
    "never", "always", "dead", "killed", "disappeared", "terrifying",
    "shocking", "impossible", "million", "billion", "secret",
    "discovered", "ancient", "forbidden", "deadly", "mysterious",
    "cursed", "haunted", "warning", "danger", "trapped", "survived",
}


def build_ssml(
    narration: str,
    genre_config: Optional[GenreConfig] = None,
    hook_line: Optional[str] = None,
) -> str:
    """Convert plain narration text into genre-specific SSML.

    Adds:
    - <mark> tags at every word boundary (for timestamp extraction)
    - <break> tags at sentence boundaries
    - <emphasis> on power words
    - Genre-specific prosody wrapper

    Args:
        narration: Plain text narration from the script.
        genre_config: Genre-specific TTS configuration.
        hook_line: The hook sentence (gets stronger emphasis).

    Returns:
        Complete SSML string ready for Google Cloud TTS.
    """
    mood = genre_config.music_mood if genre_config else "neutral"
    prosody = _GENRE_PROSODY.get(mood, _GENRE_PROSODY["neutral"])

    # Split into sentences
    sentences = _split_sentences(narration)
    if not sentences:
        return "<speak></speak>"

    ssml_parts = ['<speak>']

    # Open prosody tag with genre rate/pitch
    rate = genre_config.tts_rate if genre_config else prosody["rate"]
    pitch_val = genre_config.tts_pitch if genre_config else prosody["pitch"]
    ssml_parts.append(
        f'<prosody rate="{rate}" pitch="{pitch_val:+.1f}st">'
    )

    for i, sentence in enumerate(sentences):
        # Add sentence break (except before first sentence)
        if i > 0:
            ssml_parts.append(
                f'<break time="{prosody["break_ms"]}ms"/>'
            )

        # Check if this is the hook line
        is_hook = (
            hook_line and sentence.strip().startswith(
                hook_line[:30].strip()
            )
        )

        # Process words in this sentence
        words = sentence.split()
        for j, word in enumerate(words):
            # Clean word for the mark name (alphanumeric only)
            clean = re.sub(r'[^a-zA-Z0-9]', '', word)
            if not clean:
                ssml_parts.append(word)
                continue

            # Add <mark> tag for timestamp
            word_idx = sum(
                len(s.split()) for s in sentences[:i]
            ) + j
            mark_name = f"w{word_idx}_{clean}"
            ssml_parts.append(f'<mark name="{mark_name}"/>')

            # Add emphasis for hook or power words
            lower = clean.lower()
            if is_hook and j == 0:
                ssml_parts.append(
                    f'<emphasis level="strong">{word}</emphasis>'
                )
            elif lower in _POWER_WORDS:
                ssml_parts.append(
                    f'<emphasis level="moderate">{word}</emphasis>'
                )
            else:
                ssml_parts.append(word)

            ssml_parts.append(' ')

    ssml_parts.append('</prosody>')
    ssml_parts.append('</speak>')

    result = ''.join(ssml_parts)
    logger.debug(
        "SSML built",
        extra={"extra_data": {
            "sentence_count": len(sentences),
            "ssml_length": len(result),
        }},
    )
    return result


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences preserving punctuation.

    Args:
        text: Plain narration text.

    Returns:
        List of sentence strings.
    """
    # Split on sentence-ending punctuation followed by space or end
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in parts if s.strip()]
