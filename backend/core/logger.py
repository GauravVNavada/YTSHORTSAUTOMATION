"""
Structured logging for the application.
All agents and services MUST use this logger, never print().

Log format: JSON with timestamp, level, module, job_id, stage, message, extra.
Output: rotating file (10MB x 5) + console (dev mode).
"""
import logging
import logging.handlers
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class JSONFormatter(logging.Formatter):
    """Formats log records as JSON for structured log analysis."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "job_id"):
            log_entry["job_id"] = record.job_id
        if hasattr(record, "stage"):
            log_entry["stage"] = record.stage
        if hasattr(record, "extra_data"):
            log_entry["extra"] = record.extra_data

        # Add exception info if present
        if record.exc_info and record.exc_info[1]:
            log_entry["error"] = str(record.exc_info[1])
            log_entry["error_type"] = type(record.exc_info[1]).__name__

        return json.dumps(log_entry, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable format for console output during development."""

    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        timestamp = datetime.now().strftime("%H:%M:%S")

        parts = [f"{color}{timestamp} [{record.levelname:8s}]{self.RESET}"]
        parts.append(f"{record.module}: {record.getMessage()}")

        if hasattr(record, "job_id"):
            parts.append(f"(job={record.job_id})")
        if hasattr(record, "stage"):
            parts.append(f"[{record.stage}]")

        if record.exc_info and record.exc_info[1]:
            parts.append(f"ERROR: {record.exc_info[1]}")

        return " ".join(parts)


def setup_logging(
    logs_dir: Path,
    debug: bool = False,
    console: bool = True,
) -> logging.Logger:
    """
    Set up the application logger.

    Args:
        logs_dir: Directory for log files.
        debug: If True, set level to DEBUG and enable verbose output.
        console: If True, also log to console.

    Returns:
        The configured root logger for the app.
    """
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("ytshortsauto")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.handlers.clear()

    # File handler — JSON format, rotating
    file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)

    # Console handler — pretty format, dev mode
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
        console_handler.setFormatter(ConsoleFormatter())
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a child logger for a specific module.

    Usage:
        from backend.core.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Script generated", extra={"job_id": "abc", "stage": "script_gen"})
    """
    return logging.getLogger(f"ytshortsauto.{name}")


class PipelineLogger:
    """
    Convenience wrapper for pipeline logging with job context.

    Usage:
        log = PipelineLogger("job_abc123", "script_generation")
        log.info("Generating script", word_count=128)
        log.warning("Retrying", attempt=2)
        log.error("Failed after 3 retries")
    """

    def __init__(self, job_id: str, stage: str = "", module: str = "pipeline"):
        self._logger = get_logger(module)
        self.job_id = job_id
        self.stage = stage

    def _make_extra(self, **kwargs) -> dict:
        extra = {"job_id": self.job_id, "stage": self.stage}
        if kwargs:
            extra["extra_data"] = kwargs
        return extra

    def set_stage(self, stage: str):
        """Update the current pipeline stage."""
        self.stage = stage

    def info(self, message: str, **kwargs):
        self._logger.info(message, extra=self._make_extra(**kwargs))

    def debug(self, message: str, **kwargs):
        self._logger.debug(message, extra=self._make_extra(**kwargs))

    def warning(self, message: str, **kwargs):
        self._logger.warning(message, extra=self._make_extra(**kwargs))

    def error(self, message: str, exc: Exception = None, **kwargs):
        self._logger.error(message, extra=self._make_extra(**kwargs), exc_info=exc)

    def critical(self, message: str, exc: Exception = None, **kwargs):
        self._logger.critical(message, extra=self._make_extra(**kwargs), exc_info=exc)
