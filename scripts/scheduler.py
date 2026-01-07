from __future__ import annotations

import time
from datetime import timedelta

from src.pipeline.runner import run_once as render_once
from src.pipeline.uploader import upload_video
from src.config.settings import (
    UPLOAD_INTERVAL_HOURS,
    LAST_RUN_FILE,
    DRY_RUN,
)
from src.utils.time import utc_now
from src.utils.filesystem import read_timestamp, write_timestamp
from src.utils.logger import get_logger

log = get_logger("scheduler")


class UploadScheduler:
    def __init__(self) -> None:
        self.interval = timedelta(hours=UPLOAD_INTERVAL_HOURS)

    def should_run(self) -> bool:
        last_run = read_timestamp(LAST_RUN_FILE)
        if not last_run:
            return True
        return utc_now() - last_run >= self.interval

    def sleep_until_next_run(self) -> None:
        last_run = read_timestamp(LAST_RUN_FILE)
        if not last_run:
            return

        next_run = last_run + self.interval

        while True:
            remaining = int((next_run - utc_now()).total_seconds())
            if remaining <= 0:
                return

            hours = remaining // 3600
            minutes = (remaining % 3600) // 60

            if remaining > 3600:
                log.info("⏳ Next upload in %dh %dm", hours, minutes)
                time.sleep(3600)
            elif remaining > 600:
                log.info("⚠️ Final hour: %dm remaining", minutes)
                time.sleep(600)
            else:
                log.info("🚨 Final countdown: %dm remaining", minutes)
                time.sleep(60)

    def run_forever(self) -> None:
        log.info("🟢 Scheduler started")
        log.info("⏱ Upload interval: %d hour(s)", UPLOAD_INTERVAL_HOURS)
        log.info("🧪 DRY_RUN = %s", DRY_RUN)

        while True:
            try:
                if self.should_run():
                    log.info("🚀 Rendering video")
                    video_path, meta_path = render_once()

                    if DRY_RUN:
                        log.warning("🧪 DRY_RUN enabled — skipping upload")
                    else:
                        log.info("☁️ Uploading to YouTube")
                        metrics = upload_video(video_path, meta_path)

                        if not metrics["success"]:
                            raise RuntimeError(metrics["error"])

                    write_timestamp(LAST_RUN_FILE, utc_now())

                    log.info("✅ Pipeline completed")
                    log.info("🎬 Video: %s", video_path.name)

                else:
                    self.sleep_until_next_run()

            except KeyboardInterrupt:
                log.warning("🛑 Scheduler stopped by user")
                break

            except Exception:
                log.exception("🔥 Scheduler error — retrying in 5 minutes")
                time.sleep(300)


def main() -> None:
    UploadScheduler().run_forever()


if __name__ == "__main__":
    main()
