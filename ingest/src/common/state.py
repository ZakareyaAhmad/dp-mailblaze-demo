from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .logging import log
from .s3 import S3Client


@dataclass(frozen=True)
class StateStore:
    """
    Stores incremental watermarks in S3.
    State keys are small JSON files under:
      env={env}/raw/_state/{name}.json
    """

    s3: S3Client
    env: str

    def _key(self, name: str) -> str:
        return f"env={self.env}/raw/_state/{name}.json"

    def get(self, name: str) -> dict[str, Any] | None:
        key = self._key(name)
        if not self.s3.exists(key):
            return None

        def _do() -> dict[str, Any]:
            import boto3

            obj = boto3.client("s3", region_name=self.s3.region).get_object(
                Bucket=self.s3.bucket, Key=key
            )
            data = obj["Body"].read().decode("utf-8")
            return json.loads(data)

        out = _do()
        log("state_get", name=name, key=key)
        return out

    def put(self, name: str, value: dict[str, Any]) -> None:
        key = self._key(name)
        self.s3.put_bytes(
            key, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json"
        )
        log("state_put", name=name, key=key, value=value)
