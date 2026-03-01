# Development Contract
## The Binding Rules for Building YT Shorts Auto

> **Both developers MUST read this before writing a single line of code.**
> Any deviation from this contract must be discussed and agreed upon FIRST.

---

## 1. The Golden Rules

1. **FINAL_PRODUCT.md is the source of truth.** If you're unsure about a feature, read it. Don't invent features. Don't skip features. Build exactly what's documented.
2. **The API contract (Section 4 below) is sacred.** Both devs build to these exact request/response shapes. Change the contract? Tell the other dev FIRST, update this file, THEN code.
3. **No creative improvisation.** Don't add "nice to have" features. Don't change the UI flow. Don't add extra API fields. Build what's specified, test it, move on.
4. **If it's not in the PRD, it doesn't exist.** Scope creep kills projects. If either of you thinks "wouldn't it be cool if..." — write it down for v1.1, don't build it now.
5. **Test before merge.** Never merge to `main` without verifying your code runs without errors.

---

## 2. Coding Standards

### Python (Backend — Dev A)

```python
# NAMING
# Files: snake_case.py
# Classes: PascalCase
# Functions: snake_case
# Constants: UPPER_SNAKE_CASE
# Private: _leading_underscore

# EVERY function must have a docstring
def generate_script(genre_id: str, mode: str) -> ScriptOutput:
    """Generate a script for the given genre using Gemini.
    
    Args:
        genre_id: Genre identifier from the sheets cache.
        mode: 'auto' or 'custom'.
    
    Returns:
        Validated ScriptOutput model.
    
    Raises:
        ScriptValidationError: If script fails all 3 retry attempts.
    """

# EVERY external API call must be wrapped in try/except
try:
    response = gemini_client.generate(prompt)
except Exception as e:
    logger.error(f"Gemini API failed: {e}")
    raise GeminiError(f"Script generation failed: {e}")

# EVERY agent function must return a Pydantic model, never raw dicts
# BAD:  return {"title": "...", "script": "..."}
# GOOD: return ScriptOutput(title="...", narration="...")

# LOGGING: use structured logging, never print()
import logging
logger = logging.getLogger(__name__)
logger.info("Script generated", extra={"genre": genre_id, "word_count": 128})
```

### Frontend (Dev B)

```
# File naming: kebab-case.js / kebab-case.css
# Components: PascalCase folders with index.js
# CSS classes: BEM notation (block__element--modifier)
# All IPC calls go through a single api.js service layer
# Never call Tauri invoke() directly from UI components
```

### Shared Rules (Both Devs)

| Rule | Why |
|---|---|
| No hardcoded strings for API URLs or config | Use constants file |
| No `TODO` without a linked GitHub issue | TODOs are forgotten |
| Max function length: 50 lines | Forces decomposition |
| Max file length: 300 lines | Forces separation of concerns |
| Every error must show a user-friendly message | No raw tracebacks in UI |
| All user-facing text in a constants/strings file | Easy to change later |
| Git commits must describe WHAT and WHY | `"fix bug"` is unacceptable |

---

## 3. Error Handling Contract

Backend errors MUST follow this format. Frontend MUST handle this format.

```python
# Backend sends errors as:
class APIError(BaseModel):
    success: bool = False
    error_code: str        # Machine-readable: "GEMINI_API_ERROR"
    error_message: str     # Human-readable: "Failed to generate script. Check your Gemini API key."
    retry_allowed: bool    # Can frontend show a retry button?
    details: str | None    # Debug info (only shown in settings/logs, never to user)

# Standard error codes both devs must handle:
# AUTH_ERROR          → "API key invalid or expired"
# QUOTA_ERROR         → "Daily limit reached"
# NETWORK_ERROR       → "Can't connect to service"  
# VALIDATION_ERROR    → "Generated content didn't pass quality check"
# RENDER_ERROR        → "Video rendering failed"
# DISK_ERROR          → "Not enough disk space"
# SHEET_ERROR         → "Can't fetch data from cloud"
# LICENSE_ERROR       → "Invalid or expired license"
```

