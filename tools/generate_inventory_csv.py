from __future__ import annotations

import argparse
import csv
import hashlib
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class InventoryRow:
    snapshot_date: str  # YYYY-MM-DD
    warehouse_id: str  # e.g., WH_EU_01
    sku: str  # matches OLTP product SKU patterns
    on_hand_qty: int  # integer >= 0
    reserved_qty: int  # integer >= 0
    available_qty: int  # integer >= 0
    reorder_point: int  # integer >= 0
    supplier_lead_time_days: int
    unit_cost_cents: int  # integer >= 0
    updated_at_utc: str  # ISO8601 with Z


WAREHOUSES = ["WH_EU_01", "WH_EU_02", "WH_US_01"]
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


def stable_int(seed: str, key: str, mod: int) -> int:
    h = hashlib.sha256((seed + "::" + key).encode("utf-8")).hexdigest()
    return int(h[:12], 16) % mod


def gen_rows(snapshot: date, seed: str) -> list[InventoryRow]:
    rows: list[InventoryRow] = []
    snap = snapshot.isoformat()
    ts = datetime(snapshot.year, snapshot.month, snapshot.day, 2, 0, 0).isoformat() + "Z"

    for wh in WAREHOUSES:
        for sku in SKUS:
            base = stable_int(seed, f"{snap}:{wh}:{sku}:base", 500)
            demand = stable_int(seed, f"{snap}:{wh}:{sku}:dmd", 200)

            on_hand = max(0, base + 50 - demand)
            reserved = stable_int(seed, f"{snap}:{wh}:{sku}:rsv", min(50, on_hand + 1))
            available = max(0, on_hand - reserved)

            reorder_point = 30 + stable_int(seed, f"{snap}:{wh}:{sku}:rop", 70)
            lead_time = 3 + stable_int(seed, f"{snap}:{wh}:{sku}:lt", 18)
            unit_cost = 500 + stable_int(seed, f"{snap}:{wh}:{sku}:cost", 8000)

            rows.append(
                InventoryRow(
                    snapshot_date=snap,
                    warehouse_id=wh,
                    sku=sku,
                    on_hand_qty=on_hand,
                    reserved_qty=reserved,
                    available_qty=available,
                    reorder_point=reorder_point,
                    supplier_lead_time_days=lead_time,
                    unit_cost_cents=unit_cost,
                    updated_at_utc=ts,
                )
            )
    return rows


def write_csv(rows: Iterable[InventoryRow], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "snapshot_date",
        "warehouse_id",
        "sku",
        "on_hand_qty",
        "reserved_qty",
        "available_qty",
        "reorder_point",
        "supplier_lead_time_days",
        "unit_cost_cents",
        "updated_at_utc",
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(
                {
                    "snapshot_date": r.snapshot_date,
                    "warehouse_id": r.warehouse_id,
                    "sku": r.sku,
                    "on_hand_qty": r.on_hand_qty,
                    "reserved_qty": r.reserved_qty,
                    "available_qty": r.available_qty,
                    "reorder_point": r.reorder_point,
                    "supplier_lead_time_days": r.supplier_lead_time_days,
                    "unit_cost_cents": r.unit_cost_cents,
                    "updated_at_utc": r.updated_at_utc,
                }
            )


def main() -> None:
    p = argparse.ArgumentParser(description="Generate deterministic inventory snapshot CSV")
    p.add_argument("--date", required=True, help="Snapshot date in YYYY-MM-DD")
    p.add_argument("--out", required=True, help="Output CSV path")
    p.add_argument(
        "--seed", default=os.getenv("INVENTORY_SEED", "dp_mailblaze_demo_inventory_seed_v1")
    )
    args = p.parse_args()

    snapshot = date.fromisoformat(args.date)
    rows = gen_rows(snapshot, args.seed)
    write_csv(rows, Path(args.out))
    print(f"Wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
