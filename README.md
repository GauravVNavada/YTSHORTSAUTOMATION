# YT Shorts Auto

> AI-powered YouTube Shorts automation desktop app. One-time purchase, BYOK model.

## Project Structure

```
├── docs/
│   ├── planning/          # Product docs (locked in)
│   │   ├── FINAL_PRODUCT.md        # The definitive product spec
│   │   ├── PRD.md                  # Product Requirements Document
│   │   ├── SYSTEM_ARCHITECTURE.md  # Technical architecture
│   │   └── MASTER_BLUEPRINT.md     # Original research blueprint
│   │
│   ├── research/          # Market research & analysis
│   │   ├── deep_research_analysis.md
│   │   ├── AI YouTube Shorts Automation Market Analysis.docx
│   │   └── ... (original docs)
│   │
│   └── guides/            # Setup & collaboration
│       ├── GCP_SETUP_GUIDE.md            # Google Cloud setup steps
│       ├── COLLABORATION_GUIDE.md        # Git workflow + work division
│       ├── Genre_Research_Column_Guide.md # For research contributors
│       └── test_reference_data.json      # 10 test scripts for pipeline
│
├── backend/               # Python (FastAPI + 6 agents)    [TODO]
├── frontend/              # Tauri v2 (HTML/CSS/JS + Rust)  [TODO]
├── assets/                # Gameplay, music, SFX, fonts    [TODO]
├── .gitignore
└── README.md
```

## Quick Links

| Document | Purpose |
|---|---|
| [FINAL_PRODUCT.md](docs/planning/FINAL_PRODUCT.md) | Everything about the product in one file |
| [PRD.md](docs/planning/PRD.md) | Formal requirements with priorities |
| [SYSTEM_ARCHITECTURE.md](docs/planning/SYSTEM_ARCHITECTURE.md) | Technical architecture + diagrams |
| [GCP_SETUP_GUIDE.md](docs/guides/GCP_SETUP_GUIDE.md) | Google Cloud + Sheets setup |
| [COLLABORATION_GUIDE.md](docs/guides/COLLABORATION_GUIDE.md) | Git workflow + who builds what |

## Tech Stack

| Layer | Tech |
|---|---|
| Desktop shell | Tauri v2 (Rust) |
| Frontend | HTML/CSS/JS + Vite |
| Backend | Python + FastAPI |
| Video rendering | FFmpeg (subprocess) |
| AI | Gemini 2.5 Flash + Groq Llama 3.3 70B |
| TTS | Google Cloud Neural2 |
| Database | SQLite (local) |
| Cloud data | Google Sheets API |
| Bundling | PyInstaller + PyArmor |
