from __future__ import annotations

import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pandas as pd

from app.core.config import get_settings
from app.core.database import create_db_engine
from app.utils.sample_data import get_sample_records


class S3ExportService:
    """Export latest active Data Dictionary tables to internal S3-compatible storage.

    This implementation is built for corporate/internal S3-compatible object
    stores, not only public AWS S3. It follows the working pattern generally used
    for internal buckets:

        boto3.client(
            "s3",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_key,
            use_ssl=False,
            verify=False,
            endpoint_url=host,
        )

    Important implementation details:
    - endpoint_url must be only the base host, for example http://host:port
    - bucket name is passed separately to Bucket=...
    - object keys do not contain spaces
    - path-style addressing is used by default
    """

    TABLES = [
        "master_dictionary",
        "prj_attribute",
        "prj_attr_business_logic",
        "prj_attr_business_logic_scope",
    ]

    def __init__(self):
        self.settings = get_settings()

    def export_four_files(self, user_id: str) -> dict:
        timestamp = self._safe_timestamp()
        bucket_name = (self.settings.effective_s3_bucket_name or "").strip()
        keys_by_table = {
            table_name: self._build_object_key(table_name, timestamp)
            for table_name in self.TABLES
        }

        if not bucket_name:
            return {
                "status": "SIMULATED_SUCCESS",
                "message": "Bucket name is not configured. Export was simulated so the UI button remains usable in local/dev mode.",
                "bucket": "NOT_CONFIGURED",
                "files": list(keys_by_table.values()),
                "exported_by": user_id,
            }

        if not self.settings.enable_db:
            return {
                "status": "SIMULATED_SUCCESS",
                "message": "ENABLE_DB=false. S3 export was simulated.",
                "bucket": bucket_name,
                "files": list(keys_by_table.values()),
                "exported_by": user_id,
            }

        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise RuntimeError("boto3 is required for S3 export. Install requirements.txt again.") from exc

        endpoint_url = self._resolve_endpoint_url()
        if not endpoint_url:
            raise RuntimeError(
                "Internal S3 endpoint is not configured. Set HOST or S3_HOST in .env. "
                "Use only the base internal endpoint, for example http://host:port. "
                "Do not include bucket name or folder path in HOST."
            )

        # These env values prevent newer boto/botocore versions from adding
        # checksum behavior that some internal S3-compatible stores do not support.
        os.environ.setdefault("AWS_REQUEST_CHECKSUM_CALCULATION", "when_required")
        os.environ.setdefault("AWS_RESPONSE_CHECKSUM_VALIDATION", "when_required")

        client_kwargs = {
            "service_name": "s3",
            "aws_access_key_id": self.settings.effective_aws_access_key_id or None,
            "aws_secret_access_key": self.settings.effective_aws_secret_access_key or None,
            "use_ssl": bool(self.settings.s3_use_ssl),
            "verify": bool(self.settings.s3_verify_ssl),
            "endpoint_url": endpoint_url,
            "config": Config(
                signature_version="s3v4",
                s3={
                    "addressing_style": self.settings.s3_addressing_style or "path",
                    "payload_signing_enabled": False,
                },
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=30,
                read_timeout=120,
            ),
        }
        if self.settings.aws_region:
            client_kwargs["region_name"] = self.settings.aws_region

        s3 = boto3.client(**client_kwargs)
        uploaded_files: list[str] = []
        engine = create_db_engine()

        with engine.connect() as connection:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                for table_name in self.TABLES:
                    df = self._read_latest_table(connection, table_name)
                    local_file = tmp_path / f"{table_name}_{timestamp}.csv"
                    df.to_csv(local_file, index=False, encoding="utf-8")

                    key = keys_by_table[table_name]

                    # upload_file is intentionally used because it mirrors the
                    # working internal-cloud pattern more closely than put_object.
                    s3.upload_file(
                        Filename=str(local_file),
                        Bucket=bucket_name,
                        Key=key,
                    )
                    uploaded_files.append(key)

        return {
            "status": "SUCCESS",
            "bucket": bucket_name,
            "endpoint_url": endpoint_url,
            "use_ssl": bool(self.settings.s3_use_ssl),
            "verify_ssl": bool(self.settings.s3_verify_ssl),
            "addressing_style": self.settings.s3_addressing_style or "path",
            "files": uploaded_files,
            "exported_by": user_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

    def _read_latest_table(self, connection, table_name: str) -> pd.DataFrame:
        """Read active/latest records from a table. All target tables have is_active."""
        return pd.read_sql(f"SELECT * FROM dbo.{table_name} WHERE is_active = 1", connection)

    def _safe_timestamp(self) -> str:
        """Return timestamp safe for S3-compatible object keys and Windows paths."""
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    def _build_object_key(self, table_name: str, timestamp: str) -> str:
        prefix = self._sanitize_prefix(self.settings.s3_prefix or "data-dictionary")
        safe_table_name = re.sub(r"[^A-Za-z0-9_.-]", "_", table_name.strip())
        return f"{prefix}/{timestamp}/{safe_table_name}_{timestamp}.csv"

    def _sanitize_prefix(self, prefix: str) -> str:
        prefix = str(prefix or "data-dictionary").strip().strip("/")
        prefix = prefix.replace("\\", "/")
        parts = [self._sanitize_key_part(part) for part in prefix.split("/") if part.strip()]
        return "/".join(parts) or "data-dictionary"

    def _sanitize_key_part(self, value: str) -> str:
        value = value.strip()
        value = re.sub(r"\s+", "_", value)
        value = re.sub(r"[^A-Za-z0-9_.=-]", "_", value)
        return value

    def _resolve_endpoint_url(self) -> str:
        """Resolve internal S3 endpoint URL.

        Priority:
        1. S3_ENDPOINT_URL, if explicitly provided.
        2. HOST/S3_HOST when S3_USE_SSL=false. This matches the user's working
           internal-cloud boto3 code: use_ssl=False, verify=False, endpoint_url=host.
        3. SECURE_HOST/S3_SECURE_HOST when S3_USE_SSL=true.

        The returned endpoint is normalized to a base URL. Object key paths are
        never appended to endpoint_url; they are passed separately as Key=...
        """
        explicit_endpoint = (self.settings.s3_endpoint_url or "").strip()
        if explicit_endpoint:
            endpoint = explicit_endpoint
        elif self.settings.s3_use_ssl:
            endpoint = self.settings.effective_s3_secure_host or self.settings.effective_s3_host
        else:
            endpoint = self.settings.effective_s3_host or self.settings.effective_s3_secure_host

        endpoint = (endpoint or "").strip().strip('"').strip("'")
        if not endpoint:
            return ""

        endpoint = self._ensure_endpoint_scheme(endpoint)
        endpoint = self._normalize_endpoint_scheme(endpoint, use_ssl=bool(self.settings.s3_use_ssl))
        endpoint = self._append_port_if_needed(endpoint)
        return endpoint.rstrip("/")

    def _ensure_endpoint_scheme(self, endpoint_url: str) -> str:
        if endpoint_url.startswith(("http://", "https://")):
            return endpoint_url
        scheme = "https" if self.settings.s3_use_ssl else "http"
        return f"{scheme}://{endpoint_url}"

    def _normalize_endpoint_scheme(self, endpoint_url: str, use_ssl: bool) -> str:
        """Keep endpoint scheme consistent with boto3 use_ssl flag.

        For internal object stores with self-signed certs, the required mode is
        usually use_ssl=False and verify=False. If a https URL is accidentally
        supplied while use_ssl=False, convert it to http so boto3 does not try
        SSL/TLS certificate validation.
        """
        endpoint_url = endpoint_url.rstrip("/")
        parsed = urlparse(endpoint_url)
        if not parsed.scheme:
            return endpoint_url

        desired_scheme = "https" if use_ssl else "http"
        if parsed.scheme != desired_scheme:
            parsed = parsed._replace(scheme=desired_scheme)
            return urlunparse(parsed).rstrip("/")

        return endpoint_url

    def _append_port_if_needed(self, endpoint_url: str) -> str:
        port = str(self.settings.s3_port or "").strip()
        if not port:
            return endpoint_url.rstrip("/")

        parsed = urlparse(endpoint_url)
        if parsed.port:
            return endpoint_url.rstrip("/")

        netloc = parsed.netloc
        if not netloc:
            return endpoint_url.rstrip("/")

        rebuilt = parsed._replace(netloc=f"{netloc}:{port}")
        return rebuilt.geturl().rstrip("/")

    def export_sample_preview(self) -> dict:
        """Helper used only by tests/dev when database is disabled."""
        return {"master_dictionary": get_sample_records()}
