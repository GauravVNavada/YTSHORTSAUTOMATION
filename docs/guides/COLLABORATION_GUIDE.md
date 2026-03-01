# Collaboration Guide: Building Together with Git + Antigravity

---

## Git Setup (One-Time)

### 1. Create a GitHub Repository

```bash
# One of you creates the repo on GitHub:
# Go to github.com → New Repository → Name: "ytshortsauto" → Private → Create

# Then clone it locally (BOTH of you):
cd C:\Users\YOUR_USERNAME\Desktop
git clone https://github.com/YOUR_USERNAME/ytshortsauto.git
cd ytshortsauto
```

### 2. Copy Project Files Into Repo

```bash
# Copy all files from YTSHORTSAUTOMATION into the cloned repo
# Then push:
git add .
git commit -m "Initial commit: planning docs and project structure"
git push origin main
```

### 3. Add Your Friend as a Collaborator

- GitHub repo → Settings → Collaborators → Add your friend's GitHub username
- They accept the invite → clone the repo on their machine

---

## Project Structure (How Code Will Be Organized)

```
ytshortsauto/
├── docs/                          # ALL planning & research docs
│   ├── planning/                  # PRD, Architecture, Final Product
│   ├── research/                  # Market analysis, deep research
│   └── guides/                    # GCP setup, genre research guide
│
├── backend/                       # Python backend (FastAPI + agents)
│   ├── agents/                    # 6 specialist agents
│   │   ├── script_agent.py
│   │   ├── asset_agent.py
│   │   ├── audio_agent.py
│   │   ├── visual_agent.py
│   │   ├── upload_agent.py
│   │   └── feedback_agent.py
│   ├── core/                      # Shared modules
│   │   ├── sheets_client.py       # Google Sheets integration
│   │   ├── cache_manager.py       # SQLite caching
│   │   ├── models.py              # Pydantic schemas
│   │   └── config.py              # App configuration
│   ├── services/                  # External API wrappers
│   │   ├── gemini_service.py
│   │   ├── groq_service.py
│   │   ├── tts_service.py
│   │   ├── image_service.py
│   │   ├── youtube_service.py
│   │   └── freesound_service.py
│   ├── pipeline/                  # Orchestration
│   │   ├── orchestrator.py
│   │   └── regeneration.py
│   ├── main.py                    # FastAPI app entry point
│   └── requirements.txt
│
├── frontend/                      # Tauri frontend
│   ├── src/                       # HTML/CSS/JS
│   ├── src-tauri/                 # Rust code (license, IPC)
│   └── package.json
│
├── assets/                        # Bundled media (git-ignored, too large)
│   ├── gameplay/
│   ├── music/
│   ├── sfx/
│   └── fonts/
│
├── .gitignore
├── README.md
└── LICENSE
```

---

## Work Division: Who Builds What

### Developer A (You) — Backend Pipeline
Focus: Python backend, core pipeline, API integrations

| Week | What You Build |
|---|---|
| Week 1 | Project setup, Pydantic models, Sheets client, cache manager |
| Week 1 | Script Agent (Gemini generation + Groq 5-layer validation) |
| Week 2 | Audio Agent (TTS + SSML + timestamps + audio mixing) |
| Week 2 | Asset Agent (7-tier image fetch + SFX + music selection) |
| Week 3 | Visual Agent (FFmpeg rendering, 3 layouts, captions) |
| Week 3 | Upload Agent (YouTube API) + Feedback Agent (analytics) |
| Week 4 | Orchestrator, regeneration logic, end-to-end testing |

### Developer B (Friend) — Frontend + Desktop Shell
Focus: Tauri app, UI screens, IPC, license system

| Week | What They Build |
|---|---|
| Week 1 | Tauri v2 project setup, basic shell, IPC to Python backend |
| Week 1 | Onboarding wizard UI (license → API keys → channel connect) |
| Week 2 | Genre selection screen (reads from backend API) |
| Week 2 | Generate screen + real-time progress (SSE) |
| Week 3 | Preview screen + regeneration feedback form |
| Week 3 | Dashboard + analytics screen |
| Week 4 | Settings, caption editor, polish, license key system (Rust) |

