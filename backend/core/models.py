"""
Shared Pydantic models used across the entire application.
DO NOT modify without notifying the other developer.

This file is the ONLY shared dependency between backend and frontend.
Every agent input/output MUST use these models.
"""
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import Optional


# ─── ENUMS ─────────────────────────────────────────────

class GenreMode(str, Enum):
    AUTO = "auto"
    CUSTOM = "custom"


class VideoStatus(str, Enum):
    GENERATING = "generating"
    PREVIEW = "preview"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    FAILED = "failed"


class ComplaintType(str, Enum):
    SCRIPT = "script"
    VOICE = "voice"
    IMAGES = "images"
    CAPTIONS = "captions"
    MUSIC = "music"
    PACING = "pacing"


class PipelineStage(str, Enum):
    INITIALIZING = "initializing"
    SCRIPT_GENERATION = "script_generation"
    SCRIPT_VALIDATION = "script_validation"
    TTS_GENERATION = "tts_generation"
    IMAGE_FETCHING = "image_fetching"
    SFX_RESOLUTION = "sfx_resolution"
    MUSIC_SELECTION = "music_selection"
    AUDIO_MIXING = "audio_mixing"
    CAPTION_GENERATION = "caption_generation"
    VIDEO_RENDERING = "video_rendering"
    COMPLETE = "complete"
    FAILED = "failed"


# Stage display names and progress ranges
STAGE_INFO = {
    PipelineStage.INITIALIZING:      {"name": "Preparing...",            "start": 0.00, "end": 0.02},
    PipelineStage.SCRIPT_GENERATION:  {"name": "Writing script...",       "start": 0.02, "end": 0.10},
    PipelineStage.SCRIPT_VALIDATION:  {"name": "Validating script...",    "start": 0.10, "end": 0.15},
    PipelineStage.TTS_GENERATION:     {"name": "Generating narration...", "start": 0.15, "end": 0.35},
    PipelineStage.IMAGE_FETCHING:     {"name": "Finding images...",       "start": 0.35, "end": 0.50},
    PipelineStage.SFX_RESOLUTION:     {"name": "Selecting SFX...",        "start": 0.50, "end": 0.55},
    PipelineStage.MUSIC_SELECTION:    {"name": "Choosing music...",       "start": 0.55, "end": 0.60},
    PipelineStage.AUDIO_MIXING:       {"name": "Mixing audio...",         "start": 0.60, "end": 0.65},
    PipelineStage.CAPTION_GENERATION: {"name": "Building captions...",    "start": 0.65, "end": 0.70},
    PipelineStage.VIDEO_RENDERING:    {"name": "Rendering video...",      "start": 0.70, "end": 0.95},
    PipelineStage.COMPLETE:           {"name": "Video ready!",            "start": 1.00, "end": 1.00},
}


# ─── GENRE (from Google Sheet) ─────────────────────────

class Genre(BaseModel):
    """A single genre from the 🎯 Suggested Genres tab."""
    genre_id: str
    display_name: str
    icon: str
    difficulty: str = ""
    is_active: bool = True


class GenreConfig(BaseModel):
    """Per-genre configuration for TTS, captions, layout."""
    genre_id: str
    tts_voice: str = "en-US-Neural2-D"
    tts_rate: float = 0.95
    tts_pitch: float = 0.0
    layout: str = "split_screen"     # split_screen | full_image | full_gameplay
    caption_preset: str = "clean_pro"
    music_mood: str = "neutral"


# ─── SCRIPT ────────────────────────────────────────────

class ImageCue(BaseModel):
    """A cue for fetching a relevant image at a specific point."""
    keyword: str
    timestamp_hint: str  # "after line 3", "during word 'door'"
    mood: str            # "dark", "eerie", "dramatic"


class SfxCue(BaseModel):
    """A cue for placing a sound effect at a specific point."""
    trigger_word: str
    sfx_type: str        # "door_creak", "thunder", "footsteps"
    timestamp_hint: str


class ScriptOutput(BaseModel):
    """The validated output of the Script Agent."""
    title: str = Field(max_length=60)
    narration: str
    word_count: int = Field(ge=80, le=170)
    estimated_duration: int  # seconds: 30, 45, or 60
    hook_line: str
    image_cues: list[ImageCue]
    sfx_cues: list[SfxCue]
    description: str = ""
    hashtags: list[str] = Field(default_factory=list)


# ─── ASSET ─────────────────────────────────────────────

class AssetBundle(BaseModel):
    """Output of the Asset Agent — paths to fetched media."""
    image_paths: list[str]         # Ordered list of image file paths
    sfx_paths: list[str]           # Paths to resolved SFX files
    music_path: Optional[str] = None  # Path to selected music track
    gameplay_path: Optional[str] = None  # Path to gameplay clip


