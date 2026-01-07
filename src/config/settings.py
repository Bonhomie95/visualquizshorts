from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

# =========================================================
# PROJECT ROOT
# =========================================================

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]

# =========================================================
# LOAD ENV
# =========================================================

load_dotenv(PROJECT_ROOT / ".env")

# =========================================================
# ENV HELPERS (single source of truth)
# =========================================================


def env_str(key: str, default: str | None = None) -> str:
    val = os.getenv(key, default)
    if val is None:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return val


def env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except ValueError:
        raise RuntimeError(f"Environment variable {key} must be an integer")


def env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, default))
    except ValueError:
        raise RuntimeError(f"Environment variable {key} must be a float")


def env_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).lower() in ("1", "true", "yes", "on")


# =========================================================
# APP
# =========================================================

APP_NAME: Final[str] = env_str("APP_NAME", "VisualQuizShorts")
ENV: Final[str] = env_str("ENV", "development")

# =========================================================
# PATHS
# =========================================================

ASSETS_DIR: Final[Path] = PROJECT_ROOT / env_str("ASSETS_DIR", "assets")
DATA_DIR: Final[Path] = PROJECT_ROOT / env_str("DATA_DIR", "data")
CACHE_DIR: Final[Path] = PROJECT_ROOT / env_str("CACHE_DIR", "cache")
OUTPUT_DIR: Final[Path] = PROJECT_ROOT / env_str("OUTPUT_DIR", "output")

WIKI_CACHE_DIR: Final[Path] = CACHE_DIR / "wiki_images"
FRAME_CACHE_DIR: Final[Path] = CACHE_DIR / "rendered_frames"

VIDEO_OUTPUT_DIR: Final[Path] = OUTPUT_DIR / "videos"
META_OUTPUT_DIR: Final[Path] = OUTPUT_DIR / "meta"

STATE_DIR: Final[Path] = PROJECT_ROOT / "state"
LAST_RUN_FILE: Final[Path] = STATE_DIR / "last_run.txt"

# =========================================================
# VIDEO
# =========================================================

VIDEO_WIDTH: Final[int] = env_int("VIDEO_WIDTH", 1080)
VIDEO_HEIGHT: Final[int] = env_int("VIDEO_HEIGHT", 1920)
FPS: Final[int] = env_int("FPS", 30)

TIMER_SECONDS: Final[int] = env_int("TIMER_SECONDS", 15)

ENTRY_ANIMATION_DURATION: Final[float] = env_float("ENTRY_ANIMATION_DURATION", 0.5)
IMAGE_STAGGER_DELAY: Final[float] = env_float("IMAGE_STAGGER_DELAY", 0.2)

# =========================================================
# FONTS
# =========================================================

FONT_PRIMARY: Final[Path] = PROJECT_ROOT / env_str(
    "FONT_PRIMARY", "assets/fonts/Inter-Bold.ttf"
)
FONT_SECONDARY: Final[Path] = PROJECT_ROOT / env_str(
    "FONT_SECONDARY", "assets/fonts/Inter-Regular.ttf"
)

# =========================================================
# MODES
# =========================================================

DRY_RUN: Final[bool] = env_bool("DRY_RUN", False)

# =========================================================
# SCHEDULER
# =========================================================

UPLOAD_INTERVAL_HOURS: Final[int] = env_int("UPLOAD_INTERVAL_HOURS", 24)

# =========================================================
# WIKIPEDIA
# =========================================================

WIKI_LANG: Final[str] = env_str("WIKI_LANG", "en")
WIKI_IMAGE_MIN_WIDTH: Final[int] = env_int("WIKI_IMAGE_MIN_WIDTH", 600)
WIKI_IMAGE_MIN_HEIGHT: Final[int] = env_int("WIKI_IMAGE_MIN_HEIGHT", 600)

# =========================================================
# AUDIO
# =========================================================

ENABLE_BACKGROUND_MUSIC: Final[bool] = env_bool("ENABLE_BACKGROUND_MUSIC", True)
MUSIC_VOLUME: Final[float] = env_float("MUSIC_VOLUME", 0.15)

# =========================================================
# YOUTUBE (optional in DRY_RUN)
# =========================================================

YOUTUBE_CLIENT_ID: Final[str | None] = os.getenv("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET: Final[str | None] = os.getenv("YOUTUBE_CLIENT_SECRET")
YOUTUBE_REFRESH_TOKEN: Final[str | None] = os.getenv("YOUTUBE_REFRESH_TOKEN")
YOUTUBE_CHANNEL_ID: Final[str | None] = os.getenv("YOUTUBE_CHANNEL_ID")

# =========================================================
# LOGGING
# =========================================================

LOG_LEVEL: Final[str] = env_str("LOG_LEVEL", "INFO")

# =========================================================
# BOOTSTRAP
# =========================================================


def ensure_directories() -> None:
    for p in (
        ASSETS_DIR,
        DATA_DIR,
        CACHE_DIR,
        WIKI_CACHE_DIR,
        FRAME_CACHE_DIR,
        OUTPUT_DIR,
        VIDEO_OUTPUT_DIR,
        META_OUTPUT_DIR,
        STATE_DIR,
    ):
        p.mkdir(parents=True, exist_ok=True)


def validate_assets() -> None:
    if not FONT_PRIMARY.exists():
        raise RuntimeError(f"Primary font not found: {FONT_PRIMARY}")
    if not FONT_SECONDARY.exists():
        raise RuntimeError(f"Secondary font not found: {FONT_SECONDARY}")


def bootstrap() -> None:
    ensure_directories()
    validate_assets()


# Intentional auto-bootstrap
bootstrap()
