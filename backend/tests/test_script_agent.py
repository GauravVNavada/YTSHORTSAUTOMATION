"""
Tests for script_agent.py — script generation and validation.

Uses mock LLM services (no real API calls).
"""
import json
import pytest
import pytest_asyncio

from backend.agents.script_agent import ScriptAgent, _safe_parse_json
from backend.core.cache_manager import CacheManager
from backend.core.models import GenreConfig, ScriptOutput
from backend.core.exceptions import ScriptGenerationError


# ─── Mock LLM Services ────────────────────────────────

def _make_valid_script_json() -> str:
    """Return a valid script JSON string for testing."""
    return json.dumps({
        "title": "This Family Found A Sealed Room 😨",
        "narration": (
            "Did you know that in 1973, a family in Connecticut bought their "
            "dream home, only to discover that the previous owner had sealed "
            "an entire room behind a brick wall? When construction workers "
            "finally broke through, they found a child's bedroom that hadn't "
            "been touched in 40 years. The bed was still made. Toys were "
            "still on the floor. And on the wall, someone had scratched the "
            "words 'she can hear you' over and over again. The family moved "
            "out three days later. To this day, no one knows who the room "
            "belonged to. And the house? It's still for sale."
        ),
        "hook_line": "Did you know that in 1973, a family in Connecticut?",
        "word_count": 108,
        "estimated_duration": 52,
        "description": "Would you stay? 😱",
        "hashtags": ["#shorts", "#scary", "#horror"],
        "image_cues": [
            {"keyword": "old house dark", "timestamp_hint": "at start", "mood": "eerie"},
            {"keyword": "brick wall", "timestamp_hint": "after line 2", "mood": "dark"},
            {"keyword": "child bedroom", "timestamp_hint": "after line 3", "mood": "unsettling"},
            {"keyword": "scratched wall", "timestamp_hint": "at twist", "mood": "horror"},
            {"keyword": "for sale sign", "timestamp_hint": "at ending", "mood": "ominous"},
        ],
        "sfx_cues": [
            {"trigger_word": "sealed", "sfx_type": "door_creak", "timestamp_hint": "during word"},
        ],
    })


def _make_valid_validation_json() -> str:
    """Return a passing validation JSON."""
    return json.dumps({
        "hook_score": 9,
        "pacing_score": 8,
        "emotional_arc_score": 9,
        "authenticity_score": 9,
        "ending_score": 8,
        "shareability_score": 8,
        "overall_score": 8.5,
        "passed": True,
        "feedback": "Strong script with great escalation.",
        "issues": [],
    })


def _make_failing_validation_json() -> str:
    """Return a failing validation JSON."""
    return json.dumps({
        "hook_score": 4,
        "pacing_score": 5,
        "emotional_arc_score": 3,
        "authenticity_score": 4,
        "ending_score": 3,
        "shareability_score": 4,
        "overall_score": 3.8,
        "passed": False,
        "feedback": "Hook is generic, no emotional arc.",
        "issues": ["Generic opening", "Lacks tension"],
    })


class MockGemini:
    """Mock Gemini service that returns preset responses."""

    def __init__(self, responses=None):
        self.responses = responses or [_make_valid_script_json()]
        self.call_count = 0

    async def __call__(self, system_prompt, user_prompt):
        """Return next response in the list."""
        idx = min(self.call_count, len(self.responses) - 1)
        self.call_count += 1
        return self.responses[idx]


class MockGroq:
    """Mock Groq service that returns preset validation results."""

    def __init__(self, responses=None):
        self.responses = responses or [_make_valid_validation_json()]
        self.call_count = 0

    async def __call__(self, system_prompt, user_prompt):
        """Return next response in the list."""
        idx = min(self.call_count, len(self.responses) - 1)
        self.call_count += 1
        return self.responses[idx]


