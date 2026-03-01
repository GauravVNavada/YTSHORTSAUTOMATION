# Product Requirements Document (PRD)
## YouTube Shorts Automation Desktop Application

| Field | Value |
|---|---|
| **Product Name** | YT Shorts Auto (working title) |
| **Version** | 1.0 |
| **Date** | March 1, 2026 |
| **Status** | Approved for Development |
| **Reference** | [FINAL_PRODUCT.md](file:///C:/Users/vgaur/Desktop/YTSHORTSAUTOMATION/FINAL_PRODUCT.md) |

---

## 1. Product Overview

### 1.1 Problem Statement
YouTube Shorts automation tools produce recognizably automated content — robotic TTS, unrelated stock footage, random music, generic captions. Creators using these tools see diminishing returns as YouTube's algorithm penalizes low-quality AI content. The market is dominated by $20-150/month SaaS subscriptions that eat into creator margins.

### 1.2 Solution
A Windows desktop application that autonomously generates production-quality YouTube Shorts — scripts, narration, images, captions, SFX, music, and video rendering — then uploads to YouTube. The app produces output indistinguishable from a skilled human editor.

### 1.3 Key Differentiators

| # | Differentiator | Why It Matters |
|---|---|---|
| 1 | **BYOK (Bring Your Own Key)** | Zero cost per user. No competitor offers this. |
| 2 | **$100 one-time** | Competitors charge $240-1800/year |
| 3 | **Onboarding calibration** | 3 sample videos → user picks style → system learns |
| 4 | **Cross-model validation** | Gemini generates, Groq validates (5-layer pipeline) |
| 5 | **Self-improving** | Analytics feedback loop + user-contributed performance data |
| 6 | **Living product** | Genres + scripts served from cloud sheet, always fresh |

---

## 2. Target Users

### Primary Persona: "Faceless Channel Operator"
- Runs 1-3 YouTube channels monetized through Shorts
- Technically comfortable (can get API keys with a guide)
- Currently paying $30-100/month for inferior tools or spending 2-4 hours/day editing manually
- Cares about: cost efficiency, video quality, channel growth, time saved

### Secondary Persona: "Side Hustle Creator"
- Has a full-time job, wants passive YouTube income
- Needs maximum automation with minimum daily involvement
- Willing to pay $100 upfront to avoid monthly drain
- Cares about: ease of setup, "set and forget" with quality guardrails

---

## 3. Business Model

| Item | Detail |
|---|---|
| Pricing | **$100 one-time** |
| Free trial | None |
| Cost per user | $0 (BYOK) |
| Gross margin | 90-95% |
| Distribution | Direct download (.exe) via marketing site |
| Payment processor | LemonSqueezy / Paddle |
| License | Ed25519 signed, HWID-bound to 2 machines |

---

## 4. Functional Requirements

### FR-1: Onboarding (First Launch)

| ID | Requirement | Priority |
|---|---|---|
| FR-1.1 | License key activation screen (no free trial) | P0 |
| FR-1.2 | API key entry for 7 services with "Test Connection" per key | P0 |
| FR-1.3 | "Show me how" step-by-step guide per key (embedded in app) | P0 |
| FR-1.4 | YouTube channel OAuth2 connection | P0 |
| FR-1.5 | Genre selection from **dynamic list fetched from Google Sheet** | P0 |
| FR-1.6 | User writes a prompt describing what they want from the genre | P0 |
| FR-1.7 | System generates **3 calibration videos** for selected genre | P0 |
| FR-1.8 | User picks 1 video + writes "why I chose this" + "what to improve" | P0 |
| FR-1.9 | Calibration profile stored locally and injected into all future prompts | P0 |
| FR-1.10 | Asset download (gameplay ~500MB, music ~90MB, SFX ~15MB) | P0 |

### FR-2: Video Generation (Daily Use)

| ID | Requirement | Priority |
|---|---|---|
| FR-2.1 | One-click "Generate Video" from dashboard | P0 |
| FR-2.2 | Genre selector (populated from cached Google Sheet data) | P0 |
| FR-2.3 | Auto mode (system picks idea) and Custom mode (user provides topic) | P0 |
| FR-2.4 | Script generation via Gemini with genre template + calibration profile | P0 |
| FR-2.5 | 5-layer script validation (Pydantic → quality → safety → Groq → dedup) | P0 |
| FR-2.6 | SSML enhancement based on genre voice profile | P0 |
| FR-2.7 | TTS via Google Cloud (Neural2/Chirp3) with word timestamps | P0 |
| FR-2.8 | 7-tier image fetching with relevance scoring + caching | P0 |
| FR-2.9 | SFX resolution (local library → Freesound → skip) | P1 |
| FR-2.10 | Music selection with librosa energy analysis + beat snapping | P1 |
| FR-2.11 | Frequency-aware audio ducking + LUFS normalization | P0 |
| FR-2.12 | ASS caption generation (6 styles, 12 presets, safety rules) | P0 |
| FR-2.13 | FFmpeg video rendering (3 layout modes, Ken Burns, transitions) | P0 |
| FR-2.14 | Real-time pipeline progress via SSE (stage, %, ETA) | P0 |
| FR-2.15 | Total generation time target: **2-3 minutes** on mid-range hardware | P1 |

### FR-3: Preview & Regeneration

| ID | Requirement | Priority |
|---|---|---|
| FR-3.1 | Embedded video player for preview before upload | P0 |
| FR-3.2 | Editable title, description, hashtags, schedule on preview screen | P0 |
| FR-3.3 | "Upload" button → sends to YouTube | P0 |
| FR-3.4 | "Regenerate" button (1 per video) with feedback form | P0 |
| FR-3.5 | Feedback form: checkboxes (script/voice/images/captions/music/pacing) + notes | P0 |
| FR-3.6 | Smart partial regeneration — only re-run broken stages | P0 |
| FR-3.7 | Side-by-side compare of original vs regenerated | P0 |
| FR-3.8 | User chooses which version to upload or discards both | P0 |

### FR-4: Analytics & Feedback Loop

| ID | Requirement | Priority |
|---|---|---|
| FR-4.1 | YouTube Analytics API data collection (24h/48h/7d/14d/30d) | P1 |
| FR-4.2 | Pattern engine: best hook, optimal duration, posting time, topic saturation | P1 |
| FR-4.3 | Compressed insights injected into Gemini prompts (~85 tokens) | P1 |
| FR-4.4 | Shadow ban detection (5 signals) with auto-pause recommendation | P1 |
| FR-4.5 | Dashboard showing channel health, trends, quota remaining | P1 |

### FR-5: Dynamic Google Sheets

| ID | Requirement | Priority |
|---|---|---|
| FR-5.1 | Fetch genre list from Reference Sheet on app launch | P0 |
| FR-5.2 | Fetch reference scripts per genre from sheet | P0 |
| FR-5.3 | Cache all sheet data locally (SQLite), refresh every 24h | P0 |
| FR-5.4 | Work offline using cached data | P0 |
| FR-5.5 | Consent-gated performance data submission to Submissions Sheet | P1 |
| FR-5.6 | Anonymized submissions (SHA256 HWID, no PII) | P0 |

### FR-6: Settings & Configuration

| ID | Requirement | Priority |
|---|---|---|
| FR-6.1 | API key management (re-enter, test, update) | P0 |
| FR-6.2 | Voice selection with audio preview | P1 |
| FR-6.3 | Caption style editor with live preview | P1 |
| FR-6.4 | Custom font upload (.ttf/.otf) | P2 |
| FR-6.5 | Gameplay library management (add/remove clips) | P2 |
| FR-6.6 | Rate limit display (uploads remaining, API quotas) | P0 |

---

## 5. Non-Functional Requirements

### Performance
| Metric | Target |
|---|---|
| App startup | < 3 seconds |
| Script generation | < 8 seconds |
| Full video generation | < 3 minutes (mid-range PC) |
| Sheet cache refresh | < 5 seconds |
| App idle RAM | < 80 MB (Tauri) |

### Security
| Requirement | Implementation |
|---|---|
| API keys encrypted at rest | OS Credential Manager (Windows Credential Vault) |
| Source code protected | PyArmor AES-256 bytecode encryption |
| Prompts protected | Fernet AES, key split across Rust + machine ID |
| License validation | Ed25519 in compiled Rust, HWID-bound |
| Sheet data inaccessible to user | Separate service accounts, encrypted keys |
| No prompt injection possible | Regex + XML sandbox on all user inputs |

### Reliability
| Requirement | Target |
|---|---|
| Image fetch success rate | > 99.5% (7-tier fallback) |
| Video render success rate | > 99% (FFmpeg with validation + retry) |
| Graceful degradation | Works offline for settings/preview/analytics |
| Video corruption prevention | Temp file → ffprobe validate → atomic rename |

---

## 6. User Stories

### Onboarding
- **US-1:** As a new user, I enter my license key and API keys so I can start generating videos.
- **US-2:** As a new user, I connect my YouTube channel so the app can upload and track analytics.
- **US-3:** As a new user, I select a genre and describe what I want, so the system calibrates to my style from the first video.
- **US-4:** As a new user, I watch 3 sample videos and pick my favorite with feedback, so the system knows my preferences.

### Daily Generation
- **US-5:** As a creator, I click one button to generate a complete video, so I can produce content in under 3 minutes.
- **US-6:** As a creator, I preview the video before uploading, so I maintain quality control.
- **US-7:** As a creator, I regenerate a video I don't like with specific feedback, so the system fixes only what's wrong.
- **US-8:** As a creator, I compare original vs regenerated side-by-side, so I can pick the best version.

### Growth
- **US-9:** As a creator, I see analytics insights on my dashboard, so I know what's working.
- **US-10:** As a creator, the system warns me if my channel may be shadow banned, so I can pause and recover.
- **US-11:** As a creator, I contribute my successful scripts anonymously, so the product improves for everyone.

---

## 7. Success Metrics

| Metric | Target (Month 6) |
|---|---|
| Video generation success rate | > 95% |
| User-reported video quality (1-10 survey) | > 7.5 |
| Daily active users / total users | > 40% |
| Average videos per user per day | 2-4 |
| Regeneration rate (% of videos regenerated) | < 25% |
| Consent rate for data contribution | > 50% |
| Refund rate | < 5% |

---

## 8. Release Plan

| Phase | Scope | Timeline |
|---|---|---|
| **Phase 1: Core Pipeline** | Script gen, TTS, images, audio, captions, FFmpeg render, Sheets integration | Week 1-3 |
| **Phase 2: Desktop Shell** | Tauri setup, PyInstaller, IPC, SSE, license keys | Week 3-4 |
| **Phase 3: UI** | Onboarding, dashboard, generate, preview/regen, analytics, settings | Week 4-6 |
| **Phase 4: Polish** | PyArmor, security, shadow ban, self-improvement, auto-update, testing | Week 6-8 |
| **Launch** | AppSumo + ProductHunt + Reddit | Week 9 |

---

## 9. Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| YouTube API ToS bans automation | High | Position as "semi-automated" — user approves every upload |
| Gemini free tier removed | Medium | LLM-agnostic interface; Groq can serve as fallback |
| Algorithm penalizes AI content | Medium | Quality validation + shadow ban detection |
| User can't get API keys (too complex) | Medium | Embedded step-by-step guides with screenshots |
| YouTube upload quota (6/day limit) | Low | Prominent UI warnings + quota tracking |

---

## 10. Dependencies

| Dependency | Type | Risk |
|---|---|---|
| Google Gemini API | External (user key) | Free tier changes |
| Google Cloud TTS | External (user key) | Pricing changes |
| Groq API | External (user key) | Free tier changes |
| YouTube Data API v3 | External (user key) | ToS changes, quota |
| Pexels / Pixabay / Freesound | External (user key) | Rate limits |
| Google Sheets API | Internal (our key) | Free tier: 300 reads/min |
| FFmpeg | Bundled binary | Stable, no risk |
| Tauri v2 | Framework | Active development, good community |

---

## 11. Out of Scope (v1.0)

- Mobile app (iOS/Android)
- macOS support (Windows-first, macOS in v1.1)
- Multi-language TTS (English only in v1.0)
- AI-generated thumbnails
- Long-form video support
- Team/agency features
- Batch generation (1 video at a time in v1.0)
