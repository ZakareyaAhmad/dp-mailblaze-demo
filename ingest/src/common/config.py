from __future__ import annotations

import os
from dataclasses import dataclass


def _req(name: str) -> str:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return v


def _opt(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return default if v is None else v


@dataclass(frozen=True)
class AppConfig:
    env: str
    aws_region: str
    s3_raw_bucket: str

    pg_host: str
    pg_port: int
    pg_db: str
    pg_user: str
    pg_password: str

    mailblaze_base_url: str
    mailblaze_api_key: str

    @staticmethod
    def load() -> AppConfig:
        return AppConfig(
            env=_opt("ENV", "dev"),
            aws_region=_opt("AWS_REGION", "eu-west-1"),
            s3_raw_bucket=_req("S3_RAW_BUCKET"),
            pg_host=_opt("PG_HOST", "postgres"),
            pg_port=int(_opt("PG_PORT", "5432")),
            pg_db=_opt("PG_DB", "appdb"),
            pg_user=_opt("PG_USER", "postgres"),
            pg_password=_opt("PG_PASSWORD", "postgres"),
            mailblaze_base_url=_opt("MAILBLAZE_BASE_URL", "http://mock_saas:8000"),
            mailblaze_api_key=_opt("MAILBLAZE_API_KEY", "dev_key_123"),
        )
