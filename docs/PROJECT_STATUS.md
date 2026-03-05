# PROJECT STATUS — YT Shorts Automation Bot

> Last updated: **2026-03-05** · Git: `b18437d` (main) · Tests: **75/75** ✅

---

## Overall Progress

| Phase | Description | Status | % |
|-------|------------|--------|---|
| **Phase 1** | Core Pipeline (agents + services) | ✅ Complete | **100%** |
| **Phase 1.5** | Pipeline Orchestrator + CLI | 🔲 Not started | **0%** |
| **Phase 2** | Desktop Shell (Tauri v2) | 🔲 Not started (Dev B) | **0%** |
| **Phase 3** | Frontend UI | 🔲 Not started (Dev B) | **0%** |
| **Phase 4** | Polish + Security | 🔲 Not started | **0%** |

**Overall: ~30% complete** toward v1.0.0 launch (estimated April 14, 2026).

---

## What's Been Built (Phase 1 Complete)

### File Inventory

#### `backend/core/` — Shared Infrastructure
| File | Purpose |
|------|---------|
| `models.py` | Pydantic models: GenreConfig, ScriptOutput, AudioBundle, AssetBundle, VideoResult, WordTimestamp, ImageCue, SfxCue |
| `config.py` | AppConfig with paths, API keys (BYOK), video dimensions, retry limits. Loads `.env` |
| `cache_manager.py` | SQLite cache: genre configs, reference scripts, generated scripts, images. Async via aiosqlite |
| `sheets_client.py` | Google Sheets integration: reads genre research data, reference scripts |
| `logger.py` | Structured JSON logger with structlog. Writes to `logs/app.log` |
| `exceptions.py` | Custom errors: ScriptGenerationError, RenderError, UploadError |

#### `backend/agents/` — AI Agents
| File | Purpose |
|------|---------|
| `script_agent.py` | 5-layer script gen: Gemini → Groq validate → rules → banned phrases → TF-IDF dedup |
| `script_dedup.py` | TF-IDF cosine similarity: rejects scripts >70% similar to last 50 |
| `prompts.py` | System prompts for Gemini (generation) and Groq (validation) |
| `ssml_builder.py` | SSML markup for Google TTS: pauses, emphasis, prosody per genre |
| `audio_agent.py` | TTS → music (-14dB) → SFX (-8dB, 200ms pre-lap) → LUFS normalize |
| `asset_agent.py` | 7-tier image: cache → Pexels+Pixabay(parallel) → DDG → Wikimedia → LLM reformulation → gradient fallback |
| `caption_builder.py` | 12 ASS caption presets, word-at-a-time pop, safety zones |
| `visual_agent.py` | FFmpeg render: preprocess → captions → render → validate → atomic rename |
| `upload_agent.py` | YouTube upload with smart scheduling, AI disclosure |

#### `backend/services/` — External API Wrappers
| File | Purpose |
|------|---------|
| `gemini_service.py` | Google Gemini API (async) |
| `groq_service.py` | Groq API for cross-validation |
| `tts_service.py` | Google Cloud TTS with word timestamps |
| `image_service.py` | 4-source search (Pexels, Pixabay, DDG, Wikimedia) + 5-factor scoring |
| `audio_utils.py` | 3-band frequency ducking, SFX mixing, LUFS normalization, librosa |
| `ffmpeg_utils.py` | FFmpeg command builder: 3 layouts, xfade transitions, encoding |
| `youtube_service.py` | YouTube Data API v3: OAuth2, resumable upload |

#### `backend/tests/` — 75 Tests
| File | Tests |
|------|-------|
| test_cache_manager.py | 21 |
| test_script_agent.py | 10 |
| test_audio_agent.py | 8 |
| test_asset_agent.py | 12 |
| test_visual_agent.py | 14 |
| test_upload_agent.py | 10 |

---

## Architecture Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| LLM Generation | Gemini | Best for creative long-form |
| LLM Validation | Groq | Fast cross-model validation |
| TTS | Google Cloud TTS | Word-level timestamps, SSML |
| Image Sources | Pexels → Pixabay → DDG → Wikimedia | Free APIs, BYOK |
| Video Rendering | FFmpeg subprocess | Per blueprint: NEVER MoviePy |
| Database | SQLite + aiosqlite | Lightweight, no server needed |
| Audio Mixing | pydub + librosa | Frequency-aware ducking |
| API Framework | FastAPI | Async, automatic OpenAPI docs |

---

## How Each Agent Works

### Script Agent
```
GenreConfig → Gemini generate → JSON parse → Rule checks
→ Banned phrase filter → Groq 6-score validation
→ TF-IDF dedup (<70% vs last 50) → ScriptOutput
```

### Asset Agent (7 Tiers)
```
ImageCue[] → T1: Cache → T2+T3: Pexels+Pixabay (parallel)
→ T4: DuckDuckGo → T5: Wikimedia → T6: Gemini rewrite
→ T7: Genre gradient fallback → 5-factor score → AssetBundle
```

### Audio Agent
```
narration → SSML → TTS → .wav + timestamps
→ librosa music segment → 3-band freq ducking
→ SFX at -8dB (200ms pre-lap) → LUFS -14 → AudioBundle
```

### Visual Agent
```
AudioBundle + AssetBundle → Pillow resize → ASS captions
→ FFmpeg (xfade, layouts) → .tmp.mp4 → ffprobe → final.mp4
```

### Upload Agent
```
VideoResult → schedule (now/next_best/ISO) → AI disclosure
→ YouTube upload (3 retries) → UploadResult
```

---

## API Keys & Environment

| Key | Source | Storage |
|-----|--------|---------|
| Google Cloud TTS | `shorts-bot-tts-*.json` | Root (gitignored) |
| Gemini API | `GEMINI_API_KEY` | `.env` |
| Groq API | `GROQ_API_KEY` | `.env` |
| Pexels API | `PEXELS_API_KEY` | `.env` |
| Pixabay API | `PIXABAY_API_KEY` | `.env` |
| YouTube OAuth | `client_secrets.json` | Root (gitignored) |

---

## Git History

| Commit | Description |
|--------|-------------|
| `b18437d` | ✅ Fix all 15 agent gaps (HEAD) |
| `219d4ad` | Upload agent + YouTube service (Checkpoint 1) |
| `43f35f4` | Visual agent + caption builder + FFmpeg |
| `de7cb7e` | Asset agent + image service |
| `049459d` | Audio agent + TTS + SSML |
| `844def8` | Sheets client + cache + script agent |
| `1594684` | Backend scaffolding (models, config, FastAPI) |
| `ea8e146` | Initial commit (planning docs) |

---

## What's NOT Built Yet

### Next: Pipeline Orchestrator (`backend/pipeline/orchestrator.py`)
- State machine per ENGINEERING_SPECS_PART2 §8
- Chains: Script → Asset + Audio (parallel) → Visual → Upload
- PipelineState in SQLite (crash recovery)
- SSE progress events

### Dev B (Phase 2 + 3, not started)
- Tauri v2 desktop shell + license system (Rust)
- IPC layer + SSE streaming
- UI: Onboarding → Dashboard → Generate → Preview → Analytics

### Phase 4 (Polish)
- PyArmor, shadow ban detection, feedback loop
