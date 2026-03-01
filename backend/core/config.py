"""
Application configuration.
All paths, limits, and feature flags in one place.
"""
import os
from pathlib import Path
from pydantic import BaseModel


def _get_base_dir() -> Path:
    """Get the application data directory."""
    # In development: project root
    # In production: %APPDATA%/YTShortsAuto
    env_dir = os.environ.get("YTSHORTSAUTO_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(__file__).parent.parent.parent


class AppConfig(BaseModel):
    """Central app configuration. Loaded once at startup."""

    # ─── Server ────────────────────────────────────
    host: str = "127.0.0.1"
    port: int = 8742
    debug: bool = os.environ.get("DEV_MODE", "false").lower() == "true"

    # ─── Paths ─────────────────────────────────────
    base_dir: Path = _get_base_dir()

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def assets_dir(self) -> Path:
        return self.base_dir / "assets"

    @property
    def output_dir(self) -> Path:
        return self.base_dir / "output"

    @property
    def logs_dir(self) -> Path:
        return self.base_dir / "logs"

    @property
    def cache_db_path(self) -> Path:
        return self.data_dir / "sheets_cache.db"

    @property
    def analytics_db_path(self) -> Path:
        return self.data_dir / "analytics.db"

    @property
    def calibration_path(self) -> Path:
        return self.data_dir / "calibration.json"

    # ─── Google Sheets ─────────────────────────────
    sheet_id: str = "1w4teWGFkdX1VsMIdt3orIRkZ30-fHkfZOhW7w3Ck-QE"
    reader_key_path: str = "reference-reader-key.json"
    writer_key_path: str = "data-writer-key.json"
    cache_refresh_hours: int = 24

    # Sheet tab names
    genres_tab: str = "🎯 Suggested Genres"
    genre_config_tab: str = "genre_config"
    submissions_tab: str = "video_submissions"
    regen_feedback_tab: str = "regeneration_feedback"

    # ─── Rate Limits ───────────────────────────────
    max_videos_per_day: int = 50
    max_videos_per_hour: int = 10
    max_concurrent: int = 2
    max_retries: int = 3

    # ─── Feature Flags ─────────────────────────────
    analytics_enabled: bool = True
    submissions_enabled: bool = True
    debug_logging: bool = False

    # ─── AI Models ─────────────────────────────────
    gemini_model: str = "gemini-2.5-flash"
    groq_model: str = "llama-3.3-70b-versatile"

    # ─── TTS Defaults ──────────────────────────────
    default_tts_voice: str = "en-US-Neural2-D"
    default_tts_rate: float = 0.95
    default_tts_pitch: float = 0.0

    # ─── Video Defaults ────────────────────────────
    video_width: int = 1080
    video_height: int = 1920
    video_fps: int = 30
    target_duration_sec: int = 45  # 30, 45, or 60

    def ensure_dirs(self):
        """Create all required directories."""
        for d in [self.data_dir, self.assets_dir, self.output_dir, self.logs_dir,
                  self.assets_dir / "gameplay", self.assets_dir / "music",
                  self.assets_dir / "sfx", self.assets_dir / "fonts"]:
            d.mkdir(parents=True, exist_ok=True)

    class Config:
        arbitrary_types_allowed = True


# Singleton config instance
config = AppConfig()
