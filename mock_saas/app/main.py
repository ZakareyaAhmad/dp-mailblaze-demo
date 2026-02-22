from __future__ import annotations

import base64
import hashlib
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from dateutil.parser import isoparse
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_ts(ts: str) -> datetime:
    try:
        dt = isoparse(ts)
        if dt.tzinfo is None:
            # Treat naive timestamps as UTC
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timestamp: {ts}. Error: {e}",
        ) from e


def stable_int(seed: str, key: str, mod: int) -> int:
    h = hashlib.sha256((seed + "::" + key).encode("utf-8")).hexdigest()
    return int(h[:12], 16) % mod


def encode_cursor(i: int) -> str:
    raw = str(i).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def decode_cursor(cur: str | None) -> int:
    if not cur:
        return 0
    padding = "=" * (-len(cur) % 4)
    try:
        raw = base64.urlsafe_b64decode((cur + padding).encode("utf-8")).decode("utf-8")
        return int(raw)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail="Invalid cursor",
        ) from e


class Campaign(BaseModel):
    campaign_id: str
    name: str
    channel: str = Field(description="email, sms, push")
    status: str = Field(description="draft, scheduled, sent, paused")
    updated_at: datetime
    created_at: datetime


class EmailEvent(BaseModel):
    event_id: str
    event_type: str = Field(description="send, delivered, open, click, bounce, unsubscribe")
    occurred_at: datetime
    campaign_id: str
    customer_email: str
    message_id: str
    user_agent: str | None = None
    ip_address: str | None = None
    link_url: str | None = None


class PaginatedResponse(BaseModel):
    data: list[dict[str, Any]]
    next_cursor: str | None


app = FastAPI(title="Mock MailBlaze SaaS API", version="1.0.0")

MOCK_SEED = os.getenv("MOCK_SAAS_SEED", "dp_mailblaze_demo_seed_v1")

# Deterministic base time anchored so runs are stable across days.
ANCHOR = datetime(2026, 2, 1, 0, 0, 0, tzinfo=UTC)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "seed": MOCK_SEED}


def generate_campaigns(n: int = 250) -> list[Campaign]:
    campaigns: list[Campaign] = []
    for i in range(n):
        cid = f"cmp_{i:04d}"
        # Spread created_at over 30 days from anchor
        created_at = ANCHOR + timedelta(hours=i * 3)
        # updated_at is created_at plus deterministic offset (0..72 hours)
        upd_hours = stable_int(MOCK_SEED, cid, 73)
        updated_at = created_at + timedelta(hours=upd_hours)

        channel = ["email", "sms", "push"][stable_int(MOCK_SEED, cid + ":ch", 3)]
        status = ["draft", "scheduled", "sent", "paused"][stable_int(MOCK_SEED, cid + ":st", 4)]
        name = f"{channel.upper()} Campaign {i:04d}"

        campaigns.append(
            Campaign(
                campaign_id=cid,
                name=name,
                channel=channel,
                status=status,
                created_at=created_at,
                updated_at=updated_at,
            )
        )
    # Sort by updated_at then campaign_id for stable pagination
    campaigns.sort(key=lambda x: (x.updated_at, x.campaign_id))
    return campaigns


def generate_email_events(n: int = 5000) -> list[EmailEvent]:
    events: list[EmailEvent] = []
    event_types = ["send", "delivered", "open", "click", "bounce", "unsubscribe"]

    for i in range(n):
        eid = f"evt_{i:06d}"
        # Deterministic occurred_at: every 2 minutes from anchor
        occurred_at = ANCHOR + timedelta(minutes=i * 2)

        # Map to campaign id deterministically
        cidx = stable_int(MOCK_SEED, eid + ":cmp", 250)
        campaign_id = f"cmp_{cidx:04d}"

        # Deterministic customer email pool
        uidx = stable_int(MOCK_SEED, eid + ":usr", 500)
        customer_email = f"user{uidx:04d}@example.com"

        et = event_types[stable_int(MOCK_SEED, eid + ":typ", len(event_types))]

        # Deterministic message id
        mid = f"msg_{stable_int(MOCK_SEED, eid + ':msg', 10**9):09d}"

        user_agent = None
        ip_address = None
        link_url = None

        if et in ("open", "click"):
            user_agent = ["Mozilla/5.0", "Chrome/122.0", "Safari/17.2"][
                stable_int(MOCK_SEED, eid + ":ua", 3)
            ]
            ip_address = f"192.0.2.{stable_int(MOCK_SEED, eid + ':ip', 254) + 1}"
        if et == "click":
            link_url = f"https://shop.example.com/p/{stable_int(MOCK_SEED, eid + ':p', 9999):04d}"

        events.append(
            EmailEvent(
                event_id=eid,
                event_type=et,
                occurred_at=occurred_at,
                campaign_id=campaign_id,
                customer_email=customer_email,
                message_id=mid,
                user_agent=user_agent,
                ip_address=ip_address,
                link_url=link_url,
            )
        )

    # Sort by occurred_at then event_id for stable pagination
    events.sort(key=lambda x: (x.occurred_at, x.event_id))
    return events


_CAMPAIGNS = generate_campaigns()
_EVENTS = generate_email_events()


def paginate(items: list[Any], cursor: str | None, limit: int) -> tuple[list[Any], str | None]:
    start = decode_cursor(cursor)
    if start < 0 or start > len(items):
        raise HTTPException(status_code=400, detail="Cursor out of range")

    end = min(start + limit, len(items))
    page = items[start:end]
    next_cur = encode_cursor(end) if end < len(items) else None
    return page, next_cur


@app.get("/v1/campaigns", response_model=PaginatedResponse)
def list_campaigns(
    updated_after: str | None = Query(default=None, description="ISO timestamp (UTC recommended)"),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    filtered = _CAMPAIGNS

    if updated_after:
        since = parse_ts(updated_after)
        filtered = [c for c in filtered if c.updated_at > since]

    page, next_cur = paginate(filtered, cursor, limit)
    return {
        "data": [c.model_dump(mode="json") for c in page],
        "next_cursor": next_cur,
    }


@app.get("/v1/email_events", response_model=PaginatedResponse)
def list_email_events(
    occurred_after: str | None = Query(default=None, description="ISO timestamp (UTC recommended)"),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=250, ge=1, le=1000),
) -> dict[str, Any]:
    filtered = _EVENTS

    if occurred_after:
        since = parse_ts(occurred_after)
        filtered = [e for e in filtered if e.occurred_at > since]

    page, next_cur = paginate(filtered, cursor, limit)
    return {
        "data": [e.model_dump(mode="json") for e in page],
        "next_cursor": next_cur,
    }
