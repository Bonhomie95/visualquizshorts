from __future__ import annotations

import subprocess
import shutil
from pathlib import Path
from typing import Optional

from ..config.settings import (
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    ENABLE_BACKGROUND_MUSIC,
    MUSIC_VOLUME,
)
from ..utils.logger import get_logger

log = get_logger("ffmpeg")


# =========================================================
# CORE RUNNER
# =========================================================

def _run(cmd: list[str]) -> None:
    log.debug("FFmpeg cmd: %s", " ".join(cmd))
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "FFmpeg failed:\n"
            f"CMD: {' '.join(cmd)}\n\n"
            f"STDERR:\n{proc.stderr.strip()}"
        )


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# =========================================================
# FRAMES → VIDEO
# =========================================================

def encode_video_from_frames(
    frames_dir: Path,
    out_mp4: Path,
    *,
    fps: int,
    crf: int = 20,
    preset: str = "medium",
) -> None:
    """
    Encode PNG frame sequence → MP4 (H.264, Shorts-friendly)

    Expects:
      frames_dir/frame_00000.png
    """
    _ensure_dir(out_mp4.parent)

    log.info("Encoding frames → video (%s)", out_mp4.name)

    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-stats",
        "-framerate",
        str(fps),
        "-i",
        str(frames_dir / "frame_%05d.png"),
        "-vf",
        (
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
            "format=yuv420p"
        ),
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out_mp4),
    ]

    _run(cmd)
    log.info("Video encoding completed")


# =========================================================
# AUDIO MIX
# =========================================================

def mux_music(
    in_mp4: Path,
    music_file: Path,
    out_mp4: Path,
    *,
    music_volume: float = MUSIC_VOLUME,
) -> None:
    """
    Add or mix background music safely.
    Falls back to music-only if input video has no audio.
    """
    _ensure_dir(out_mp4.parent)

    log.info("Adding background music: %s", music_file.name)

    # Attempt mix (video audio + music)
    mix_cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(in_mp4),
        "-i",
        str(music_file),
        "-filter_complex",
        (
            f"[1:a]volume={music_volume}[bg];"
            "[0:a][bg]amix=inputs=2:duration=shortest[aout]"
        ),
        "-map",
        "0:v:0",
        "-map",
        "[aout]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(out_mp4),
    ]

    try:
        _run(mix_cmd)
        log.info("Music mixed with existing audio")
        return
    except RuntimeError:
        log.warning("No audio stream detected, using music only")

    # Fallback: music only
    fallback_cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(in_mp4),
        "-i",
        str(music_file),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(out_mp4),
    ]

    _run(fallback_cmd)
    log.info("Music added as sole audio track")


# =========================================================
# ONE-SHOT PIPELINE (DISK-BASED)
# =========================================================

def frames_to_mp4(
    *,
    frames_dir: Path,
    out_mp4: Path,
    fps: int,
    music_file: Optional[Path] = None,
    crf: int = 20,
    preset: str = "medium",
) -> Path:
    """
    Full pipeline (RAM-safe):

      frames on disk → mp4 → (optional) mp4 + music
    """
    temp_video = out_mp4.with_suffix(".nomusic.mp4")

    encode_video_from_frames(
        frames_dir=frames_dir,
        out_mp4=temp_video,
        fps=fps,
        crf=crf,
        preset=preset,
    )

    if ENABLE_BACKGROUND_MUSIC and music_file:
        mux_music(temp_video, music_file, out_mp4)
        temp_video.unlink(missing_ok=True)
    else:
        shutil.move(temp_video, out_mp4)

    return out_mp4
