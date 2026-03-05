"""
Script Agent — generates and validates YouTube Shorts scripts.

Architecture:
    Gemini 2.5 Flash → generates script JSON
    5-layer validation → Pydantic + rules + Groq cross-check
    Retry up to 3x with feedback injection on failure

Follows agent isolation rules:
    - Input/output are Pydantic models
    - Services are dependency-injected
    - Never imports other agents
    - Retries are agent-internal
"""
import json
import re
from typing import Optional

from backend.agents.prompts import (
    SCRIPT_SYSTEM_PROMPT,
    SCRIPT_USER_PROMPT,
    VALIDATION_SYSTEM_PROMPT,
    VALIDATION_USER_PROMPT,
    RETRY_PROMPT,
    CUSTOM_TOPIC_LINE,
    NO_CUSTOM_TOPIC,
    CALIBRATION_SECTION,
    NO_CALIBRATION,
    BANNED_PHRASES,
    WORD_TARGETS,
)
from backend.agents.script_dedup import check_dedup
from backend.core.cache_manager import CacheManager
from backend.core.config import config
from backend.core.exceptions import (
    ScriptGenerationError,
    ScriptValidationError,
)
from backend.core.logger import get_logger
from backend.core.models import (
    GenreCalibration,
    GenreConfig,
    ImageCue,
    ScriptOutput,
    SfxCue,
)

logger = get_logger(__name__)

# ─── Constants ─────────────────────────────────────────
_MAX_RETRIES = 3
_MIN_IMAGE_CUES = 3
_WORD_TOLERANCE = 15


