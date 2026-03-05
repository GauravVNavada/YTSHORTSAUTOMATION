"""
Pipeline Orchestrator — state machine that chains all agents.

Per ENGINEERING_SPECS_PART2 §8: runs Script → Asset + Audio (parallel)
→ Visual → Upload. Persists state for crash recovery.

Never exceeds 300 lines. Agents are injected, never imported directly.
"""
import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional, Awaitable

from backend.core.cache_manager import CacheManager
from backend.core.exceptions import PipelineError
from backend.core.logger import get_logger
from backend.core.models import (
    PipelineStage,
    PipelineState,
    GenreMode,
)

logger = get_logger(__name__)

# Type alias for progress callback
ProgressCallback = Optional[
    Callable[[PipelineStage, float, str], Awaitable[None]]
]


class Orchestrator:
    """Runs the full video generation pipeline.

    Chains agents: Script → Asset+Audio (parallel) → Visual → Upload.
    Persists state after each stage for crash recovery.

    Args:
        script_agent: Injected ScriptAgent instance.
        asset_agent: Injected AssetAgent instance.
        audio_agent: Injected AudioAgent instance.
        visual_agent: Injected VisualAgent instance.
        upload_agent: Injected UploadAgent instance.
        cache: CacheManager for state persistence.
    """

    def __init__(
        self,
        script_agent,
        asset_agent,
        audio_agent,
        visual_agent,
        upload_agent,
        cache: CacheManager,
    ):
        self._script = script_agent
        self._asset = asset_agent
        self._audio = audio_agent
        self._visual = visual_agent
        self._upload = upload_agent
        self._cache = cache

    async def generate(
        self,
        genre_id: str,
        mode: str = "auto",
        custom_topic: str = "",
        schedule: str = "now",
        on_progress: ProgressCallback = None,
    ) -> PipelineState:
        """Run the full pipeline from script to upload.

        Args:
            genre_id: Genre identifier (e.g. "scary_stories").
            mode: "auto" or "custom".
            custom_topic: Topic string when mode="custom".
            schedule: "now" | "next_best" | ISO datetime.
            on_progress: Async callback for progress updates.

        Returns:
            Final PipelineState with all outputs.

        Raises:
            PipelineError: If any stage fails fatally.
        """
        job_id = f"{genre_id}_{uuid.uuid4().hex[:8]}"
        state = PipelineState(
            job_id=job_id,
            genre_id=genre_id,
            mode=GenreMode(mode),
            custom_topic=custom_topic or None,
        )

        try:
            # Stage 1: Script generation
            state = await self._run_script(state, on_progress)

            # Stage 2: Asset + Audio in parallel
            state = await self._run_parallel_fetch(state, on_progress)

            # Stage 3: Video rendering
            state = await self._run_video_render(state, on_progress)

            # Stage 4: Upload
            state = await self._run_upload(state, schedule, on_progress)

            # Done
            state.state = PipelineStage.COMPLETE
            await self._save(state)
            await self._progress(
                on_progress, PipelineStage.COMPLETE, 1.0, "Pipeline complete"
            )

            logger.info("Pipeline complete", extra={"extra_data": {
                "job_id": job_id,
                "timings": state.stage_timings,
            }})
            return state

        except Exception as exc:
            state.state = PipelineStage.FAILED
            state.errors.append(str(exc))
            await self._save(state)
            logger.error(f"Pipeline failed: {exc}", extra={"extra_data": {
                "job_id": job_id, "stage": state.state,
            }})
            raise PipelineError(
                f"Pipeline failed at {state.state}: {exc}",
                details=str(exc),
            )

    async def resume(self, job_id: str, **kwargs) -> PipelineState:
        """Resume a crashed pipeline from the last checkpoint.

        Args:
            job_id: Previously saved job ID.

        Returns:
            Final PipelineState.

        Raises:
            PipelineError: If job not found or resume fails.
        """
        state = await self._cache.load_pipeline_state(job_id)
        if not state:
            raise PipelineError(f"Job {job_id} not found in cache")

        logger.info(f"Resuming job {job_id} from {state.state}")

        # Re-enter at the appropriate stage
        on_progress = kwargs.get("on_progress")
        schedule = kwargs.get("schedule", "now")

        if state.state in (
            PipelineStage.INITIALIZING,
            PipelineStage.SCRIPT_GENERATION,
            PipelineStage.SCRIPT_VALIDATION,
        ):
            state = await self._run_script(state, on_progress)
            state = await self._run_parallel_fetch(state, on_progress)
            state = await self._run_video_render(state, on_progress)
            state = await self._run_upload(state, schedule, on_progress)

        elif state.state in (
            PipelineStage.TTS_GENERATION,
            PipelineStage.IMAGE_FETCHING,
            PipelineStage.SFX_RESOLUTION,
            PipelineStage.MUSIC_SELECTION,
            PipelineStage.AUDIO_MIXING,
        ):
            state = await self._run_parallel_fetch(state, on_progress)
            state = await self._run_video_render(state, on_progress)
            state = await self._run_upload(state, schedule, on_progress)

        elif state.state in (
            PipelineStage.CAPTION_GENERATION,
            PipelineStage.VIDEO_RENDERING,
        ):
            state = await self._run_video_render(state, on_progress)
            state = await self._run_upload(state, schedule, on_progress)

        state.state = PipelineStage.COMPLETE
        await self._save(state)
        return state

    # ─── Stage Runners ────────────────────────────────

    async def _run_script(
        self, state: PipelineState, on_progress: ProgressCallback,
    ) -> PipelineState:
        """Run script generation + validation."""
        state.state = PipelineStage.SCRIPT_GENERATION
        await self._save(state)
        await self._progress(
            on_progress, PipelineStage.SCRIPT_GENERATION, 0.10,
            "Generating script...",
        )

        t0 = time.monotonic()
        genre_config = await self._cache.get_genre_config(state.genre_id)
        script_output = await self._script.generate(
            state.genre_id,
            mode=state.mode.value,
            custom_topic=state.custom_topic or "",
        )
        state.script_output = script_output
        state.stage_timings["script"] = round(time.monotonic() - t0, 2)
        await self._save(state)
        return state

    async def _run_parallel_fetch(
        self, state: PipelineState, on_progress: ProgressCallback,
    ) -> PipelineState:
        """Run Asset + Audio agents in parallel."""
        state.state = PipelineStage.IMAGE_FETCHING
        await self._save(state)
        await self._progress(
            on_progress, PipelineStage.IMAGE_FETCHING, 0.30,
            "Fetching assets + generating audio...",
        )

        t0 = time.monotonic()
        script = state.script_output
        genre_config = await self._cache.get_genre_config(state.genre_id)

        # Run asset + audio in parallel
        asset_task = self._asset.generate(
            script.image_cues, script.sfx_cues,
            genre_config, state.job_id,
        )
        audio_task = self._audio.generate(
            narration=script.narration,
            genre_config=genre_config,
        )

        asset_bundle, audio_bundle = await asyncio.gather(
            asset_task, audio_task,
        )

        state.asset_bundle = asset_bundle
        state.audio_bundle = audio_bundle
        state.stage_timings["parallel_fetch"] = round(
            time.monotonic() - t0, 2
        )
        await self._save(state)
        return state

    async def _run_video_render(
        self, state: PipelineState, on_progress: ProgressCallback,
    ) -> PipelineState:
        """Run video rendering."""
        state.state = PipelineStage.VIDEO_RENDERING
        await self._save(state)
        await self._progress(
            on_progress, PipelineStage.VIDEO_RENDERING, 0.60,
            "Rendering video...",
        )

        t0 = time.monotonic()
        genre_config = await self._cache.get_genre_config(state.genre_id)
        script = state.script_output

        video_result = await self._visual.generate(
            audio_bundle=state.audio_bundle,
            asset_bundle=state.asset_bundle,
            genre_config=genre_config,
            job_id=state.job_id,
            title=script.title,
            description=script.description,
            hashtags=script.hashtags,
        )

        state.video_path = video_result.video_path
        state.stage_timings["video_render"] = round(
            time.monotonic() - t0, 2
        )
        await self._save(state)
        return state

    async def _run_upload(
        self, state: PipelineState, schedule: str,
        on_progress: ProgressCallback,
    ) -> PipelineState:
        """Run YouTube upload."""
        await self._progress(
            on_progress, PipelineStage.COMPLETE, 0.85,
            "Uploading to YouTube...",
        )

        t0 = time.monotonic()
        from backend.core.models import VideoResult
        video_result = VideoResult(
            job_id=state.job_id,
            video_path=state.video_path,
            title=state.script_output.title,
            description=state.script_output.description,
            hashtags=state.script_output.hashtags,
            genre_id=state.genre_id,
        )

        upload_result = await self._upload.upload(
            video_result, schedule=schedule,
        )
        state.stage_timings["upload"] = round(time.monotonic() - t0, 2)
        await self._save(state)
        return state

    # ─── Helpers ──────────────────────────────────────

    async def _save(self, state: PipelineState) -> None:
        """Persist state to SQLite."""
        state.updated_at = datetime.now(timezone.utc)
        await self._cache.save_pipeline_state(state)

    @staticmethod
    async def _progress(
        callback: ProgressCallback, stage: PipelineStage,
        pct: float, message: str,
    ) -> None:
        """Fire progress callback if provided."""
        if callback:
            await callback(stage, pct, message)
