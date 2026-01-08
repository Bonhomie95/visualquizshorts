from __future__ import annotations

import hashlib
import io
import re
import time
from pathlib import Path
from typing import Optional

import requests
from PIL import Image, UnidentifiedImageError

from ..config.settings import (
    WIKI_LANG,
    WIKI_CACHE_DIR,
    WIKI_IMAGE_MIN_WIDTH,
    WIKI_IMAGE_MIN_HEIGHT,
)
from ..utils.logger import get_logger


log = get_logger("wiki")

# =========================================================
# CONSTANTS
# =========================================================

WIKI_API = "https://{lang}.wikipedia.org/w/api.php"
HEADERS = {
    "User-Agent": "VisualQuizShortsBot/1.0 (educational use; contact admin@example.com)"
}

RATE_LIMIT_SLEEP = 30  # seconds


# =========================================================
# HELPERS
# =========================================================


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text


def _cache_path(query: str) -> Path:
    slug = _slugify(query)
    h = hashlib.sha1(query.encode("utf-8")).hexdigest()[:8]
    return WIKI_CACHE_DIR / f"{slug}_{h}.jpg"


def _valid_image(img: Image.Image) -> bool:
    w, h = img.size
    return w >= WIKI_IMAGE_MIN_WIDTH and h >= WIKI_IMAGE_MIN_HEIGHT


def _upscale(img: Image.Image) -> Image.Image:
    w, h = img.size
    scale = max(
        WIKI_IMAGE_MIN_WIDTH / w,
        WIKI_IMAGE_MIN_HEIGHT / h,
    )
    new_size = (int(w * scale), int(h * scale))
    log.warning("Upscaling image from %sx%s → %sx%s", w, h, *new_size)
    return img.resize(new_size, Image.LANCZOS)


def _save_cache(path: Path, img: Image.Image) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path, format="JPEG", quality=92)
    except Exception:
        pass


def _download_image(url: str) -> Image.Image:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)

        if resp.status_code == 429:
            log.error(
                "Wikimedia rate-limited (429). Cooling down %ss", RATE_LIMIT_SLEEP
            )
            time.sleep(RATE_LIMIT_SLEEP)
            raise RuntimeError("Rate limited by Wikimedia")

        resp.raise_for_status()

        try:
            return Image.open(io.BytesIO(resp.content)).convert("RGB")
        except UnidentifiedImageError:
            raise RuntimeError("Downloaded file is not a valid image")

    except requests.RequestException as e:
        raise RuntimeError(str(e)) from e


# =========================================================
# CORE
# =========================================================


def fetch_wikipedia_image(query: str, *, force_refresh: bool = False) -> Image.Image:
    cache_file = _cache_path(query)

    # -----------------------------------------------------
    # CACHE
    # -----------------------------------------------------
    if cache_file.exists() and not force_refresh:
        try:
            img = Image.open(cache_file).convert("RGB")
            if _valid_image(img):
                return img
        except Exception:
            cache_file.unlink(missing_ok=True)

    api_url = WIKI_API.format(lang=WIKI_LANG)

    # -----------------------------------------------------
    # ORIGINAL IMAGE
    # -----------------------------------------------------
    try:
        params = {
            "action": "query",
            "format": "json",
            "prop": "pageimages",
            "piprop": "original",
            "titles": query,
            "redirects": 1,
        }

        resp = requests.get(api_url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        pages = resp.json().get("query", {}).get("pages", {})

        for page in pages.values():
            original = page.get("original")
            if original and "source" in original:
                img = _download_image(original["source"])
                if not _valid_image(img):
                    img = _upscale(img)

                _save_cache(cache_file, img)
                return img

    except Exception as e:
        log.warning("Original image failed for '%s': %s", query, e)

    # -----------------------------------------------------
    # FALLBACK: THUMBNAIL
    # -----------------------------------------------------
    try:
        log.warning("Original image missing for '%s', trying thumbnail", query)

        params["piprop"] = "thumbnail"
        params["pithumbsize"] = max(
            WIKI_IMAGE_MIN_WIDTH,
            WIKI_IMAGE_MIN_HEIGHT,
        )

        resp = requests.get(api_url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        pages = resp.json().get("query", {}).get("pages", {})

        for page in pages.values():
            thumb = page.get("thumbnail")
            if thumb and "source" in thumb:
                img = _download_image(thumb["source"])
                if not _valid_image(img):
                    img = _upscale(img)

                _save_cache(cache_file, img)
                return img

    except Exception as e:
        log.warning("Thumbnail image failed for '%s': %s", query, e)

    # -----------------------------------------------------
    # FINAL FAILURE
    # -----------------------------------------------------
    raise RuntimeError(f"No usable image found for '{query}'")


# =========================================================
# BATCH
# =========================================================


def fetch_images_for_items(items: list[str]) -> list[Image.Image]:
    images: list[Image.Image] = []

    for item in items:
        try:
            img = fetch_wikipedia_image(item)
            images.append(img)
        except Exception as e:
            log.error("Failed to fetch image for '%s': %s", item, e)
            raise

    return images
