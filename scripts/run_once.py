from __future__ import annotations

from src.pipeline.runner import run_once
from src.pipeline.uploader import upload_video
from src.utils.logger import get_logger

log = get_logger("run-once")


def main() -> None:
    log.info("🚀 Starting visual quiz pipeline")

    log.info("🎨 Rendering video...")
    video_path, meta_path = run_once()

    log.info("📹 Render complete")
    log.info("Video: %s", video_path.name)

    log.info("☁️ Uploading to YouTube...")
    metrics = upload_video(video_path, meta_path)

    if metrics["success"]:
        log.info("🎉 Pipeline completed successfully")
        log.info("YouTube Video ID: %s", metrics["video_id"])
    else:
        log.error("❌ Pipeline failed")
        log.error("Error: %s", metrics["error"])


if __name__ == "__main__":
    main()
