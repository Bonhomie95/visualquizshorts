from __future__ import annotations

from pathlib import Path
from typing import Set

from ..puzzle.loader import select_next_puzzle, Puzzle
from ..media.wiki import fetch_images_for_items
from ..video.renderer import RenderJob, render_job_to_mp4
from ..config.settings import OUTPUT_DIR


# =========================================================
# STATE
# =========================================================

USED_FILE = OUTPUT_DIR / "used_puzzles.txt"


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
    used: Set[str] = load_used_ids()

    puzzle: Puzzle = select_next_puzzle(used)

    puzzle_id: str = puzzle["id"]
    hook: str = puzzle["prompt"]
    instruction: str = puzzle["rule"]
    items: list[str] = puzzle["items"]

    images = fetch_images_for_items(items)

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

    return video_path, meta_path


# =========================================================
# CLI
# =========================================================

if __name__ == "__main__":
    video, meta = run_once()
    print("✅ Video created:", video)
    print("📝 Metadata:", meta)
