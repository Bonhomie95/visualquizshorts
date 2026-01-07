from __future__ import annotations

import time
from datetime import timedelta

from src.pipeline.runner import run_once
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

    # =====================================================
    # CHECK IF WE SHOULD RUN
    # =====================================================

    def should_run(self) -> bool:
        last_run = read_timestamp(LAST_RUN_FILE)
        if not last_run:
            return True
        return utc_now() - last_run >= self.interval

    # =====================================================
    # COUNTDOWN SLEEP
    # =====================================================

    def sleep_until_next_run(self) -> None:
        last_run = read_timestamp(LAST_RUN_FILE)
        if not last_run:
            return

        next_run = last_run + self.interval

        while True:
            now = utc_now()
            remaining = int((next_run - now).total_seconds())

            if remaining <= 0:
                return

            hours = remaining // 3600
            minutes = (remaining % 3600) // 60

            if remaining > 3600:
                log.info(f"⏳ Next upload in {hours}h {minutes}m")
                sleep_for = 3600  # 1 hour
            elif remaining > 600:
                log.info(f"⚠️ Final hour: next upload in {minutes} minutes")
                sleep_for = 600  # 10 minutes
            else:
                log.info(f"🚨 Final countdown: {minutes} minute(s) left")
                sleep_for = 60  # 1 minute

            time.sleep(min(sleep_for, remaining))

    # =====================================================
    # MAIN LOOP
    # =====================================================

    def run_forever(self) -> None:
        log.info("🟢 Scheduler started")
        log.info(f"⏱ Upload interval: {UPLOAD_INTERVAL_HOURS} hour(s)")
        log.info(f"🧪 DRY_RUN = {DRY_RUN}")

        while True:
            try:
                if self.should_run():
                    log.info("🚀 Starting pipeline run")
                    video_path, meta_path = run_once()

                    write_timestamp(LAST_RUN_FILE, utc_now())

                    log.info("✅ Pipeline completed")
                    log.info(f"🎬 Video: {video_path}")
                else:
                    self.sleep_until_next_run()

            except KeyboardInterrupt:
                log.warning("🛑 Scheduler stopped by user")
                break

            except Exception:
                log.exception("🔥 Scheduler error — retrying in 5 minutes")
                time.sleep(300)


# =====================================================
# ENTRY POINT
# =====================================================


def main() -> None:
    UploadScheduler().run_forever()


if __name__ == "__main__":
    main()
