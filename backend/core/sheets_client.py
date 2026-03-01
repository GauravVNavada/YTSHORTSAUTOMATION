"""
Google Sheets API client for reading reference data and writing submissions.

Uses two separate service accounts:
- reference-reader (read-only): genres, scripts, genre_config
- data-writer (append-only): video_submissions, regeneration_feedback

All methods are synchronous (blocking) — called from async context via
asyncio.to_thread() in the cache manager.
"""
from pathlib import Path
from typing import Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.core.config import config
from backend.core.exceptions import SheetError
from backend.core.logger import get_logger
from backend.core.models import Genre, GenreConfig

logger = get_logger(__name__)


# ─── Scopes ────────────────────────────────────────────
_READ_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
_WRITE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _build_service(key_path: str, scopes: list[str]):
    """Build a Google Sheets API service from a service account key file.

    Args:
        key_path: Path to the JSON service account key.
        scopes: OAuth scopes for the service.

    Returns:
        A Google Sheets API service resource.

    Raises:
        SheetError: If the key file is missing or auth fails.
    """
    resolved = config.base_dir / key_path
    if not resolved.exists():
        raise SheetError(
            f"Service account key not found: {resolved}",
            details="Run GCP setup first. See docs/guides/GCP_SETUP_GUIDE.md",
        )
    try:
        creds = Credentials.from_service_account_file(
            str(resolved), scopes=scopes
        )
        return build("sheets", "v4", credentials=creds, cache_discovery=False)
    except Exception as exc:
        raise SheetError(
            f"Failed to authenticate with Google Sheets: {exc}",
            details=str(exc),
        )


class ReferenceReader:
    """Reads genre list, reference scripts, and genre config from the sheet.

    Uses the reference-reader service account (read-only scope).
    """

    def __init__(self):
        self._service = None

    def _ensure_service(self):
        """Lazily initialize the Sheets service on first use."""
        if self._service is None:
            self._service = _build_service(
                config.reader_key_path, _READ_SCOPES
            )

    def read_genres(self) -> list[Genre]:
        """Read all genres from the '🎯 Suggested Genres' tab.

        Returns:
            List of Genre models parsed from the sheet.

        Raises:
            SheetError: If the API call fails.
        """
        self._ensure_service()
        try:
            result = (
                self._service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=config.sheet_id,
                    range=f"'{config.genres_tab}'!A1:E50",
                )
                .execute()
            )
        except HttpError as exc:
            raise SheetError(
                "Failed to read genres from Google Sheet",
                details=str(exc),
            )

        rows = result.get("values", [])
        if len(rows) < 2:
            logger.warning("Genres tab is empty or has no data rows")
            return []

        header = _normalize_header(rows[0])
        genres = []
        for row in rows[1:]:
            parsed = _row_to_dict(header, row)
            if not parsed.get("genre_id"):
                continue
            genres.append(
                Genre(
                    genre_id=parsed.get("genre_id", ""),
                    display_name=parsed.get("display_name", ""),
                    icon=parsed.get("icon", "🎬"),
                    difficulty=parsed.get(
                        "difficulty",
                        parsed.get("competition_level", ""),
                    ),
                    is_active=_parse_bool(
                        parsed.get("is_active", "true")
                    ),
                )
            )
        logger.info(
            "Genres loaded from sheet",
            extra={"extra_data": {"count": len(genres)}},
        )
        return genres

    def read_genre_config(self) -> list[GenreConfig]:
        """Read per-genre configuration from the 'genre_config' tab.

        Returns:
            List of GenreConfig models.

        Raises:
            SheetError: If the API call fails.
        """
        self._ensure_service()
        try:
            result = (
                self._service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=config.sheet_id,
                    range=f"'{config.genre_config_tab}'!A1:H50",
                )
                .execute()
            )
        except HttpError as exc:
            raise SheetError(
                "Failed to read genre config from Google Sheet",
                details=str(exc),
            )

        rows = result.get("values", [])
        if len(rows) < 2:
            logger.warning("genre_config tab is empty")
            return []

        header = _normalize_header(rows[0])
        configs = []
        for row in rows[1:]:
            parsed = _row_to_dict(header, row)
            if not parsed.get("genre_id"):
                continue
            configs.append(
                GenreConfig(
                    genre_id=parsed.get("genre_id", ""),
                    tts_voice=parsed.get("tts_voice", "en-US-Neural2-D"),
                    tts_rate=float(parsed.get("tts_rate", "0.95")),
                    tts_pitch=float(parsed.get("tts_pitch", "0.0")),
                    layout=parsed.get("layout", "split_screen"),
                    caption_preset=parsed.get("caption_preset", "clean_pro"),
                    music_mood=parsed.get("music_mood", "neutral"),
                )
            )
        logger.info(
            "Genre configs loaded",
            extra={"extra_data": {"count": len(configs)}},
        )
        return configs

    def read_reference_scripts(self, tab_name: str) -> list[dict]:
        """Read reference scripts from a genre-specific tab.

        Args:
            tab_name: The sheet tab name (e.g. 'Genre 2').

        Returns:
            List of dicts with script data (raw key-value pairs).

        Raises:
            SheetError: If the API call fails.
        """
        self._ensure_service()
        try:
            result = (
                self._service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=config.sheet_id,
                    range=f"'{tab_name}'!A1:DU50",
                )
                .execute()
            )
        except HttpError as exc:
            raise SheetError(
                f"Failed to read scripts from tab '{tab_name}'",
                details=str(exc),
            )

        rows = result.get("values", [])
        if len(rows) < 2:
            return []

        header = _normalize_header(rows[0])
        scripts = []
        for row in rows[1:]:
            parsed = _row_to_dict(header, row)
            # Only include rows that have a script
            script_key = "full script / transcript"
            if parsed.get(script_key) or parsed.get("full_script"):
                scripts.append(parsed)
        logger.info(
            f"Reference scripts loaded from '{tab_name}'",
            extra={"extra_data": {"count": len(scripts)}},
        )
        return scripts

    def get_tab_names(self) -> list[str]:
        """Get all tab names in the spreadsheet.

        Returns:
            List of tab name strings.

        Raises:
            SheetError: If the API call fails.
        """
        self._ensure_service()
        try:
            meta = (
                self._service.spreadsheets()
                .get(spreadsheetId=config.sheet_id)
                .execute()
            )
            return [s["properties"]["title"] for s in meta["sheets"]]
        except HttpError as exc:
            raise SheetError(
                "Failed to get sheet tab names",
                details=str(exc),
            )


