from __future__ import annotations

import json
import random
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image

from .compositor import QuizCompositor
from .ffmpeg import frames_to_mp4
from ..config.settings import (
    ASSETS_DIR,
    VIDEO_OUTPUT_DIR,
    META_OUTPUT_DIR,
    CACHE_DIR,
    TIMER_SECONDS,
    FPS,
)
from ..utils.logger import get_logger

log = get_logger("renderer")


# =========================================================
# DATA MODEL
# =========================================================


@dataclass
class RenderJob:
    puzzle_id: str
    hook: str
    instruction: str
    items: list[str]
    images: list[Image.Image]
    duration_seconds: int = 20
    title: str = "Can you answer it? #shorts"
    description: str = ""
    tags: Optional[list[str]] = None


# =========================================================
# ASSET PICKERS
# =========================================================


def _list_files(dir_path: Path, exts: tuple[str, ...]) -> list[Path]:
    if not dir_path.exists():
        return []
    return [p for p in dir_path.rglob("*") if p.is_file() and p.suffix.lower() in exts]


def pick_background() -> Image.Image:
    bg_dir = ASSETS_DIR / "backgrounds"
    candidates = _list_files(bg_dir, (".jpg", ".jpeg", ".png", ".webp"))

    if not candidates:
        log.warning("No background images found, using fallback color")
        return Image.new("RGB", (1080, 1920), (10, 10, 14))

    chosen = random.choice(candidates)
    log.info("Background selected: %s", chosen.name)
    return Image.open(chosen).convert("RGB")


def pick_music() -> Optional[Path]:
    music_dir = ASSETS_DIR / "music"
    candidates = _list_files(music_dir, (".mp3", ".wav", ".m4a", ".aac"))

    if not candidates:
        log.info("No background music found")
        return None

    chosen = random.choice(candidates)
    log.info("Music selected: %s", chosen.name)
    return chosen


# =========================================================
# METADATA
# =========================================================


def _now_stamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def build_default_description(job: RenderJob) -> str:
    return "\n".join(
        [
            "Comment your answers (4 words).",
            "",
            "🎁 Monthly Surprise:",
            "Subscribers with the highest correct answers this month get a surprise gift!",
            "",
            "#quiz #brainteaser #shorts",
            "",
            f"(Puzzle: {job.puzzle_id})",
        ]
    )


def save_metadata(meta_path: Path, job: RenderJob) -> None:
    meta = {
        "puzzle_id": job.puzzle_id,
        "hook": job.hook,
        "instruction": job.instruction,
        "items": job.items,
        "timer_seconds": TIMER_SECONDS,
        "fps": FPS,
        "title": job.title,
        "description": job.description,
        "tags": job.tags or [],
    }

    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log.info("Metadata saved: %s", meta_path.name)


# =========================================================
# RENDER (STREAMING TO DISK)
# =========================================================


def render_job_to_mp4(job: RenderJob) -> tuple[Path, Path]:
    """
    Render video + metadata with detailed logging.

    IMPORTANT:
    - Renders frames directly to disk (RAM-safe for low-memory VPS)
    - FFmpeg reads frames from disk
    """
    start_time = time.time()

    log.info("========================================")
    log.info("Starting render for puzzle: %s", job.puzzle_id)

    if len(job.images) != 4:
        raise ValueError("RenderJob.images must contain exactly 4 images")

    if not job.description.strip():
        job.description = build_default_description(job)

    bg = pick_background()
    music = pick_music()

    # -------------------------------------
    # COMPOSITOR INIT
    # -------------------------------------
    log.info("Initializing compositor")
    comp = QuizCompositor(
        hook_text=job.hook,
        instruction_text=job.instruction,
        images=job.images,
        duration_seconds=job.duration_seconds,
        background=bg,
    )

    total_frames = comp.total_frames
    log.info(
        "Rendering %d frames (%ds @ %dfps)",
        total_frames,
        job.duration_seconds,
        FPS,
    )

    # -------------------------------------
    # OUTPUT PATHS
    # -------------------------------------
    stamp = _now_stamp()
    safe_id = "".join(c for c in job.puzzle_id if c.isalnum() or c in ("-", "_"))
    base_name = f"{stamp}_{safe_id}"

    out_video = VIDEO_OUTPUT_DIR / f"{base_name}.mp4"
    out_meta = META_OUTPUT_DIR / f"{base_name}.json"

    # temp dirs
    temp_dir = CACHE_DIR / "tmp" / base_name
    frames_dir = temp_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    log.info("Temporary render directory: %s", temp_dir)
    log.info("Writing frames to: %s", frames_dir)

    # -------------------------------------
    # FRAME RENDERING → DISK (RAM SAFE)
    # -------------------------------------
    last_log_pct = -1
    tick = time.time()

    # choose logging granularity
    # - keep it clean: log each 10% + periodic ETA
    for i in range(total_frames):
        t = i / FPS
        frame = comp._render_frame(t)

        # save immediately (do NOT store in list)
        frame_path = frames_dir / f"frame_{i:05d}.png"
        frame.save(frame_path, "PNG")

        # progress logging every 10%
        pct = int((i + 1) * 100 / total_frames)
        if pct % 10 == 0 and pct != last_log_pct:
            elapsed = max(0.001, time.time() - start_time)
            fps_eff = (i + 1) / elapsed
            remaining_frames = total_frames - (i + 1)
            eta_sec = int(remaining_frames / max(0.1, fps_eff))

            log.info(
                "Frame render progress: %d%% (%d/%d) | %.2f fps | ETA ~%ds",
                pct,
                i + 1,
                total_frames,
                fps_eff,
                eta_sec,
            )
            last_log_pct = pct

        # small heartbeat every ~5 seconds (helps when 10% steps are slow)
        if time.time() - tick >= 5:
            log.info("Rendering... frame %d/%d", i + 1, total_frames)
            tick = time.time()

    log.info("Frame rendering completed")

    # -------------------------------------
    # FFMPEG ENCODE (READ FRAMES FROM DISK)
    # -------------------------------------
    log.info("Starting FFmpeg encoding")
    frames_to_mp4(
        frames_dir=frames_dir,
        out_mp4=out_video,
        fps=FPS,
        music_file=music,
        crf=20,
        preset="medium",
    )
    log.info("FFmpeg encoding completed")

    # -------------------------------------
    # METADATA + CLEANUP
    # -------------------------------------
    save_metadata(out_meta, job)

    log.info("Cleaning up temporary frames")
    shutil.rmtree(temp_dir, ignore_errors=True)
    log.info("Temporary directory removed")

    elapsed = round(time.time() - start_time, 2)
    log.info("Render finished in %ss", elapsed)
    log.info("Video output: %s", out_video.name)
    log.info("========================================")

    return out_video, out_meta
