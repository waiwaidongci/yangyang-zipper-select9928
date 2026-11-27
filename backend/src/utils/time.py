from datetime import datetime, timezone


def utc_stamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')
