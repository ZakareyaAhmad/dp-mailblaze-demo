from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
from src.common.config import AppConfig
from src.common.logging import log, log_exc
from src.common.s3 import S3Client
from src.common.state import StateStore

TABLES = [
    ("customers", "updated_at"),
    ("products", "updated_at"),
    ("orders", "updated_at"),
    ("order_items", None),  # no updated_at; extracted fully each run (small)
    ("payments", None),  # no updated_at; extracted fully each run (small)
]


def iso_z(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def dt_partition(now: datetime) -> str:
    return now.astimezone(UTC).strftime("%Y-%m-%d")


def fetch_rows(
    conn: psycopg.Connection, table: str, watermark_col: str | None, watermark: datetime | None
) -> list[dict[str, Any]]:
    cur = conn.cursor()
    if watermark_col and watermark:
        cur.execute(
            f"SELECT * FROM {table} WHERE {watermark_col} > %s ORDER BY {watermark_col} ASC",
            (watermark,),
        )
    else:
        cur.execute(f"SELECT * FROM {table}")
    cols = [c.name for c in cur.description]
    out: list[dict[str, Any]] = []
    for row in cur.fetchall():
        obj = {}
        for k, v in zip(cols, row, strict=False):
            if isinstance(v, datetime):
                obj[k] = iso_z(v)
            else:
                obj[k] = v
        out.append(obj)
    return out


def main() -> None:
    cfg = AppConfig.load()
    run_id = uuid.uuid4().hex
    now = datetime.now(UTC)
    dt = dt_partition(now)

    s3 = S3Client(bucket=cfg.s3_raw_bucket, region=cfg.aws_region)
    state = StateStore(s3=s3, env=cfg.env)

    state_name = "postgres_watermarks"
    current_state = state.get(state_name) or {}

    # 5-minute lookback to handle small clock skews / late updates
    lookback = timedelta(minutes=5)

    dsn = f"host={cfg.pg_host} port={cfg.pg_port} dbname={cfg.pg_db} user={cfg.pg_user} password={cfg.pg_password}"
    log("postgres_connect", host=cfg.pg_host, db=cfg.pg_db)

    try:
        with psycopg.connect(dsn) as conn:
            new_state: dict[str, Any] = dict(current_state)

            for table, wm_col in TABLES:
                wm_str = current_state.get(table)
                wm = datetime.fromisoformat(wm_str.replace("Z", "+00:00")) if wm_str else None
                effective_wm = (wm - lookback) if wm else None

                rows = fetch_rows(conn, table, wm_col, effective_wm)
                log("postgres_extract", table=table, rows=len(rows), watermark=wm_str)

                # Serialize as JSONL
                payload = b"".join(
                    (json.dumps(r, ensure_ascii=False) + "\n").encode("utf-8") for r in rows
                )

                data_key = (
                    f"env={cfg.env}/raw/source=postgres/table={table}/dt={dt}/run_id={run_id}.jsonl"
                )
                manifest_key = f"env={cfg.env}/raw/_manifests/source=postgres/table={table}/dt={dt}/run_id={run_id}.json"

                uploaded = s3.put_idempotent(
                    data_key=data_key,
                    data=payload,
                    content_type="application/json",
                    manifest_key=manifest_key,
                )

                # Update watermark if table is incremental and we uploaded rows
                if wm_col and rows:
                    max_ts = max(r[wm_col] for r in rows if wm_col in r and r[wm_col])
                    new_state[table] = max_ts

                log("postgres_upload_done", table=table, uploaded=uploaded, data_key=data_key)

            state.put(state_name, new_state)
            log("postgres_done", run_id=run_id, dt=dt)

    except Exception as e:
        log_exc("postgres_failed", e, run_id=run_id)
        raise


if __name__ == "__main__":
    main()
