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
    # TODO: Start pipeline via orchestrator
    return {
        "success": True,
        "job_id": "not_implemented",
        "message": "Generation not yet implemented",
    }


# ─── SSE Progress ─────────────────────────────────────

@app.get("/events")
async def events(job_id: str):
    """SSE stream for pipeline progress."""
    # TODO: Implement SSE with sse-starlette
    return {"message": "SSE not yet implemented"}


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
    # TODO
    return {"success": True, "videos": [], "total": 0, "page": page, "pages": 0}


# ─── Entry Point ──────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
    )
