from __future__ import annotations

import glob
import os
from pathlib import Path

from src.common.config import AppConfig
from src.common.logging import log, log_exc
from src.common.s3 import S3Client


def parse_dt_from_filename(path: str) -> str:
    # inventory_snapshot_YYYY-MM-DD.csv
    base = os.path.basename(path)
    parts = base.replace(".csv", "").split("_")
    if len(parts) < 3:
        raise ValueError(f"Unexpected inventory filename: {base}")
    return parts[-1]


def main() -> None:
    cfg = AppConfig.load()
    s3 = S3Client(bucket=cfg.s3_raw_bucket, region=cfg.aws_region)

    input_dir = os.getenv("INVENTORY_INPUT_DIR", "/data/inventory")
    files = sorted(glob.glob(os.path.join(input_dir, "inventory_snapshot_*.csv")))

    if not files:
        log("inventory_no_files", input_dir=input_dir)
        return

    try:
        for fp in files:
            dt = parse_dt_from_filename(fp)
            data = Path(fp).read_bytes()

            data_key = f"env={cfg.env}/raw/source=3pl_inventory/dt={dt}/inventory_snapshot.csv"
            manifest_key = (
                f"env={cfg.env}/raw/_manifests/source=3pl_inventory/dt={dt}/inventory_snapshot.json"
            )
            uploaded = s3.put_idempotent(
                data_key=data_key, data=data, content_type="text/csv", manifest_key=manifest_key
            )
            log("inventory_uploaded", file=fp, dt=dt, uploaded=uploaded, data_key=data_key)

    except Exception as e:
        log_exc("inventory_failed", e)
        raise


if __name__ == "__main__":
    main()
