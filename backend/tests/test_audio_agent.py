"""
Tests for the Audio Agent — SSML builder, TTS, and audio generation.

Uses mock TTS service (no real API calls per testing rules).
"""
import pytest
import pytest_asyncio

from backend.agents.ssml_builder import build_ssml, _split_sentences
from backend.agents.audio_agent import AudioAgent, _get_wav_duration_ms
from backend.core.models import GenreConfig, AudioBundle, WordTimestamp


# ─── SSML Builder Tests ───────────────────────────────

def test_ssml_wraps_in_speak_tags():
    """SSML output must start with <speak> and end with </speak>."""
    ssml = build_ssml("Hello world.")
    assert ssml.startswith("<speak>")
    assert ssml.endswith("</speak>")


def test_ssml_contains_mark_tags():
    """Every word should get a <mark> tag for timestamp extraction."""
    ssml = build_ssml("Did you know that cats are amazing.")
    assert "<mark name=" in ssml
    # Should have multiple mark tags
    mark_count = ssml.count("<mark name=")
    assert mark_count >= 5


def test_ssml_contains_prosody():
    """SSML should include prosody tags for rate/pitch control."""
    ssml = build_ssml("Hello world.")
    assert "<prosody" in ssml


def test_ssml_genre_specific_prosody():
    """Genre config should influence prosody settings."""
    scary_config = GenreConfig(
        genre_id="scary",
        tts_rate=0.88,
        tts_pitch=-2.0,
        music_mood="dark_ambient",
    )
    ssml = build_ssml("A dark story unfolds.", scary_config)
    assert 'rate="0.88"' in ssml
    assert 'pitch="-2.0st"' in ssml


def test_ssml_break_between_sentences():
    """Should add <break> tags between sentences."""
    ssml = build_ssml("First sentence. Second sentence.")
    assert "<break time=" in ssml


def test_ssml_emphasis_on_power_words():
    """Power words like 'dead' should get emphasis."""
    ssml = build_ssml("He was found dead in the room.")
    assert "<emphasis" in ssml
    assert "dead" in ssml


def test_ssml_hook_emphasis():
    """Hook line's first word should get strong emphasis."""
    ssml = build_ssml(
        "Did you know this? No one expected it.",
        hook_line="Did you know this?",
    )
    assert 'level="strong"' in ssml


def test_ssml_empty_text():
    """Empty narration should return empty SSML."""
    ssml = build_ssml("")
    assert ssml == "<speak></speak>"


# ─── Sentence Splitting Tests ─────────────────────────

def test_split_sentences_basic():
    """Should split on periods, exclamation marks, question marks."""
    result = _split_sentences("Hello. World! How? Fine.")
    assert len(result) == 4


def test_split_sentences_single():
    """Single sentence should return one item."""
    result = _split_sentences("Just one sentence.")
    assert len(result) == 1
    assert result[0] == "Just one sentence."


def test_split_sentences_empty():
    """Empty string should return empty list."""
    result = _split_sentences("")
    assert result == []


# ─── Mock TTS Service ─────────────────────────────────

class MockTTSService:
    """Mock TTS service that returns fake WAV audio."""

    def __init__(self):
        self.call_count = 0

    async def synthesize(
        self, ssml, voice_name="", speaking_rate=1.0, pitch=0.0
    ):
        """Return fake audio bytes and timestamps."""
        self.call_count += 1
        # Create a minimal valid WAV file (44-byte header + silence)
        import struct
        sample_rate = 24000
        num_samples = sample_rate * 3  # 3 seconds
        data_size = num_samples * 2  # 16-bit = 2 bytes
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + data_size, b"WAVE",
            b"fmt ", 16, 1, 1,  # PCM, mono
            sample_rate, sample_rate * 2, 2, 16,  # 24kHz, 16-bit
            b"data", data_size,
        )
        audio = header + b"\x00" * data_size

        timestamps = [
            WordTimestamp(word="hello", start_ms=0, end_ms=500),
            WordTimestamp(word="world", start_ms=500, end_ms=1000),
        ]
        return audio, timestamps


class FailTTSService:
    """Mock TTS service that always fails."""

    async def synthesize(self, ssml, **kwargs):
        """Always raises TTSError."""
        from backend.core.exceptions import TTSError
        raise TTSError("Mock TTS failure")


# ─── Audio Agent Tests ─────────────────────────────────

@pytest.mark.asyncio
async def test_generate_returns_audio_bundle(tmp_path, monkeypatch):
    """Audio agent should return a valid AudioBundle."""
    monkeypatch.setattr(
        "backend.agents.audio_agent.config",
        type("Config", (), {"data_dir": tmp_path})(),
    )
    agent = AudioAgent(tts_service=MockTTSService())
    genre = GenreConfig(genre_id="scary_stories")

    result = await agent.generate(
        narration="Hello world. This is a test.",
        genre_config=genre,
        job_id="test_job_001",
    )
    assert isinstance(result, AudioBundle)
    assert result.duration_ms > 0
    assert len(result.word_timestamps) == 2


@pytest.mark.asyncio
async def test_narration_file_created(tmp_path, monkeypatch):
    """Should save narration.wav to the audio directory."""
    monkeypatch.setattr(
        "backend.agents.audio_agent.config",
        type("Config", (), {"data_dir": tmp_path})(),
    )
    agent = AudioAgent(tts_service=MockTTSService())
    genre = GenreConfig(genre_id="test")

    result = await agent.generate(
        narration="Test narration.",
        genre_config=genre,
        job_id="test_job_002",
    )
    from pathlib import Path
    assert Path(result.narration_path).exists()
    assert Path(result.audio_path).exists()


@pytest.mark.asyncio
async def test_tts_retry_on_failure(tmp_path, monkeypatch):
    """Should raise after all TTS retries fail."""
    monkeypatch.setattr(
        "backend.agents.audio_agent.config",
        type("Config", (), {"data_dir": tmp_path})(),
    )
    agent = AudioAgent(tts_service=FailTTSService())
    genre = GenreConfig(genre_id="test")

    from backend.core.exceptions import TTSError
    with pytest.raises(TTSError):
        await agent.generate(
            narration="This will fail.",
            genre_config=genre,
            job_id="test_job_003",
        )


# ─── WAV Duration Helper Tests ────────────────────────

def test_wav_duration_from_valid_wav():
    """Should calculate correct duration from WAV header."""
    import struct
    sample_rate = 24000
    num_samples = sample_rate * 2  # 2 seconds
    data_size = num_samples * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, 1,
        sample_rate, sample_rate * 2, 2, 16,
        b"data", data_size,
    )
    audio = header + b"\x00" * data_size
    duration = _get_wav_duration_ms(audio)
    assert abs(duration - 2000) < 10  # Should be ~2000ms


def test_wav_duration_fallback():
    """Should use fallback estimate for invalid data."""
    duration = _get_wav_duration_ms(b"not a wav file")
    assert duration > 0  # Should return a positive estimate
