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

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # Startup
    config.ensure_dirs()
    setup_logging(config.logs_dir, debug=config.debug)
    logger.info("Backend starting", extra={"extra_data": {
        "port": config.port, "debug": config.debug
    }})
    # TODO: Initialize sheets cache, load calibration
    yield
    # Shutdown
    logger.info("Backend shutting down")


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
    # TODO: Read from sheets cache
    return {
        "success": True,
        "genres": [],
        "cache_age_hours": 0,
        "last_refresh": None,
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