```javascript
// Frontend handles errors as:
async function generateVideo(genre, mode) {
  const result = await api.generate(genre, mode);
  if (!result.success) {
    if (result.error_code === 'QUOTA_ERROR') {
      showToast('Daily limit reached. Try again tomorrow.', 'warning');
    } else if (result.retry_allowed) {
      showRetryDialog(result.error_message);
    } else {
      showErrorScreen(result.error_message);
    }
  }
}
```

---

## 4. API Contract (The Integration Bible)

**Dev A builds these endpoints. Dev B consumes them. These shapes are LAW.**

### 4.1 Health Check

```
GET /api/health

Response (200):
{
  "status": "ok",
  "version": "1.0.0",
  "uptime_seconds": 3600
}
```

### 4.2 Get Genres (from cache)

```
GET /api/genres

Response (200):
{
  "success": true,
  "genres": [
    {
      "genre_id": "scary_stories",
      "display_name": "Scary Stories & Mysteries",
      "icon": "👻",
      "difficulty": "Easy",
      "is_active": true
    }
  ],
  "cache_age_hours": 2.5,
  "last_refresh": "2026-03-01T14:00:00Z"
}
```

### 4.3 Generate Video

```
POST /api/generate

Request:
{
  "genre_id": "scary_stories",
  "mode": "auto",              // "auto" | "custom"
  "custom_topic": null,        // string if mode is "custom"
  "schedule": "next_best"      // "now" | "next_best" | ISO datetime
}

Response (202 — accepted, async):
{
  "success": true,
  "job_id": "job_abc123",
  "message": "Generation started"
}
```

### 4.4 SSE Progress Stream

```
GET /events?job_id=job_abc123

SSE Events:
data: {
  "job_id": "job_abc123",
  "stage": "script_generation",    // see stage list below
  "stage_name": "Writing script...",
  "progress": 0.15,               // 0.0 to 1.0
  "eta_seconds": 120,
  "error": null
}

data: {
  "job_id": "job_abc123", 
  "stage": "tts_generation",
  "stage_name": "Generating narration...",
  "progress": 0.35,
  "eta_seconds": 80,
  "error": null
}

data: {
  "job_id": "job_abc123",
  "stage": "complete",
  "stage_name": "Video ready!",
  "progress": 1.0,
  "eta_seconds": 0,
  "error": null,
  "result": {
    "video_path": "C:/Users/.../output/job_abc123.mp4",
    "title": "This Family Found A Sealed Room 😨",
    "description": "Would you stay? 😱",
    "hashtags": ["#shorts", "#scary", "#horror"],
    "duration_seconds": 42,
    "word_count": 128
  }
}

// PIPELINE STAGES (in order):
// "script_generation"     → 0.00 - 0.10
// "script_validation"     → 0.10 - 0.15
// "tts_generation"        → 0.15 - 0.35
// "image_fetching"        → 0.35 - 0.50  (parallel with TTS)
// "sfx_resolution"        → 0.50 - 0.55
// "music_selection"       → 0.55 - 0.60
// "audio_mixing"          → 0.60 - 0.65
// "caption_generation"    → 0.65 - 0.70
// "video_rendering"       → 0.70 - 0.95
// "complete"              → 1.00
```

### 4.5 Get Preview Data

```
GET /api/preview/{job_id}

Response (200):
{
  "success": true,
  "job_id": "job_abc123",
  "video_path": "C:/Users/.../output/job_abc123.mp4",
  "title": "This Family Found A Sealed Room 😨",
  "description": "Would you stay? 😱",
  "hashtags": ["#shorts", "#scary", "#horror"],
  "duration_seconds": 42,
  "genre_id": "scary_stories",
  "can_regenerate": true,
  "regenerations_remaining": 1
}
```