class SubmissionWriter:
    """Appends data to the submissions and feedback tabs.

    Uses the data-writer service account (write scope).
    """

    def __init__(self):
        self._service = None

    def _ensure_service(self):
        """Lazily initialize the Sheets service on first use."""
        if self._service is None:
            self._service = _build_service(
                config.writer_key_path, _WRITE_SCOPES
            )

    def append_submission(self, row: list[str]) -> None:
        """Append a video submission row to the submissions tab.

        Args:
            row: List of string values matching the submission headers.

        Raises:
            SheetError: If the API call fails.
        """
        self._ensure_service()
        try:
            self._service.spreadsheets().values().append(
                spreadsheetId=config.sheet_id,
                range=f"'{config.submissions_tab}'!A:A",
                valueInputOption="RAW",
                body={"values": [row]},
            ).execute()
            logger.info("Submission appended to sheet")
        except HttpError as exc:
            raise SheetError(
                "Failed to write submission to sheet",
                details=str(exc),
            )

    def append_feedback(self, row: list[str]) -> None:
        """Append a regeneration feedback row to the feedback tab.

        Args:
            row: List of string values matching the feedback headers.

        Raises:
            SheetError: If the API call fails.
        """
        self._ensure_service()
        try:
            self._service.spreadsheets().values().append(
                spreadsheetId=config.sheet_id,
                range=f"'{config.regen_feedback_tab}'!A:A",
                valueInputOption="RAW",
                body={"values": [row]},
            ).execute()
            logger.info("Feedback appended to sheet")
        except HttpError as exc:
            raise SheetError(
                "Failed to write feedback to sheet",
                details=str(exc),
            )


# ─── Helpers ───────────────────────────────────────────

def _normalize_header(header_row: list[str]) -> list[str]:
    """Normalize sheet header names to snake_case.

    Converts 'Genre ID' → 'genre_id', 'Display Name' → 'display_name'.

    Args:
        header_row: Raw header strings from the sheet.

    Returns:
        List of normalized snake_case header strings.
    """
    import re
    normalized = []
    for h in header_row:
        key = h.strip().lower()
        key = re.sub(r'[^a-z0-9\s_]', '', key)  # Remove special chars
        key = re.sub(r'\s+', '_', key)            # Spaces → underscores
        normalized.append(key)
    return normalized


def _row_to_dict(header: list[str], row: list[str]) -> dict:
    """Map a row of values to a dict using the header row as keys.

    Args:
        header: List of normalized column header strings.
        row: List of cell values.

    Returns:
        Dict mapping header names to cell values.
    """
    result = {}
    for i, key in enumerate(header):
        result[key] = row[i].strip() if i < len(row) and row[i] else ""
    return result


def _parse_bool(value: str) -> bool:
    """Parse a string boolean value from the sheet.

    Args:
        value: String like 'true', 'yes', '1', 'TRUE'.

    Returns:
        Boolean interpretation of the string.
    """
    return value.strip().lower() in ("true", "yes", "1", "y")
