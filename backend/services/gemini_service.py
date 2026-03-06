"""
Gemini API service wrapper.

Wraps the Google Gemini 2.5 Flash API for script generation.
Handles authentication, rate limiting, and error mapping.
"""
import asyncio
from typing import Optional

from backend.core.config import config
from backend.core.exceptions import AuthError, NetworkError, QuotaError
from backend.core.logger import get_logger

logger = get_logger(__name__)


class GeminiService:
    """Wrapper for Google Gemini API calls.

    Args:
        api_key: Gemini API key. If None, must be set before calling.
    """

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key
        self._client = None

    def _ensure_client(self) -> None:
        """Lazily initialize the Gemini client."""
        if self._client is not None:
            return
        if not self._api_key:
            raise AuthError(
                "Gemini API key not configured",
                details="Set your Gemini API key in Settings",
            )
        try:
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
        except Exception as exc:
            raise AuthError(
                f"Failed to initialize Gemini client: {exc}",
                details=str(exc),
            )

    async def generate(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """Generate text using Gemini.

        Args:
            system_prompt: System instruction for the model.
            user_prompt: User message / content to process.

        Returns:
            The model's text response.

        Raises:
            AuthError: If the API key is invalid.
            QuotaError: If the daily limit is exceeded.
            NetworkError: If the API is unreachable.
        """
        self._ensure_client()
        try:
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=config.gemini_model,
                contents=user_prompt,
                config={
                    "system_instruction": system_prompt,
                    "temperature": 0.9,
                    "max_output_tokens": 4096,
                    "response_mime_type": "application/json",
                },
            )
            text = response.text or ""
            logger.debug(
                "Gemini response received",
                extra={"extra_data": {"length": len(text)}},
            )
            return text
        except Exception as exc:
            error_str = str(exc).lower()
            if "api key" in error_str or "401" in error_str:
                raise AuthError(
                    "Gemini API key is invalid or expired",
                    details=str(exc),
                )
            if "quota" in error_str or "429" in error_str:
                raise QuotaError(
                    "Gemini daily quota exceeded",
                    details=str(exc),
                )
            raise NetworkError(
                f"Gemini API call failed: {exc}",
                details=str(exc),
            )

    async def __call__(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """Allow using the service as a callable (for DI).

        Args:
            system_prompt: System instruction.
            user_prompt: User message.

        Returns:
            Generated text response.
        """
        return await self.generate(system_prompt, user_prompt)