### 4.6 Update Preview Metadata

```
PATCH /api/preview/{job_id}

Request:
{
  "title": "Updated Title 😨",
  "description": "Updated description",
  "hashtags": ["#shorts", "#updated"]
}

Response (200):
{
  "success": true,
  "message": "Metadata updated"
}
```

### 4.7 Upload Video

```
POST /api/upload

Request:
{
  "job_id": "job_abc123",
  "schedule": "now"        // "now" | ISO datetime
}

Response (202):
{
  "success": true,
  "youtube_video_id": "dQw4w9WgXcQ",
  "message": "Upload started"
}
```

### 4.8 Regenerate

```
POST /api/regenerate

Request:
{
  "job_id": "job_abc123",
  "complaints": ["script"],   // array from: "script", "voice", "images", "captions", "music", "pacing"
  "notes": "The twist was too predictable"
}

Response (202):
{
  "success": true,
  "regen_job_id": "job_abc123_regen",
  "stages_rerunning": ["script_generation", "tts_generation", "image_fetching", "caption_generation", "video_rendering"],
  "message": "Regeneration started"
}
```

### 4.9 Get Quota

```
GET /api/quota

Response (200):
{
  "success": true,
  "youtube_uploads_remaining": 4,
  "youtube_uploads_max": 6,
  "gemini_requests_today": 12,
  "gemini_limit": 500,
  "tts_chars_this_month": 162000,
  "tts_limit": 1000000
}
```

### 4.10 Analytics Summary

```
GET /api/analytics/summary

Response (200):
{
  "success": true,
  "period": "7d",
  "total_videos": 12,
  "total_views": 8400,
  "avg_retention": 0.54,
  "subs_gained": 23,
  "trend": "upward",
  "trend_change": "+12%",
  "best_hook_pattern": "second_person_time",
  "best_post_hour": 18,
  "channel_health": "normal",
  "insights": [
    {
      "text": "Second-person hooks outperform questions by 27%",
      "action": "apply",
      "insight_id": "ins_001"
    }
  ]
}
```

### 4.11 Validate API Key

```
POST /api/keys/validate

Request:
{
  "service": "gemini",    // "gemini" | "youtube" | "tts" | "groq" | "pexels" | "pixabay" | "freesound"
  "key": "AIzaSy..."
}

Response (200):
{
  "success": true,
  "valid": true,
  "service": "gemini",
  "message": "Gemini API key is valid"
}
```

### 4.12 Save Calibration

```
POST /api/calibration

Request:
{
  "genre_id": "scary_stories",
  "user_intent": "dark, creepy stories with twists...",
  "preferred_video_id": "job_cal_002",
  "why_chosen": "Pacing felt right, voice tone perfect",
  "improvement_notes": "Music too loud, twist predictable"
}

Response (200):
{
  "success": true,
  "message": "Calibration saved"
}
```

### 4.13 Get Videos History

```
GET /api/history?page=1&per_page=20

Response (200):
{
  "success": true,
  "videos": [
    {
      "job_id": "job_abc123",
      "title": "This Family Found A Sealed Room 😨",
      "genre_id": "scary_stories",
      "status": "uploaded",
      "youtube_video_id": "dQw4w9WgXcQ",
      "created_at": "2026-03-01T14:30:00Z",
      "views": 2400,
      "retention": 0.62,
      "thumbnail_path": "C:/Users/.../thumbs/job_abc123.jpg"
    }
  ],
  "total": 45,
  "page": 1,
  "pages": 3
}
```

---

## 5. Shared Models (models.py)

**This file is the ONLY shared dependency. Both devs must agree on it. Dev A owns it, Dev B reviews changes.**

