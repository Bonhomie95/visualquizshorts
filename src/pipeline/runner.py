from __future__ import annotations

from pathlib import Path
from typing import Set

from ..puzzle.loader import select_next_puzzle, Puzzle
from ..media.wiki import fetch_images_for_items
from ..video.renderer import RenderJob, render_job_to_mp4
from ..config.settings import OUTPUT_DIR
from ..utils.logger import get_logger

log = get_logger("runner")

# =========================================================
# STATE
# =========================================================

USED_FILE = OUTPUT_DIR / "used_puzzles.txt"
MAX_PUZZLE_ATTEMPTS = 10  # safety guard to avoid infinite loops


def load_used_ids() -> Set[str]:
    if not USED_FILE.exists():
        return set()

    return {
        line.strip()
        for line in USED_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def mark_used(puzzle_id: str) -> None:
    USED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with USED_FILE.open("a", encoding="utf-8") as f:
        f.write(puzzle_id + "\n")


# =========================================================
# RUNNER
# =========================================================


def run_once() -> tuple[Path, Path]:
    """
    Runs the pipeline once:
    - Selects a puzzle
    - Fetches images
    - Renders video
    - Skips puzzles that fail
    """

    used: Set[str] = load_used_ids()
    last_error: Exception | None = None

    for attempt in range(1, MAX_PUZZLE_ATTEMPTS + 1):
        puzzle: Puzzle = select_next_puzzle(used)

        puzzle_id: str = puzzle["id"]
        hook: str = puzzle["prompt"]
        instruction: str = puzzle["rule"]
        items: list[str] = puzzle["items"]

        log.info(
            "🧩 Puzzle attempt %d/%d — %s",
            attempt,
            MAX_PUZZLE_ATTEMPTS,
            puzzle_id,
        )

        try:
            # -------------------------------------------------
            # IMAGE FETCH
            # -------------------------------------------------
            images = fetch_images_for_items(items)

            # -------------------------------------------------
            # RENDER
            # -------------------------------------------------
            job = RenderJob(
                puzzle_id=puzzle_id,
                hook=hook,
                instruction=instruction,
                items=items,
                images=images,
                duration_seconds=20,
                title="Can you answer it? 🤔 #shorts",
                tags=["quiz", "brainteaser", "shorts"],
            )

            video_path, meta_path = render_job_to_mp4(job)

            mark_used(puzzle_id)

            log.info("✅ Puzzle %s rendered successfully", puzzle_id)
            return video_path, meta_path

        except Exception as e:
            last_error = e
            log.warning(
                "⚠️ Skipping puzzle %s due to error: %s",
                puzzle_id,
                str(e),
            )

            # Mark as used so we never retry this bad puzzle
            mark_used(puzzle_id)
            used.add(puzzle_id)

    # -----------------------------------------------------
    # FAIL SAFE
    # -----------------------------------------------------
    raise RuntimeError(
        f"Failed to render a video after {MAX_PUZZLE_ATTEMPTS} puzzle attempts"
    ) from last_error


# =========================================================
# CLI
# =========================================================

if __name__ == "__main__":
    video, meta = run_once()
    print("✅ Video created:", video)
    print("📝 Metadata:", meta)
