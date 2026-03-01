"""
Custom exceptions for the application.
Every error the pipeline can raise is defined here.
Frontend handles these via the APIError response format.
"""


class YTShortsAutoError(Exception):
    """Base exception for the application."""
    error_code: str = "UNKNOWN_ERROR"
    retry_allowed: bool = False

    def __init__(self, message: str, details: str = None):
        super().__init__(message)
        self.message = message
        self.details = details


# ─── API / Auth Errors ─────────────────────────────────

class AuthError(YTShortsAutoError):
    """API key is invalid or expired."""
    error_code = "AUTH_ERROR"
    retry_allowed = False


class QuotaError(YTShortsAutoError):
    """Daily API limit reached."""
    error_code = "QUOTA_ERROR"
    retry_allowed = False


class NetworkError(YTShortsAutoError):
    """Can't connect to external service."""
    error_code = "NETWORK_ERROR"
    retry_allowed = True


# ─── Pipeline Errors ──────────────────────────────────

class ScriptGenerationError(YTShortsAutoError):
    """Failed to generate a valid script after retries."""
    error_code = "SCRIPT_GEN_ERROR"
    retry_allowed = True


class ScriptValidationError(YTShortsAutoError):
    """Script failed quality/safety validation."""
    error_code = "VALIDATION_ERROR"
    retry_allowed = True


class TTSError(YTShortsAutoError):
    """Text-to-speech generation failed."""
    error_code = "TTS_ERROR"
    retry_allowed = True


class ImageFetchError(YTShortsAutoError):
    """All image fetch tiers exhausted."""
    error_code = "IMAGE_FETCH_ERROR"
    retry_allowed = True


class AudioMixError(YTShortsAutoError):
    """Audio mixing/ducking failed."""
    error_code = "AUDIO_MIX_ERROR"
    retry_allowed = True


class RenderError(YTShortsAutoError):
    """FFmpeg video rendering failed."""
    error_code = "RENDER_ERROR"
    retry_allowed = True


class UploadError(YTShortsAutoError):
    """YouTube upload failed."""
    error_code = "UPLOAD_ERROR"
    retry_allowed = True


# ─── System Errors ─────────────────────────────────────

class DiskError(YTShortsAutoError):
    """Not enough disk space."""
    error_code = "DISK_ERROR"
    retry_allowed = False


class SheetError(YTShortsAutoError):
    """Google Sheets API error."""
    error_code = "SHEET_ERROR"
    retry_allowed = True


class LicenseError(YTShortsAutoError):
    """Invalid or expired license."""
    error_code = "LICENSE_ERROR"
    retry_allowed = False


class CacheError(YTShortsAutoError):
    """Local cache read/write failed."""
    error_code = "CACHE_ERROR"
    retry_allowed = True
