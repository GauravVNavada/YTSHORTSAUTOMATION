# YouTube Shorts Automation — FINAL Product Document

> **The definitive, single-source-of-truth document. Consolidates 20 research files, Deep Research market validation, and all user decisions. This alone is enough to build the product.**

---

# TABLE OF CONTENTS

1. [Product Vision & Positioning](#1-product-vision--positioning)
2. [Business Model](#2-business-model)
3. [Market Validation (Deep Research Summary)](#3-market-validation-deep-research-summary)
4. [BYOK API Inventory](#4-byok-api-inventory)
5. [System Architecture](#5-system-architecture)
6. [User Journey: Onboarding](#6-user-journey-onboarding)
7. [User Journey: Normal Generation](#7-user-journey-normal-generation)
8. [Preview & Regeneration System](#8-preview--regeneration-system)
9. [Script Generation Pipeline](#9-script-generation-pipeline)
10. [TTS & Audio Engineering](#10-tts--audio-engineering)
11. [Image Fetching (7-Tier)](#11-image-fetching-7-tier)
12. [Background Video & Layout System](#12-background-video--layout-system)
13. [ASS Caption System](#13-ass-caption-system)
14. [SFX & Music Strategy](#14-sfx--music-strategy)
15. [Crash-Proof Video Rendering](#15-crash-proof-video-rendering)
16. [Analytics Intelligence & Feedback Loop](#16-analytics-intelligence--feedback-loop)
17. [Self-Improving Example Library](#17-self-improving-example-library)
18. [Genre Template System](#18-genre-template-system)
19. [Desktop App (Tauri + PyInstaller)](#19-desktop-app-tauri--pyinstaller)
20. [Product Security & Anti-Piracy](#20-product-security--anti-piracy)
21. [Data Collection Sheet (122 Columns)](#21-data-collection-sheet-122-columns)
22. [Tech Stack](#22-tech-stack)

---

# 1. Product Vision & Positioning

## The Problem
YouTube Shorts automation tools produce recognizably automated content — robotic TTS, unrelated stock footage, random music, generic captions. Viewers scroll past. Channels stagnate.

## Our Thesis
A tool that produces output **indistinguishable from a skilled human editor** — at zero marginal cost — wins this market. Not by being cheaper. By being **better.**

## What Makes Us Different
1. **Onboarding calibration** — during setup, the system generates 3 sample videos, user picks the style they prefer and tells us what to improve. The system learns from day one.
2. **Self-improving feedback loop** — gets better every week from real YouTube performance data
3. **BYOK = zero cost per user** — users bring their own API keys, our margin is 90-95%
4. **One-time purchase ($100)** — competitors charge $20-150/MONTH. Ours pays for itself in <2 months.
5. **Quality over volume** — cross-model validation (Gemini generates, Groq validates), preview before upload, 1 regeneration per video. We don't produce spam.
6. **Living product** — genres and reference scripts served dynamically from our Google Sheet. We add genres, refresh scripts, and the product improves — no app update needed. Buy once, it keeps getting better.

---

# 2. Business Model

| Item | Detail |
|---|---|
| **Pricing** | **$100 one-time purchase** |
| **Free trial** | None. Paid only. |
| **Cost per user** | $0 — all API keys are user-provided (BYOK) |
| **Gross margin** | 90-95% (only payment processor fees) |
| **Distribution** | Direct download (.exe installer) from marketing site |
| **Payment** | LemonSqueezy or Paddle (handles global tax/VAT + license keys) |
| **License** | Ed25519 signed keys, HWID-bound to 2 machines |
| **Value pitch** | Competitors: $20-150/month = $240-1800/year. Us: $100 once, then free forever. |

---

# 3. Market Validation (Deep Research Summary)

Based on Google Deep Research report with 58 cited sources:

| Finding | Data |
|---|---|
| Video AI tool market | $131M (2024) → **$1.17B by 2032** (37.1% CAGR) |
| YouTube Shorts views | **70 billion daily**, 2.74 billion active users |
| BYOK competitors | **Zero.** No video tool offers BYOK. |
| Can competitors copy BYOK? | **No.** Their VC valuations depend on recurring revenue (MRR). |
| $100 pricing validation | AppSumo proves $39-99 LTDs drive massive conversion. Topaz Video AI ($299) proves creators pay upfront. |
| API free tiers | All validated as sufficient for 6 videos/day |
| Desktop vs cloud advantage | Desktop uploads from user's IP — avoids IP cross-contamination risk that kills SaaS competitors |

### Revenue Projections (at $100/sale)
| Phase | Revenue |
|---|---|
| Month 1-2 (AppSumo launch) | $15,000-25,000 |
| Month 3-6 (affiliates + organic) | $5,000-8,000/month |
| Month 6-12 (word of mouth) | $8,000-15,000/month |

### Top Risks
1. **YouTube API ToS change** → Position as "semi-automated" (user approves every upload)
2. **Gemini goes paid** → Gemini key is user's, and architecture can fallback to Groq
3. **Algorithm burnout** → Our quality validation + shadow ban detection already handles this

---

# 4. BYOK API Inventory

**We NEVER provide, bundle, or ship any API keys. Users provide all keys. Our cost per user = $0.**

### User-Provided Keys

| API | Powers | Free Tier |
|---|---|---|
| **Gemini 2.5 Flash** | Script generation | ~15 RPM, 500 req/day |
| **Google Cloud TTS** | Narration (Neural2/Chirp3 HD) + SSML | 1M chars/month |
| **Google Cloud STT** | Word timestamps (fallback) | 60 min/month |
| **Groq (Llama 3.3 70B)** | Script validation (quality gate) | 500K tokens/day |
| **YouTube Data API** | Upload + scheduling | 10K units/day (**1,600 per upload = max 6/day**) |
| **YouTube Analytics API** | Performance tracking | Same quota |
| **Pexels** | Image search (Tier 2) | 200 req/hour |
| **Pixabay** | Backup images (Tier 3) | 5000 req/hour |
| **Freesound** | SFX (CC0) | 60 req/min |

### Keyless APIs
| API | Purpose |
|---|---|
| **DuckDuckGo (ddgs)** | Image fallback (Tier 4) |
| **Wikimedia Commons** | Public domain images (Tier 5) |

### Our Internal Keys (the ONLY keys we manage)

We use **2 separate Google Sheets** for maximum security:

| Sheet | Service Account | Access | Purpose |
|---|---|---|---|
| **Reference Sheet** | `reference-reader@...` | **Read-only** | Genre list, curated scripts, genre configs, SSML profiles |
| **Submissions Sheet** | `data-writer@...` | **Append-only** | Receives anonymized user performance data (with consent) |

- Both service account keys encrypted in binary (PyArmor + Fernet AES)
- Sheets restricted to their specific service account email only
- User never sees sheet URL, contents, or other users' data
- Even if one key is compromised, the other sheet is on a separate account
- **Cost: $0** (Google Sheets API free tier: 300 reads/min, 60 writes/min)

---

# 5. System Architecture

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

Each agent fails independently, retries with circuit breakers (max 3), Pydantic validation at every boundary.

---

# 6. User Journey: Onboarding

This is the **first-time experience** — happens once when user installs the app.

```
STEP 1: License Key
┌──────────────────────────────────────────────┐
│  🎬 Welcome to YT Shorts Auto               │
│                                              │
│  Enter your license key:                     │
│  [____________________________________]      │
│  [Activate]                                  │
│                                              │
│  Purchase: [Buy License ($100) →]            │
└──────────────────────────────────────────────┘

STEP 2: API Keys (with "Test Connection" per key)
┌──────────────────────────────────────────────┐
│  Step 2 · API Setup                          │
│  🔑 Google Gemini Key    [paste] [✅ Test]   │
│  🔑 YouTube API Key      [paste] [✅ Test]   │
│  🔑 Google Cloud TTS     [paste] [✅ Test]   │
│  🔑 Groq API Key         [paste] [✅ Test]   │
│  🔑 Pexels               [paste] [✅ Test]   │
│  🔑 Pixabay              [paste] [✅ Test]   │
│  🔑 Freesound            [paste] [✅ Test]   │
│                                              │
│  Each has a "📖 Show me how" guide.          │
│  Can't proceed until all green.              │
└──────────────────────────────────────────────┘

STEP 3: YouTube Channel Connection
┌──────────────────────────────────────────────┐
│  Step 3 · Connect Your Channel               │
│  [🔗 Connect YouTube Channel]                │
│  Connected: ✅ @YourChannel (423 subs)       │
└──────────────────────────────────────────────┘

STEP 4: Genre Selection + Intent
(Genre list fetched DYNAMICALLY from our Google Sheet — not hardcoded)
(If we add a new genre to the sheet, all users see it on next launch)
┌──────────────────────────────────────────────┐
│  Step 4 · Pick Your Genre                    │
│                                              │
│  [👻 Scary Stories]  [💪 Motivation]         │
│  [🤖 AI & Tech]     [🏛️ History Facts]      │
│  [🧠 Psychology]    [🌌 Space]              │
│  [🐾 Animal Facts]  [📖 Reddit Stories]     │
│  [⚔️ Mythology]     [🎮 Gaming Facts]       │
│  (+ any new genres we add to the sheet)      │
│                                              │
│  Selected: 👻 Scary Stories                  │
│                                              │
│  What are you looking for from this genre?   │
│  ┌────────────────────────────────────────┐  │
│  │ I want dark, creepy stories with       │  │
│  │ unexpected twists. Not jump scares     │  │
│  │ but slow building dread. Think         │  │
│  │ r/nosleep style. Narration should      │  │
│  │ feel like someone telling you a secret │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  [Generate 3 Sample Videos →]                │
└──────────────────────────────────────────────┘

STEP 5: Genre Calibration (THE KEY STEP)
┌──────────────────────────────────────────────┐
│  Step 5 · Pick Your Style                    │
│                                              │
│  We generated 3 videos for Scary Stories.    │
│  Watch all 3 and pick the one closest to     │
│  what you want.                              │
│                                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │ Video 1 │ │ Video 2 │ │ Video 3 │       │
│  │ [▶ Play]│ │ [▶ Play]│ │ [▶ Play]│       │
│  │         │ │  ✅     │ │         │       │
│  └─────────┘ └─────────┘ └─────────┘       │
│                                              │
│  Why did you pick this one?                  │
│  ┌────────────────────────────────────────┐  │
│  │ The pacing felt right - slow start     │  │
│  │ then builds tension. Voice tone was    │  │
│  │ perfect. Images matched the narration. │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  What could be improved?                     │
│  ┌────────────────────────────────────────┐  │
│  │ Music was too loud at the end. The     │  │
│  │ twist could be less predictable. Want  │  │
│  │ more dramatic pauses before reveals.   │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  [Complete Setup →]                          │
└──────────────────────────────────────────────┘

STEP 6: Download Assets
┌──────────────────────────────────────────────┐
│  Setting up your workspace...                │
│                                              │
│  ⏳ Downloading gameplay clips (~500MB)      │
│  ⏳ Downloading music library (~90MB)        │
│  ⏳ Downloading SFX pack (~15MB)             │
│  ████████████░░░░░░░░ 62%                    │
└──────────────────────────────────────────────┘
```

### What the Calibration Data Does
The user's selection + "why I picked this" + "what to improve" is stored and becomes the **genre calibration profile:**

```python
class GenreCalibration(BaseModel):
    genre_id: str
    user_intent: str          # "dark, creepy stories with twists..."
    preferred_video_id: str   # Which of the 3 they picked
    preferred_script: str     # The full script text of the chosen video
    why_chosen: str           # "Pacing felt right, voice tone perfect..."
    improvement_notes: str    # "Music too loud, twist too predictable..."
    preferred_config: dict    # The exact config (voice, speed, music, captions) used
```

This profile is injected into EVERY future script generation prompt:
```
The user prefers: {user_intent}
They liked: {why_chosen}
They want improved: {improvement_notes}
Reference script style: {preferred_script[:500]}
```

**This is why our output is better — it's calibrated to THIS specific user from day one.**

---

# 7. User Journey: Normal Generation

After onboarding is complete, the user's daily workflow:

```
Dashboard → Click "Generate Video" → Select genre → 1 video generated
→ Preview screen → Edit title/description → UPLOAD or REGENERATE
```

### Generate Screen
```
┌──────────────────────────────────────────────┐
│  🎬 Generate New Video                       │
│                                              │
│  Genre: [Scary Stories ▼]                    │
│                                              │
│  Mode:                                       │
│  (●) Auto — system picks idea + generates    │
│  ( ) Custom — you provide the topic          │
│                                              │
│  Custom Topic (optional):                    │
│  [e.g. "A haunted hospital in Japan"]        │
│                                              │
│  Schedule: [Next best time ▼] or [Now]       │
│                                              │
│  [🎬 Generate Video]                         │
│                                              │
│  ── Advanced Options (▸ expand) ──           │
│  Duration: [Auto] Voice: [Default]           │
│  Captions: [Default] Music: [Auto]           │
└──────────────────────────────────────────────┘
```

**One click → one video.** The system handles everything: idea → script → validate → TTS → images → SFX → music → captions → render.

**Total time: ~2-3 minutes.**

---

# 8. Preview & Regeneration System

### After generation → Preview screen

```
┌──────────────────────────────────────────────┐
│  🎬 Preview                                  │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │         [ VIDEO PLAYER ]               │  │
│  │         (full rendered video)           │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  Title: [This Family Found A Sealed Room 😨] │
│  Description: [Would you stay? 😱         ]  │
│  Hashtags: [#shorts #scary #horror        ]  │
│  Schedule: [Best time: 6 PM ▼] or [Now]      │
│                                              │
│  [✅ UPLOAD]     [🔄 REGENERATE (1/1)]       │
└──────────────────────────────────────────────┘
```

### When user clicks REGENERATE (1 per video)

```
Feedback Form:
┌──────────────────────────────────────────────┐
│  🔄 What didn't you like?                    │
│                                              │
│  [✅] Script / narration content             │
│  [ ] Voice / audio quality                   │
│  [ ] Images don't match narration            │
│  [ ] Captions look wrong                     │
│  [ ] Music doesn't fit                       │
│  [ ] Pacing too fast / too slow              │
│                                              │
│  Additional notes:                           │
│  [The twist was too predictable...]          │
│                                              │
│  [🔄 Regenerate]  [Cancel]                   │
└──────────────────────────────────────────────┘
```

### Smart Partial Regeneration

Only the broken stages re-run:

| Complaint | Re-runs | Reuses |
|---|---|---|
| Script | Script → TTS → images → captions → render | Settings |
| Voice | TTS → render | Script, images, captions |
| Images | Image fetch → render | Script, audio, captions |
| Captions | Caption gen → render | Script, audio, images |
| Music | Music pick → remix → render | Script, audio, images, captions |
| Pacing | SSML adjust → TTS → render | Script text, images |

### After Regeneration → Side-by-Side Compare

```
┌──────────────────────────────────────────────┐
│  🎬 Compare & Choose                         │
│                                              │
│  ┌──────────────┐    ┌──────────────┐       │
│  │  ORIGINAL    │    │ REGENERATED  │       │
│  │  [▶ Play]    │    │  [▶ Play]    │       │
│  │ [Upload This]│    │ [Upload This]│       │
│  └──────────────┘    └──────────────┘       │
│                                              │
│  [🗑️ Discard Both]                           │
└──────────────────────────────────────────────┘
```

User picks which to upload. Feedback stored in SQLite → patterns detected → system self-tunes.

---

# 9. Script Generation Pipeline

## 3 Stages

### Stage 1: Idea Generation (Gemini)
- **Inputs:** Genre template, calibration profile, recent videos (avoid repeats), feedback summary
- **Output:** 1 idea (auto mode) or custom topic from user
- **Context budget:** ~400 tokens

### Stage 2: Script Writing (Gemini)
- **Inputs:** Idea, genre rules, 2 few-shot examples (fetched from Reference Sheet, cached locally), calibration profile
- **Few-shot source:** Our Google Sheet `reference_scripts` tab → fetched once/day → cached in local SQLite. Scripts always fresh without app update.
- **Output (Pydantic schema):**

```python
class ScriptOutput(BaseModel):
    title: str                 # Max 60 chars
    narration: str             # Full script (80-150 words)
    word_count: int
    estimated_duration: int    # 30, 45, or 60 seconds
    hook_line: str
    image_cues: list[ImageCue] # What images when
    sfx_cues: list[SfxCue]     # Sound effects triggers
```

### Stage 3: Validation (5 Layers)
1. **Pydantic schema** — structural validity
2. **Content quality** — word count, hook detection, image cue density
3. **Safety** — YouTube-unsafe patterns, banned phrases
4. **Groq cross-validation** — Llama 3.3 70B rates 1-10 on hook, pacing, clarity, engagement, ending, originality (min 7.0)
5. **Deduplication** — TF-IDF cosine similarity <70% vs recent scripts

Max 3 retries with specific feedback injection.

---

# 10. TTS & Audio Engineering

## Voice
- **Default:** Google Cloud TTS Neural2 (1M chars/month free)
- **Premium:** Chirp 3 HD (user pays)
- **User selects voice during setup**

## SSML Enhancement (per genre)

| Genre | Rate | Pitch | Hook Pause | Reveal Pause |
|---|---|---|---|---|
| Scary | 85-92% | -1 to -2st | 500ms | 700ms |
| Motivation | 100-105% | +0.5st | 300ms | 400ms |
| Tech/AI | 95-100% | 0st | 300ms | 500ms |
| History | 90-95% | -0.5st | 400ms | 600ms |

## Word Timestamps
- Primary: SSML `<mark>` tags → returned in TTS response
- Fallback: Whisper tiny model (39MB)

## Audio Mixing
- Frequency-aware ducking (100Hz-4kHz attenuated when voice active, bass/sparkle remain)
- SFX pre-lapped 200ms before trigger word
- LUFS normalized to -14 (YouTube standard)

---

# 11. Image Fetching (7-Tier)

```
Tier 1: Local Cache (SQLite) → 15-45ms, 60%+ hit rate after month 1
Tier 2: Pexels API → 400-730ms, ~85% generic success
Tier 3: Pixabay API → 370-680ms, illustrations + vectors
Tier 4: DuckDuckGo → 1.2-4s, ~95% success, CC filter
Tier 5: Wikimedia Commons → 700ms-1.5s, 70% celebrities
Tier 6: LLM Reformulation → Gemini rewrites query → retry Tiers 2-5
Tier 7: Genre Fallback → 100ms, pre-cached local images, NEVER fails
```

Each result scored on keyword match (30), resolution (20), recency (15), reliability (15), format (10). All fetched in parallel, hidden behind TTS time.

---

# 12. Background Video & Layout System

## 3 Modes

| Mode | Used For | Layout |
|---|---|---|
| Full Image | History, Tech, Science | Images 100% + Ken Burns + transitions |
| Split Screen | Scary, Reddit, Stories | Images 55% top + gameplay 45% bottom |
| Full Gameplay | Gaming | Gameplay 100% + captions overlay |

## Gameplay Library (~500MB shipped with app)
8 clips × 5 min: Minecraft Parkour (3), Subway Surfers (2), Satisfying (2), Nature Aerial (1). Random segment extraction (<100ms). Users can add their own.

---

# 13. ASS Caption System

## 6 Display Styles
1. Word-at-a-Time Pop (120% → 100%)
2. Sentence with Active Word Highlight
3. Karaoke Wipe (color fill left-to-right)
4. Emphasis-Only (power words highlighted)
5. Bounce Pop (spring animation from below)
6. Typewriter (progressive sentence build)

## 12 Presets
Classic White, Bold Pop, Horror Red, Neon Glow, Minimal, TikTok Style, Karaoke Fill, Typewriter, Comic, Clean Pro, Fire, Ice.

## Safety Rules
- Max 2 lines, 7-8 words on screen, 25 chars/line
- Font: 48px min, 84px max
- Margins: 60px sides, 200px top, 250px bottom
- 4.5:1 contrast ratio (WCAG)
- Phrase grouping for short words
- Dynamic font sizing (never below 48px)

## 6 Bundled Fonts (~5MB)
Roboto Bold, Montserrat Black, Oswald Bold, Bangers, Creepster, Anton.

---

# 14. SFX & Music Strategy

## SFX
- **Local:** ~80 CC0 files (~15MB) across 10 categories
- **API:** Freesound (0.5-3s, rating ≥4.0, CC0)
- **Timing:** 200ms before trigger word (pre-lap)
- **Skip if nothing matches** (silence > wrong sound)

## Music
- **30 CC0 tracks** from Freesound (~90MB)
- **Smart section:** Librosa RMS energy → highest-energy segment
- **Beat snapping:** Cuts on beats via `librosa.beat.beat_track()`
- **Frequency-aware ducking:** Voice band attenuated, bass/sparkle remain
- **Why CC0:** Zero Content ID risk

---

# 15. Crash-Proof Video Rendering

**MoviePy NEVER used for rendering.** Only metadata reading → immediately close. ALL rendering = FFmpeg subprocess.

| Tool | Job |
|---|---|
| Pillow | Image preprocessing |
| pysubs2 + PyonFX | ASS captions |
| pydub | Audio mixing |
| librosa | Audio analysis |
| **FFmpeg** | ALL video rendering |

## Safety
- Disk check ≥500MB, ffprobe validate all inputs
- Dry-run filter validation, 5-min timeout
- Temp file → verify → atomic rename
- Encoding: `-preset medium -crf 20 -pix_fmt yuv420p -movflags +faststart`

## Render Times (40-50s Short)
Low-end: 2-3 min | Mid: 1-1.5 min | High-end: 30-45s

---

# 16. Analytics Intelligence & Feedback Loop

## Collection: 24h → 48h → 7d → 14d → 30d snapshots

## Pattern Engine (Python math, not LLM)
- Best hook style (group by pattern → highest retention)
- Optimal duration (bucket → best retention)
- Best posting time (correlate upload hour → 48h views)
- Topic saturation (linear regression slope)

## What LLM Sees (~85 tokens)
```
Channel: upward (+15% WoW). Health: normal.
Best hook: 'second_person_time' (68%). Avoid: 'question' (41%).
Duration: 35-50s. Post time: ~18:00. Fatiguing: 'ghost encounters'.
```

## Shadow Ban Detection (5 signals)
Impression collapse, traffic shift, performance cliff, CTR paradox, healthy engagement + low reach. 3+ signals → pause 48h, shift to safe content.

## YouTube Upload Quota
**1,600 units per upload** = max 6 uploads/day per API key. UI shows remaining uploads prominently.

---

# 17. Dynamic Google Sheets Architecture (The Living Product)

This is what makes the product **evergreen**. Genres, scripts, and intelligence are served from our cloud-hosted Google Sheets — not baked into the app binary.

## 2-Sheet Architecture

### Sheet 1: Reference Sheet (READ-ONLY)
Our curated content. Users fetch from it, never write to it.

| Tab | Contents | How App Uses It |
|---|---|---|
| `genres` | genre_id, display_name, icon, difficulty, is_active | Populates the genre picker in UI — add a genre here, all users see it |
| `scary_stories` | script_text, hook_pattern, quality_score, word_count | 2 best scripts fetched as few-shot for Gemini |
| `psychology` | (same columns per genre) | Each genre = its own tab |
| `genre_config` | per-genre SSML profiles, caption defaults, layout | Overrides local YAML if sheet version is newer |
| ... | One tab per active genre | Scales to any number of genres |

### Sheet 2: Submissions Sheet (APPEND-ONLY)
Anonymized user performance data. Users write to it (with consent), never read from it.

| Tab | Contents | Who Writes |
|---|---|---|
| `video_submissions` | user_hash, genre, script, views, retention, likes, config | App (after user consent) |
| `regeneration_feedback` | user_hash, genre, complaint_type, notes | App (after regeneration) |

## Caching Strategy

```
App Launch:
1. Check: is local cache < 24 hours old?
   YES → use cache (instant, works offline)
   NO  → fetch from Reference Sheet → update local SQLite cache

On Generation:
1. Read 2 best scripts from LOCAL CACHE (not sheet)
2. Read genre config from LOCAL CACHE
3. Generate video using cached data

Result: Sheet is hit once/day max per user. 10,000 users = 10,000 reads/day = trivial.
```

## Why Not Just Bundle Scripts Locally?

| Bundled (old approach) | Dynamic Sheet (our approach) |
|---|---|
| Scripts baked into app binary | Scripts served from cloud |
| Adding genres = app update | Adding genres = add a sheet tab |
| Stale scripts forever | We swap scripts anytime |
| 15 scripts per genre, fixed | Unlimited, always growing |
| Dead product after purchase | Living product that improves |
| No real-world performance data | User-contributed data makes it better |

## The Self-Improvement Flywheel

```
We curate 15 scripts per genre (initial launch)
    → Users generate videos using these as few-shot examples
    → Video performs well (views > threshold at 14 days)
    → User sees consent prompt:
      ┌──────────────────────────────────────────┐
      │  🎉 Your video hit 2,400 views!          │
      │                                          │
      │  Contribute this script to help           │
      │  improve future generations?              │
      │                                          │
      │  ℹ️ We log: script + metrics only         │
      │  No personal data, channel, or email     │
      │                                          │
      │  [✅ Yes]  [❌ No]                         │
      │  [ ] Auto-contribute in future            │
      └──────────────────────────────────────────┘
    → Anonymized data appended to Submissions Sheet
    → WE review submissions → promote best to Reference Sheet
    → Next generation uses even better examples
    → Cycle continues → product gets better every month
```

## What Gets Submitted (Anonymized)

```python
class VideoSubmission(BaseModel):
    user_hash: str           # SHA256(HWID) — anonymous, can't ID the user
    genre: str               # "scary_stories"
    script_text: str         # The full script
    hook_pattern: str        # "second_person_time"
    word_count: int
    duration: int
    views_14d: int
    retention_avg: float
    likes: int
    caption_style: str
    voice_id: str
    music_mood: str
    timestamp: str
```

**No PII. No username. No channel name. No email. Just performance data.**

## Freshness Score (for selecting few-shot examples)
```
score = quality × 0.4 + recency × 0.2 + performance × 0.3 + variety × 0.1
```
Top 2 scripts by freshness score are used as few-shot examples for Gemini.

## Cost: $0
- Google Sheets API free tier: 300 reads/min, 60 writes/min per project
- With daily caching: 10,000 users = 10,000 reads/day + ~1,000 writes/day = well within limits
- No server, no database, no hosting costs

---

# 18. Genre Template System

Complete YAML blueprint per genre:

```yaml
genre_id: scary_stories
display_name: "Scary Stories & Mysteries"

script_config:
  system_prompt: "You are a horror narrator..."
  few_shot_count: 2
  word_count_range: [100, 140]
  hook_patterns: ["You {action} {time}. But {twist}.", ...]
  banned_phrases: ["Did you know", "Scientists say"]
  pacing: "slow_build_fast_climax"

audio_config:
  tts_voice: "en-US-Neural2-D"
  tts_speaking_rate: 0.85
  tts_pitch: -2.0
  music_mood: ["dark_ambient", "tension"]
  sfx_triggers: { door: "door_creak", phone: "phone_ring_eerie" }

visual_config:
  layout: "split_screen"
  split_ratio: 0.55
  caption_preset: "horror_red"
  caption_font: "Creepster"
  gameplay_type: "minecraft_parkour"
  image_transition: "dissolve"
  ken_burns: true

youtube_config:
  title_templates: ["{hook} 😱 #shorts #scary"]
  tags: ["scary stories", "horror shorts", "creepy"]
```

## 10 Recommended Genres
1. Scary Stories ★★★★★
2. Psychology Facts ★★★★★
3. History Facts ★★★★★
4. Mythology & Legends ★★★★★
5. Motivation ★★★★☆
6. Tech & AI ★★★★☆
7. Space & Universe ★★★★☆
8. Animal Facts ★★★★☆
9. Science Facts ★★★★☆
10. Gaming Facts ★★★★☆

---

# 19. Desktop App (Tauri + PyInstaller)

## Architecture
```
┌─────────────────────────────┐
│  Tauri v2 (Rust)            │
│  ├─ Frontend: HTML/CSS/JS   │
│  ├─ License validation      │
│  ├─ OS Keyring              │
│  └─ Auto-updater            │
├─────────────────────────────┤
│  IPC: Tauri commands + SSE  │
├─────────────────────────────┤
│  Python Backend (PyInstaller)│
│  ├─ FastAPI localhost:8742  │
│  ├─ 6 specialist agents    │
│  ├─ PyArmor encrypted      │
│  └─ Encrypted prompts      │
├─────────────────────────────┤
│  FFmpeg (bundled)           │
└─────────────────────────────┘
```

## UI Screens
1. Dashboard (stats, generate button, insights, quota remaining)
2. Generate (genre select, auto/custom mode)
3. Preview (video player, edit metadata, upload/regenerate)
4. History (all videos with status and views)
5. Analytics (trends, insights, channel health)
6. Settings (voice, captions, music, API keys, gameplay library)
7. Caption Editor (live preview)

---

# 20. Product Security & Anti-Piracy

## 8 Defense Layers
1. **PyArmor** — bytecode → AES-256 encrypted blobs
2. **Encrypted prompts** — key split: Rust + machine ID
3. **OS credential vault** — Windows Credential Manager for API keys
4. **Google Sheets locked** — 2 separate sheets, 2 separate service accounts (read-only + append-only), restricted sharing
5. **Server-side prompts** — built in Python, never in HTTP
6. **Frontend obfuscation** — Vite minification
7. **Input sanitization** — prevents prompt injection
8. **Rate limits** — 50/day, 10/hour, 2 concurrent

## License Key System
- Ed25519 signed (Rust `rust-license-key`)
- HWID binding: SHA256(CPU_ID + disk_serial + OS_install_ID) → 2 machines max
- Validation in compiled Rust (not Python)
- No valid license = no prompt decryption = app doesn't generate
- Auto-update requires valid license
- $100 via Gumroad/LemonSqueezy → receive key → enter in app

---

# 21. Data Collection Sheet (122 Columns)

14 sections for genre research:

| Section | Cols | Key Data |
|---|---|---|
| 📌 Video Info | 10 | URL, channel, views, likes, comments, duration |
| 📝 Script | 4 | **Full transcript**, word count, WPS |
| 🪝 Hook & Structure | 10 | Hook sentence, type, emotional trigger, twist |
| 📊 Script Analysis | 10 | Tense, POV, power words, narrative technique |
| ⏱️ Script Pacing | 11 | Sentence variation, density, surprises, CTA |
| 🎙️ Voice | 7 | Gender, tone, speed, pauses |
| 🖼️ Visuals | 14 | Layout, images, transitions, Ken Burns |
| 📝 Captions | 7 | Style, font, colors, position |
| 🎵 Audio | 11 | Music, SFX, ducking, clarity |
| 📤 Upload | 8 | Title, emoji, hashtags, pattern type |
| 🔥 Virality | 10 | Engagement ratios, shareability, scroll-stop |
| 💬 Engagement | 7 | Comment themes, share triggers |
| 🖼️ Thumbnail | 3 | Style, text, colors |
| ⭐ Scores | 11 | 7 dimensions (1-10) + notes |

Target: 15 top + 5 low-performing per genre.

---

# 22. Tech Stack

## Python Backend
| Library | Purpose |
|---|---|
| FastAPI | IPC server |
| Pydantic | Schema validation |
| google-cloud-texttospeech | TTS + SSML |
| google-api-python-client | YouTube + Sheets |
| groq | Script validation |
| google-generativeai | Gemini 2.5 Flash |
| pysubs2 + PyonFX | ASS captions |
| Pillow | Image processing |
| pydub | Audio mixing |
| librosa | Audio analysis |
| duckduckgo_search | Image fallback |
| scikit-learn | Deduplication |
| cryptography | Prompt encryption |

## Frontend
HTML/CSS/JS + Vite + Tauri v2 + rust-license-key + tauri-plugin-keyring

## Bundled
FFmpeg + ffprobe (from gyan.dev static builds)

---

> **This is the FINAL document.** Research phase complete. Ready for implementation.
>
> **Document version:** February 27, 2026 (updated with Dynamic Sheets architecture)
> **Research files consolidated:** 20 research files + Deep Research market validation (58 sources)
> **Key architecture:** Dynamic Google Sheets (genres + scripts served from cloud, user data logged back)
