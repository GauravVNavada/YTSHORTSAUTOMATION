"""
Audio Agent — orchestrates TTS generation and audio mixing.

Pipeline:
    1. Build SSML from narration + genre config
    2. Call TTS service → get audio bytes + word timestamps
    3. Save raw narration WAV
    4. Mix with music + SFX (basic version — ducking in v2)
    5. Return AudioBundle

Follows agent isolation rules:
    - Input/output are Pydantic models
    - TTSService is dependency-injected
    - Never imports other agents
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
    AudioBundle,
    GenreConfig,
    WordTimestamp,
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
        self,
        narration: str,
        genre_config: GenreConfig,
        job_id: str,
        hook_line: str = "",
        sfx_paths: Optional[list[str]] = None,
        music_path: Optional[str] = None,
    ) -> AudioBundle:
        """Generate complete audio for a video.

        Args:
            narration: Plain text narration from ScriptOutput.
            genre_config: Genre-specific TTS settings.
            job_id: Unique job identifier for file naming.
            hook_line: The hook sentence for emphasis.
            sfx_paths: Optional SFX file paths to mix in.
            music_path: Optional background music file path.

        Returns:
            AudioBundle with paths and timestamps.

        Raises:
            TTSError: If TTS generation fails.
            AudioMixError: If audio mixing fails.
        """
        audio_dir = config.data_dir / "audio" / job_id
        audio_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: Build SSML
        ssml = build_ssml(narration, genre_config, hook_line)
        logger.info(
            "SSML built for TTS",
            extra={"extra_data": {"job_id": job_id}},
        )

        # Step 2: Call TTS with retry
        audio_bytes, timestamps = await self._tts_with_retry(
            ssml, genre_config
        )

        # Step 3: Save raw narration WAV
        narration_path = audio_dir / "narration.wav"
        _save_wav(audio_bytes, narration_path)
        logger.info(
            "Narration audio saved",
            extra={"extra_data": {
                "path": str(narration_path),
                "bytes": len(audio_bytes),
                "timestamps": len(timestamps),
            }},
        )

        # Step 4: Calculate duration
        duration_ms = _get_wav_duration_ms(audio_bytes)

        # Step 5: Mix audio (basic — just copy narration for now)
        final_path = audio_dir / "final_audio.wav"
        if music_path and Path(music_path).exists():
            await self._mix_audio(
                narration_path, music_path, sfx_paths or [],
                final_path, duration_ms,
            )
        else:
            # No music — narration only
            _save_wav(audio_bytes, final_path)
            logger.info("No music provided, using narration only")

        return AudioBundle(
            audio_path=str(final_path),
            narration_path=str(narration_path),
            duration_ms=duration_ms,
            word_timestamps=timestamps,
        )

    async def _tts_with_retry(
        self, ssml: str, genre_config: GenreConfig
    ) -> tuple[bytes, list[WordTimestamp]]:
        """Call TTS with retry logic.

        Args:
            ssml: SSML-formatted text.
            genre_config: Genre TTS settings.

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

    async def _mix_audio(
        self,
        narration_path: Path,
        music_path: str,
        sfx_paths: list[str],
        output_path: Path,
        duration_ms: int,
    ) -> None:
        """Mix narration with background music and SFX.

        Uses pydub for audio manipulation. Background music is lowered
        to -18dB relative to narration (basic ducking).

        Args:
            narration_path: Path to narration WAV.
            music_path: Path to background music file.
            sfx_paths: List of SFX file paths.
            output_path: Path to write final mixed WAV.
            duration_ms: Target duration in milliseconds.

        Raises:
            AudioMixError: If mixing fails.
        """
        try:
            from pydub import AudioSegment

            narration = AudioSegment.from_wav(str(narration_path))

            # Load and prepare background music
            music = AudioSegment.from_file(music_path)
            # Loop/trim music to match narration length
            if len(music) < len(narration):
                loops = (len(narration) // len(music)) + 1
                music = music * loops
            music = music[:len(narration)]
            # Duck music volume (-18dB relative to narration)
            music = music - 18

            # Mix narration + music
            mixed = narration.overlay(music)

            # Export final audio
            mixed.export(str(output_path), format="wav")
            logger.info(
                "Audio mixed successfully",
                extra={"extra_data": {
                    "duration_ms": len(mixed),
                    "has_music": True,
                }},
            )

        except Exception as exc:
            raise AudioMixError(
                f"Audio mixing failed: {exc}",
                details=str(exc),
            )


# ─── Helpers ───────────────────────────────────────────

def _save_wav(audio_bytes: bytes, path: Path) -> None:
    """Save raw audio bytes to a WAV file.

    Args:
        audio_bytes: Raw audio content from TTS.
        path: Path to save the WAV file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(audio_bytes)


def _get_wav_duration_ms(audio_bytes: bytes) -> int:
    """Calculate the duration of a WAV file in milliseconds.

    Args:
        audio_bytes: Raw WAV audio bytes.

    Returns:
        Duration in milliseconds.
    """
    try:
        buf = io.BytesIO(audio_bytes)
        with wave.open(buf, "rb") as w:
            frames = w.getnframes()
            rate = w.getframerate()
            return int((frames / rate) * 1000)
    except Exception:
        # Fallback: assume ~24KB per second for 24kHz 16-bit mono
        estimated = int(len(audio_bytes) / 48.0)
        return max(estimated, 1000)  # At least 1 second
