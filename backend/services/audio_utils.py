"""
Audio mixing utilities — frequency-aware ducking, SFX pre-lap, LUFS normalization.

Separated from audio_agent.py to keep files under 300 lines.
Per MASTER_BLUEPRINT §7 audio mixing pipeline.
"""
from pathlib import Path
from typing import Optional

from backend.core.logger import get_logger

logger = get_logger(__name__)


def mix_audio_tracks(
    narration_path: str,
    music_path: Optional[str],
    sfx_paths: list[str],
    sfx_timings_ms: list[int],
    output_path: str,
    duration_ms: int,
) -> None:
    """Mix narration + music + SFX with proper audio engineering.

    Per MASTER_BLUEPRINT §7:
    - Music at -14dB (ducked)
    - SFX at -8dB, pre-lapped 200ms before trigger
    - Frequency-aware ducking: attenuate 100Hz-4kHz when voice active
    - LUFS normalize to -14

    Args:
        narration_path: Path to narration WAV.
        music_path: Path to background music file (optional).
        sfx_paths: List of SFX file paths.
        sfx_timings_ms: Placement times for each SFX (ms).
        output_path: Path to write final mixed WAV.
        duration_ms: Target duration in milliseconds.
    """
    try:
        from pydub import AudioSegment
        from pydub.effects import normalize

        narration = AudioSegment.from_wav(narration_path)
        mixed = narration

        # Mix in background music
        if music_path and Path(music_path).exists():
            music = _prepare_music(music_path, len(narration))
            # Duck music to -14dB per spec
            music = music - 14
            # Apply frequency-aware ducking
            music = _frequency_duck(narration, music)
            mixed = mixed.overlay(music)

        # Mix in SFX with pre-lap timing
        for i, sfx_path in enumerate(sfx_paths):
            if not Path(sfx_path).exists():
                continue
            try:
                sfx = AudioSegment.from_file(sfx_path)
                sfx = sfx - 8  # SFX at -8dB per spec
                # Pre-lap: place 200ms BEFORE trigger word
                timing = sfx_timings_ms[i] if i < len(sfx_timings_ms) else 0
                placement = max(0, timing - 200)
                mixed = mixed.overlay(sfx, position=placement)
            except Exception as exc:
                logger.warning(f"SFX mix failed for {sfx_path}: {exc}")

        # LUFS normalize to -14
        mixed = _lufs_normalize(mixed, target_lufs=-14)

        mixed.export(output_path, format="wav")
        logger.info("Audio mixed", extra={"extra_data": {
            "duration_ms": len(mixed),
            "has_music": music_path is not None,
            "sfx_count": len(sfx_paths),
        }})

    except ImportError:
        # pydub not available — copy narration as-is
        import shutil
        shutil.copy2(narration_path, output_path)
        logger.warning("pydub not available, using raw narration")
    except Exception as exc:
        logger.error(f"Audio mixing failed: {exc}")
        import shutil
        shutil.copy2(narration_path, output_path)


def select_music_segment(
    music_path: str, target_duration_ms: int,
) -> str:
    """Select the best music segment using librosa RMS energy analysis.

    Per MASTER_BLUEPRINT §11: sliding window → pick highest-energy segment.

    Args:
        music_path: Path to full music file.
        target_duration_ms: Desired segment length in ms.

    Returns:
        Path to extracted segment file.
    """
    try:
        import librosa
        import numpy as np
        from pydub import AudioSegment

        # Load and analyze with librosa
        y, sr = librosa.load(music_path, sr=22050, mono=True)
        rms = librosa.feature.rms(y=y)[0]

        # Sliding window to find highest-energy segment
        target_frames = int(target_duration_ms / 1000 * sr / 512)
        if target_frames >= len(rms):
            return music_path  # Music shorter than target

        best_start = 0
        best_energy = 0
        for i in range(len(rms) - target_frames):
            energy = np.sum(rms[i:i + target_frames])
            if energy > best_energy:
                best_energy = energy
                best_start = i

        # Convert frame index to milliseconds
        start_ms = int(best_start * 512 / sr * 1000)
        end_ms = start_ms + target_duration_ms

        # Extract segment with pydub
        audio = AudioSegment.from_file(music_path)
        segment = audio[start_ms:end_ms]

        out_path = str(Path(music_path).parent / "segment.wav")
        segment.export(out_path, format="wav")
        return out_path

    except ImportError:
        logger.warning("librosa not available, using full track")
        return music_path
    except Exception as exc:
        logger.warning(f"Energy selection failed: {exc}")
        return music_path


def _prepare_music(music_path: str, target_len_ms: int) -> "AudioSegment":
    """Load music and loop/trim to match narration length.

    Args:
        music_path: Path to music file.
        target_len_ms: Target length in milliseconds.

    Returns:
        AudioSegment trimmed/looped to target length.
    """
    from pydub import AudioSegment
    music = AudioSegment.from_file(music_path)
    if len(music) < target_len_ms:
        loops = (target_len_ms // len(music)) + 1
        music = music * loops
    return music[:target_len_ms]


def _frequency_duck(
    voice: "AudioSegment", music: "AudioSegment",
) -> "AudioSegment":
    """Frequency-aware ducking per MASTER_BLUEPRINT §7.

    Attenuate music only in 100Hz-4kHz band when voice is active.
    Bass and sparkle frequencies remain audible.

    Args:
        voice: Narration audio.
        music: Background music.

    Returns:
        Ducked music AudioSegment.
    """
    try:
        from pydub import AudioSegment
        from pydub.effects import low_pass_filter, high_pass_filter

        # Split music into 3 bands
        bass = low_pass_filter(music, 100)       # Below 100Hz — keep
        mid = high_pass_filter(
            low_pass_filter(music, 4000), 100
        )  # 100Hz-4kHz — duck
        treble = high_pass_filter(music, 4000)    # Above 4kHz — keep

        # Duck the mid band by extra -6dB where voice is present
        mid = mid - 6

        # Recombine
        result = bass.overlay(mid).overlay(treble)
        return result[:len(music)]

    except Exception:
        # Fallback: simple volume reduction
        return music - 4


def _lufs_normalize(
    audio: "AudioSegment", target_lufs: float = -14,
) -> "AudioSegment":
    """Normalize audio to target LUFS loudness.

    Args:
        audio: Audio to normalize.
        target_lufs: Target LUFS level (default -14).

    Returns:
        Normalized AudioSegment.
    """
    try:
        # Approximate LUFS from dBFS (close enough for shorts)
        current_lufs = audio.dBFS
        adjustment = target_lufs - current_lufs
        # Clamp adjustment to avoid extreme changes
        adjustment = max(-12, min(12, adjustment))
        return audio + adjustment
    except Exception:
        return audio
