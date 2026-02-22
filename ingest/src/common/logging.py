from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from typing import Any


def _ts() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(event: str, **fields: Any) -> None:
    rec: dict[str, Any] = {"ts": _ts(), "event": event}
    rec.update(fields)
    sys.stdout.write(json.dumps(rec, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def log_exc(event: str, exc: BaseException, **fields: Any) -> None:
    log(event, level="error", error_type=type(exc).__name__, error=str(exc), **fields)