# ─── AUDIO ─────────────────────────────────────────────

class WordTimestamp(BaseModel):
    """A single word with its start/end time in the audio."""
    word: str
    start_ms: int
    end_ms: int


class AudioBundle(BaseModel):
    """Output of the Audio Agent — final audio + timestamps."""
    audio_path: str                # Path to final mixed audio wav
    narration_path: str            # Path to raw TTS audio
    duration_ms: int               # Total duration in milliseconds
    word_timestamps: list[WordTimestamp]


# ─── CALIBRATION ───────────────────────────────────────

class GenreCalibration(BaseModel):
    """User's calibration profile from onboarding."""
    genre_id: str
    user_intent: str
    preferred_video_id: str = ""
    preferred_script: str = ""
    why_chosen: str = ""
    improvement_notes: str = ""
    preferred_config: dict = Field(default_factory=dict)


# ─── API REQUESTS ──────────────────────────────────────

class GenerateRequest(BaseModel):
    genre_id: str
    mode: GenreMode = GenreMode.AUTO
    custom_topic: Optional[str] = None
    schedule: str = "next_best"  # "now" | "next_best" | ISO datetime


class RegenerateRequest(BaseModel):
    job_id: str
    complaints: list[ComplaintType]
    notes: str = ""


class UploadRequest(BaseModel):
    job_id: str
    schedule: str = "now"


class KeyValidateRequest(BaseModel):
    service: str  # "gemini" | "youtube" | "tts" | "groq" | ...
    key: str


class PreviewUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    hashtags: Optional[list[str]] = None


class CalibrationRequest(BaseModel):
    genre_id: str
    user_intent: str
    preferred_video_id: str
    why_chosen: str
    improvement_notes: str


# ─── API RESPONSES ─────────────────────────────────────

class APIResponse(BaseModel):
    """Standard success response."""
    success: bool = True
    message: str = ""


class APIError(BaseModel):
    """Standard error response. Frontend must handle this shape."""
    success: bool = False
    error_code: str
    error_message: str
    retry_allowed: bool = False
    details: Optional[str] = None


class ProgressEvent(BaseModel):
    """Sent via SSE to frontend during pipeline execution."""
    job_id: str
    stage: PipelineStage
    stage_name: str
    progress: float = Field(ge=0.0, le=1.0)
    eta_seconds: int = 0
    error: Optional[str] = None


class VideoResult(BaseModel):
    """Final video output metadata."""
    job_id: str
    video_path: str
    title: str
    description: str
    hashtags: list[str]
    duration_seconds: int
    word_count: int
    genre_id: str = ""


class PreviewResponse(BaseModel):
    success: bool = True
    job_id: str
    video_path: str
    title: str
    description: str
    hashtags: list[str]
    duration_seconds: int
    genre_id: str
    can_regenerate: bool
    regenerations_remaining: int


class QuotaResponse(BaseModel):
    success: bool = True
    youtube_uploads_remaining: int = 6
    youtube_uploads_max: int = 6
    gemini_requests_today: int = 0
    gemini_limit: int = 500
    tts_chars_this_month: int = 0
    tts_limit: int = 1000000


class VideoHistoryItem(BaseModel):
    job_id: str
    title: str
    genre_id: str
    status: VideoStatus
    youtube_video_id: Optional[str] = None
    created_at: datetime
    views: int = 0
    retention: float = 0.0
    thumbnail_path: Optional[str] = None


# ─── PIPELINE STATE ───────────────────────────────────

class PipelineState(BaseModel):
    """Persisted state for crash recovery and partial regeneration."""
    job_id: str
    state: PipelineStage = PipelineStage.INITIALIZING
    genre_id: str
    mode: GenreMode = GenreMode.AUTO
    custom_topic: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Intermediate outputs
    script_output: Optional[ScriptOutput] = None
    asset_bundle: Optional[AssetBundle] = None
    audio_bundle: Optional[AudioBundle] = None
    caption_path: Optional[str] = None
    video_path: Optional[str] = None
    regen_video_path: Optional[str] = None

    # Tracking
    retries: dict = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    stage_timings: dict = Field(default_factory=dict)
    regenerations_remaining: int = 1


# ─── SUBMISSION (to Google Sheet) ──────────────────────

class VideoSubmission(BaseModel):
    """Anonymized data submitted to Submissions Sheet with user consent."""
    user_hash: str           # SHA256(HWID) — anonymous
    genre: str
    script_text: str
    hook_pattern: str
    word_count: int
    duration: int
    views_14d: int
    retention_avg: float
    likes: int
    caption_style: str
    voice_id: str
    music_mood: str
    timestamp: str
