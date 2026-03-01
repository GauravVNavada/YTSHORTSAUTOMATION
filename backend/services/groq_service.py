"""
Groq API service wrapper.

Wraps the Groq API (Llama 3.3 70B) for script validation.
Used as a cross-model check to catch issues Gemini might miss.
"""
import asyncio
from typing import Optional

from backend.core.config import config
from backend.core.exceptions import AuthError, NetworkError, QuotaError
from backend.core.logger import get_logger

logger = get_logger(__name__)


class GroqService:
    """Wrapper for Groq API calls (Llama 3.3 70B validation).

    Args:
        api_key: Groq API key. If None, must be set before calling.
    """

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key
        self._client = None

    def _ensure_client(self) -> None:
        """Lazily initialize the Groq client."""
        if self._client is not None:
            return
        if not self._api_key:
            raise AuthError(
                "Groq API key not configured",
                details="Set your Groq API key in Settings",
            )
        try:
            from groq import Groq
            self._client = Groq(api_key=self._api_key)
        except Exception as exc:
            raise AuthError(
                f"Failed to initialize Groq client: {exc}",
                details=str(exc),
            )

    async def generate(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """Generate text using Groq / Llama.

        Args:
            system_prompt: System instruction for the model.
            user_prompt: User message / content to validate.

        Returns:
            The model's text response.

        Raises:
            AuthError: If the API key is invalid.
            QuotaError: If the rate limit is exceeded.
            NetworkError: If the API is unreachable.
        """
        self._ensure_client()
        try:
            response = await asyncio.to_thread(
                self._client.chat.completions.create,
                model=config.groq_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=512,
            )
            text = response.choices[0].message.content or ""
            logger.debug(
                "Groq response received",
                extra={"extra_data": {"length": len(text)}},
            )
            return text
        except Exception as exc:
            error_str = str(exc).lower()
            if "api key" in error_str or "401" in error_str:
                raise AuthError(
                    "Groq API key is invalid or expired",
                    details=str(exc),
                )
            if "rate" in error_str or "429" in error_str:
                raise QuotaError(
                    "Groq rate limit exceeded",
                    details=str(exc),
                )
            raise NetworkError(
                f"Groq API call failed: {exc}",
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
