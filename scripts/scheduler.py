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


RENDER_RETRY_SECONDS = 5 * 60  # 5 minutes
UPLOAD_RETRY_SECONDS = 30 * 60  # 30 minutes


class UploadScheduler:
    def __init__(self) -> None:
        self.interval = timedelta(hours=UPLOAD_INTERVAL_HOURS)

    # =====================================================
    # SHOULD WE RUN?
    # =====================================================

    def should_run(self) -> bool:
        last_run = read_timestamp(LAST_RUN_FILE)
        if not last_run:
            return True
        return utc_now() - last_run >= self.interval

    # =====================================================
    # COUNTDOWN / SLEEP
    # =====================================================

    def sleep_until_next_run(self) -> None:
        last_run = read_timestamp(LAST_RUN_FILE)

        if not last_run:
            log.info("⏳ No previous run found — waiting 60s")
            time.sleep(60)
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
                sleep_for = 3600
            elif remaining > 600:
                log.info("⚠️ Final hour: %dm remaining", minutes)
                sleep_for = 600
            else:
                log.info("🚨 Final countdown: %dm remaining", minutes)
                sleep_for = 60

            time.sleep(min(sleep_for, remaining))

    # =====================================================
    # MAIN LOOP
    # =====================================================

    def run_forever(self) -> None:
        log.info("🟢 Scheduler started")
        log.info("⏱ Upload interval: %d hour(s)", UPLOAD_INTERVAL_HOURS)
        log.info("🧪 DRY_RUN = %s", DRY_RUN)

        while True:
            try:
                if not self.should_run():
                    self.sleep_until_next_run()
                    continue

                # -------------------------------
                # RENDER
                # -------------------------------
                log.info("🎨 Rendering video")
                video_path, meta_path = render_once()
                log.info("🎬 Render complete: %s", video_path.name)

                # -------------------------------
                # UPLOAD
                # -------------------------------
                if DRY_RUN:
                    log.warning("🧪 DRY_RUN enabled — skipping upload")
                else:
                    log.info("☁️ Uploading to YouTube")
                    metrics = upload_video(video_path, meta_path)

                    if not metrics.get("success"):
                        raise RuntimeError(f"Upload failed: {metrics.get('error')}")

                # -------------------------------
                # SUCCESS → SAVE TIMESTAMP
                # -------------------------------
                write_timestamp(LAST_RUN_FILE, utc_now())
                log.info("✅ Pipeline completed successfully")

            except KeyboardInterrupt:
                log.warning("🛑 Scheduler stopped by user")
                break

            except RuntimeError as e:
                log.error("❌ Pipeline failure: %s", e)
                log.info("⏳ Retrying render in %d seconds", RENDER_RETRY_SECONDS)
                time.sleep(RENDER_RETRY_SECONDS)

            except Exception:
                log.exception("🔥 Unexpected scheduler error")
                log.info("⏳ Retrying in %d seconds", UPLOAD_RETRY_SECONDS)
                time.sleep(UPLOAD_RETRY_SECONDS)


def main() -> None:
    UploadScheduler().run_forever()


if __name__ == "__main__":
    main()
