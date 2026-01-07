from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from ..config.settings import (
    YOUTUBE_CLIENT_ID,
    YOUTUBE_CLIENT_SECRET,
    YOUTUBE_REFRESH_TOKEN,
)
from ..utils.logger import get_logger
from ..utils.time import utc_timestamp


log = get_logger("youtube-uploader")

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
DEFAULT_CATEGORY_ID = "22"  # People & Blogs


# =========================================================
# AUTH
# =========================================================


def get_youtube_client():
    log.info("Initializing YouTube client (refresh-token flow)")

    if not all(
        [
            YOUTUBE_CLIENT_ID,
            YOUTUBE_CLIENT_SECRET,
            YOUTUBE_REFRESH_TOKEN,
        ]
    ):
        raise RuntimeError("Missing YouTube OAuth credentials")

    creds = Credentials(
        token=None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )

    return build(
        YOUTUBE_API_SERVICE_NAME,
        YOUTUBE_API_VERSION,
        credentials=creds,
    )


# =========================================================
# METADATA
# =========================================================


def load_metadata(meta_path: Path) -> dict:
    if not meta_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {meta_path}")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def build_snippet(meta: dict) -> dict:
    title = meta.get("title", "").strip()
    description = meta.get("description", "").strip()
    tags = meta.get("tags", [])

    if "#shorts" not in title.lower():
        title = f"{title} #shorts"

    return {
        "title": title[:100],
        "description": description[:5000],
        "tags": tags,
        "categoryId": DEFAULT_CATEGORY_ID,
    }


# =========================================================
# UPLOAD
# =========================================================


def upload_video(
    video_path: Path,
    meta_path: Path,
    *,
    privacy_status: str = "public",
    retries: int = 3,
) -> Dict[str, object]:
    """
    Upload video with retry + metrics.
    Returns metrics dict.
    """
    start_ts = utc_timestamp()
    metrics = {
        "video_path": str(video_path),
        "start_ts": start_ts,
        "attempts": 0,
        "success": False,
        "video_id": None,
        "duration_sec": None,
        "error": None,
    }

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    file_size_mb = video_path.stat().st_size / (1024 * 1024)
    log.info("Preparing upload (%.2f MB): %s", file_size_mb, video_path.name)

    meta = load_metadata(meta_path)
    snippet = build_snippet(meta)

    youtube = get_youtube_client()

    body = {
        "snippet": snippet,
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=8 * 1024 * 1024,  # 8MB
    )

    for attempt in range(1, retries + 1):
        metrics["attempts"] = attempt
        log.info("Upload attempt %d/%d", attempt, retries)

        try:
            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    log.info(
                        "Upload progress: %5.1f%%",
                        status.progress() * 100,
                    )

            video_id = response["id"]
            end_ts = utc_timestamp()

            metrics.update(
                {
                    "success": True,
                    "video_id": video_id,
                    "duration_sec": end_ts - start_ts,
                }
            )

            log.info("Upload completed successfully")
            log.info("Video ID: %s", video_id)
            log.info("Total upload time: %ds", metrics["duration_sec"])

            return metrics

        except HttpError as e:
            log.error("YouTube API error on attempt %d: %s", attempt, e)
            metrics["error"] = str(e)

        except Exception as e:
            log.exception("Unexpected upload error")
            metrics["error"] = str(e)

        if attempt < retries:
            sleep_time = 5 * attempt
            log.info("Retrying in %ds...", sleep_time)
            time.sleep(sleep_time)

    metrics["duration_sec"] = utc_timestamp() - start_ts
    log.error("Upload failed after %d attempts", retries)
    return metrics


# =========================================================
# CLI
# =========================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: uploader.py <video.mp4> <meta.json>")
        sys.exit(1)

    video = Path(sys.argv[1])
    meta = Path(sys.argv[2])

    result = upload_video(video, meta)
    print(json.dumps(result, indent=2))