```python
"""
Shared Pydantic models used across the entire application.
DO NOT modify without notifying the other developer.
"""
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


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


# ─── SCRIPT ────────────────────────────────────────────

class ImageCue(BaseModel):
    keyword: str
    timestamp_hint: str  # "after line 3", "during word 'door'"
    mood: str            # "dark", "eerie", "dramatic"

class SfxCue(BaseModel):
    trigger_word: str
    sfx_type: str        # "door_creak", "thunder", "footsteps"
    timestamp_hint: str

class ScriptOutput(BaseModel):
    title: str = Field(max_length=60)
    narration: str
    word_count: int = Field(ge=80, le=150)
    estimated_duration: int  # seconds: 30, 45, or 60
    hook_line: str
    image_cues: list[ImageCue]
    sfx_cues: list[SfxCue]


# ─── GENRE ─────────────────────────────────────────────

class Genre(BaseModel):
    genre_id: str
    display_name: str
    icon: str
    difficulty: str
    is_active: bool

class GenreConfig(BaseModel):
    genre_id: str
    tts_voice: str
    tts_rate: float
    tts_pitch: float
    layout: str          # "split_screen" | "full_image" | "full_gameplay"
    caption_preset: str
    music_mood: str


# ─── CALIBRATION ───────────────────────────────────────

class GenreCalibration(BaseModel):
    genre_id: str
    user_intent: str
    preferred_video_id: str
    preferred_script: str
    why_chosen: str
    improvement_notes: str
    preferred_config: dict


# ─── REQUESTS ──────────────────────────────────────────

class GenerateRequest(BaseModel):
    genre_id: str
    mode: GenreMode = GenreMode.AUTO
    custom_topic: str | None = None
    schedule: str = "next_best"  # "now" | "next_best" | ISO datetime

class RegenerateRequest(BaseModel):
    job_id: str
    complaints: list[ComplaintType]
    notes: str = ""

class UploadRequest(BaseModel):
    job_id: str
    schedule: str = "now"

class KeyValidateRequest(BaseModel):
    service: str
    key: str

class PreviewUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    hashtags: list[str] | None = None

class CalibrationRequest(BaseModel):
    genre_id: str
    user_intent: str
    preferred_video_id: str
    why_chosen: str
    improvement_notes: str


# ─── RESPONSES ─────────────────────────────────────────

class APIResponse(BaseModel):
    success: bool = True
    message: str = ""

class APIError(BaseModel):
    success: bool = False
    error_code: str
    error_message: str
    retry_allowed: bool = False
    details: str | None = None

class ProgressEvent(BaseModel):
    job_id: str
    stage: PipelineStage
    stage_name: str
    progress: float = Field(ge=0.0, le=1.0)
    eta_seconds: int = 0
    error: str | None = None

class VideoResult(BaseModel):
    job_id: str
    video_path: str
    title: str
    description: str
    hashtags: list[str]
    duration_seconds: int
    word_count: int

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
    youtube_uploads_remaining: int
    youtube_uploads_max: int = 6
    gemini_requests_today: int
    gemini_limit: int = 500
    tts_chars_this_month: int
    tts_limit: int = 1000000

class VideoHistoryItem(BaseModel):
    job_id: str
    title: str
    genre_id: str
    status: VideoStatus
    youtube_video_id: str | None
    created_at: datetime
    views: int = 0
    retention: float = 0.0
    thumbnail_path: str | None
```

---

## 6. Integration Checkpoints

**Both devs MUST sync at these points. No skipping.**

### Checkpoint 1: End of Week 1
| Dev A Delivers | Dev B Delivers | Integration Test |
|---|---|---|
| `GET /api/health` working | Tauri shell opens | Frontend can hit `/api/health` and show "Connected" |
| `GET /api/genres` working (from test data) | Onboarding wizard UI (steps 1-3) | Genres display in the UI from backend |
| `POST /api/keys/validate` working | API key entry screen with test buttons | Clicking "Test" in UI validates key via backend |
| `models.py` finalized | Understands all model shapes | Both agree on data shapes |

