"""
Google Cloud Text-to-Speech service wrapper.

Uses a service account key for authentication. Supports both plain text
and SSML input. Returns audio bytes and word-level timestamps via
SSML <mark> tags and timepoint data.
"""
import asyncio
from pathlib import Path
from typing import Optional

from backend.core.config import config
from backend.core.exceptions import TTSError, AuthError
from backend.core.logger import get_logger
from backend.core.models import WordTimestamp

logger = get_logger(__name__)


class TTSService:
    """Wrapper for Google Cloud Text-to-Speech API.

    Uses service account authentication (not user API key).

    Args:
        key_path: Path to the TTS service account JSON key file.
    """

    def __init__(self, key_path: Optional[str] = None):
        self._key_path = key_path or config.tts_key_path
        self._client = None

    def _ensure_client(self) -> None:
        """Lazily initialize the TTS client."""
        if self._client is not None:
            return
        resolved = config.base_dir / self._key_path
        if not resolved.exists():
            raise AuthError(
                f"TTS service account key not found: {resolved}",
                details="Add your TTS key file to the project root",
            )
        try:
            from google.cloud import texttospeech
            self._client = texttospeech.TextToSpeechClient.from_service_account_json(
                str(resolved)
            )
        except Exception as exc:
            raise AuthError(
                f"Failed to initialize TTS client: {exc}",
                details=str(exc),
            )

    async def synthesize(
        self,
        ssml: str,
        voice_name: str = "en-US-Neural2-D",
        speaking_rate: float = 0.95,
        pitch: float = 0.0,
    ) -> tuple[bytes, list[WordTimestamp]]:
        """Synthesize speech from SSML input.

        Args:
            ssml: SSML-formatted text with <mark> tags.
            voice_name: Google TTS voice name.
            speaking_rate: Speech rate (0.25 to 4.0).
            pitch: Pitch adjustment in semitones (-20 to 20).

        Returns:
            Tuple of (audio_bytes, word_timestamps).

        Raises:
            TTSError: If the API call fails.
        """
        self._ensure_client()
        try:
            from google.cloud import texttospeech
            result = await asyncio.to_thread(
                self._synthesize_sync,
                ssml, voice_name, speaking_rate, pitch,
            )
            return result
        except TTSError:
            raise
        except Exception as exc:
            raise TTSError(
                f"TTS synthesis failed: {exc}",
                details=str(exc),
            )

    def _synthesize_sync(
        self,
        ssml: str,
        voice_name: str,
        speaking_rate: float,
        pitch: float,
    ) -> tuple[bytes, list[WordTimestamp]]:
        """Synchronous TTS call (run via asyncio.to_thread).

        Returns:
            Tuple of (audio_bytes, word_timestamps).
        """
        from google.cloud import texttospeech

        synthesis_input = texttospeech.SynthesisInput(ssml=ssml)
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_name[:5],  # e.g. "en-US"
            name=voice_name,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            speaking_rate=speaking_rate,
            pitch=pitch,
            sample_rate_hertz=24000,
            effects_profile_id=["headphone-class-device"],
        )

        try:
            response = self._client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )
        except Exception as exc:
            raise TTSError(
                f"Google TTS API error: {exc}",
                details=str(exc),
            )

        # Generate estimated word timestamps from audio duration
        # (enable_time_pointing was removed in google-cloud-texttospeech v2.24)
        timestamps = _estimate_timestamps(ssml, response.audio_content)

        logger.info(
            "TTS synthesis complete",
            extra={"extra_data": {
                "voice": voice_name,
                "audio_bytes": len(response.audio_content),
                "timepoints": len(timestamps),
            }},
        )
        return response.audio_content, timestamps


def _estimate_timestamps(ssml: str, audio_bytes: bytes) -> list[WordTimestamp]:
    """Estimate word timestamps by distributing words evenly across audio duration.

    Args:
        ssml: The SSML text that was synthesized.
        audio_bytes: The resulting audio bytes (WAV format).

    Returns:
        List of estimated WordTimestamp models.
    """
    import re
    import io
    import wave

    # Strip SSML tags to get plain text
    plain_text = re.sub(r"<[^>]+>", " ", ssml)
    words = plain_text.split()
    words = [w for w in words if w.strip()]

    if not words:
        return []

    # Calculate audio duration from WAV bytes
    try:
        buf = io.BytesIO(audio_bytes)
        with wave.open(buf, "rb") as w:
            frames = w.getnframes()
            rate = w.getframerate()
            duration_ms = int((frames / rate) * 1000)
    except Exception:
        # Estimate from byte size if WAV parsing fails  
        duration_ms = max(int(len(audio_bytes) / 48.0), 1000)

    # Distribute words evenly across the duration
    word_duration_ms = duration_ms // len(words) if words else 300
    stamps = []
    for i, word in enumerate(words):
        start_ms = i * word_duration_ms
        end_ms = start_ms + word_duration_ms
        stamps.append(WordTimestamp(
            word=word,
            start_ms=start_ms,
            end_ms=min(end_ms, duration_ms),
        ))
    return stamps
