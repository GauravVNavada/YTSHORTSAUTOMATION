"""
Asset Agent — fetches images, SFX, and music for a video.

Implements the 7-tier image fallback system from MASTER_BLUEPRINT:
    Tier 1: Local cache (SQLite)
    Tier 2: Pexels API
    Tier 3: Pixabay API
    Tier 4-7: Fallback stubs (DDG, Wikimedia, LLM rewrite, genre default)

Also resolves SFX from the local library and selects background music.
Follows agent isolation rules — no cross-agent imports.
"""
import asyncio
from pathlib import Path
from typing import Optional

from backend.core.config import config
from backend.core.exceptions import ImageFetchError, AudioMixError
from backend.core.logger import get_logger
from backend.core.models import (
    AssetBundle,
    ImageCue,
    SfxCue,
    GenreConfig,
)
from backend.services.image_service import (
    search_pexels,
    search_pixabay,
    download_image,
)

logger = get_logger(__name__)


class AssetAgent:
    """Fetches all media assets needed for video rendering.

    Args:
        pexels_key: User's Pexels API key (optional).
        pixabay_key: User's Pixabay API key (optional).
    """

    def __init__(
        self,
        pexels_key: str = "",
        pixabay_key: str = "",
    ):
        self._pexels_key = pexels_key
        self._pixabay_key = pixabay_key

    async def generate(
        self,
        image_cues: list[ImageCue],
        sfx_cues: list[SfxCue],
        genre_config: GenreConfig,
        job_id: str,
    ) -> AssetBundle:
        """Fetch all assets for the video.

        Args:
            image_cues: Image cues from ScriptOutput.
            sfx_cues: SFX cues from ScriptOutput.
            genre_config: Genre configuration for music mood.
            job_id: Unique job identifier for file organization.

        Returns:
            AssetBundle with paths to all fetched assets.

        Raises:
            AssetError: If critical assets cannot be fetched.
        """
        asset_dir = config.data_dir / "assets" / job_id
        image_dir = asset_dir / "images"
        image_dir.mkdir(parents=True, exist_ok=True)

        # Fetch images in parallel (one task per cue)
        image_tasks = [
            self._fetch_image(cue, image_dir, i)
            for i, cue in enumerate(image_cues)
        ]
        image_paths = await asyncio.gather(
            *image_tasks, return_exceptions=True
        )

        # Filter out failures, keep valid paths
        valid_image_paths = [
            p for p in image_paths if isinstance(p, str)
        ]
        failed_count = len(image_paths) - len(valid_image_paths)
        if failed_count > 0:
            logger.warning(
                f"{failed_count} image(s) failed to fetch",
                extra={"extra_data": {"job_id": job_id}},
            )

        # Resolve SFX from local library
        sfx_paths = self._resolve_sfx(sfx_cues)

        # Select background music by mood
        music_path = self._select_music(genre_config.music_mood)

        # Select gameplay clip if layout requires it
        gameplay_path = self._select_gameplay(genre_config.layout)

        logger.info(
            "Assets fetched",
            extra={"extra_data": {
                "images": len(valid_image_paths),
                "sfx": len(sfx_paths),
                "has_music": music_path is not None,
                "has_gameplay": gameplay_path is not None,
            }},
        )

        return AssetBundle(
            image_paths=valid_image_paths,
            sfx_paths=sfx_paths,
            music_path=music_path,
            gameplay_path=gameplay_path,
        )

    async def _fetch_image(
        self, cue: ImageCue, save_dir: Path, index: int
    ) -> str:
        """Fetch a single image using the 7-tier fallback.

        Args:
            cue: Image cue with keyword and mood.
            save_dir: Directory to save downloaded images.
            index: Image index for filename.

        Returns:
            Path to the downloaded image.

        Raises:
            AssetError: If all tiers fail.
        """
        query = cue.keyword
        filename = f"img_{index:02d}.jpg"

        # Tier 1: Check local cache
        cached = save_dir / filename
        if cached.exists():
            logger.debug(f"Tier 1 cache hit: {filename}")
            return str(cached)

        # Tier 2: Pexels API
        try:
            results = await search_pexels(
                query, self._pexels_key
            )
            if results:
                best = max(results, key=lambda r: r.score)
                return await download_image(
                    best.url, save_dir, filename
                )
        except Exception as exc:
            logger.debug(f"Tier 2 (Pexels) failed: {exc}")

        # Tier 3: Pixabay API
        try:
            results = await search_pixabay(
                query, self._pixabay_key
            )
            if results:
                best = max(results, key=lambda r: r.score)
                return await download_image(
                    best.url, save_dir, filename
                )
        except Exception as exc:
            logger.debug(f"Tier 3 (Pixabay) failed: {exc}")

        # Tier 4-6: DuckDuckGo, Wikimedia, LLM (stubs)
        logger.debug(f"Tiers 4-6 not yet implemented for: {query}")

        # Tier 7: Genre fallback — use a placeholder
        logger.warning(
            f"All image tiers failed for '{query}', using fallback",
        )
        return _create_fallback_image(save_dir, filename, cue.mood)

    def _resolve_sfx(self, sfx_cues: list[SfxCue]) -> list[str]:
        """Resolve SFX cues to local file paths.

        Checks the local SFX library (assets/sfx/) for matching files.
        If no match found, the cue is skipped (silence > wrong sound).

        Args:
            sfx_cues: SFX cues from ScriptOutput.

        Returns:
            List of paths to resolved SFX files.
        """
        sfx_dir = config.assets_dir / "sfx"
        paths = []
        for cue in sfx_cues:
            # Try exact match: sfx_type.wav or sfx_type.mp3
            for ext in (".wav", ".mp3", ".ogg"):
                candidate = sfx_dir / f"{cue.sfx_type}{ext}"
                if candidate.exists():
                    paths.append(str(candidate))
                    break
            # Also try category folders
            category_dir = sfx_dir / cue.sfx_type
            if category_dir.is_dir():
                files = list(category_dir.glob("*.*"))
                if files:
                    paths.append(str(files[0]))
        return paths

    def _select_music(
        self, mood: str
    ) -> Optional[str]:
        """Select a background music track by mood.

        Looks in assets/music/{mood}/ for available tracks.

        Args:
            mood: Music mood from GenreConfig.

        Returns:
            Path to the selected music file, or None.
        """
        music_dir = config.assets_dir / "music"

        # Try mood-specific folder
        mood_dir = music_dir / mood
        if mood_dir.is_dir():
            tracks = list(mood_dir.glob("*.mp3")) + \
                     list(mood_dir.glob("*.wav"))
            if tracks:
                import random
                selected = random.choice(tracks)
                logger.debug(f"Music selected: {selected.name}")
                return str(selected)

        # Try any music file
        all_tracks = list(music_dir.rglob("*.mp3")) + \
                     list(music_dir.rglob("*.wav"))
        if all_tracks:
            import random
            selected = random.choice(all_tracks)
            return str(selected)

        logger.info("No music tracks found")
        return None

    def _select_gameplay(
        self, layout: str
    ) -> Optional[str]:
        """Select a gameplay clip if the layout requires it.

        Args:
            layout: Layout mode from GenreConfig.

        Returns:
            Path to gameplay clip, or None.
        """
        if layout not in ("split_screen", "full_gameplay"):
            return None

        gameplay_dir = config.assets_dir / "gameplay"
        if not gameplay_dir.is_dir():
            return None

        clips = list(gameplay_dir.glob("*.mp4"))
        if clips:
            import random
            selected = random.choice(clips)
            logger.debug(f"Gameplay selected: {selected.name}")
            return str(selected)

        return None


def _create_fallback_image(
    save_dir: Path, filename: str, mood: str
) -> str:
    """Create a solid-color fallback image with genre-appropriate tint.

    Args:
        save_dir: Directory to save the image.
        filename: Target filename.
        mood: Mood hint for color selection.

    Returns:
        Path to the created fallback image.
    """
    # Mood → color mapping
    colors = {
        "eerie": (20, 10, 30),
        "dark": (15, 15, 25),
        "horror": (30, 5, 5),
        "dramatic": (10, 10, 35),
        "ominous": (25, 10, 20),
        "unsettling": (20, 15, 25),
    }
    color = colors.get(mood, (30, 30, 40))

    try:
        from PIL import Image
        img = Image.new("RGB", (1080, 1920), color)
        path = save_dir / filename
        img.save(str(path), "JPEG", quality=85)
        return str(path)
    except ImportError:
        # Pillow not available — write a minimal file
        path = save_dir / filename
        path.write_bytes(b"\xff\xd8\xff\xe0")  # JPEG header stub
        return str(path)
