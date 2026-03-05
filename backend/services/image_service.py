"""
Image search service — wraps Pexels, Pixabay, DuckDuckGo, and Wikimedia.

Provides Tiers 2-5 of the 7-tier image fallback system from
MASTER_BLUEPRINT §8. Full 5-factor scoring per spec.
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
        source: Source provider (pexels, pixabay, ddg, wikimedia).
        width: Image width in pixels.
        height: Image height in pixels.
        description: Alt text / description.
        query: Original search query (for scoring).
    """

    def __init__(
        self, url: str, source: str,
        width: int = 0, height: int = 0,
        description: str = "", query: str = "",
    ):
        self.url = url
        self.source = source
        self.width = width
        self.height = height
        self.description = description
        self.query = query

    def score_for(self, keywords: str) -> int:
        """5-factor scoring per MASTER_BLUEPRINT §8.

        Keyword match (30), resolution (20), recency (15),
        source reliability (15), format (10).

        Args:
            keywords: Search keywords for relevance scoring.

        Returns:
            Score from 0-100.
        """
        s = 0
        # Keyword match (30 pts)
        kw_lower = keywords.lower().split()
        desc_lower = (self.description or "").lower()
        matches = sum(1 for k in kw_lower if k in desc_lower)
        s += min(30, matches * 10)

        # Resolution (20 pts)
        if self.width >= 1080:
            s += 20
        elif self.width >= 720:
            s += 12
        elif self.width >= 480:
            s += 5

        # Recency (15 pts) — APIs don't return dates, proxy by source
        if self.source in ("pexels", "pixabay"):
            s += 15  # Curated = recent
        elif self.source == "wikimedia":
            s += 8

        # Source reliability (15 pts)
        _reliability = {"pexels": 15, "pixabay": 13, "ddg": 8, "wikimedia": 12}
        s += _reliability.get(self.source, 5)

        # Format (10 pts) — prefer JPEG/PNG
        ext = _get_extension(self.url)
        if ext in (".jpg", ".jpeg"):
            s += 10
        elif ext == ".png":
            s += 8
        elif ext == ".webp":
            s += 6
        return s

    @property
    def score(self) -> int:
        """Legacy score property using stored query."""
        return self.score_for(self.query)


# ─── Tier 2: Pexels ───────────────────────────────────

async def search_pexels(
    query: str, api_key: str, per_page: int = 3,
) -> list[ImageResult]:
    """Search Pexels for images. Spec: 400-730ms, ~85% generic success."""
    if not api_key:
        return []
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": api_key}
    params = {"query": query, "per_page": per_page, "orientation": "portrait"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=10) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
    except Exception as exc:
        logger.warning(f"Pexels search failed: {exc}")
        return []

    return [
        ImageResult(
            url=p["src"]["large2x"], source="pexels",
            width=p.get("width", 0), height=p.get("height", 0),
            description=p.get("alt", ""), query=query,
        ) for p in data.get("photos", [])
    ]


# ─── Tier 3: Pixabay ──────────────────────────────────

async def search_pixabay(
    query: str, api_key: str, per_page: int = 3,
) -> list[ImageResult]:
    """Search Pixabay. Spec: 370-680ms, editors_choice filter."""
    if not api_key:
        return []
    url = "https://pixabay.com/api/"
    params = {
        "key": api_key, "q": query, "per_page": per_page,
        "editors_choice": "true", "safesearch": "true", "image_type": "photo",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
    except Exception as exc:
        logger.warning(f"Pixabay search failed: {exc}")
        return []

    return [
        ImageResult(
            url=h.get("largeImageURL", h.get("webformatURL", "")),
            source="pixabay",
            width=h.get("imageWidth", 0), height=h.get("imageHeight", 0),
            description=h.get("tags", ""), query=query,
        ) for h in data.get("hits", [])
    ]


# ─── Tier 4: DuckDuckGo ───────────────────────────────

async def search_duckduckgo(
    query: str, max_results: int = 3,
) -> list[ImageResult]:
    """Search DuckDuckGo Images. Spec: 1.2-4s, ~95% success, CC filter."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            raw = list(ddgs.images(
                query, max_results=max_results,
                license_image="Share",
            ))
        return [
            ImageResult(
                url=r.get("image", ""), source="ddg",
                width=r.get("width", 0), height=r.get("height", 0),
                description=r.get("title", ""), query=query,
            ) for r in raw if r.get("image")
        ]
    except Exception as exc:
        logger.warning(f"DuckDuckGo search failed: {exc}")
        return []


# ─── Tier 5: Wikimedia Commons ─────────────────────────

async def search_wikimedia(
    query: str, max_results: int = 3,
) -> list[ImageResult]:
    """Search Wikimedia Commons. Spec: 700ms-1.5s, good for celebrities/landmarks."""
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query", "format": "json",
        "generator": "search", "gsrsearch": f"File:{query}",
        "gsrlimit": str(max_results), "prop": "imageinfo",
        "iiprop": "url|size", "iiurlwidth": "1080",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
    except Exception as exc:
        logger.warning(f"Wikimedia search failed: {exc}")
        return []

    results = []
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        info_list = page.get("imageinfo", [])
        if not info_list:
            continue
        info = info_list[0]
        img_url = info.get("thumburl") or info.get("url", "")
        if img_url:
            results.append(ImageResult(
                url=img_url, source="wikimedia",
                width=info.get("thumbwidth", info.get("width", 0)),
                height=info.get("thumbheight", info.get("height", 0)),
                description=page.get("title", ""), query=query,
            ))
    return results


# ─── Download ──────────────────────────────────────────

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
                    raise ImageFetchError(f"HTTP {resp.status}")
                data = await resp.read()
                path.write_bytes(data)
                return str(path)
    except ImageFetchError:
        raise
    except Exception as exc:
        raise ImageFetchError(f"Download failed: {exc}", details=str(exc))


def _get_extension(url: str) -> str:
    """Extract file extension from URL."""
    path = url.split("?")[0]
    if "." in path.split("/")[-1]:
        ext = "." + path.split(".")[-1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".webp"):
            return ext
    return ".jpg"
