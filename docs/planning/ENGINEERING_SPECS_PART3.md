# Engineering Specifications — Part 3
## Data Contract Map | Regression Checklist | Single-Developer Continuity Plan

---

# 9. Data Contract Map

Every data transformation in the system, from input to output.

```mermaid
flowchart TD
    subgraph "EXTERNAL → APP"
        SHEET_R["📗 Reference Sheet<br/>(Google Sheets)"] -->|"genres, scripts,<br/>genre_config"| CACHE["💾 sheets_cache.db<br/>(SQLite)"]
        USER_KEY["🔑 User API Keys<br/>(OS Vault)"] -->|"at startup"| SERVICES["Services Layer"]
        USER_INPUT["👤 User Input<br/>(genre, mode, topic)"] -->|"GenerateRequest"| ORCH["Orchestrator"]
    end

    subgraph "PIPELINE (internal data flow)"
        CACHE -->|"Genre + GenreConfig<br/>+ 2 reference scripts"| SCRIPT_A["Script Agent"]
        ORCH -->|"GenerateRequest"| SCRIPT_A

        SCRIPT_A -->|"ScriptOutput<br/>(title, narration,<br/>image_cues, sfx_cues)"| SPLIT{{"Split"}}

        SPLIT -->|"narration +<br/>GenreConfig"| AUDIO_A["Audio Agent"]
        SPLIT -->|"image_cues +<br/>sfx_cues"| ASSET_A["Asset Agent"]

        AUDIO_A -->|"AudioBundle<br/>(audio.wav,<br/>word_timestamps[])"| VISUAL_A["Visual Agent"]

        ASSET_A -->|"AssetBundle<br/>(image_paths[],<br/>sfx_paths[],<br/>music_path)"| AUDIO_A
        ASSET_A -->|"AssetBundle"| VISUAL_A

        VISUAL_A -->|"VideoResult<br/>(video.mp4,<br/>title, description,<br/>hashtags)"| PREVIEW["Preview State"]
    end

    subgraph "USER DECISION"
        PREVIEW -->|"UploadRequest"| UPLOAD_A["Upload Agent"]
        PREVIEW -->|"RegenerateRequest<br/>(complaints, notes)"| REGEN["Regeneration Router"]
        REGEN -->|"re-run subset<br/>of agents"| SPLIT2{{"Partial Re-run"}}
        SPLIT2 --> AUDIO_A
        SPLIT2 --> ASSET_A
        SPLIT2 --> SCRIPT_A
    end

    subgraph "APP → EXTERNAL"
        UPLOAD_A -->|"video.mp4 +<br/>title, desc, tags"| YT["📺 YouTube<br/>(Data API v3)"]
        YT -->|"youtube_video_id"| ANALYTICS["analytics.db"]
        ANALYTICS -->|"performance data<br/>(views, retention)"| FB_A["Feedback Agent"]
        FB_A -->|"FeedbackSummary<br/>(~85 tokens)"| CACHE
        FB_A -->|"VideoSubmission<br/>(anonymized)"| SHEET_W["📕 Submissions Sheet<br/>(Google Sheets)"]
    end

    style SHEET_R fill:#4CAF50,color:white
    style SHEET_W fill:#f44336,color:white
    style CACHE fill:#2196F3,color:white
    style YT fill:#f44336,color:white
```

### Contract: What Crosses Each Boundary

| From → To | Data Model | Size | Validation |
|---|---|---|---|
| Sheet → Cache | `Genre`, `GenreConfig`, raw scripts | ~50KB | Pydantic on read |
| Cache → Script Agent | `GenreConfig` + 2 script strings | ~2KB | Pydantic |
| Script Agent → Audio | `ScriptOutput.narration` (str) | ~500B | word count 80-150 |
| Script Agent → Asset | `ImageCue[]`, `SfxCue[]` | ~1KB | min 3 image cues |
| Audio Agent → Visual | `AudioBundle` (wav path + timestamps) | path ref | file exists check |
| Asset Agent → Visual | `AssetBundle` (paths) | path refs | all files exist |
| Visual Agent → Preview | `VideoResult` (mp4 path + metadata) | path ref | ffprobe valid |
| Preview → YouTube | mp4 + title + desc + tags | ~50MB | YouTube API limits |

### Data Model Dependency Graph

