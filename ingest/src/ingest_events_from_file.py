from __future__ import annotations

import glob
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from src.common.config import AppConfig
from src.common.logging import log, log_exc
from src.common.s3 import S3Client


def dt_partition(now: datetime) -> str:
    return now.astimezone(UTC).strftime("%Y-%m-%d")


def guess_dt_from_filename(fp: str) -> str:
    # events_2026-02-18T090000Z.jsonl -> 2026-02-18
    base = os.path.basename(fp)
    if base.startswith("events_") and "T" in base:
        try:
            return base.split("_", 1)[1].split("T", 1)[0]
        except Exception:
            pass
    return dt_partition(datetime.now(UTC))


def main() -> None:
    cfg = AppConfig.load()
    s3 = S3Client(bucket=cfg.s3_raw_bucket, region=cfg.aws_region)

    input_glob = os.getenv("EVENTS_INPUT_GLOB", "/data/events/*.jsonl")
    files = sorted(glob.glob(input_glob))

    if not files:
        log("events_no_files", input_glob=input_glob)
        return

    try:
        for fp in files:
            dt = guess_dt_from_filename(fp)
            run_id = uuid.uuid4().hex
            data = Path(fp).read_bytes()

            data_key = f"env={cfg.env}/raw/source=events/dt={dt}/run_id={run_id}.jsonl"
            manifest_key = (
                f"env={cfg.env}/raw/_manifests/source=events/dt={dt}/run_id={run_id}.json"
            )

            uploaded = s3.put_idempotent(
                data_key=data_key,
                data=data,
                content_type="application/x-ndjson",
                manifest_key=manifest_key,
            )
            log("events_uploaded", file=fp, dt=dt, uploaded=uploaded, data_key=data_key)

    except Exception as e:
        log_exc("events_failed", e)
        raise


if __name__ == "__main__":
    main()
