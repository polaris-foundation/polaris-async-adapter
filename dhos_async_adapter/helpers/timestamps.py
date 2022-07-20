from datetime import datetime, timezone


def generate_iso8601_timestamp() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds")
