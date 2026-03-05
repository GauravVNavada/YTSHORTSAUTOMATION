"""
Audio Agent — orchestrates TTS generation and audio mixing.

Pipeline per MASTER_BLUEPRINT §7:
    1. Build SSML from narration + genre config
    2. Call TTS service → get audio bytes + word timestamps
    3. Save raw narration WAV
    4. Select best music segment (librosa RMS energy)
    5. Mix: narration + music (-14dB ducked) + SFX (-8dB pre-lap 200ms)
    6. LUFS normalize to -14
    7. Return AudioBundle
"""
import asyncio
import io
import wave
from pathlib import Path
from typing import Optional

from backend.agents.ssml_builder import build_ssml
from backend.core.config import config
from backend.core.exceptions import TTSError, AudioMixError
from backend.core.logger import get_logger
from backend.core.models import (
    AudioBundle, GenreConfig, WordTimestamp,
)
from backend.services.audio_utils import (
    mix_audio_tracks, select_music_segment,
)

logger = get_logger(__name__)

_MAX_RETRIES = 2


class AudioAgent:
    """Generates narration audio and mixes the final audio track.

    Args:
        tts_service: Injected TTS service for synthesis.
    """

    def __init__(self, tts_service):
        self._tts = tts_service

    async def generate(
        self, narration: str, genre_config: GenreConfig,
        job_id: str, hook_line: str = "",
        sfx_paths: Optional[list[str]] = None,
        sfx_timings_ms: Optional[list[int]] = None,
        music_path: Optional[str] = None,
    ) -> AudioBundle:
        """Generate complete audio for a video.

        Args:
            narration: Plain text narration from ScriptOutput.
            genre_config: Genre-specific TTS settings.
            job_id: Unique job identifier.
            hook_line: Hook sentence for emphasis.
            sfx_paths: SFX file paths to mix in.
            sfx_timings_ms: Placement times for each SFX (ms).
            music_path: Background music file path.

        Returns:
            AudioBundle with paths and timestamps.
        """
        audio_dir = config.data_dir / "audio" / job_id
        audio_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: Build SSML
        ssml = build_ssml(narration, genre_config, hook_line)
        logger.info("SSML built", extra={"extra_data": {"job_id": job_id}})

        # Step 2: Call TTS with retry
        audio_bytes, timestamps = await self._tts_with_retry(
            ssml, genre_config,
        )

        # Step 3: Save raw narration WAV
        narration_path = audio_dir / "narration.wav"
        _save_wav(audio_bytes, narration_path)

        # Step 4: Calculate duration
        duration_ms = _get_wav_duration_ms(audio_bytes)

        # Step 5: Select best music segment (librosa energy)
        prepared_music = None
        if music_path and Path(music_path).exists():
            prepared_music = select_music_segment(music_path, duration_ms)

        # Step 6: Mix audio with frequency-aware ducking
        final_path = audio_dir / "final_audio.wav"
        mix_audio_tracks(
            narration_path=str(narration_path),
            music_path=prepared_music,
            sfx_paths=sfx_paths or [],
            sfx_timings_ms=sfx_timings_ms or [],
            output_path=str(final_path),
            duration_ms=duration_ms,
        )

        logger.info("Audio pipeline complete", extra={"extra_data": {
            "job_id": job_id, "duration_ms": duration_ms,
            "has_music": prepared_music is not None,
            "sfx_count": len(sfx_paths or []),
        }})

        return AudioBundle(
            audio_path=str(final_path),
            narration_path=str(narration_path),
            duration_ms=duration_ms,
            word_timestamps=timestamps,
        )

    async def _tts_with_retry(
        self, ssml: str, genre_config: GenreConfig,
    ) -> tuple[bytes, list[WordTimestamp]]:
        """Call TTS with retry logic.

        Returns:
            Tuple of (audio_bytes, word_timestamps).

        Raises:
            TTSError: If all retries fail.
        """
        last_error = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return await self._tts.synthesize(
                    ssml=ssml,
                    voice_name=genre_config.tts_voice,
                    speaking_rate=genre_config.tts_rate,
                    pitch=genre_config.tts_pitch,
                )
            except TTSError as exc:
                last_error = exc
                logger.warning(
                    f"TTS attempt {attempt} failed: {exc.message}",
                    extra={"extra_data": {"attempt": attempt}},
                )
        raise TTSError(
            f"TTS failed after {_MAX_RETRIES} attempts",
            details=str(last_error),
        )


# ─── Helpers ───────────────────────────────────────────

def _save_wav(audio_bytes: bytes, path: Path) -> None:
    """Save raw audio bytes to a WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(audio_bytes)


def _get_wav_duration_ms(audio_bytes: bytes) -> int:
    """Calculate WAV file duration in milliseconds."""
    try:
        buf = io.BytesIO(audio_bytes)
        with wave.open(buf, "rb") as w:
            frames = w.getnframes()
            rate = w.getframerate()
            return int((frames / rate) * 1000)
    except Exception:
        estimated = int(len(audio_bytes) / 48.0)
        return max(estimated, 1000)
