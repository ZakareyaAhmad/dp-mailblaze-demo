from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import requests
from src.common.config import AppConfig
from src.common.logging import log, log_exc
from src.common.s3 import S3Client
from src.common.state import StateStore


def dt_partition(now: datetime) -> str:
    return now.astimezone(UTC).strftime("%Y-%m-%d")


def iso_z(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_paginated(
    base_url: str,
    path: str,
    params: dict[str, Any],
    api_key: str,
    limit: int,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    cursor: str | None = None

    while True:
        p = dict(params)
        p["limit"] = limit
        if cursor:
            p["cursor"] = cursor

        resp = requests.get(
            f"{base_url}{path}",
            params=p,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()

        data = payload.get("data", [])
        out.extend(data)
        cursor = payload.get("next_cursor")
        if not cursor:
            break

    return out


def main() -> None:
    cfg = AppConfig.load()
    run_id = uuid.uuid4().hex
    now = datetime.now(UTC)
    dt = dt_partition(now)

    s3 = S3Client(bucket=cfg.s3_raw_bucket, region=cfg.aws_region)
    state = StateStore(s3=s3, env=cfg.env)

    state_name = "saas_mailblaze_watermarks"
    current_state = state.get(state_name) or {}

    lookback = timedelta(minutes=10)

    campaigns_since = current_state.get("campaigns_updated_after") or "2026-02-01T00:00:00Z"
    events_since = current_state.get("email_events_occurred_after") or "2026-02-01T00:00:00Z"

    def _apply_lookback(ts: str) -> str:
        dt_ = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return iso_z(dt_.astimezone(UTC) - lookback)

    campaigns_since_eff = _apply_lookback(campaigns_since)
    events_since_eff = _apply_lookback(events_since)

    log("saas_start", base_url=cfg.mailblaze_base_url, run_id=run_id, dt=dt)

    try:
        campaigns = fetch_paginated(
            base_url=cfg.mailblaze_base_url,
            path="/v1/campaigns",
            params={"updated_after": campaigns_since_eff},
            api_key=cfg.mailblaze_api_key,
            limit=200,
        )
        log("saas_campaigns_fetched", rows=len(campaigns), updated_after=campaigns_since_eff)

        email_events = fetch_paginated(
            base_url=cfg.mailblaze_base_url,
            path="/v1/email_events",
            params={"occurred_after": events_since_eff},
            api_key=cfg.mailblaze_api_key,
            limit=500,
        )
        log("saas_email_events_fetched", rows=len(email_events), occurred_after=events_since_eff)

        def to_jsonl(objs: list[dict[str, Any]]) -> bytes:
            return b"".join(
                (json.dumps(o, ensure_ascii=False) + "\n").encode("utf-8") for o in objs
            )

        c_data_key = f"env={cfg.env}/raw/source=saas_mailblaze/entity=campaigns/dt={dt}/run_id={run_id}.jsonl"
        c_manifest_key = f"env={cfg.env}/raw/_manifests/source=saas_mailblaze/entity=campaigns/dt={dt}/run_id={run_id}.json"
        s3.put_idempotent(c_data_key, to_jsonl(campaigns), "application/json", c_manifest_key)

        e_data_key = f"env={cfg.env}/raw/source=saas_mailblaze/entity=email_events/dt={dt}/run_id={run_id}.jsonl"
        e_manifest_key = f"env={cfg.env}/raw/_manifests/source=saas_mailblaze/entity=email_events/dt={dt}/run_id={run_id}.json"
        s3.put_idempotent(e_data_key, to_jsonl(email_events), "application/json", e_manifest_key)

        new_state = dict(current_state)

        if campaigns:
            max_updated = max(c["updated_at"] for c in campaigns if c.get("updated_at"))
            new_state["campaigns_updated_after"] = max_updated

        if email_events:
            max_occ = max(e["occurred_at"] for e in email_events if e.get("occurred_at"))
            new_state["email_events_occurred_after"] = max_occ

        state.put(state_name, new_state)
        log("saas_done", run_id=run_id, new_state=new_state)

    except Exception as e:
        log_exc("saas_failed", e, run_id=run_id)
        raise


if __name__ == "__main__":
    main()