### Shared / Integration Points
- **Week 2**: Backend exposes FastAPI endpoints, Frontend starts consuming them
- **Week 3**: End-to-end test: UI → backend → generate → preview → upload
- **Week 4**: Full integration testing, bug fixing

---

## Git Branching Strategy

Keep it simple — you're only 2 people:

```
main (always working, deployable)
  │
  ├── feature/script-agent      (Dev A)
  ├── feature/tts-audio          (Dev A)
  ├── feature/image-fetcher      (Dev A)
  │
  ├── feature/tauri-setup        (Dev B)
  ├── feature/onboarding-ui      (Dev B)
  ├── feature/generate-screen    (Dev B)
  │
  └── (merge to main when feature is done)
```

### Daily Workflow

```bash
# Start of day — get latest code
git checkout main
git pull origin main

# Create/switch to your feature branch
git checkout -b feature/script-agent
# ... write code ...

# Save your work (do this frequently!)
git add .
git commit -m "Script agent: idea generation with Gemini"
git push origin feature/script-agent

# When feature is complete — merge to main
git checkout main
git pull origin main
git merge feature/script-agent
git push origin main

# Delete the branch
git branch -d feature/script-agent
```

### Avoiding Conflicts

Since Dev A works on `backend/` and Dev B works on `frontend/`, **conflicts will be rare**. The only shared file is:
- `backend/core/models.py` (Pydantic schemas) — agree on these early

**Rule: Never both edit the same file at the same time.** If you need to, coordinate via message first.

---

## Using Antigravity Together

Both of you can use Antigravity (this tool) independently on different parts of the codebase:

### Dev A (Backend)
- Open the repo folder in your editor
- Tell Antigravity: "Build the Script Agent based on the PRD and System Architecture docs"
- It reads `docs/planning/PRD.md` and `docs/planning/SYSTEM_ARCHITECTURE.md` for context

### Dev B (Frontend)
- Open the same repo folder on their machine
- Tell Antigravity: "Build the onboarding wizard UI based on the PRD"
- It reads the same docs for context

### Key Tips
1. **Both developers should read the docs first** — share the `docs/` folder. It's the shared brain.
2. **Commit often** — small commits are easier to merge and debug
3. **Communicate the API contract early** — agree on the FastAPI endpoint shapes in Week 1
4. **Don't copy artifacts between machines** — each person has their own Antigravity brain folder

---

## .gitignore (Important!)

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
*.egg-info/

# Keys & secrets (NEVER commit these!)
*-key.json
*.enc
.env
config/secrets.json

# Assets (too large for git)
assets/gameplay/
assets/music/
assets/sfx/

# Build artifacts
dist/
build/
*.exe
*.spec

# Tauri
frontend/src-tauri/target/
frontend/node_modules/

# IDE
.vscode/
.idea/

# OS
Thumbs.db
.DS_Store

# Antigravity
.gemini/
```

---

## First Steps Checklist

### Dev A (You)
- [ ] Create GitHub repo (private)
- [ ] Copy all files from `YTSHORTSAUTOMATION/` into repo
- [ ] Push initial commit
- [ ] Add friend as collaborator
- [ ] Follow GCP_SETUP_GUIDE.md to create sheets + service accounts
- [ ] Set up Python venv + install dependencies
- [ ] Start with `backend/core/models.py` (Pydantic schemas)

### Dev B (Friend)
- [ ] Accept GitHub invite + clone repo
- [ ] Read `docs/planning/FINAL_PRODUCT.md` thoroughly
- [ ] Read `docs/planning/PRD.md` + `SYSTEM_ARCHITECTURE.md`
- [ ] Install Node.js + Rust toolchain
- [ ] Run `npx create-tauri-app` to scaffold Tauri v2
- [ ] Start with basic window + IPC health check

---

## Communication Protocol

This is what keeps 2-person teams fast:

1. **Start of day**: Quick message — "Today I'm working on [X]"
2. **Before merging to main**: Message — "Merging [feature] to main, pull before you push"
3. **When adding/changing endpoints**: Update `backend/core/models.py` and tell the other person
4. **End of day**: Push all work, even if unfinished (use WIP commits)
