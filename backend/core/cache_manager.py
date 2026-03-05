"""
SQLite-backed cache for Google Sheets data.

Sits between API endpoints and the Sheets client. On startup, checks if
the cache is stale (>24h) and refreshes from Google Sheets if needed.
During generation, only the local cache is read — never the live sheet.

Schema matches SYSTEM_ARCHITECTURE.md §5.
"""
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

from backend.core.config import config
from backend.core.exceptions import CacheError, SheetError
from backend.core.logger import get_logger
from backend.core.models import Genre, GenreConfig

logger = get_logger(__name__)

# ─── Schema ────────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS genres (
    genre_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    icon TEXT DEFAULT '🎬',
    difficulty TEXT DEFAULT '',
    is_active INTEGER DEFAULT 1,
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reference_scripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    genre_id TEXT NOT NULL,
    tab_name TEXT NOT NULL,
    script_text TEXT NOT NULL,
    hook_pattern TEXT DEFAULT '',
    quality_score REAL DEFAULT 0.0,
    word_count INTEGER DEFAULT 0,
    raw_data TEXT DEFAULT '{}',
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS genre_config (
    genre_id TEXT PRIMARY KEY,
    tts_voice TEXT DEFAULT 'en-US-Neural2-D',
    tts_rate REAL DEFAULT 0.95,
    tts_pitch REAL DEFAULT 0.0,
    layout TEXT DEFAULT 'split_screen',
    caption_preset TEXT DEFAULT 'clean_pro',
    music_mood TEXT DEFAULT 'neutral',
    config_json TEXT DEFAULT '{}',
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cache_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class CacheManager:
    """Async SQLite cache for genres, scripts, and config.

    Usage:
        cache = CacheManager()
        await cache.initialize()
        genres = await cache.get_genres()
    """

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or config.cache_db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Create the database and tables if they don't exist.

        Raises:
            CacheError: If database creation fails.
        """
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = await aiosqlite.connect(str(self._db_path))
            self._db.row_factory = aiosqlite.Row
            await self._db.executescript(_SCHEMA)
            await self._db.commit()
            logger.info(
                "Cache database initialized",
                extra={"extra_data": {"path": str(self._db_path)}},
            )
        except Exception as exc:
            raise CacheError(
                f"Failed to initialize cache database: {exc}",
                details=str(exc),
            )

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    # ─── Read Methods ──────────────────────────────────

    async def get_genres(self) -> list[Genre]:
        """Get all active genres from the cache.

        Returns:
            List of Genre models from the local cache.

        Raises:
            CacheError: If the database query fails.
        """
        try:
            async with self._db.execute(
                "SELECT * FROM genres WHERE is_active = 1 ORDER BY genre_id"
            ) as cursor:
                rows = await cursor.fetchall()
            return [
                Genre(
                    genre_id=row["genre_id"],
                    display_name=row["display_name"],
                    icon=row["icon"],
                    difficulty=row["difficulty"],
                    is_active=bool(row["is_active"]),
                )
                for row in rows
            ]
        except Exception as exc:
            raise CacheError(
                f"Failed to read genres from cache: {exc}",
                details=str(exc),
            )

    async def get_genre_config(self, genre_id: str) -> Optional[GenreConfig]:
        """Get configuration for a specific genre.

        Args:
            genre_id: The genre identifier.

        Returns:
            GenreConfig model or None if not found.

        Raises:
            CacheError: If the database query fails.
        """
        try:
            async with self._db.execute(
                "SELECT * FROM genre_config WHERE genre_id = ?", (genre_id,)
            ) as cursor:
                row = await cursor.fetchone()
            if not row:
                return None
            return GenreConfig(
                genre_id=row["genre_id"],
                tts_voice=row["tts_voice"],
                tts_rate=row["tts_rate"],
                tts_pitch=row["tts_pitch"],
                layout=row["layout"],
                caption_preset=row["caption_preset"],
                music_mood=row["music_mood"],
            )
        except Exception as exc:
            raise CacheError(
                f"Failed to read genre config from cache: {exc}",
                details=str(exc),
            )

    async def get_reference_scripts(
        self, genre_id: str, limit: int = 5
    ) -> list[dict]:
        """Get reference scripts for a genre (few-shot examples).

        Args:
            genre_id: The genre identifier.
            limit: Maximum number of scripts to return.

        Returns:
            List of script dicts with keys like script_text, hook_pattern.

        Raises:
            CacheError: If the database query fails.
        """
        try:
            async with self._db.execute(
                "SELECT * FROM reference_scripts WHERE genre_id = ? "
                "ORDER BY quality_score DESC LIMIT ?",
                (genre_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
            return [
                {
                    "script_text": row["script_text"],
                    "hook_pattern": row["hook_pattern"],
                    "word_count": row["word_count"],
                    "quality_score": row["quality_score"],
                    "raw_data": json.loads(row["raw_data"]),
                }
                for row in rows
            ]
        except Exception as exc:
            raise CacheError(
                f"Failed to read reference scripts: {exc}",
                details=str(exc),
            )

    # ─── Write Methods ─────────────────────────────────

    async def get_recent_scripts(
        self, genre_id: str, limit: int = 50,
    ) -> list[str]:
        """Get narrations from recently generated scripts for dedup.

        Args:
            genre_id: Genre identifier.
            limit: Max number of recent scripts (default 50).

        Returns:
            List of narration text strings.
        """
        try:
            async with self._db.execute(
                "SELECT script_text FROM reference_scripts "
                "WHERE genre_id = ? ORDER BY id DESC LIMIT ?",
                (genre_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
            return [row["script_text"] for row in rows]
        except Exception:
            return []

    async def store_genres(self, genres: list[Genre]) -> None:
        """Replace all genres in the cache.

        Args:
            genres: List of Genre models to store.

        Raises:
            CacheError: If the database write fails.
        """
        now = datetime.now(timezone.utc).isoformat()
        try:
            await self._db.execute("DELETE FROM genres")
            for g in genres:
                await self._db.execute(
                    "INSERT INTO genres VALUES (?, ?, ?, ?, ?, ?)",
                    (g.genre_id, g.display_name, g.icon,
                     g.difficulty, int(g.is_active), now),
                )
            await self._set_meta("genres_fetched_at", now)
            await self._db.commit()
            logger.info(
                "Genres stored in cache",
                extra={"extra_data": {"count": len(genres)}},
            )
        except Exception as exc:
            raise CacheError(
                f"Failed to store genres in cache: {exc}",
                details=str(exc),
            )

    async def store_genre_configs(self, configs: list[GenreConfig]) -> None:
        """Replace all genre configs in the cache.

        Args:
            configs: List of GenreConfig models to store.

        Raises:
            CacheError: If the database write fails.
        """
        now = datetime.now(timezone.utc).isoformat()
        try:
            await self._db.execute("DELETE FROM genre_config")
            for c in configs:
                await self._db.execute(
                    "INSERT INTO genre_config VALUES "
                    "(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (c.genre_id, c.tts_voice, c.tts_rate, c.tts_pitch,
                     c.layout, c.caption_preset, c.music_mood, "{}", now),
                )
            await self._db.commit()
            logger.info(
                "Genre configs stored in cache",
                extra={"extra_data": {"count": len(configs)}},
            )
        except Exception as exc:
            raise CacheError(
                f"Failed to store genre configs: {exc}",
                details=str(exc),
            )

    async def store_reference_scripts(
        self, genre_id: str, tab_name: str, scripts: list[dict]
    ) -> None:
        """Store reference scripts for a genre.

        Args:
            genre_id: The genre identifier.
            tab_name: The sheet tab name where scripts came from.
            scripts: List of raw script dicts from the sheet.

        Raises:
            CacheError: If the database write fails.
        """
        now = datetime.now(timezone.utc).isoformat()
        try:
            await self._db.execute(
                "DELETE FROM reference_scripts WHERE genre_id = ?",
                (genre_id,),
            )
            for s in scripts:
                script_text = (
                    s.get("full script / transcript", "")
                    or s.get("full_script", "")
                )
                if not script_text:
                    continue
                word_count = len(script_text.split())
                await self._db.execute(
                    "INSERT INTO reference_scripts "
                    "(genre_id, tab_name, script_text, hook_pattern, "
                    "quality_score, word_count, raw_data, fetched_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        genre_id, tab_name, script_text,
                        s.get("hook type", ""),
                        float(s.get("score: overall", "0") or "0"),
                        word_count,
                        json.dumps(s, default=str),
                        now,
                    ),
                )
            await self._db.commit()
            logger.info(
                f"Reference scripts stored for '{genre_id}'",
                extra={"extra_data": {"count": len(scripts)}},
            )
        except Exception as exc:
            raise CacheError(
                f"Failed to store reference scripts: {exc}",
                details=str(exc),
            )

    # ─── Cache Freshness ───────────────────────────────

    async def cache_age_hours(self) -> float:
        """Get the age of the cache in hours.

        Returns:
            Hours since last refresh, or float('inf') if never refreshed.
        """
        fetched_at = await self._get_meta("genres_fetched_at")
        if not fetched_at:
            return float("inf")
        try:
            last = datetime.fromisoformat(fetched_at)
            delta = datetime.now(timezone.utc) - last
            return delta.total_seconds() / 3600.0
        except ValueError:
            return float("inf")

    async def last_refresh_iso(self) -> Optional[str]:
        """Get the ISO timestamp of the last cache refresh.

        Returns:
            ISO string or None if never refreshed.
        """
        return await self._get_meta("genres_fetched_at")

    async def is_stale(self) -> bool:
        """Check if the cache needs refreshing.

        Returns:
            True if cache is older than config.cache_refresh_hours.
        """
        age = await self.cache_age_hours()
        return age > config.cache_refresh_hours

    # ─── Meta Helpers ──────────────────────────────────

    async def _set_meta(self, key: str, value: str) -> None:
        """Set a metadata key-value pair."""
        await self._db.execute(
            "INSERT OR REPLACE INTO cache_meta (key, value) VALUES (?, ?)",
            (key, value),
        )

    async def _get_meta(self, key: str) -> Optional[str]:
        """Get a metadata value by key."""
        try:
            async with self._db.execute(
                "SELECT value FROM cache_meta WHERE key = ?", (key,)
            ) as cursor:
                row = await cursor.fetchone()
            return row["value"] if row else None
        except Exception:
            return None
