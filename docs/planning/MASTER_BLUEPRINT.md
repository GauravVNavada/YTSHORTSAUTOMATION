# YouTube Shorts Automation — Complete Product Blueprint

> **If you lose everything else, this single document contains every decision, every algorithm, and every technical detail needed to rebuild this product from scratch.**

---

# TABLE OF CONTENTS

1. [Product Vision & Market Position](#1-product-vision--market-position)
2. [Business Model](#2-business-model)
3. [Complete API & Key Inventory (BYOK)](#3-complete-api--key-inventory-byok)
4. [System Architecture](#4-system-architecture)
5. [The Video Generation Pipeline (End-to-End)](#5-the-video-generation-pipeline-end-to-end)
6. [Preview & Regeneration System](#6-preview--regeneration-system)
7. [Script Generation Pipeline (3 Stages)](#7-script-generation-pipeline-3-stages)
8. [TTS & Audio Engineering](#8-tts--audio-engineering)
9. [Image Fetching (7-Tier Fallback)](#9-image-fetching-7-tier-fallback)
10. [Background Video & Layout System](#10-background-video--layout-system)
11. [ASS Caption System](#11-ass-caption-system)
12. [SFX & Music Strategy](#12-sfx--music-strategy)
13. [Crash-Proof Video Rendering](#13-crash-proof-video-rendering)
14. [Analytics Intelligence & Feedback Loop](#14-analytics-intelligence--feedback-loop)
15. [Self-Improving Example Library](#15-self-improving-example-library)
16. [Genre Template System](#16-genre-template-system)
17. [Desktop Application (Tauri + PyInstaller)](#17-desktop-application-tauri--pyinstaller)
18. [Product Security & Anti-Piracy](#18-product-security--anti-piracy)
19. [Data Collection Sheet (122 Columns)](#19-data-collection-sheet-122-columns)
20. [User Experience: First Run, Error Recovery & Offline Mode](#20-user-experience-first-run-error-recovery--offline-mode)
21. [Tech Stack Summary](#21-tech-stack-summary)

---

# 1. Product Vision & Market Position

## The Problem
Most YouTube Shorts automation tools produce *recognizably automated* content — robotic TTS, unrelated stock footage, random music, generic captions. Viewers scroll past. Channels stagnate.

## Our Thesis
A tool that produces output **indistinguishable from a skilled human editor** — at zero marginal cost to the user — wins this market. Not by being cheaper. By being **better.**

## Competitors & Their Weaknesses

| Competitor | Price | Fatal Weakness |
|---|---|---|
| **ShortX** | $15–150/mo | Template-driven. Every user's channel looks identical. |
| **AutoShorts.ai** | $19–69/mo | No real AI intelligence in asset selection. |
| **InVideo AI** | $28–120/mo | General-purpose, unfocused. |
| **Opus Clip** | $19–69/mo | Cuts existing content. Doesn't create. |
| **Fliki / Pictory** | $23–89/mo | Text-to-video with bulk stock. No narration intelligence. |

## Our Edge
1. **Onboarding calibration** — the system learns what THIS user's audience responds to
2. **Self-improving feedback loop** — gets better every week from real performance data
3. **BYOK = zero cost per user** — pure margin on every sale
4. **No subscription fatigue** — one-time purchase ($100) in a market of $20+/month tools (pays for itself in ~2 months vs cheapest competitor)

---

# 2. Business Model

| Item | Detail |
|---|---|
| **Pricing** | One-time purchase: **$100** |
| **Free trial** | 3 videos free (all features enabled, no time limit) |
| **Cost per user** | $0 — users bring ALL their own API keys |
| **Distribution** | Direct download from marketing site (.exe installer) |
| **Moat** | Self-improving feedback loop + genre research data |
| **License** | Ed25519 signed keys, HWID-bound to 2 machines |
| **Value pitch** | Competitors charge $20-150/MONTH. $100 one-time = less than 2 months of the cheapest alternative, then free forever |

---

# 3. Complete API & Key Inventory (BYOK)

**We NEVER provide, bundle, or ship any API keys. Users provide all keys during setup. Our cost-per-user is zero.**

### User-Provided Keys (entered during setup wizard)

| API | What It Powers | Free Tier | Key? |
|---|---|---|---|
| **Gemini 2.5 Flash** | Script generation (idea + writing) | ~15 RPM, 1M token context | User's Google AI key |
| **Google Cloud TTS** | Narration audio (Neural2/Chirp3 HD) + SSML | 1M chars/month | User's GCP key |
| **Google Cloud STT** | Word timestamps (fallback) | 60 min/month | Same GCP key |
| **Groq (Llama 3.3 70B)** | Script validation (quality gate) | 500K tokens/day, 30 RPM | User's Groq key |
| **YouTube Data API** | Video upload + scheduling | 10,000 units/day (~6 uploads) | User's GCP key |
| **YouTube Analytics API** | Performance tracking | Same quota | User's GCP key |
| **Pexels** | Image + video search (Tier 2) | 200 req/hour | User's Pexels key (free) |
| **Pixabay** | Backup images + SFX + music (Tier 3) | 5000 req/hour | User's Pixabay key (free) |
| **Freesound** | SFX library (CC0) | 60 req/min | User's Freesound key (free) |

### Keyless APIs (no key needed)

| API | What It Does |
|---|---|
| **DuckDuckGo (ddgs)** | Image search fallback (Tier 4) |
| **Wikimedia Commons** | Public domain images (Tier 5) |

### Our Internal Key (the ONLY key we manage)

| Key | Purpose | Protection |
|---|---|---|
| **Google Sheets service account** | Reads our curated reference script library | Encrypted in binary, read-only scope, sheet restricted to this account |

---

# 4. System Architecture

## Master-Child Agent Pattern

```
Master Orchestrator → Script Agent → Idea Generation
                                   → Script Writing
                                   → Script Validation (Groq)
                  → Asset Agent  → Image Fetcher (7-tier)
                                → SFX Fetcher
                                → Music Fetcher
                                → Cache Manager
                  → Audio Agent → TTS (Google Cloud)
                                → Word Timestamps
                                → Audio Post-Processing
                  → Visual Agent → Caption Renderer (ASS)
                                 → Image Overlay Engine
                                 → Background Video Selector
                                 → Final FFmpeg Composition
                  → Upload Agent → YouTube Upload
                                 → Smart Scheduling
                  → Feedback Agent → Analytics Collector
                                   → Performance Analyzer
                                   → Experimentation Engine
```

**Why this matters:**
- Each agent fails independently without crashing the pipeline
- Agents retry with circuit breakers (max 3 retries, exponential backoff)
- Pydantic schema validation at every agent boundary
- Partial failure at step 4 doesn't redo steps 1–3

## Data Flow

```
User clicks "Generate" → { genre: "scary_stories", mode: "auto" }
   ↓
Master Agent orchestrates sequential + parallel execution:
   1. Script Agent:     ~5s (Gemini → JSON with narration, image cues, SFX cues)
   2. [PARALLEL]:
      a. Audio Agent:   ~8s (SSML enhance → TTS → audio + timestamps)
      b. Asset Agent:   ~3s (fetch images, SFX, music — most hidden behind TTS time)
      c. Caption Agent: ~1s (build .ass file from timestamps)
   3. Visual Agent:     ~90s (FFmpeg render: compose video + captions + audio)
   4. Upload Agent:     ~30s (upload to YouTube)
   ↓
Total: ~2-3 minutes per video
```

---

# 5. The Video Generation Pipeline (End-to-End)

```
1. IDEA GENERATION (Gemini)
   ├─ Inputs: genre template, recent videos (avoid repeats), feedback summary
   ├─ Output: 3 ideas with title, hook, angle
   └─ User picks one OR auto-select best

2. SCRIPT WRITING (Gemini)
   ├─ Inputs: selected idea, genre rules, 2 few-shot examples (from Google Sheet)
   ├─ Output: structured JSON with narration, image_cues[], sfx_cues[], word_count
   └─ Validated by Pydantic schema

3. VALIDATION (5 layers — Python + Groq)
   ├─ Layer 1: Pydantic schema validation
   ├─ Layer 2: Content quality checks (word count, hook detection, image cue density)
   ├─ Layer 3: Safety & compliance (YouTube-unsafe patterns, banned phrases)
   ├─ Layer 4: Groq LLM quality rating (cross-model validation, min score 7/10)
   └─ Layer 5: Deduplication check (TF-IDF similarity <70% vs recent scripts)

4. SSML ENHANCEMENT (Python)
   ├─ Auto-add genre-appropriate pauses, emphasis, pitch/rate adjustments
   └─ Output: SSML-tagged narration text

5. TTS GENERATION (Google Cloud TTS)
   ├─ Neural2 (default) or Chirp 3 HD (premium option)
   ├─ Returns: audio file + word-level timestamps via SSML marks
   └─ Fallback: Whisper tiny model for timestamps if SSML marks fail

6. IMAGE FETCHING (7-tier, parallel)
   ├─ Tier 1: Local SQLite cache (15-45ms)
   ├─ Tier 2: Pexels API (400-730ms)
   ├─ Tier 3: Pixabay API (370-680ms)
   ├─ Tier 4: DuckDuckGo images (1.2-4s, CC filter)
   ├─ Tier 5: Wikimedia Commons (700ms-1.5s)
   ├─ Tier 6: LLM query reformulation → retry Tiers 2-5
   └─ Tier 7: Genre fallback from local pre-cached images (100ms, never fails)
   Each image: scored for relevance, resized to 1080x1920, cached for reuse

7. SFX RESOLUTION
   ├─ Check local curated pack (~80 CC0 files, ~15MB, ships with app)
   ├─ Freesound API (filtered: duration 0.5-3s, rating ≥4.0, CC0, genre-tagged)
   └─ Skip if nothing matches (silence > wrong sound)

8. MUSIC SELECTION
   ├─ Pick from curated library (30 CC0 tracks, ~90MB)
   ├─ Librosa energy analysis → find best section of track
   ├─ Beat snapping → cut on beats, not random
   └─ Quality validation (not silent, not clipping, right duration)

9. AUDIO MIXING (pydub + librosa)
   ├─ Layer narration + music + SFX
   ├─ Frequency-aware ducking (music ducks under voice frequencies, not flat volume)
   ├─ SFX placed 200ms BEFORE word trigger (pre-lap — same as film editors)
   └─ LUFS normalization to -14 (YouTube target)

10. CAPTION GENERATION (pysubs2 + PyonFX)
    ├─ 6 display styles: word-at-a-time, sentence highlight, karaoke wipe,
    │                     emphasis-only, bounce pop, typewriter
    ├─ 12 built-in presets mapped to genres
    ├─ Safety: max 2 lines, max 7-8 words, min font 48px, safe zones
    └─ Output: .ass file with animations

11. VIDEO RENDERING (FFmpeg subprocess — NEVER MoviePy)
    ├─ 3 layout modes: full image, split screen, full gameplay
    ├─ Ken Burns effect on images (slow zoom 1.0→1.15x)
    ├─ Transitions between images (dissolve, fade, slide)
    ├─ ASS captions burned via ffmpeg -vf "ass=captions.ass"
    ├─ Settings: -preset medium -crf 20 -pix_fmt yuv420p -movflags +faststart
    └─ Safety: temp file → atomic rename, disk space check, 5-min timeout

12. PREVIEW & USER DECISION
    ├─ Video plays in embedded preview player
    ├─ User can edit title, description, hashtags
    ├─ User chooses: UPLOAD or REGENERATE (1 regen allowed per video)
    └─ If regenerate → user fills feedback form → smart partial re-generation

13. YOUTUBE UPLOAD (YouTube Data API)
    ├─ Title from genre template (with emoji + hashtags)
    ├─ Auto-scheduling based on best posting time (from analytics)
    ├─ AI disclosure field (manual workaround — no API field exists yet)
    └─ Performance tracking starts 24h after upload
```

---

# 6. Preview & Regeneration System

## Why This Exists
Automated ≠ blind. Before ANY video goes to YouTube, the user sees it, approves it, or requests a fix. This is what separates a professional tool from a spam bot.

## The Preview Flow
```
Video rendered → Preview Screen opens
┌────────────────────────────────────────────────────┐
│  🎬 Preview                          [← Back]      │
│                                                     │
│  ┌──────────────────────────────────────────┐       │
│  │                                          │       │
│  │         [ VIDEO PLAYER ]                 │       │
│  │         (plays the full rendered video)   │       │
│  │                                          │       │
│  └──────────────────────────────────────────┘       │
│                                                     │
│  Title: [This Family Found A Sealed Room... 😨  ]   │
│  Description: [Would you stay? 😱             ]     │
│  Hashtags: [#shorts #scary #horror #creepy    ]     │
│  Schedule: [Best time: 6 PM ▼] or [Now]             │
│                                                     │
│  ┌──────────────┐    ┌──────────────────────┐       │
│  │  ✅ UPLOAD    │    │  🔄 REGENERATE (1/1) │       │
│  └──────────────┘    └──────────────────────┘       │
│                                                     │
└────────────────────────────────────────────────────┘
```

## Regeneration System (1 Per Video)

**User gets exactly 1 regeneration per generated video.** This prevents the system from being abused as an infinite generator while still giving users control over quality.

### When User Clicks "Regenerate"

```
Feedback Form opens:
┌────────────────────────────────────────────────────┐
│  🔄 What didn't you like?                           │
│                                                     │
│  [✅] Script / narration content                    │
│  [ ] Voice / audio quality                          │
│  [ ] Images don't match the narration               │
│  [ ] Captions look wrong                            │
│  [ ] Music doesn't fit                              │
│  [ ] Pacing is too fast / too slow                  │
│                                                     │
│  Additional notes (optional):                       │
│  ┌──────────────────────────────────────────┐       │
│  │ The twist was too predictable, make it   │       │
│  │ more surprising. Also the 3rd image was  │       │
│  │ not related to what was being said.      │       │
│  └──────────────────────────────────────────┘       │
│                                                     │
│  [🔄 Regenerate]    [Cancel]                        │
│                                                     │
└────────────────────────────────────────────────────┘
```

### Smart Partial Regeneration

The system only re-runs the stages that need to change:

| User Complaint | What Gets Re-Run | What's Reused |
|---|---|---|
| **Script content** | Script Agent (with feedback injected) → TTS → images → captions → render | Genre template, settings |
| **Voice/audio** | TTS only (different voice or rate) → re-render | Script, images, captions |
| **Images** | Image Agent only (new queries) → re-render | Script, audio, captions |
| **Captions** | Caption Agent only (different style) → re-render | Script, audio, images |
| **Music** | Music selection only → re-mix → re-render | Script, audio, images, captions |
| **Pacing** | SSML adjustment (speaking rate) → TTS → re-render | Script text, images |

**Time savings:** If only images need fixing → ~10 seconds (fetch + render), not 2-3 minutes.

### After Regeneration

```
┌────────────────────────────────────────────────────┐
│  🎬 Compare & Choose                                │
│                                                     │
│  ┌─────────────────┐    ┌─────────────────┐        │
│  │   ORIGINAL      │    │   REGENERATED    │        │
│  │  [▶ Play]       │    │  [▶ Play]        │        │
│  │                 │    │                  │        │
│  │  [Upload This]  │    │  [Upload This]   │        │
│  └─────────────────┘    └─────────────────┘        │
│                                                     │
│  [🗑️ Discard Both]                                  │
│                                                     │
└────────────────────────────────────────────────────┘
```

User sees both versions side-by-side. Picks the one they prefer. Uploads that one. The other is discarded.

### What Happens to Feedback Data
- User feedback is stored locally in SQLite
- After 20+ regenerations across videos, the system detects patterns:
  - "Script" complaints spike → adjust script validation thresholds
  - "Images" complaints spike → tighten image relevance scoring
  - "Pacing" complaints spike → adjust SSML rate defaults
- This feeds back into the self-improvement loop (with user consent)

---

# 7. Script Generation Pipeline (3 Stages)

## Stage 1: Idea Generation
- **Context budget:** ~400 tokens total
- **Inputs:** genre template rules, top 3 performing titles, 3 recent titles (avoid repeats), feedback summary (~85 tokens)
- **Outputs:** 3 ideas, each with title, hook, angle, estimated_duration

## Stage 2: Script Writing
- **Context budget:** ~1200 tokens
- **Inputs:** selected idea, genre writing rules, 2 few-shot examples from Google Sheet
- **Output schema (Pydantic):**

```python
class ImageCue(BaseModel):
    trigger_sentence_index: int
    search_query: str          # "NASA Curiosity rover Mars red terrain"
    visual_description: str
    zoom_direction: str        # "in" | "out" | "left" | "right"

class SfxCue(BaseModel):
    word_trigger: str          # "explosion"
    sfx_type: str              # "impact"
    mood: str                  # "dramatic"

class ScriptOutput(BaseModel):
    title: str                 # Max 60 chars
    narration: str             # Full script text
    word_count: int            # 80-150 words
    estimated_duration: int    # 30, 45, or 60 seconds
    hook_line: str             # First sentence
    image_cues: list[ImageCue]
    sfx_cues: list[SfxCue]
```

## Stage 3: Validation (5 Layers)
1. **Pydantic schema** — structural validity
2. **Content quality** — word count in range, hook present, image cue density ≥1 per 2 sentences
3. **Safety** — YouTube-unsafe patterns, banned phrases, medical/legal claims
4. **Groq cross-validation** — Llama 3.3 70B rates 1-10 on: hook, pacing, clarity, engagement, ending, originality (min 7.0 avg)
5. **Deduplication** — TF-IDF cosine similarity < 70% vs last 50 scripts

**Retry system:** On failure, specific feedback from the failed layer is injected into the retry prompt. Max 3 retries. If 3 fail → different idea → full restart.

---

# 7. TTS & Audio Engineering

## Voice Selection
- **Default:** Google Cloud TTS Neural2 (free tier: 1M chars/month)
- **Premium option:** Chirp 3 HD ($30/4M chars, studio quality)
- **User picks voice during setup** — 6+ Neural2 voices available

## SSML Enhancement (Auto per Genre)

Each genre has a voice profile:

| Genre | Rate | Pitch | Hook Pause | Reveal Pause | Emphasis Words |
|---|---|---|---|---|---|
| Scary | 85-92% | -1 to -2st | 500ms | 700ms | terrifying, sealed, dead |
| Motivation | 100-105% | +0.5st | 300ms | 400ms | success, champion, believe |
| Tech/AI | 95-100% | 0st | 300ms | 500ms | billion, revolutionary, AI |
| History | 90-95% | -0.5st | 400ms | 600ms | ancient, destroyed, secret |

## Word Timestamps
- **Primary:** SSML `<mark>` tags placed between every word → returned in TTS response
- **Fallback:** Whisper `tiny` model (39MB) for alignment if marks fail
- Used for: caption sync, SFX timing, image transition triggers

## Audio Mixing Pipeline
```
TTS narration → base track
  + Music (energy-selected section, beat-snapped) at -14dB (ducked)
  + SFX (pre-lapped 200ms before trigger word) at -8dB
  → Frequency-aware ducking: attenuate music only in 100Hz-4kHz when voice active
  → LUFS normalize to -14
  → Export final_audio.wav
```

---

# 8. Image Fetching (7-Tier Fallback)

```
Script says: [IMAGE: "Tom Holland Spider-Man"]
   ↓
Tier 1: Local Cache (SQLite) → 15-45ms, hit rate 60%+ after month 1
   ↓ miss
Tier 2: Pexels API → 400-730ms, ~85% generic success, alt-text relevance scoring
   ↓ miss
Tier 3: Pixabay API → 370-680ms, has illustrations + vectors, editors_choice filter
   ↓ miss
Tier 4: DuckDuckGo (ddgs) → 1.2-4s, ~95% success, CC filter, exponential backoff
   ↓ miss
Tier 5: Wikimedia Commons → 700ms-1.5s, 70% celebrities, 90% landmarks
   ↓ miss
Tier 6: LLM Reformulation → Gemini rewrites "Spider-Man" → "person in red spandex"
   ↓ miss
Tier 7: Genre Fallback → 100ms, pre-cached images + genre color tint, NEVER fails
```

**Image Scoring:** Each result scored on keyword match (30pts), resolution (20pts), recency (15pts), source reliability (15pts), format (10pts). Top result selected.

**Cache Strategy:** SQLite + local files. Day 1: 0%. Month 1: 40-60%. Month 3+: 70-80%.

**Parallel Execution:** All 5 image slots fetched concurrently. Tiers 2+3 run in parallel per slot. Total time typically 3-3.5s worst case, hidden behind TTS time (~8s).

---

# 9. Background Video & Layout System

## 3 Layout Modes

| Mode | When Used | Visual |
|---|---|---|
| **Full Image** | History, Tech, Science | Images fill 100% of 1080×1920 + Ken Burns + transitions |
| **Split Screen** | Scary, Reddit, Stories | Images top 55% + gameplay bottom 45% |
| **Full Gameplay** | Gaming Facts | Gameplay 100% + captions centered overlay |

## Built-In Gameplay Library (~500MB)
- 8 clips × 5 min each: Minecraft Parkour (3), Subway Surfers (2), Satisfying (2), Nature Aerial (1)
- All vertical 9:16, 1080×1920, 30fps, audio stripped
- **Random segment extraction** — FFmpeg `-c copy` (no re-encode, <100ms)
- User can add their own via Settings (MP4, vertical, min 2 min)

## Image Timing
- Each image mapped to a sentence via `trigger_sentence_index`
- Word timestamps tell us exactly when each sentence starts/ends
- Transitions happen at sentence boundaries (never mid-word)
- Ken Burns: zoompan filter, 1.0x→1.15x over image duration

## FFmpeg Transitions
| Transition | FFmpeg | Best For |
|---|---|---|
| Dissolve | `xfade=transition=dissolve:duration=0.3` | Horror, History |
| Fade | `xfade=transition=fade` | All genres |
| Slide Left | `xfade=transition=slideleft` | Motivation |
| Zoom In | `xfade=transition=circlecrop` | Reveals, twists |

---

# 10. ASS Caption System

## 6 Display Styles
1. **Word-at-a-Time Pop** — each word appears alone, pops in at 120% then settles to 100%
2. **Sentence with Active Word Highlight** — full sentence visible, current word highlighted
3. **Karaoke Wipe** — sentence fills with color left-to-right as spoken (`\k` tags)
4. **Emphasis-Only** — only power words highlighted (bigger, different color, glow)
5. **Bounce Pop** — words bounce in from below with spring animation
6. **Typewriter** — words appear one by one, building sentence progressively

## 12 Built-In Presets
Classic White, Bold Pop, Horror Red, Neon Glow, Minimal, TikTok Style, Karaoke Fill, Typewriter, Comic, Clean Pro, Fire, Ice.

## Caption Safety Rules

| Rule | Value | Why |
|---|---|---|
| Max chars/line | 25 | Fills ~90% of 960px usable width |
| Max lines | 2 | 3+ = cluttered |
| Max words on screen | 7-8 | More = viewer reads instead of watching |
| Side margins | 60px | Prevents edge clipping |
| Top safe zone | 200px | Below YouTube username overlay |
| Bottom safe zone | 250px | Above YouTube buttons |
| Min font size | 48px | Below = unreadable on phone |
| Max font size | 84px | Above = feels childish |
| Min contrast ratio | 4.5:1 | WCAG accessibility |
| Min border | 2px | Text disappears on bright backgrounds without |

## Smart Features
- **Phrase grouping:** Short words ("a", "the", "is") combined with neighbors
- **Dynamic font sizing:** Auto-shrink ≥48px if text overflows
- **Natural break points:** Break at commas, conjunctions, dashes — not mid-phrase
- **Emphasis detection:** From script model SFX triggers, genre template word list, or SSML tags

## Custom Fonts (6 bundled ~5MB)
Roboto Bold, Montserrat Black, Oswald Bold, Bangers, Creepster, Anton (all Google Fonts, OFL/Apache). Users add .ttf/.otf via Settings.

---

# 11. SFX & Music Strategy

## SFX System
- **Local library ships with app:** ~80 CC0 files (~15MB) across 10 categories (transitions, impacts, risers, horror, nature, comedy, tech, emphasis, ambient, UI)
- **API fallback:** Freesound (filtered: duration 0.5-3s, avg_rating ≥4.0, CC0 license, sorted by rating)
- **Genre-aware scoring:** Matching genre tags = +15pts each, anti-tags (e.g., "cartoon" for horror) = -20pts each
- **Timing:** Placed 200ms BEFORE trigger word (pre-lap, standard film technique)
- **If nothing matches → skip** (silence > wrong sound)

## Music System
- **Curated library:** 30 CC0 tracks from Freesound (~90MB), 6 mood categories × 5 tracks
- **Why CC0 from Freesound, not Pixabay:** CC0 = public domain = zero Content ID risk
- **Smart section selection:** Librosa RMS energy analysis → sliding window → pick highest-energy segment matching video duration
- **Beat snapping:** `librosa.beat.beat_track()` → cut/fade-in/fade-out happen ON beats
- **Frequency-aware ducking:** Music voice band (100Hz-4kHz) attenuated when narration active; bass and sparkle remain audible

## Audio Quality Gate
Before any audio enters the mix:
- Is it silent? (RMS < 0.001 → reject)
- Is it clipping? (>0.5s near peak → reject)
- Right duration? (SFX <10s, Music >30s)
- Decent sample rate? (≥16kHz)
- Has actual content? (spectral centroid 500-8000Hz)

---

# 12. Crash-Proof Video Rendering

## Core Principle
**MoviePy is NEVER used for rendering, compositing, or writing video.** Only for reading metadata (duration, fps, size) → immediately close handles. ALL rendering = FFmpeg subprocess.

## 20 Mapped Failure Modes

| Category | Count | Key Mitigations |
|---|---|---|
| MoviePy failures | 7 | Don't use for compositing. FFmpeg `xfade` for transitions. |
| FFmpeg failures | 7 | Validate filter string with dry run, ffprobe every input, 5-min timeout. |
| System failures | 6 | Disk space pre-check (500MB min), temp → atomic rename, antivirus guide. |

## Safe Rendering Architecture
| Step | Tool | Why This Tool |
|---|---|---|
| Image preprocessing | Pillow | Fast in-memory, no subprocess |
| ASS captions | pysubs2 + PyonFX | Purpose-built for karaoke effects |
| Audio mixing | pydub | Simple, reliable |
| Audio analysis | librosa | Scientific audio analysis |
| Video metadata | MoviePy (read-only!) | Then **immediately close** |
| ALL rendering | FFmpeg subprocess | Fast, stable, no memory leaks |

## Safety Checklist (every render)
1. Disk space ≥500MB?
2. All input files exist and pass ffprobe?
3. Filter string passes dry-run validation?
4. FFmpeg found in PATH?
5. Render to `.tmp.mp4` → verify output → atomic rename to final
6. 5-minute hard timeout on FFmpeg process

## Encoding Settings
```
-c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p
-c:a aac -b:a 192k -movflags +faststart
```

## Render Times (40-50s Short)
| Machine | Time |
|---|---|
| Low-end (4GB, i3) | 2-3 min |
| Mid-range (8GB, i5) | 1-1.5 min |
| High-end (16GB+, i7) | 30-45s |

---

# 13. Analytics Intelligence & Feedback Loop

## Collection Schedule
| Snapshot | Delay | Metrics |
|---|---|---|
| 24h | 24 hours | views, likes, comments |
| 48h | 48 hours | + impressions, CTR, retention curve |
| 7d (maturity) | 7 days | ALL metrics |
| 14d (final) | 14 days | ALL metrics |
| 30d | 30 days | views, impressions (long-tail) |

## YouTube API Metrics Collected
- Core: views, engaged views, likes, dislikes, comments, shares, subscribersGained
- Reach: impressions, CTR (click-through rate)
- Quality: avgViewDuration, avgViewPercentage, relativeRetentionPerformance
- Traffic: trafficSourceType (Browse, Search, Suggested, Shorts)
- Shorts-specific: viewedVsSwipedAway

## Pattern Engine (Python math, NOT LLM)
1. **Best hook style:** Group by hook pattern → highest avg retention with ≥3 samples
2. **Optimal duration:** Bucket into 15-25s, 25-35s, 35-50s, 50-65s → best retention
3. **Best posting time:** Correlate upload hour with first-48h views
4. **Topic saturation:** Linear regression of retention per topic → if slope < -2 → stale

## What the LLM Sees (~85 tokens, never raw numbers)
```
Channel trend: upward (+15% week-over-week). Channel health: normal.
Best hook: 'second_person_time' (68% retention). Avoid: 'question' (41%).
Optimal duration: 35-50s. Best posting time: ~18:00.
Topics fatiguing: 'ghost encounters'. Try fresh angles.
```

## Shadow Ban Detection (5 Signals)
1. Impression collapse (>40% drop vs 2-4 weeks ago)
2. Algorithm traffic loss (Browse + Suggested < 25%)
3. New video performance cliff (< 20% of historical first-48h)
4. CTR paradox (CTR >5% but impressions still dropping)
5. Healthy engagement + low reach (engagement >5% but views collapsed)

**3+ signals detected → "likely_suppressed" → pause uploads 48h, shift to safe content, exclude suppressed period from analytics.**

## Storage: SQLite
4 tables: `video_analytics` (per-video snapshots), `channel_daily`, `insights` (cached computed results + prompt text), `suppression_events`.

---

# 14. Self-Improving Example Library

## Architecture: Google Sheets with 3 Tabs

### Tab 1: `reference_scripts` (curated by us)
| genre | script_text | hook_pattern | quality_score | source |
|---|---|---|---|---|
| scary_stories | "Did you know that in 1973..." | question+time | 9 | human_curated |

### Tab 2: `generated_scripts` (auto-filled by pipeline)
Every video generated → script text, config, video_id, performance metrics at 7d/14d.

### Tab 3: `genre_config`
Per-genre: active example count, max age, promotion threshold, variety weight.

## Self-Improvement Loop
```
Pipeline reads 2 best examples → generates new script → uploads video
→ After 14d: analytics scored → if score exceeds threshold AND user consents
→ PROPOSED for promotion → human reviews → approved → added to reference_scripts
→ Next generation benefits from the new example
```

## Freshness Score
```
score = (quality × 0.4) + (recency × 0.2) + (performance × 0.3) + (variety × 0.1)
```

## Access Control
- Read via Google Sheets service account (our key, encrypted in binary)
- Sheet restricted to specific service account email
- Read-only scope: `spreadsheets.readonly`
- User data writes go to Tab 2 with consent gate

---

# 15. Genre Template System

A genre template is a **complete production blueprint** in YAML:

```yaml
genre_id: scary_stories
display_name: "Scary Stories & Mysteries"

script_config:
  system_prompt: "You are a horror narrator..."
  few_shot_count: 2
  word_count_range: [100, 140]
  hook_patterns: ["You {action} {time}. But {twist}.", "The {object}..."]
  banned_phrases: ["Did you know", "Scientists say"]
  tone_descriptors: ["eerie", "unsettling", "suspenseful"]
  pacing: "slow_build_fast_climax"

audio_config:
  tts_voice: "en-US-Neural2-D"
  tts_speaking_rate: 0.85
  tts_pitch: -2.0
  music_mood: ["dark_ambient", "tension"]
  sfx_triggers: { door: "door_creak", phone: "phone_ring_eerie" }
  ducking_db: -14
  sfx_pre_lap_ms: 300

visual_config:
  layout: "split_screen"
  split_ratio: 0.55
  caption_preset: "horror_red"
  caption_font: "Creepster"
  gameplay_type: "minecraft_parkour"
  image_transition: "dissolve"
  ken_burns: true
  ken_burns_zoom: 1.15
  color_grading: "cold_desaturated"

youtube_config:
  title_templates: ["{hook} 😱 #shorts #scary"]
  tags: ["scary stories", "horror shorts", "creepy"]
  category_id: 24
```

## Recommended Genres (Top 10)

| # | Genre | Difficulty | Audience | Rating |
|---|---|---|---|---|
| 1 | Scary Stories | Easy | Huge | ★★★★★ |
| 2 | Psychology Facts | Medium | Large | ★★★★★ |
| 3 | History Facts | Medium | Large | ★★★★★ |
| 4 | Mythology & Legends | Medium | Medium | ★★★★★ |
| 5 | Motivation/Mindset | Easy | Huge | ★★★★☆ |
| 6 | Tech & AI News | Medium | Large | ★★★★☆ |
| 7 | Space & Universe | Medium | Large | ★★★★☆ |
| 8 | Animal Facts | Easy | Huge | ★★★★☆ |
| 9 | Science Facts | Medium | Large | ★★★★☆ |
| 10 | Gaming Facts | Easy | Large | ★★★★☆ |

---

# 16. Desktop Application (Tauri + PyInstaller)

## Why Tauri Over Electron
| Factor | Electron | Tauri |
|---|---|---|
| Install size | ~80-150 MB | ~5-10 MB |
| RAM (idle) | ~400+ MB | ~30-40 MB |
| Startup | 2-5 seconds | <1 second |

## Architecture Stack
```
┌───────────────────────────────────┐
│  Tauri v2 (Rust core)             │
│  ├─ Frontend: HTML/CSS/JS (Vite)  │
│  ├─ License validation (Rust)     │
│  ├─ Keyring (OS credential vault) │
│  └─ Auto-updater                  │
├───────────────────────────────────┤
│  IPC: Tauri commands + SSE events │
├───────────────────────────────────┤
│  Python Backend (PyInstaller)     │
│  ├─ FastAPI on localhost:8742     │
│  ├─ 6 specialist agents          │
│  ├─ PyArmor encrypted bytecode   │
│  └─ Encrypted prompts            │
├───────────────────────────────────┤
│  FFmpeg (bundled, subprocess)     │
└───────────────────────────────────┘
```

## IPC Communication
- **Frontend → Python:** Tauri invoke → Rust command → HTTP to Python localhost
- **Python → Frontend:** Server-Sent Events (SSE) for real-time progress
- SSE data: current stage, percentage, ETA, stage-specific metadata

## PyInstaller Bundling
- Core app: ~60MB (with UPX compression)
- Optional Whisper addon: ~200MB
- PyArmor encrypts bytecode before bundling
- FFmpeg bundled from gyan.dev static builds

## UI Screens
1. **Setup Wizard:** API key entry, voice selection, genre setup
2. **Dashboard:** Generate button, recent videos, analytics summary
3. **Generate Flow:** Real-time pipeline progress with stage animations
4. **Preview:** Watch video before upload, edit title/description
5. **Analytics:** Trend chart, insights, channel health, top videos
6. **Settings:** Voice, captions, music, scheduling, API keys, gameplay library
7. **Caption Editor:** Style selection, font, colors, animations, live preview

---

# 17. Product Security & Anti-Piracy

## 8 Defense Layers

| # | Layer | Protects |
|---|---|---|
| 1 | **PyArmor encryption** | Python source → AES-256 encrypted blobs |
| 2 | **Encrypted prompts** | `prompts.enc` — key split between Rust + machine ID |
| 3 | **OS credential vault** | User's API keys in Windows Credential Manager |
| 4 | **Google Sheet locked** | Restricted to service account, read-only scope |
| 5 | **Server-side prompts** | Prompts built in Python backend, never in HTTP |
| 6 | **Frontend obfuscation** | Vite minification + optional JS obfuscator |
| 7 | **Input sanitization** | Regex + XML sandbox → prevents prompt injection |
| 8 | **Rate limits** | 50/day, 10/hour, 2 concurrent → protects user quotas |

## Anti-Piracy: License Key System
- **Ed25519 signed keys** via `rust-license-key` Rust crate — can't be forged without our private key
- **HWID machine binding:** `SHA256(CPU_ID + disk_serial + OS_install_ID)` → 2 machines max per license
- **Trial:** 3 free videos, all features enabled, no time limit
- **Validation in Rust** compiled native code → much harder to patch than Python
- **Prompt decryption tied to license** → no valid license = no prompts = app won't generate
- **Auto-update requires valid license** → pirated copies can't update
- **Price:** $100 one-time (purchase via Gumroad/Lemonsqueezy → receive key → enter in app)

### Hardware Change Handling
| Change | Effect |
|---|---|
| RAM/GPU upgrade | No change (not in HWID) |
| Windows reinstall + same disk | 1 free re-activation |
| New PC entirely | "Deactivate" button → frees slot → activate on new machine |

---

# 18. Data Collection Sheet (122 Columns)

The research sheet has 14 sections for analyzing viral YouTube Shorts:

| Section | Cols | Key Data |
|---|---|---|
| 📌 Video Info | 10 | URL, channel, views, likes, comments, duration, post time |
| 📝 Script | 4 | **Full transcript** (most critical), word count, WPS |
| 🪝 Hook & Structure | 10 | Hook sentence, hook type, emotional trigger, twist, ending |
| 📊 Script Analysis | 10 | Tense, POV, power/emphasis words, narrative technique, emotional arc |
| ⏱️ Script Pacing | 11 | Sentence length variation, density, surprises, CTA, repetition |
| 🎙️ Voice & Pacing | 7 | Gender, tone, speed, pauses in ms |
| 🖼️ Visuals | 14 | Layout, face, images, transitions, Ken Burns, color grading |
| 📝 Captions | 7 | Style, font, colors, position |
| 🎵 Audio | 11 | Music mood/volume, SFX placements, audio clarity |
| 📤 Upload Metadata | 8 | Title, emoji, hashtags, title pattern type |
| 🔥 Virality Signals | 10 | Engagement ratios (auto-formula), shareability, re-watch, scroll-stop |
| 💬 Engagement | 7 | Comment themes, share triggers, retention hooks |
| 🖼️ Thumbnail | 3 | Style, text, colors |
| ⭐ Scores | 11 | 7 dimension scores (1-10) + why it worked + improvement notes |

**Target:** 15 top-performing + 5 low-performing videos per genre.

---

# 19. Tech Stack Summary

## Python Backend Libraries
| Library | Purpose |
|---|---|
| FastAPI | HTTP server for IPC |
| Pydantic | Schema validation at every boundary |
| google-cloud-texttospeech | TTS + SSML |
| google-api-python-client | YouTube Data/Analytics + Sheets |
| groq | Script validation (Llama 3.3 70B) |
| google-generativeai | Gemini 2.5 Flash |
| pysubs2 | ASS subtitle files |
| PyonFX | Karaoke animation |
| Pillow | Image prep, text measurement |
| pydub | Audio mixing |
| librosa | Audio analysis, beat tracking |
| duckduckgo_search | Image fallback (Tier 4) |
| scikit-learn | TF-IDF deduplication |
| cryptography | Fernet AES for prompt encryption |
| openpyxl | Excel generation |

## Frontend
| Tech | Purpose |
|---|---|
| HTML/CSS/JS | Core UI |
| Vite | Build tool |
| Tauri v2 | Desktop shell (Rust) |
| rust-license-key | License validation |
| tauri-plugin-keyring | Secure credential storage |

## Bundled Tools
| Tool | Purpose |
|---|---|
| FFmpeg | ALL video rendering |
| ffprobe | Asset validation |

---

# 20. User Experience: First Run, Error Recovery & Offline Mode

## First Run Setup
```
1. Install → launch → Welcome screen
2. License key entry (or "Start Free Trial")
3. Setup Wizard:
   ├─ Step 1: Enter API keys (with "Test Connection" button per key)
   ├─ Step 2: Pick a genre (shows descriptions + difficulty ratings)
   ├─ Step 3: Pick a voice (plays sample of each TTS voice)
   ├─ Step 4: Pick caption style (animated preview)
   └─ Step 5: Download assets (gameplay clips ~500MB + music ~90MB + SFX ~15MB)
4. Dashboard → "Generate Your First Video" prominent CTA
```

## Error Recovery
| Error | User Sees | System Does |
|---|---|---|
| API key invalid | "Your Gemini key isn't working. [Re-enter] [Test]" | Specific error from API response |
| TTS fails mid-video | "Audio generation failed. [Retry] [Change Voice]" | Retry up to 3x, then offer different voice |
| Image fetch all tiers fail | Nothing — genre fallback is invisible | Uses pre-cached fallback images |
| FFmpeg crash | "Video rendering failed. [Retry] [Report Bug]" | Logs full error, offers retry with safe settings |
| No internet | "You're offline. [Work Offline] [Retry]" | Can preview old videos, edit settings, can't generate |
| Disk full | "Not enough space ({X}MB free, need 500MB). [Open Folder]" | Blocks render before starting |

## Offline Mode
- Settings, caption editor, analytics dashboard all work offline
- Previously generated videos available for re-preview
- Generation requires internet (API calls)
- Cached assets (images, SFX, music, gameplay) available offline

---

# 21. Tech Stack Summary