### Checkpoint 2: End of Week 2
| Dev A Delivers | Dev B Delivers | Integration Test |
|---|---|---|
| `POST /api/generate` working (full pipeline) | Generate screen UI | Click "Generate" → see real progress → video appears |
| `GET /events` SSE stream working | SSE progress bar working | Progress bar updates in real-time from backend |
| `GET /api/preview/{job_id}` working | Preview screen with video player | Video plays in preview, metadata editable |
| `POST /api/calibration` working | Calibration flow (pick 1 of 3 + notes) | User picks video → calibration saved → affects next gen |

### Checkpoint 3: End of Week 3
| Dev A Delivers | Dev B Delivers | Integration Test |
|---|---|---|
| `POST /api/regenerate` working | Regen feedback form | Click regenerate → see progress → compare screen |
| `POST /api/upload` working | Upload button + schedule picker | Upload works → YouTube video ID returned |
| `GET /api/analytics/summary` working | Dashboard with stats | Dashboard shows real analytics data |
| `GET /api/quota` working | Quota display in UI | Remaining uploads show correctly |

### Checkpoint 4: End of Week 4
| Dev A Delivers | Dev B Delivers | Integration Test |
|---|---|---|
| Shadow ban detection | Alert banner in dashboard | Shadow ban warning shows when detected |
| Performance submission (consent flow) | Consent dialog UI | User consents → data submitted → confirm in sheet |
| Full error handling | All error screens | Every error code shows correct UI |
| **Full end-to-end test** | **Full end-to-end test** | **Onboarding → Generate → Preview → Upload → Analytics** |

---

## 7. Definition of Done

A feature is ONLY done when:

- [ ] Code runs locally without errors
- [ ] Handles errors gracefully (no crashes, no raw tracebacks)
- [ ] Follows the coding standards (Section 2)
- [ ] API response matches the contract (Section 4) exactly
- [ ] Committed to feature branch with descriptive message
- [ ] Tested against the other dev's code at integration checkpoint
- [ ] Code reviewed briefly by the other dev (even a 5-min look)

---

## 8. What to NEVER Do

| ❌ NEVER DO THIS | ✅ DO THIS INSTEAD |
|---|---|
| Add a feature not in the PRD | Write it down for v1.1 |
| Change an API shape without telling the other dev | Update this contract first → notify → then code |
| Use `print()` for debugging | Use `logging.getLogger(__name__)` |
| Return raw dicts from backend | Return Pydantic models |
| Hardcode file paths | Use `pathlib.Path` + config |
| Store API keys in plaintext files | Use OS credential manager |
| Merge to `main` without basic testing | Run the code first, check it works |
| Skip an integration checkpoint | Sync even if "almost done" — partial sync > no sync |
| Use MoviePy for rendering | FFmpeg subprocess only |
| Build the UI before the API works | Backend first, UI consumes it |
| Commit `.env`, keys, or secrets | They're in `.gitignore` for a reason |
| Work for >2 days without pushing code | Push daily, even WIP |

---

## 9. File Ownership (Who Edits What)

| Path | Owner | Other Dev Can? |
|---|---|---|
| `backend/**` | Dev A | Read only, suggest changes |
| `frontend/**` | Dev B | Read only, suggest changes |
| `backend/core/models.py` | Dev A (but SHARED) | Must review all changes |
| `docs/**` | Both | Either can update |
| `.gitignore` | Both | Either can update |
| `README.md` | Both | Either can update |

**The ONLY file that MUST be reviewed by both devs when changed is `models.py`.** Everything else is owned by one person.

---

## 10. Communication Triggers

**You MUST message the other dev when:**

1. You change ANY field in `models.py`
2. You add, remove, or change an API endpoint
3. You're about to merge to `main`
4. You're blocked and need the other dev's piece
5. You discover a bug that affects the other dev's code
6. You finish a checkpoint feature

**You DON'T need to message for:**
- Normal coding within your own directory
- Refactoring your own code
- Adding helper functions
- Fixing bugs in your own code
