"""
CLI runner — test the full pipeline end-to-end from command line.

Usage:
    python -m backend.pipeline.cli --genre scary_stories
    python -m backend.pipeline.cli --genre scary_stories --schedule next_best
    python -m backend.pipeline.cli --genre scary_stories --mode custom --topic "A haunted lighthouse"
"""
import argparse
import asyncio
import sys

from backend.core.cache_manager import CacheManager
from backend.core.config import config
from backend.core.logger import get_logger
from backend.core.models import PipelineStage
from backend.pipeline.orchestrator import Orchestrator

# Import agents
from backend.agents.script_agent import ScriptAgent
from backend.agents.asset_agent import AssetAgent
from backend.agents.audio_agent import AudioAgent
from backend.agents.visual_agent import VisualAgent
from backend.agents.upload_agent import UploadAgent

# Import services for DI
from backend.services.gemini_service import GeminiService
from backend.services.groq_service import GroqService
from backend.services.tts_service import TTSService
from backend.services.youtube_service import YouTubeService

logger = get_logger(__name__)


async def print_progress(
    stage: PipelineStage, pct: float, message: str,
) -> None:
    """Print progress to console."""
    bar = "█" * int(pct * 30) + "░" * (30 - int(pct * 30))
    print(f"\r  [{bar}] {pct:.0%} — {message}", end="", flush=True)
    if pct >= 1.0:
        print()  # Newline at 100%


async def run(args: argparse.Namespace) -> None:
    """Wire up all services and run the pipeline."""
    print(f"\n🎬 YT Shorts Pipeline — genre={args.genre}\n")

    # Initialize cache
    cache = CacheManager()
    await cache.initialize()

    # Wire services (DI pattern)
    gemini = GeminiService()
    groq = GroqService()
    tts = TTSService()

    # Create agents
    script_agent = ScriptAgent(
        gemini_service=gemini,
        groq_service=groq,
        cache=cache,
    )
    asset_agent = AssetAgent()
    audio_agent = AudioAgent(tts_service=tts)
    visual_agent = VisualAgent()
    upload_agent = UploadAgent(
        youtube_service=YouTubeService(),
    )

    # Create orchestrator
    orch = Orchestrator(
        script_agent=script_agent,
        asset_agent=asset_agent,
        audio_agent=audio_agent,
        visual_agent=visual_agent,
        upload_agent=upload_agent,
        cache=cache,
    )

    # Run pipeline
    try:
        state = await orch.generate(
            genre_id=args.genre,
            mode=args.mode,
            custom_topic=args.topic or "",
            schedule=args.schedule,
            on_progress=print_progress,
        )
        print(f"\n✅ Pipeline complete!")
        print(f"   Job ID:       {state.job_id}")
        print(f"   Video:        {state.video_path}")
        print(f"   Stage timings: {state.stage_timings}")
        print(f"   Word count:   {state.script_output.word_count}")
    except Exception as exc:
        print(f"\n❌ Pipeline failed: {exc}")
        sys.exit(1)
    finally:
        await cache.close()


def main():
    """Parse args and run."""
    parser = argparse.ArgumentParser(
        description="Run the YT Shorts generation pipeline",
    )
    parser.add_argument(
        "--genre", required=True,
        help="Genre ID (e.g. scary_stories)",
    )
    parser.add_argument(
        "--mode", default="auto", choices=["auto", "custom"],
        help="Generation mode",
    )
    parser.add_argument(
        "--topic", default="",
        help="Custom topic (required when mode=custom)",
    )
    parser.add_argument(
        "--schedule", default="now",
        help="Upload schedule: now | next_best | ISO datetime",
    )

    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
