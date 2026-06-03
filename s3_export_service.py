from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO
from urllib.parse import urlparse

import pandas as pd

from app.core.config import get_settings
from app.core.database import create_db_engine
from app.utils.sample_data import get_sample_records


class S3ExportService:
    """Export the latest active Data Dictionary tables to S3/S3-compatible storage.

    The service supports corporate S3-compatible endpoints through .env values:
    S3_BUCKET_NAME, S3_HOST, S3_SECURE_HOST, S3_PORT, AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY, S3_USE_SSL and S3_VERIFY_SSL.
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
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        simulated_files = [
            f"{self.settings.s3_prefix}/{timestamp}/{name}_{timestamp}.csv"
            for name in self.TABLES
        ]

        if not self.settings.s3_bucket_name:
            return {
                "status": "SIMULATED_SUCCESS",
                "message": "S3_BUCKET_NAME is not configured. Export was simulated so the UI button remains usable in local/dev mode.",
                "bucket": "NOT_CONFIGURED",
                "files": simulated_files,
                "exported_by": user_id,
            }

        if not self.settings.enable_db:
            return {
                "status": "SIMULATED_SUCCESS",
                "message": "ENABLE_DB=false. S3 export was simulated.",
                "bucket": self.settings.s3_bucket_name,
                "files": simulated_files,
                "exported_by": user_id,
            }

        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for S3 export. Install requirements.txt again.") from exc

        endpoint_url = self._resolve_endpoint_url()
        client_kwargs = {
            "service_name": "s3",
            "aws_access_key_id": self.settings.aws_access_key_id or None,
            "aws_secret_access_key": self.settings.aws_secret_access_key or None,
            "use_ssl": self.settings.s3_use_ssl,
            "verify": self.settings.s3_verify_ssl,
        }
        if self.settings.aws_region:
            client_kwargs["region_name"] = self.settings.aws_region
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url

        s3 = boto3.client(**client_kwargs)
        uploaded_files: list[str] = []
        engine = create_db_engine()

        with engine.connect() as connection:
            for table_name in self.TABLES:
                df = self._read_latest_table(connection, table_name)
                csv_buffer = StringIO()
                df.to_csv(csv_buffer, index=False)
                key = f"{self.settings.s3_prefix}/{timestamp}/{table_name}_{timestamp}.csv"
                s3.put_object(
                    Bucket=self.settings.s3_bucket_name,
                    Key=key,
                    Body=csv_buffer.getvalue().encode("utf-8"),
                    ContentType="text/csv",
                    Metadata={
                        "exported-by": str(user_id),
                        "environment": str(self.settings.selected_environment),
                        "export-type": "latest-active-records",
                    },
                )
                uploaded_files.append(key)

        return {
            "status": "SUCCESS",
            "bucket": self.settings.s3_bucket_name,
            "endpoint_url": endpoint_url or "AWS_DEFAULT",
            "files": uploaded_files,
            "exported_by": user_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

    def _read_latest_table(self, connection, table_name: str) -> pd.DataFrame:
        """Read active/latest records from a table. All target tables have is_active."""
        return pd.read_sql(f"SELECT * FROM dbo.{table_name} WHERE is_active = 1", connection)

    def _resolve_endpoint_url(self) -> str:
        explicit_endpoint = (self.settings.s3_endpoint_url or "").strip()
        if explicit_endpoint:
            return self._append_port_if_needed(explicit_endpoint)

        host = (
            self.settings.s3_secure_host
            if self.settings.s3_secure and self.settings.s3_secure_host
            else self.settings.s3_host
        ).strip()
        if not host:
            return ""

        if not host.startswith(("http://", "https://")):
            scheme = "https" if self.settings.s3_secure else "http"
            host = f"{scheme}://{host}"

        return self._append_port_if_needed(host)

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
