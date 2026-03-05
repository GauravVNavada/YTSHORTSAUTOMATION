"""
Asset Agent — fetches images, SFX, and music for a video.

Implements the full 7-tier image fallback system from MASTER_BLUEPRINT §8.
Tiers 2+3 run in parallel per slot. All 5 image slots fetched concurrently.
"""
import asyncio
import random
from pathlib import Path
from typing import Optional

from backend.core.config import config
from backend.core.exceptions import ImageFetchError
from backend.core.logger import get_logger
from backend.core.models import (
    AssetBundle, ImageCue, SfxCue, GenreConfig,
)
from backend.services.image_service import (
    search_pexels, search_pixabay, search_duckduckgo,
    search_wikimedia, download_image, ImageResult,
)

logger = get_logger(__name__)

# Genre fallback colors for Tier 7
_GENRE_COLORS = {
    "scary_stories": (20, 10, 30),
    "motivation": (30, 20, 10),
    "tech_ai": (10, 15, 30),
    "history": (25, 20, 15),
    "science": (10, 20, 30),
    "psychology": (20, 15, 25),
}


class AssetAgent:
    """Fetches all media assets needed for video rendering.

    Args:
        pexels_key: Pexels API key.
        pixabay_key: Pixabay API key.
        gemini_service: Optional LLM service for Tier 6 reformulation.
    """

    def __init__(self, pexels_key="", pixabay_key="", gemini_service=None):
        self._pexels_key = pexels_key
        self._pixabay_key = pixabay_key
        self._gemini = gemini_service

    async def generate(
        self, image_cues: list[ImageCue], sfx_cues: list[SfxCue],
        genre_config: GenreConfig, job_id: str,
    ) -> AssetBundle:
        """Fetch all assets for the video.

        All image slots fetched concurrently per MASTER_BLUEPRINT §8.
        """
        asset_dir = config.data_dir / "assets" / job_id
        image_dir = asset_dir / "images"
        image_dir.mkdir(parents=True, exist_ok=True)

        # Parallel image fetching — one task per cue
        image_tasks = [
            self._fetch_image(cue, image_dir, i, genre_config.genre_id)
            for i, cue in enumerate(image_cues)
        ]
        results = await asyncio.gather(*image_tasks, return_exceptions=True)

        valid = [p for p in results if isinstance(p, str)]
        failed = len(results) - len(valid)
        if failed > 0:
            logger.warning(f"{failed} image(s) failed to fetch")

        sfx_paths = self._resolve_sfx(sfx_cues)
        music_path = self._select_music(genre_config.music_mood)
        gameplay_path = self._select_gameplay(genre_config.layout)

        logger.info("Assets fetched", extra={"extra_data": {
            "images": len(valid), "sfx": len(sfx_paths),
            "has_music": music_path is not None,
        }})

        return AssetBundle(
            image_paths=valid, sfx_paths=sfx_paths,
            music_path=music_path, gameplay_path=gameplay_path,
        )

    async def _fetch_image(
        self, cue: ImageCue, save_dir: Path, idx: int, genre_id: str,
    ) -> str:
        """Fetch one image using full 7-tier fallback.

        Tiers 2+3 run in parallel per MASTER_BLUEPRINT §8.
        """
        query = cue.keyword
        fname = f"img_{idx:02d}.jpg"

        # Tier 1: Local cache
        cached = save_dir / fname
        if cached.exists():
            logger.debug(f"Tier 1 cache hit: {fname}")
            return str(cached)

        # Tier 2+3: Pexels + Pixabay IN PARALLEL
        best = await self._search_tiers_2_3(query)
        if best:
            return await download_image(best.url, save_dir, fname)

        # Tier 4: DuckDuckGo
        try:
            results = await search_duckduckgo(query)
            if results:
                best = max(results, key=lambda r: r.score_for(query))
                return await download_image(best.url, save_dir, fname)
        except Exception as exc:
            logger.debug(f"Tier 4 (DDG) failed: {exc}")

        # Tier 5: Wikimedia Commons
        try:
            results = await search_wikimedia(query)
            if results:
                best = max(results, key=lambda r: r.score_for(query))
                return await download_image(best.url, save_dir, fname)
        except Exception as exc:
            logger.debug(f"Tier 5 (Wikimedia) failed: {exc}")

        # Tier 6: LLM reformulation → retry Pexels
        reformulated = await self._llm_reformulate(query)
        if reformulated and reformulated != query:
            logger.info(f"Tier 6: '{query}' → '{reformulated}'")
            best = await self._search_tiers_2_3(reformulated)
            if best:
                return await download_image(best.url, save_dir, fname)

        # Tier 7: Genre fallback — pre-cached image + genre tint
        logger.warning(f"All tiers failed for '{query}', using genre fallback")
        return _create_genre_fallback(save_dir, fname, genre_id, cue.mood)

    async def _search_tiers_2_3(self, query: str) -> Optional[ImageResult]:
        """Run Pexels + Pixabay in parallel, return best result."""
        try:
            pexels_task = search_pexels(query, self._pexels_key)
            pixabay_task = search_pixabay(query, self._pixabay_key)
            pex_results, pix_results = await asyncio.gather(
                pexels_task, pixabay_task, return_exceptions=True,
            )
            all_results = []
            if isinstance(pex_results, list):
                all_results.extend(pex_results)
            if isinstance(pix_results, list):
                all_results.extend(pix_results)
            if all_results:
                return max(all_results, key=lambda r: r.score_for(query))
        except Exception as exc:
            logger.debug(f"Tiers 2+3 failed: {exc}")
        return None

    async def _llm_reformulate(self, query: str) -> Optional[str]:
        """Use Gemini to rewrite a failed image query.

        Spec §8 Tier 6: "Spider-Man" → "person in red spandex".
        """
        if not self._gemini:
            return None
        try:
            prompt = (
                f"Rewrite this image search query to avoid copyrighted "
                f"names while keeping the visual meaning. Return ONLY "
                f"the new query, nothing else.\n\nQuery: {query}"
            )
            result = await self._gemini(
                "You are a helpful image search assistant.", prompt,
            )
            return result.strip()[:100] if result else None
        except Exception as exc:
            logger.debug(f"Tier 6 LLM reformulation failed: {exc}")
            return None

    def _resolve_sfx(self, sfx_cues: list[SfxCue]) -> list[str]:
        """Resolve SFX cues to local file paths.

        Silence > wrong sound per MASTER_BLUEPRINT §11.
        """
        sfx_dir = config.assets_dir / "sfx"
        paths = []
        for cue in sfx_cues:
            for ext in (".wav", ".mp3", ".ogg"):
                candidate = sfx_dir / f"{cue.sfx_type}{ext}"
                if candidate.exists():
                    paths.append(str(candidate))
                    break
            else:
                # Try category folders
                cat_dir = sfx_dir / cue.sfx_type
                if cat_dir.is_dir():
                    files = list(cat_dir.glob("*.*"))
                    if files:
                        paths.append(str(files[0]))
        return paths

    def _select_music(self, mood: str) -> Optional[str]:
        """Select background music track by mood."""
        music_dir = config.assets_dir / "music"
        mood_dir = music_dir / mood
        if mood_dir.is_dir():
            tracks = list(mood_dir.glob("*.mp3")) + list(mood_dir.glob("*.wav"))
            if tracks:
                return str(random.choice(tracks))
        all_tracks = list(music_dir.rglob("*.mp3")) + list(music_dir.rglob("*.wav"))
        if all_tracks:
            return str(random.choice(all_tracks))
        return None

    def _select_gameplay(self, layout: str) -> Optional[str]:
        """Select gameplay clip if layout requires it."""
        if layout not in ("split_screen", "full_gameplay"):
            return None
        gp_dir = config.assets_dir / "gameplay"
        if not gp_dir.is_dir():
            return None
        clips = list(gp_dir.glob("*.mp4"))
        return str(random.choice(clips)) if clips else None


def _create_genre_fallback(
    save_dir: Path, filename: str, genre_id: str, mood: str,
) -> str:
    """Create a genre-tinted fallback image per Tier 7.

    Uses pre-cached genre colors + gradient effect.
    """
    base_color = _GENRE_COLORS.get(genre_id, (30, 30, 40))
    mood_tints = {
        "eerie": (-5, -10, 10), "dark": (-10, -10, 5),
        "horror": (15, -10, -10), "dramatic": (-5, -5, 15),
    }
    tint = mood_tints.get(mood, (0, 0, 0))
    color = tuple(max(0, min(255, b + t)) for b, t in zip(base_color, tint))

    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (1080, 1920), color)
        draw = ImageDraw.Draw(img)
        # Add subtle gradient overlay
        for y in range(1920):
            alpha = int(y / 1920 * 40)
            draw.line([(0, y), (1080, y)], fill=(
                min(255, color[0] + alpha),
                min(255, color[1] + alpha),
                min(255, color[2] + alpha),
            ))
        path = save_dir / filename
        img.save(str(path), "JPEG", quality=85)
        return str(path)
    except ImportError:
        path = save_dir / filename
        path.write_bytes(b"\xff\xd8\xff\xe0")
        return str(path)