```mermaid
graph TD
    GR["GenerateRequest"] --> SO["ScriptOutput"]
    SO --> IC["ImageCue[]"]
    SO --> SC["SfxCue[]"]
    SO --> AB["AssetBundle"]
    SO --> AUB["AudioBundle"]
    AB --> AUB
    AUB --> VR["VideoResult"]
    AB --> VR
    VR --> PR["PreviewResponse"]
    VR --> UR["UploadRequest"]
    RR["RegenerateRequest"] --> VR

    style GR fill:#E8EAF6
    style SO fill:#C8E6C9
    style VR fill:#FFCCBC
    style PR fill:#FFF9C4
```

---

# 10. Regression Checklist

Run this checklist **before every merge to main** and **before every release**.

```mermaid
flowchart TD
    START["Feature Complete"] --> UNIT["1️⃣ Unit Tests Pass?"]
    UNIT -->|✅| MODELS["2️⃣ models.py unchanged<br/>or both devs agreed?"]
    UNIT -->|❌| FIX1["Fix unit tests"]
    FIX1 --> UNIT

    MODELS -->|✅| API["3️⃣ API contract<br/>matches DEVELOPMENT<br/>_CONTRACT.md?"]
    MODELS -->|❌| SYNC["Sync with other dev"]
    SYNC --> MODELS

    API -->|✅| PYDANTIC["4️⃣ All inputs/outputs<br/>Pydantic validated?"]
    API -->|❌| FIX2["Fix API shape"]
    FIX2 --> API

    PYDANTIC -->|✅| ERRORS["5️⃣ All errors return<br/>APIError format?"]
    PYDANTIC -->|❌| FIX3["Add Pydantic models"]
    FIX3 --> PYDANTIC

    ERRORS -->|✅| LOGS["6️⃣ Logging uses<br/>structured logger?<br/>No print()?"]
    ERRORS -->|❌| FIX4["Fix error returns"]
    FIX4 --> ERRORS

    LOGS -->|✅| PATHS["7️⃣ No hardcoded<br/>paths or URLs?"]
    LOGS -->|❌| FIX5["Replace print → logger"]
    FIX5 --> LOGS

    PATHS -->|✅| SECRETS["8️⃣ No secrets or<br/>API keys in code?"]
    PATHS -->|❌| FIX6["Use pathlib + config"]
    FIX6 --> PATHS

    SECRETS -->|✅| MERGE["✅ SAFE TO MERGE"]
    SECRETS -->|❌| FIX7["Remove + rotate key"]
    FIX7 --> SECRETS

    style MERGE fill:#4CAF50,color:white
    style FIX1 fill:#f44336,color:white
    style FIX2 fill:#f44336,color:white
    style FIX3 fill:#f44336,color:white
    style FIX4 fill:#f44336,color:white
    style FIX5 fill:#f44336,color:white
    style FIX6 fill:#f44336,color:white
    style FIX7 fill:#f44336,color:white
```

### Pre-Merge Checklist (copy to PR description)

```markdown
## Pre-Merge Checklist
- [ ] Unit tests pass (`pytest backend/tests/`)
- [ ] No changes to `models.py` OR other dev notified
- [ ] API responses match DEVELOPMENT_CONTRACT.md
- [ ] All function inputs/outputs use Pydantic models
- [ ] All errors return `APIError` format
- [ ] All logging uses structured logger (no `print()`)
- [ ] No hardcoded paths (all via `config.py` + `pathlib`)
- [ ] No API keys, secrets, or credentials in code
- [ ] No files over 300 lines
- [ ] No functions over 50 lines
- [ ] Commit messages follow `type: description` format
- [ ] Feature matches PRD scope (nothing extra added)
```

### Pre-Release Checklist (before any version bump)

```markdown
## Pre-Release Checklist
- [ ] ALL pre-merge checks pass
- [ ] End-to-end test: generate → preview → upload (1 real video)
- [ ] Onboarding flow works from clean install
- [ ] All 13 API endpoints return correct shapes
- [ ] SSE progress stream works (frontend shows real progress)
- [ ] Regeneration produces different video + compare works
- [ ] YouTube quota display shows correct numbers
- [ ] Settings changes take effect on next generation
- [ ] App starts and stops cleanly (no zombie processes)
- [ ] Crash recovery works (kill mid-render → restart → resume)
- [ ] License validation works (invalid key = blocked)
- [ ] Log file rotation works (doesn't fill disk)
- [ ] Genres load from Google Sheet cache
```

---

# 11. Single-Developer Continuity Plan

What happens if one of you has to step away, is sick, or needs to hand off work.