class ScriptAgent:
    """Generates and validates YouTube Shorts scripts.

    Uses Gemini for generation and Groq for cross-validation.
    Services are injected for testability.

    Args:
        gemini_service: Callable that takes (system, user) prompts
                        and returns a string response.
        groq_service: Callable that takes (system, user) prompts
                      and returns a string response.
        cache: CacheManager for fetching reference scripts.
    """

    def __init__(
        self,
        gemini_service,
        groq_service,
        cache: CacheManager,
    ):
        self._gemini = gemini_service
        self._groq = groq_service
        self._cache = cache

    async def generate(
        self,
        genre_id: str,
        mode: str = "auto",
        custom_topic: Optional[str] = None,
        calibration: Optional[GenreCalibration] = None,
    ) -> ScriptOutput:
        """Generate a validated script for the given genre.

        Args:
            genre_id: Genre identifier from the cache.
            mode: 'auto' or 'custom'.
            custom_topic: User-provided topic (if mode is 'custom').
            calibration: User's calibration profile (if available).

        Returns:
            Validated ScriptOutput model.

        Raises:
            ScriptGenerationError: If generation fails after retries.
            ScriptValidationError: If validation fails after retries.
        """
        genre_config = await self._cache.get_genre_config(genre_id)
        if not genre_config:
            genre_config = GenreConfig(genre_id=genre_id)

        ref_scripts = await self._cache.get_reference_scripts(genre_id)
        target_duration = config.target_duration_sec
        target_words = WORD_TARGETS.get(target_duration, 108)

        retry_feedback = ""
        last_error = None

        for attempt in range(1, _MAX_RETRIES + 1):
            logger.info(
                f"Script generation attempt {attempt}/{_MAX_RETRIES}",
                extra={"extra_data": {
                    "genre": genre_id, "attempt": attempt,
                }},
            )
            try:
                # Step 1: Generate with Gemini
                script_output = await self._call_gemini(
                    genre_id, genre_config, ref_scripts,
                    target_duration, target_words,
                    mode, custom_topic, calibration,
                    retry_feedback,
                )

                # Step 2: Validate (5 layers)
                issues = self._validate_rules(
                    script_output, target_words
                )
                if issues:
                    retry_feedback = "; ".join(issues)
                    logger.warning(
                        f"Rule validation failed: {retry_feedback}",
                        extra={"extra_data": {"attempt": attempt}},
                    )
                    last_error = retry_feedback
                    continue

                # Step 3: Groq cross-validation
                groq_result = await self._call_groq(
                    script_output, genre_id, target_duration
                )
                if not groq_result.get("passed", False):
                    retry_feedback = groq_result.get("feedback", "")
                    issues_list = groq_result.get("issues", [])
                    retry_feedback += " Issues: " + "; ".join(issues_list)
                    logger.warning(
                        f"Groq validation failed (score: "
                        f"{groq_result.get('overall_score', '?')})",
                        extra={"extra_data": {
                            "attempt": attempt,
                            "score": groq_result.get("overall_score"),
                        }},
                    )
                    last_error = retry_feedback
                    continue

                # Layer 5: Deduplication (TF-IDF cosine <70%)
                prev_scripts = await self._cache.get_recent_scripts(
                    genre_id, limit=50
                )
                dedup_issue = check_dedup(
                    script_output.narration, prev_scripts,
                )
                if dedup_issue:
                    retry_feedback = dedup_issue
                    logger.warning(
                        f"Dedup failed: {dedup_issue}",
                        extra={"extra_data": {"attempt": attempt}},
                    )
                    last_error = dedup_issue
                    continue

                logger.info(
                    "Script generated and validated successfully",
                    extra={"extra_data": {
                        "genre": genre_id,
                        "word_count": script_output.word_count,
                        "attempt": attempt,
                    }},
                )
                return script_output

            except (ScriptGenerationError, ScriptValidationError):
                raise
            except Exception as exc:
                last_error = str(exc)
                logger.error(
                    f"Script generation error: {exc}",
                    extra={"extra_data": {"attempt": attempt}},
                )

        raise ScriptGenerationError(
            f"Script generation failed after {_MAX_RETRIES} attempts",
            details=last_error,
        )

    # ─── Gemini Call ───────────────────────────────────

    async def _call_gemini(
        self, genre_id, genre_config, ref_scripts,
        target_duration, target_words, mode, custom_topic,
        calibration, retry_feedback,
    ) -> ScriptOutput:
        """Call Gemini to generate a script and parse the response.

        Returns:
            Parsed ScriptOutput model.

        Raises:
            ScriptGenerationError: If parsing fails.
        """
        # Build prompts
        system_prompt = SCRIPT_SYSTEM_PROMPT.format(
            target_words=target_words,
        )

        scripts_text = self._format_reference_scripts(ref_scripts)
        calibration_section = self._format_calibration(calibration)

        user_prompt = SCRIPT_USER_PROMPT.format(
            genre_name=genre_id.replace("_", " ").title(),
            target_duration=target_duration,
            target_words=target_words,
            mode=mode,
            custom_topic_line=(
                CUSTOM_TOPIC_LINE.format(topic=custom_topic)
                if custom_topic else NO_CUSTOM_TOPIC
            ),
            reference_scripts=scripts_text,
            calibration_section=calibration_section,
        )

        if retry_feedback:
            user_prompt += "\n\n" + RETRY_PROMPT.format(
                issues=retry_feedback, feedback=retry_feedback,
            )

        # Call Gemini
        response = await self._gemini(system_prompt, user_prompt)
        return self._parse_script_response(response)

    # ─── Groq Validation ──────────────────────────────

    async def _call_groq(
        self, script: ScriptOutput, genre_id: str,
        target_duration: int,
    ) -> dict:
        """Call Groq/Llama for cross-validation scoring.

        Returns:
            Dict with scores and pass/fail result.
        """
        try:
            user_prompt = VALIDATION_USER_PROMPT.format(
                genre_name=genre_id.replace("_", " ").title(),
                narration=script.narration,
                word_count=script.word_count,
                target_duration=target_duration,
                hook_line=script.hook_line,
            )
            response = await self._groq(
                VALIDATION_SYSTEM_PROMPT, user_prompt
            )
            return _safe_parse_json(response)
        except Exception as exc:
            logger.warning(f"Groq validation call failed: {exc}")
            # If Groq is down, pass by default (graceful degradation)
            return {"passed": True, "overall_score": 0, "feedback": ""}

    # ─── Rule Validation (Layers 1-4) ─────────────────

    def _validate_rules(
        self, script: ScriptOutput, target_words: int
    ) -> list[str]:
        """Run rule-based validation checks on the script.

        Args:
            script: The parsed ScriptOutput.
            target_words: Expected word count.

        Returns:
            List of issue strings. Empty = all checks passed.
        """
        issues = []

        # Layer 1: Pydantic schema (already validated by parsing)

        # Layer 2: Word count bounds
        actual = len(script.narration.split())
        if abs(actual - target_words) > _WORD_TOLERANCE:
            issues.append(
                f"Word count {actual} is too far from target "
                f"{target_words} (±{_WORD_TOLERANCE})"
            )

        # Layer 3: Minimum image cues
        if len(script.image_cues) < _MIN_IMAGE_CUES:
            issues.append(
                f"Need at least {_MIN_IMAGE_CUES} image cues, "
                f"got {len(script.image_cues)}"
            )

        # Layer 4: Banned phrases check
        narration_lower = script.narration.lower()
        for phrase in BANNED_PHRASES:
            if phrase in narration_lower:
                issues.append(f"Contains banned phrase: '{phrase}'")

        return issues

    # ─── Helpers ───────────────────────────────────────

    def _format_reference_scripts(self, scripts: list[dict]) -> str:
        """Format reference scripts for the prompt."""
        if not scripts:
            return "(No reference scripts available for this genre)"

        parts = []
        for i, s in enumerate(scripts[:3], 1):
            text = s.get("script_text", "")[:500]
            parts.append(f"--- Example {i} ---\n{text}")
        return "\n\n".join(parts)

    def _format_calibration(
        self, cal: Optional[GenreCalibration]
    ) -> str:
        """Format calibration data for the prompt."""
        if not cal:
            return NO_CALIBRATION
        return CALIBRATION_SECTION.format(
            user_intent=cal.user_intent,
            why_chosen=cal.why_chosen,
            improvement_notes=cal.improvement_notes,
        )

    def _parse_script_response(self, response: str) -> ScriptOutput:
        """Parse Gemini's JSON response into a ScriptOutput.

        Args:
            response: Raw string response from Gemini.

        Returns:
            Validated ScriptOutput model.

        Raises:
            ScriptGenerationError: If JSON parsing fails.
        """
        data = _safe_parse_json(response)
        if not data or "narration" not in data:
            raise ScriptGenerationError(
                "Gemini returned invalid JSON — no 'narration' field",
                details=response[:500],
            )

        try:
            return ScriptOutput(
                title=data.get("title", "Untitled")[:60],
                narration=data["narration"],
                word_count=len(data["narration"].split()),
                estimated_duration=int(
                    data.get("estimated_duration", 45)
                ),
                hook_line=data.get("hook_line", ""),
                image_cues=[
                    ImageCue(**cue)
                    for cue in data.get("image_cues", [])
                ],
                sfx_cues=[
                    SfxCue(**cue)
                    for cue in data.get("sfx_cues", [])
                ],
                description=data.get("description", ""),
                hashtags=data.get("hashtags", []),
            )
        except Exception as exc:
            raise ScriptGenerationError(
                f"Failed to parse script JSON: {exc}",
                details=str(data)[:500],
            )


# ─── Module-level Helpers ─────────────────────────────

def _safe_parse_json(text: str) -> dict:
    """Extract and parse JSON from an LLM response string.

    Handles common issues like markdown code fences around JSON.

    Args:
        text: Raw LLM response string.

    Returns:
        Parsed dict, or empty dict on failure.
    """
    if not text:
        return {}

    # Strip markdown code fences
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first and last lines (```json and ```)
        lines = [
            l for l in lines
            if not l.strip().startswith("```")
        ]
        cleaned = "\n".join(lines)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}
