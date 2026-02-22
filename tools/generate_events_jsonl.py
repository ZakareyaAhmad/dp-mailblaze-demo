from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

EVENT_TYPES = [
    "page_view",
    "product_view",
    "add_to_cart",
    "checkout_started",
    "purchase",
    "email_open",
    "email_click",
]

PLATFORMS = ["web", "ios", "android"]
COUNTRY_CODES = ["US", "GB", "DE", "FR", "NL", "ES", "IT"]
SKUS = [
    "SKU-RED-TSHIRT",
    "SKU-BLUE-JEANS",
    "SKU-SNEAKERS",
    "SKU-BLACK-HOODIE",
    "SKU-WHITE-SOCKS",
    "SKU-SPORTS-CAP",
    "SKU-LEATHER-BELT",
    "SKU-RUNNING-SHORTS",
]


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def iso_z(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_idempotency_key(seed: str, event_id: str) -> str:
    # Stable idempotency key for exactly-once semantics on replays
    return sha256_hex(f"{seed}::idempotency::{event_id}")


def make_event(rng: random.Random, seed: str, base_ts: datetime, i: int) -> dict:
    event_id = f"ev_{i:010d}"
    event_type = rng.choice(EVENT_TYPES)

    # Event time advances deterministically by i * delta seconds + jitter
    delta_sec = 3 * i + rng.randint(0, 2)
    event_ts = base_ts + timedelta(seconds=delta_sec)

    customer_id = rng.randint(1, 5000)
    session_id = f"sess_{rng.randint(1, 200000):06d}"
    platform = rng.choice(PLATFORMS)
    country_code = rng.choice(COUNTRY_CODES)

    sku: str | None = None
    quantity: int | None = None
    revenue_cents: int | None = None
    campaign_id: str | None = None
    url: str | None = None

    if event_type in ("product_view", "add_to_cart", "purchase"):
        sku = rng.choice(SKUS)
        quantity = 1 if event_type != "add_to_cart" else rng.randint(1, 3)

    if event_type == "purchase":
        # revenue is loosely tied to sku hash for stability
        revenue_cents = 1500 + (int(sha256_hex(sku or "x")[:6], 16) % 9000)

    if event_type in ("email_open", "email_click"):
        campaign_id = f"cmp_{rng.randint(0, 249):04d}"

    if event_type in ("page_view", "product_view"):
        if sku:
            url = f"https://shop.example.com/p/{sku}"
        else:
            url = f"https://shop.example.com/c/{rng.randint(1, 50):02d}"

    event = {
        "schema_version": 1,
        "event_id": event_id,
        "idempotency_key": make_idempotency_key(seed, event_id),
        "event_type": event_type,
        "event_ts": iso_z(event_ts),
        "received_ts": iso_z(event_ts + timedelta(seconds=rng.randint(1, 30))),
        "customer_id": customer_id,
        "session_id": session_id,
        "platform": platform,
        "country_code": country_code,
        "sku": sku,
        "quantity": quantity,
        "revenue_cents": revenue_cents,
        "campaign_id": campaign_id,
        "url": url,
        "user_agent": rng.choice(["Mozilla/5.0", "Chrome/122.0", "Safari/17.2"]),
        "ip_address": f"198.51.100.{rng.randint(1, 254)}",
    }
    return event


def write_jsonl(events: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, separators=(",", ":"), ensure_ascii=False) + "\n")


def main() -> None:
    p = argparse.ArgumentParser(description="Generate deterministic event JSONL file")
    p.add_argument("--count", type=int, required=True, help="Number of events to generate")
    p.add_argument("--out", required=True, help="Output JSONL path")
    p.add_argument("--seed", default=os.getenv("EVENTS_SEED", "dp_mailblaze_demo_events_seed_v1"))
    p.add_argument(
        "--base-ts",
        default="2026-02-18T09:00:00Z",
        help="Base timestamp (UTC) ISO8601 ending with Z (default: 2026-02-18T09:00:00Z)",
    )
    args = p.parse_args()

    # Deterministic RNG seeded by seed+base-ts so re-running produces identical file
    seed_material = f"{args.seed}::{args.base_ts}"
    rng = random.Random(int(sha256_hex(seed_material)[:12], 16))

    if not args.base_ts.endswith("Z"):
        raise SystemExit("--base-ts must be UTC ISO8601 ending with Z, e.g. 2026-02-18T09:00:00Z")

    base_ts = datetime.strptime(args.base_ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)

    events = [make_event(rng, args.seed, base_ts, i) for i in range(args.count)]
    write_jsonl(events, Path(args.out))
    print(f"Wrote {len(events)} events to {args.out}")


if __name__ == "__main__":
    main()
