"""
Shared test fixtures for all tests.
Provides mock data and configured test clients.
"""
import pytest
from backend.core.models import (
    Genre, GenreConfig, ScriptOutput, ImageCue, SfxCue,
    GenerateRequest, GenreMode,
)


@pytest.fixture
def sample_genre():
    """A sample genre for testing."""
    return Genre(
        genre_id="scary_stories",
        display_name="Scary Stories & Mysteries",
        icon="👻",
        difficulty="Easy",
        is_active=True,
    )


@pytest.fixture
def sample_genre_config():
    """A sample genre config for testing."""
    return GenreConfig(
        genre_id="scary_stories",
        tts_voice="en-US-Neural2-D",
        tts_rate=0.88,
        tts_pitch=-2.0,
        layout="split_screen",
        caption_preset="horror_red",
        music_mood="dark_ambient",
    )


@pytest.fixture
def sample_script_output():
    """A valid ScriptOutput for testing downstream agents."""
    return ScriptOutput(
        title="This Family Found A Sealed Room 😨",
        narration=(
            "Did you know that in 1973, a family in Connecticut bought their "
            "dream home, only to discover that the previous owner had sealed "
            "an entire room behind a brick wall? When construction workers "
            "finally broke through, they found a child's bedroom that hadn't "
            "been touched in 40 years. The bed was still made. Toys were still "
            "on the floor. And on the wall, someone had scratched the words "
            "'she can hear you' over and over again. The family moved out "
            "three days later. To this day, no one knows who the room "
            "belonged to. And the house? It's still for sale."
        ),
        word_count=108,
        estimated_duration=52,
        hook_line="Did you know that in 1973, a family in Connecticut bought their dream home?",
        image_cues=[
            ImageCue(keyword="old house exterior dark", timestamp_hint="at start", mood="eerie"),
            ImageCue(keyword="brick wall sealed room", timestamp_hint="after line 2", mood="dark"),
            ImageCue(keyword="abandoned child bedroom toys", timestamp_hint="after line 3", mood="unsettling"),
            ImageCue(keyword="scratched wall writing", timestamp_hint="at twist", mood="horror"),
            ImageCue(keyword="for sale sign house", timestamp_hint="at ending", mood="ominous"),
        ],
        sfx_cues=[
            SfxCue(trigger_word="sealed", sfx_type="door_creak", timestamp_hint="during word 'sealed'"),
            SfxCue(trigger_word="scratched", sfx_type="scratching", timestamp_hint="during 'scratched the words'"),
        ],
        description="Would you stay? 😱",
        hashtags=["#shorts", "#scary", "#horror", "#creepy", "#mystery"],
    )


@pytest.fixture
def sample_generate_request():
    """A sample generate request."""
    return GenerateRequest(
        genre_id="scary_stories",
        mode=GenreMode.AUTO,
    )


@pytest.fixture
def sample_reference_scripts():
    """Sample reference scripts from the Google Sheet (few-shot examples)."""
    return [
        "You wake up at 3 AM to the sound of scratching inside your walls. "
        "You grab a flashlight and press your ear against the plaster. The "
        "scratching stops. Then something whispers your name.",
        
        "In 1987, a family in rural Ohio bought a farmhouse at auction. The "
        "previous owners had vanished. While renovating the basement, the father "
        "found a door behind the drywall.",
    ]
