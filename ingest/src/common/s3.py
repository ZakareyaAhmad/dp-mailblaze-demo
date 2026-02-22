from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError

from .logging import log
from .retry import with_retry


@dataclass(frozen=True)
class S3Client:
    bucket: str
    region: str

    def _client(self):
        return boto3.client("s3", region_name=self.region)

    @staticmethod
    def sha256_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def exists(self, key: str) -> bool:
        def _do() -> bool:
            try:
                self._client().head_object(Bucket=self.bucket, Key=key)
                return True
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code")
                if code in ("404", "NoSuchKey", "NotFound"):
                    return False
                raise

        return with_retry(_do)

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        def _do() -> None:
            self._client().put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )

        with_retry(_do)
        log("s3_put", bucket=self.bucket, key=key, bytes=len(data))

    def put_json(self, key: str, obj: dict) -> None:
        data = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
        self.put_bytes(key, data, "application/json")

    def put_idempotent(
        self, data_key: str, data: bytes, content_type: str, manifest_key: str
    ) -> bool:
        """
        Idempotent write:
        - if manifest exists => skip (already uploaded)
        - else upload data and write manifest containing sha256 + size
        Returns True if uploaded, False if skipped.
        """
        if self.exists(manifest_key):
            log(
                "s3_skip_existing", bucket=self.bucket, manifest_key=manifest_key, data_key=data_key
            )
            return False

        sha = self.sha256_bytes(data)
        self.put_bytes(data_key, data, content_type)
        self.put_json(manifest_key, {"data_key": data_key, "sha256": sha, "bytes": len(data)})
        return True