```mermaid
flowchart TD
    subgraph "Knowledge Bus"
        direction LR
        DCA["FINAL_PRODUCT.md<br/>What to build"] 
        DCB["PRD.md<br/>Requirements"]
        DCC["SYSTEM_ARCHITECTURE.md<br/>How it's built"]
        DCD["DEVELOPMENT_CONTRACT.md<br/>How to code it"]
        DCE["ENGINEERING_SPECS<br/>All diagrams"]
    end

    DCA & DCB & DCC & DCD & DCE --> ANY["Any developer<br/>(even a new person)<br/>can read these 5 docs<br/>and understand everything"]

    ANY --> B1["Can build backend<br/>from SYSTEM_ARCHITECTURE<br/>+ DEVELOPMENT_CONTRACT"]
    ANY --> B2["Can build frontend<br/>from PRD<br/>+ API Contract"]
    ANY --> B3["Can test everything<br/>from REGRESSION_CHECKLIST<br/>+ Testing Levels"]
```

### If Dev A (Backend) Is Unavailable

```mermaid
flowchart TD
    A["Dev A unavailable"] --> Q{"Backend built?"}
    Q -->|"Not yet"| R1["Dev B reads:<br/>1. SYSTEM_ARCHITECTURE.md<br/>2. DEVELOPMENT_CONTRACT.md §4-5<br/>3. ENGINEERING_SPECS Part 2 §7-8"]
    Q -->|"Partially"| R2["Dev B reads:<br/>1. Git log for last commits<br/>2. Pipeline state machine<br/>3. Tests in backend/tests/"]
    Q -->|"Mostly done"| R3["Dev B can:<br/>1. Run existing tests<br/>2. Fix bugs using error logs<br/>3. Continue from checkpoint"]

    R1 --> ACT1["Build backend agents<br/>following the contract"]
    R2 --> ACT2["Continue from<br/>last working state"]
    R3 --> ACT3["Focus on integration<br/>+ bug fixes"]

    style A fill:#f44336,color:white
```

### If Dev B (Frontend) Is Unavailable

```mermaid
flowchart TD
    A["Dev B unavailable"] --> Q{"Frontend built?"}
    Q -->|"Not yet"| R1["Dev A reads:<br/>1. PRD.md (UI sections)<br/>2. FINAL_PRODUCT.md §6-8 (UI mockups)<br/>3. DEVELOPMENT_CONTRACT.md §4"]
    Q -->|"Partially"| R2["Dev A reads:<br/>1. Git log<br/>2. Existing components in frontend/src/<br/>3. api.js for IPC patterns"]
    Q -->|"Mostly done"| R3["Dev A can:<br/>1. Test via browser DevTools<br/>2. Fix styling/layout<br/>3. Wire remaining endpoints"]

    R1 --> ACT1["Build UI screens<br/>following mockups in docs"]
    R2 --> ACT2["Continue from<br/>last working screen"]
    R3 --> ACT3["Polish + integration"]

    style A fill:#f44336,color:white
```

### Continuity Rules

| Rule | Why |
|---|---|
| **Push code daily** | Other dev can always see current state |
| **Write descriptive commits** | Git log = progress journal |
| **Keep docs updated** | Docs are the handoff mechanism |
| **Tests ARE documentation** | Reading tests shows how code works |
| **No knowledge in your head only** | If it's not in a doc or in code, it doesn't exist |

### Bus Factor Mitigation

| Risk | Mitigation |
|---|---|
| Only one dev knows the API contract | It's in `DEVELOPMENT_CONTRACT.md` — both read it |
| Only one dev knows the state machine | It's in `ENGINEERING_SPECS Part 2 §8` — documented |
| Only one dev knows the Sheets integration | It's in `GCP_SETUP_GUIDE.md` + `sheets_client.py` |
| Only one dev knows the build process | It's in `SYSTEM_ARCHITECTURE.md §9` |
| Only one dev knows the license system | It will be in `frontend/src-tauri/src/license.rs` with comments |

### The "Hit by a Bus" Test

> **If either developer disappears tomorrow, can the other person:**
> 1. ✅ Understand what the product does? → `FINAL_PRODUCT.md`
> 2. ✅ Know what's left to build? → `PRD.md` + git log
> 3. ✅ Continue building? → `DEVELOPMENT_CONTRACT.md` + `ENGINEERING_SPECS`
> 4. ✅ Test what's built? → `Regression Checklist` + `backend/tests/`
> 5. ✅ Deploy? → `SYSTEM_ARCHITECTURE.md §9`
>
> **If all answers are YES, continuity is ensured.**
