"""
Image search service — wraps Pexels and Pixabay APIs.

Provides a unified interface for searching and downloading images
from Tier 2 (Pexels) and Tier 3 (Pixabay) of the 7-tier fallback.
"""
import asyncio
import hashlib
import aiohttp
from pathlib import Path
from typing import Optional

from backend.core.config import config
from backend.core.exceptions import ImageFetchError
from backend.core.logger import get_logger

logger = get_logger(__name__)


class ImageResult:
    """A single image search result with metadata.

    Args:
        url: Direct download URL.
        source: Source provider (pexels, pixabay, etc).
        width: Image width in pixels.
        height: Image height in pixels.
        description: Alt text / description.
    """

    def __init__(
        self, url: str, source: str,
        width: int = 0, height: int = 0,
        description: str = "",
    ):
        self.url = url
        self.source = source
        self.width = width
        self.height = height
        self.description = description

    @property
    def score(self) -> int:
        """Calculate a quality score for ranking results.

        Returns:
            Score from 0-100.
        """
        s = 0
        # Resolution: prefer >= 1080px width
        if self.width >= 1080:
            s += 20
        elif self.width >= 720:
            s += 10
        # Source reliability
        if self.source == "pexels":
            s += 15
        elif self.source == "pixabay":
            s += 12
        # Has description (better for relevance)
        if self.description:
            s += 10
        return s


async def search_pexels(
    query: str, api_key: str, per_page: int = 3,
) -> list[ImageResult]:
    """Search Pexels for images matching the query.

    Args:
        query: Search keywords.
        api_key: Pexels API key.
        per_page: Number of results to return.

    Returns:
        List of ImageResult objects.

    Raises:
        AssetError: If the API call fails.
    """
    if not api_key:
        return []
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "per_page": per_page,
        "orientation": "portrait",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=headers, params=params, timeout=10
            ) as resp:
                if resp.status != 200:
                    logger.warning(
                        f"Pexels API returned {resp.status}",
                    )
                    return []
                data = await resp.json()
    except Exception as exc:
        logger.warning(f"Pexels search failed: {exc}")
        return []

    results = []
    for photo in data.get("photos", []):
        results.append(ImageResult(
            url=photo["src"]["large2x"],
            source="pexels",
            width=photo.get("width", 0),
            height=photo.get("height", 0),
            description=photo.get("alt", ""),
        ))
    return results


async def search_pixabay(
    query: str, api_key: str, per_page: int = 3,
) -> list[ImageResult]:
    """Search Pixabay for images matching the query.

    Args:
        query: Search keywords.
        api_key: Pixabay API key.
        per_page: Number of results to return.

    Returns:
        List of ImageResult objects.

    Raises:
        AssetError: If the API call fails.
    """
    if not api_key:
        return []
    url = "https://pixabay.com/api/"
    params = {
        "key": api_key,
        "q": query,
        "per_page": per_page,
        "editors_choice": "true",
        "safesearch": "true",
        "image_type": "photo",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, params=params, timeout=10
            ) as resp:
                if resp.status != 200:
                    logger.warning(
                        f"Pixabay API returned {resp.status}",
                    )
                    return []
                data = await resp.json()
    except Exception as exc:
        logger.warning(f"Pixabay search failed: {exc}")
        return []

    results = []
    for hit in data.get("hits", []):
        results.append(ImageResult(
            url=hit.get("largeImageURL", hit.get("webformatURL", "")),
            source="pixabay",
            width=hit.get("imageWidth", 0),
            height=hit.get("imageHeight", 0),
            description=hit.get("tags", ""),
        ))
    return results


async def download_image(
    url: str, save_dir: Path, filename: Optional[str] = None,
) -> str:
    """Download an image from URL and save to disk.

    Args:
        url: Image URL to download.
        save_dir: Directory to save the image.
        filename: Optional filename. If None, uses URL hash.

    Returns:
        Absolute path to the saved image file.

    Raises:
        ImageFetchError: If download fails.
    """
    save_dir.mkdir(parents=True, exist_ok=True)
    if not filename:
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        ext = _get_extension(url)
        filename = f"{url_hash}{ext}"

    path = save_dir / filename
    if path.exists():
        return str(path)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as resp:
                if resp.status != 200:
                    raise ImageFetchError(
                        f"Image download failed: HTTP {resp.status}",
                    )
                data = await resp.read()
                path.write_bytes(data)
                logger.debug(
                    "Image downloaded",
                    extra={"extra_data": {
                        "url": url[:80],
                        "size": len(data),
                    }},
                )
                return str(path)
    except ImageFetchError:
        raise
    except Exception as exc:
        raise ImageFetchError(
            f"Image download failed: {exc}",
            details=str(exc),
        )


def _get_extension(url: str) -> str:
    """Extract file extension from URL.

    Args:
        url: Image URL.

    Returns:
        File extension with dot (e.g. '.jpg').
    """
    path = url.split("?")[0]
    if "." in path.split("/")[-1]:
        ext = "." + path.split(".")[-1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".webp"):
            return ext
    return ".jpg"
