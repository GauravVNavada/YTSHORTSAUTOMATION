# Engineering Specifications — Part 2
## Config Management | Release Cadence | Agent Isolation | Orchestrator State Machine

---

# 5. Configuration Management Strategy

```mermaid
flowchart TD
    subgraph "Config Hierarchy (highest priority wins)"
        direction TB
        ENV["🔴 Environment Variables<br/>Override everything<br/>DEV_MODE=true"]
        CLI["🟠 Runtime Flags<br/>--port 8742 --debug"]
        USER["🟡 User Settings<br/>settings.json<br/>(voice, captions, genre)"]
        GENRE["🟢 Genre Config<br/>From Google Sheet cache<br/>(voice, rate, layout)"]
        DEFAULT["🔵 Defaults<br/>Hardcoded in config.py<br/>(fallback values)"]
    end

    ENV --> MERGE["Config Resolver<br/>Merges all layers"]
    CLI --> MERGE
    USER --> MERGE
    GENRE --> MERGE
    DEFAULT --> MERGE
    MERGE --> APP["Final AppConfig<br/>(Pydantic validated)"]

    style ENV fill:#f44336,color:white
    style CLI fill:#FF9800,color:white
    style USER fill:#FFEB3B
    style GENRE fill:#4CAF50,color:white
    style DEFAULT fill:#2196F3,color:white
```

### Config Files Structure

```mermaid
flowchart LR
    subgraph "On Disk"
        S1["settings.json<br/>User preferences"]
        S2["calibration.json<br/>Genre calibration profile"]
        S3["sheets_cache.db<br/>Cached genres + scripts"]
        S4[".env (dev only)<br/>Debug flags"]
    end

    subgraph "In OS Vault"
        K1["gemini_key"]
        K2["youtube_key"]
        K3["tts_key"]
        K4["groq_key"]
        K5["pexels_key"]
        K6["pixabay_key"]
        K7["freesound_key"]
    end

    subgraph "Encrypted in Binary"
        E1["prompts.enc<br/>All LLM prompts"]
        E2["sheet_config.enc<br/>Sheet IDs + service keys"]
    end

    style K1 fill:#4CAF50,color:white
    style K2 fill:#4CAF50,color:white
    style K3 fill:#4CAF50,color:white
    style K4 fill:#4CAF50,color:white
    style K5 fill:#4CAF50,color:white
    style K6 fill:#4CAF50,color:white
    style K7 fill:#4CAF50,color:white
    style E1 fill:#f44336,color:white
    style E2 fill:#f44336,color:white
```

### Config Pydantic Model

```python
class AppConfig(BaseModel):
    # Server
    port: int = 8742
    debug: bool = False
    
    # Paths
    data_dir: Path          # SQLite, calibration, cache
    assets_dir: Path        # Gameplay, music, SFX, fonts
    output_dir: Path        # Rendered videos
    logs_dir: Path          # Log files
    
    # Limits
    max_videos_per_day: int = 50
    max_videos_per_hour: int = 10
    max_concurrent: int = 2
    cache_refresh_hours: int = 24
    
    # Feature flags
    analytics_enabled: bool = True
    submissions_enabled: bool = True
    debug_logging: bool = False
```

### Rules

| Rule | Detail |
|---|---|
| **Never hardcode paths** | All paths via `AppConfig` + `pathlib.Path` |
| **Never hardcode API URLs** | Constants in `config.py` |
| **Settings changes = restart-free** | Hot-reload `settings.json` |
| **Genre config from sheet overrides local** | Sheet version wins if newer |
| **Dev vs Prod** | `DEV_MODE=true` enables debug logging + mock APIs |

---

# 6. Release Cadence Plan

```mermaid
gantt
    title Release Timeline
    dateFormat  YYYY-MM-DD
    axisFormat  %b %d

    section Phase 1: Core Pipeline
    Pydantic models + config       :a1, 2026-03-03, 2d
    Sheets client + cache          :a2, after a1, 2d
    Script Agent (Gemini + Groq)   :a3, after a2, 3d
    Audio Agent (TTS + SSML + mix) :a4, after a3, 3d
    Asset Agent (images + SFX)     :a5, after a3, 3d
    Visual Agent (FFmpeg render)   :a6, after a4, 4d
    Upload Agent (YouTube)         :a7, after a6, 2d
    Checkpoint 1 milestone         :milestone, after a7, 0d

    section Phase 2: Desktop Shell
    Tauri v2 setup                 :b1, 2026-03-03, 2d
    License system (Rust)          :b2, after b1, 3d
    IPC layer + SSE                :b3, after b2, 2d
    Backend integration            :b4, after b3, 2d
    Checkpoint 2 milestone         :milestone, after b4, 0d

    section Phase 3: UI
    Onboarding wizard              :c1, 2026-03-17, 3d
    Dashboard                      :c2, after c1, 2d
    Generate + Progress            :c3, after c2, 2d
    Preview + Regeneration         :c4, after c3, 3d
    Analytics + Settings           :c5, after c4, 3d
    Checkpoint 3 milestone         :milestone, after c5, 0d

    section Phase 4: Polish
    PyArmor + security             :d1, 2026-03-31, 2d
    Shadow ban detection           :d2, after d1, 2d
    Self-improvement loop          :d3, after d2, 2d
    Testing + bug fixing           :d4, after d3, 3d
    Checkpoint 4 milestone         :milestone, after d4, 0d
    LAUNCH                         :milestone, 2026-04-14, 0d
```

