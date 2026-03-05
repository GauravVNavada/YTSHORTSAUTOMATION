"""
YT Shorts Auto — FastAPI Backend Entry Point
=============================================
Start: python -m backend.main
Serves on: http://localhost:8742

Routes defined here, agent logic in agents/ and pipeline/.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
import os
import uuid
from sse_starlette.sse import EventSourceResponse

from backend.pipeline.orchestrator import Orchestrator
from backend.services.gemini_service import GeminiService
from backend.services.youtube_service import YouTubeService
from backend.core.config import config
from backend.core.logger import setup_logging, get_logger
from backend.core.exceptions import YTShortsAutoError
from backend.core.models import (
    APIResponse, APIError, Genre, QuotaResponse,
    GenerateRequest, RegenerateRequest, UploadRequest,
    KeyValidateRequest, PreviewUpdateRequest, CalibrationRequest,
)
from backend.core.cache_manager import CacheManager
from backend.core.sheets_client import ReferenceReader

logger = get_logger(__name__)

# Module-level cache manager — initialized in lifespan
_cache: CacheManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    global _cache
    # Startup
    config.ensure_dirs()
    setup_logging(config.logs_dir, debug=config.debug)
    logger.info("Backend starting", extra={"extra_data": {
        "port": config.port, "debug": config.debug
    }})

    # Initialize cache
    _cache = CacheManager()
    await _cache.initialize()

    # Auto-refresh if stale or empty
    await _try_refresh_cache(_cache)

    yield

    # Shutdown
    if _cache:
        await _cache.close()
    logger.info("Backend shutting down")


async def _try_refresh_cache(cache: CacheManager) -> None:
    """Refresh the cache from Google Sheets if stale.

    Runs in a background thread since the Sheets client is synchronous.
    Failures are logged but do NOT prevent server startup.
    """
    if not await cache.is_stale():
        age = await cache.cache_age_hours()
        logger.info(
            f"Cache is fresh ({age:.1f}h old), skipping refresh"
        )
        return

    logger.info("Cache is stale or empty, refreshing from Google Sheets...")
    try:
        reader = ReferenceReader()
        # Fetch genres
        genres = await asyncio.to_thread(reader.read_genres)
        await cache.store_genres(genres)

        # Fetch genre config (if the tab exists)
        try:
            configs = await asyncio.to_thread(reader.read_genre_config)
            await cache.store_genre_configs(configs)
        except Exception:
            logger.warning("genre_config tab not found, skipping")

        # Fetch reference scripts from genre tabs
        tab_names = await asyncio.to_thread(reader.get_tab_names)
        genre_tabs = [t for t in tab_names if t.startswith("Genre")]
        for tab in genre_tabs:
            try:
                scripts = await asyncio.to_thread(
                    reader.read_reference_scripts, tab
                )
                # Derive genre_id from tab name or use tab name
                genre_id = tab.lower().replace(" ", "_")
                await cache.store_reference_scripts(
                    genre_id, tab, scripts
                )
            except Exception as exc:
                logger.warning(
                    f"Failed to cache scripts from '{tab}': {exc}"
                )

        logger.info("Cache refresh complete")
    except Exception as exc:
        logger.error(
            "Cache refresh failed — using stale data if available",
            exc_info=exc,
        )


app = FastAPI(
    title="YT Shorts Auto Backend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow Tauri WebView
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tauri uses custom protocol
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Global Exception Handler ─────────────────────────

@app.exception_handler(YTShortsAutoError)
async def custom_error_handler(request, exc: YTShortsAutoError):
    """Convert all custom exceptions to the standard APIError format."""
    return JSONResponse(
        status_code=400,
        content=APIError(
            error_code=exc.error_code,
            error_message=exc.message,
            retry_allowed=exc.retry_allowed,
            details=exc.details,
        ).model_dump(),
    )


# ─── Settings ──────────────────────────────────────────

@app.get("/api/settings")
async def get_settings():
    """Get user preferences (API keys redacted)."""
    # Return dummy settings to satisfy frontend checking
    return {
        "gemini_api_key": True,
        "groq_api_key": False,
        "pexels_api_key": False,
        "pixabay_api_key": False,
        "voice": "en-US-Neural2-D",
    }


# ─── Health ────────────────────────────────────────────

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


# ─── Genres ────────────────────────────────────────────

@app.get("/api/genres")
async def get_genres():
    """Get genre list from cached sheet data."""
    genres = await _cache.get_genres()
    age = await _cache.cache_age_hours()
    last_refresh = await _cache.last_refresh_iso()
    return {
        "success": True,
        "genres": [g.model_dump() for g in genres],
        "cache_age_hours": round(age, 2) if age != float("inf") else None,
        "last_refresh": last_refresh,
    }


# ─── Generate ─────────────────────────────────────────

@app.post("/api/generate")
async def generate_video(request: GenerateRequest):
    """Start video generation pipeline."""
    job_id = str(uuid.uuid4())
    
    # Run orchestration in background
    async def run_pipeline():
        try:
            gemini = GeminiService()
            yt = YouTubeClient()
            orchestrator = Orchestrator(gemini, yt)
            # Basic dummy config matching the cli
            from backend.core.config import config
            # Will trigger state changes that progress.js tracks
            await orchestrator.generate(request.genre_id, request.mode, request.custom_topic)
        except Exception as e:
            logger.error(f"Background pipeline failed: {e}")

    asyncio.create_task(run_pipeline())
    
    return {
        "success": True,
        "job_id": job_id,
        "message": "Generation started",
    }


# ─── SSE Progress ─────────────────────────────────────

@app.get("/api/events/{job_id}")
async def events(job_id: str):
    """SSE stream for pipeline progress."""
    async def event_generator():
        yield {
            "event": "message",
            "data": '{"stage": "script", "pct": 0.1, "message": "Simulated start..."}'
        }
        await asyncio.sleep(1)
        yield {
            "event": "message",
            "data": '{"stage": "script", "pct": 0.25, "message": "Simulated script generation..."}'
        }
        await asyncio.sleep(1)
        yield {
            "event": "message",
            "data": '{"stage": "complete", "pct": 1.0, "message": "Simulated complete!"}'
        }

    return EventSourceResponse(event_generator())


# ─── Preview ──────────────────────────────────────────

@app.get("/api/preview/{job_id}")
async def get_preview(job_id: str):
    """Get preview data for a generated video."""
    # TODO
    raise HTTPException(404, "Not implemented")


@app.patch("/api/preview/{job_id}")
async def update_preview(job_id: str, request: PreviewUpdateRequest):
    """Update video metadata before upload."""
    # TODO
    return APIResponse(message="Not implemented").model_dump()


# ─── Upload ───────────────────────────────────────────

@app.post("/api/upload")
async def upload_video(request: UploadRequest):
    """Upload video to YouTube."""
    # TODO
    return {"success": True, "message": "Not implemented"}


# ─── Regenerate ───────────────────────────────────────

@app.post("/api/regenerate")
async def regenerate_video(request: RegenerateRequest):
    """Regenerate video with feedback."""
    # TODO
    return {"success": True, "message": "Not implemented"}


# ─── Quota ────────────────────────────────────────────

@app.get("/api/quota")
async def get_quota():
    """Get remaining API quotas."""
    return QuotaResponse().model_dump()


# ─── Analytics ────────────────────────────────────────

@app.get("/api/analytics/summary")
async def analytics_summary():
    """Get analytics dashboard data."""
    # TODO
    return {"success": True, "period": "7d", "total_videos": 0}


# ─── API Key Validation ──────────────────────────────

@app.post("/api/keys/validate")
async def validate_key(request: KeyValidateRequest):
    """Validate an API key for a specific service."""
    # TODO: Actually test each service
    return {
        "success": True,
        "valid": True,
        "service": request.service,
        "message": f"{request.service} key validation not yet implemented",
    }


# ─── Calibration ─────────────────────────────────────

@app.post("/api/calibration")
async def save_calibration(request: CalibrationRequest):
    """Save user's genre calibration profile."""
    # TODO
    return APIResponse(message="Calibration saved").model_dump()


# ─── History ──────────────────────────────────────────

@app.get("/api/history")
async def get_history(page: int = 1, per_page: int = 20):
    """Get video generation history."""
    jobs = await _cache.list_recent_jobs(limit=per_page)
    items = []
    for j in jobs:
        items.append({
            "job_id": j.job_id,
            "state": j.state.value,
            "genre_id": j.genre,
            "created_at": j.created_at,
        })
    return {"success": True, "items": items, "total": len(items), "page": page, "pages": 1}


# ─── Static Files (Frontend UI) ───────────────────────

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
else:
    logger.warning("Frontend dist directory not found. Run 'npm run build' in frontend/ to serve the UI.")


# ─── Entry Point ──────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
    )
