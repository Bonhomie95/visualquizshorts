from pathlib import Path
from datetime import datetime, timezone

def read_timestamp(path: Path) -> datetime | None:
    if not path.exists():
        return None
    try:
        return datetime.fromisoformat(path.read_text().strip())
    except Exception:
        return None


def write_timestamp(path: Path, dt: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dt.isoformat())