### Release Versions

```mermaid
flowchart LR
    A["v0.1.0-alpha<br/>CLI pipeline<br/>Script → Video"] --> B["v0.2.0-alpha<br/>Tauri shell<br/>Basic UI"]
    B --> C["v0.3.0-beta<br/>Full onboarding<br/>Generate + Preview"]
    C --> D["v0.4.0-beta<br/>Analytics<br/>Regeneration"]
    D --> E["v0.9.0-rc<br/>Security<br/>Polish"]
    E --> F["v1.0.0<br/>🚀 LAUNCH"]

    style A fill:#E3F2FD
    style B fill:#BBDEFB
    style C fill:#90CAF9
    style D fill:#64B5F6
    style E fill:#42A5F5,color:white
    style F fill:#1565C0,color:white
```

---

# 7. Agent Isolation Specification

```mermaid
flowchart TD
    subgraph "Agent Boundaries"
        direction TB

        subgraph SCRIPT["Script Agent"]
            S_IN["📥 Input<br/>GenreConfig<br/>CalibrationProfile<br/>FeedbackSummary"]
            S_PROC["⚙️ Process<br/>Gemini → generate<br/>Groq → validate<br/>3 retries max"]
            S_OUT["📤 Output<br/>ScriptOutput (Pydantic)<br/>or ScriptValidationError"]
            S_IN --> S_PROC --> S_OUT
        end

        subgraph ASSET["Asset Agent"]
            A_IN["📥 Input<br/>ImageCue[]<br/>SfxCue[]<br/>GenreConfig"]
            A_PROC["⚙️ Process<br/>7-tier image fetch<br/>SFX resolve<br/>Music select"]
            A_OUT["📤 Output<br/>AssetBundle (Pydantic)<br/>image_paths[]<br/>sfx_paths[]<br/>music_path"]
            A_IN --> A_PROC --> A_OUT
        end

        subgraph AUDIO["Audio Agent"]
            AU_IN["📥 Input<br/>narration text<br/>GenreConfig<br/>SfxPaths<br/>MusicPath"]
            AU_PROC["⚙️ Process<br/>SSML enhance<br/>TTS → audio<br/>Timestamps<br/>Mix all tracks"]
            AU_OUT["📤 Output<br/>AudioBundle (Pydantic)<br/>final_audio.wav<br/>word_timestamps[]"]
            AU_IN --> AU_PROC --> AU_OUT
        end

        subgraph VISUAL["Visual Agent"]
            V_IN["📥 Input<br/>AudioBundle<br/>AssetBundle<br/>GenreConfig<br/>CaptionPreset"]
            V_PROC["⚙️ Process<br/>Build .ass captions<br/>Build FFmpeg filter<br/>Render video"]
            V_OUT["📤 Output<br/>VideoResult (Pydantic)<br/>final_video.mp4"]
            V_IN --> V_PROC --> V_OUT
        end
    end

    S_OUT -->|"ScriptOutput"| A_IN
    S_OUT -->|"ScriptOutput.narration"| AU_IN
    A_OUT -->|"AssetBundle"| AU_IN
    A_OUT -->|"AssetBundle"| V_IN
    AU_OUT -->|"AudioBundle"| V_IN

    style SCRIPT fill:#E8EAF6
    style ASSET fill:#E0F2F1
    style AUDIO fill:#FFF3E0
    style VISUAL fill:#FCE4EC
```

### Isolation Rules