@pytest_asyncio.fixture
async def cache(tmp_path):
    """Create a fresh cache with sample genre data."""
    mgr = CacheManager(db_path=tmp_path / "test.db")
    await mgr.initialize()
    await mgr.store_genre_configs([
        GenreConfig(
            genre_id="scary_stories",
            tts_voice="en-US-Neural2-D",
            tts_rate=0.88,
            tts_pitch=-2.0,
            layout="split_screen",
            caption_preset="horror_red",
            music_mood="dark_ambient",
        ),
    ])
    await mgr.store_reference_scripts(
        "scary_stories", "Genre 2",
        [{"full script / transcript": "You wake up at 3 AM...",
          "score: overall": "8"}],
    )
    # Mock get_recent_scripts to return [] — these tests
    # exercise generation + validation, not dedup.
    # Dedup is tested separately in test_script_dedup.
    async def _empty_recent(*args, **kwargs):
        return []
    mgr.get_recent_scripts = _empty_recent
    yield mgr
    await mgr.close()


# ─── JSON Parsing Tests ───────────────────────────────

def test_safe_parse_valid_json():
    """Should parse clean JSON."""
    result = _safe_parse_json('{"key": "value"}')
    assert result == {"key": "value"}


def test_safe_parse_json_with_code_fences():
    """Should strip markdown code fences."""
    text = '```json\n{"key": "value"}\n```'
    result = _safe_parse_json(text)
    assert result == {"key": "value"}


def test_safe_parse_invalid_json():
    """Should return empty dict for invalid JSON."""
    result = _safe_parse_json("not json at all")
    assert result == {}


def test_safe_parse_empty_string():
    """Should return empty dict for empty input."""
    result = _safe_parse_json("")
    assert result == {}


def test_safe_parse_json_embedded_in_text():
    """Should extract JSON from surrounding text."""
    text = 'Here is the result:\n{"key": "value"}\nEnd.'
    result = _safe_parse_json(text)
    assert result == {"key": "value"}


# ─── Script Generation Tests ──────────────────────────

@pytest.mark.asyncio
async def test_generate_success(cache):
    """Should generate a valid script on first attempt."""
    agent = ScriptAgent(
        gemini_service=MockGemini(),
        groq_service=MockGroq(),
        cache=cache,
    )
    result = await agent.generate("scary_stories")
    assert isinstance(result, ScriptOutput)
    assert result.word_count > 0
    assert len(result.image_cues) >= 3


@pytest.mark.asyncio
async def test_generate_retries_on_validation_fail(cache):
    """Should retry when Groq validation fails."""
    agent = ScriptAgent(
        gemini_service=MockGemini(
            responses=[_make_valid_script_json()] * 3
        ),
        groq_service=MockGroq(
            responses=[
                _make_failing_validation_json(),  # Fail 1st
                _make_valid_validation_json(),     # Pass 2nd
            ]
        ),
        cache=cache,
    )
    result = await agent.generate("scary_stories")
    assert isinstance(result, ScriptOutput)
    assert agent._gemini.call_count == 2


@pytest.mark.asyncio
async def test_generate_fails_after_max_retries(cache):
    """Should raise after all retries exhausted."""
    agent = ScriptAgent(
        gemini_service=MockGemini(
            responses=[_make_valid_script_json()] * 5
        ),
        groq_service=MockGroq(
            responses=[_make_failing_validation_json()] * 5
        ),
        cache=cache,
    )
    with pytest.raises(ScriptGenerationError):
        await agent.generate("scary_stories")


@pytest.mark.asyncio
async def test_generate_with_custom_topic(cache):
    """Should accept custom topic without error."""
    agent = ScriptAgent(
        gemini_service=MockGemini(),
        groq_service=MockGroq(),
        cache=cache,
    )
    result = await agent.generate(
        "scary_stories",
        mode="custom",
        custom_topic="A haunted lighthouse",
    )
    assert isinstance(result, ScriptOutput)


# ─── Rule Validation Tests ────────────────────────────

@pytest.mark.asyncio
async def test_banned_phrases_detected(cache):
    """Should reject scripts with banned phrases."""
    bad_script = _make_valid_script_json()
    data = json.loads(bad_script)
    data["narration"] = "Hey guys, scientists say this is scary."
    bad_script = json.dumps(data)

    agent = ScriptAgent(
        gemini_service=MockGemini(responses=[bad_script] * 5),
        groq_service=MockGroq(),
        cache=cache,
    )
    with pytest.raises(ScriptGenerationError):
        await agent.generate("scary_stories")