| Rule | Enforcement |
|---|---|
| **Agents NEVER call each other directly** | Only Orchestrator passes data between agents |
| **Agents NEVER share state** | No global variables, no shared files during execution |
| **Every input/output is Pydantic validated** | Type mismatch = immediate error, not silent corruption |
| **Agents can fail independently** | Script Agent crash → doesn't crash Audio Agent |
| **Retry is agent-internal** | Agent retries 3x before reporting failure to Orchestrator |
| **No agent imports another agent** | `script_agent.py` never imports from `audio_agent.py` |
| **Services are injected, not hardcoded** | `ScriptAgent(gemini_service, groq_service)` — testable with mocks |

### Dependency Injection Pattern

```python
# CORRECT — service injected, testable
class ScriptAgent:
    def __init__(self, gemini: GeminiService, groq: GroqService, cache: CacheManager):
        self.gemini = gemini
        self.groq = groq
        self.cache = cache

# WRONG — hardcoded, untestable
class ScriptAgent:
    def __init__(self):
        self.gemini = GeminiService(api_key=os.getenv("GEMINI_KEY"))
```

---

# 8. Orchestrator State Machine

```mermaid
stateDiagram-v2
    [*] --> IDLE

    IDLE --> INITIALIZING: generate(request)
    INITIALIZING --> SCRIPT_GEN: config loaded

    SCRIPT_GEN --> SCRIPT_VALIDATION: script generated
    SCRIPT_VALIDATION --> SCRIPT_GEN: validation failed (retry ≤ 3)
    SCRIPT_VALIDATION --> PARALLEL_FETCH: validation passed

    state PARALLEL_FETCH {
        [*] --> TTS_GEN
        [*] --> IMAGE_FETCH
        [*] --> SFX_FETCH
        TTS_GEN --> TTS_DONE
        IMAGE_FETCH --> IMAGES_DONE
        SFX_FETCH --> SFX_DONE
    }

    PARALLEL_FETCH --> MUSIC_SELECT: TTS + assets done
    MUSIC_SELECT --> AUDIO_MIX: music selected
    AUDIO_MIX --> CAPTION_GEN: audio mixed
    CAPTION_GEN --> VIDEO_RENDER: captions built
    VIDEO_RENDER --> PREVIEW: render complete

    PREVIEW --> UPLOADING: user clicks upload
    PREVIEW --> REGEN_INIT: user clicks regenerate
    PREVIEW --> DISCARDED: user discards

    REGEN_INIT --> REGEN_PARTIAL: determine stages to re-run
    REGEN_PARTIAL --> COMPARE: regen complete
    COMPARE --> UPLOADING: user picks version
    COMPARE --> DISCARDED: user discards both

    UPLOADING --> UPLOADED: YouTube confirms
    UPLOADING --> UPLOAD_FAILED: API error

    UPLOAD_FAILED --> UPLOADING: retry
    UPLOAD_FAILED --> FAILED: max retries

    UPLOADED --> TRACKING: schedule analytics
    TRACKING --> [*]

    DISCARDED --> [*]
    FAILED --> [*]

    note right of SCRIPT_GEN: Max 3 retries
    note right of PARALLEL_FETCH: TTS + images + SFX run simultaneously
    note right of PREVIEW: User decision point
    note right of REGEN_INIT: Only 1 regen allowed per video
```

### State Persistence

```python
class PipelineState(BaseModel):
    job_id: str
    state: str                    # Current state name
    genre_id: str
    created_at: datetime
    updated_at: datetime
    
    # Intermediate outputs (saved so partial re-runs work)
    script_output: ScriptOutput | None = None
    asset_bundle: dict | None = None          # Paths only 
    audio_bundle: dict | None = None          # Paths only
    caption_path: str | None = None
    video_path: str | None = None
    regen_video_path: str | None = None
    
    # Tracking
    retries: dict = {}           # {"script_generation": 2}
    errors: list[str] = []
    stage_timings: dict = {}     # {"script_generation": 4.2}
```

### State Transition Rules

| From | To | Condition |
|---|---|---|
| IDLE | INITIALIZING | `generate(request)` called |
| SCRIPT_VALIDATION | SCRIPT_GEN | `retries["script"] < 3` |
| SCRIPT_VALIDATION | FAILED | `retries["script"] >= 3` |
| PREVIEW | REGEN_INIT | `regenerations_remaining > 0` |
| PREVIEW | UPLOADING | User clicks upload |
| Any error state | FAILED | Max retries exceeded |

### Recovery: If App Crashes Mid-Pipeline

```
On app restart:
1. Load PipelineState from SQLite
2. If state == "VIDEO_RENDER" and temp file exists → resume render
3. If state == "TTS_GEN" → re-run from TTS (script is saved)
4. If state == "SCRIPT_GEN" → re-run from scratch
5. Show user: "Previous generation was interrupted. [Resume] [Start Over]"
```
