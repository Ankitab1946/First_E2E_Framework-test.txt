# from __future__ import annotations

# from datetime import datetime, timezone
# from io import StringIO
# from urllib.parse import urlparse

# import pandas as pd

# from app.core.config import get_settings
# from app.core.database import create_db_engine
# from app.utils.sample_data import get_sample_records


# class S3ExportService:
#     """Export the latest active Data Dictionary tables to S3/S3-compatible storage.

#     The service supports corporate S3-compatible endpoints through .env values:
#     S3_BUCKET_NAME, S3_HOST, S3_SECURE_HOST, S3_PORT, AWS_ACCESS_KEY_ID,
#     AWS_SECRET_ACCESS_KEY, S3_USE_SSL and S3_VERIFY_SSL.
#     """

#     TABLES = [
#         "master_dictionary",
#         "prj_attribute",
#         "prj_attr_business_logic",
#         "prj_attr_business_logic_scope",
#     ]

#     def __init__(self):
#         self.settings = get_settings()

#     def export_four_files(self, user_id: str) -> dict:
#         timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
#         simulated_files = [
#             f"{self.settings.s3_prefix}/{timestamp}/{name}_{timestamp}.csv"
#             for name in self.TABLES
#         ]

#         if not self.settings.s3_bucket_name:
#             return {
#                 "status": "SIMULATED_SUCCESS",
#                 "message": "S3_BUCKET_NAME is not configured. Export was simulated so the UI button remains usable in local/dev mode.",
#                 "bucket": "NOT_CONFIGURED",
#                 "files": simulated_files,
#                 "exported_by": user_id,
#             }

#         if not self.settings.enable_db:
#             return {
#                 "status": "SIMULATED_SUCCESS",
#                 "message": "ENABLE_DB=false. S3 export was simulated.",
#                 "bucket": self.settings.s3_bucket_name,
#                 "files": simulated_files,
#                 "exported_by": user_id,
#             }

#         try:
#             import boto3
#         except ImportError as exc:
#             raise RuntimeError("boto3 is required for S3 export. Install requirements.txt again.") from exc

#         endpoint_url = self._resolve_endpoint_url()
#         client_kwargs = {
#             "service_name": "s3",
#             "aws_access_key_id": self.settings.aws_access_key_id or None,
#             "aws_secret_access_key": self.settings.aws_secret_access_key or None,
#             "use_ssl": self.settings.s3_use_ssl,
#             "verify": self.settings.s3_verify_ssl,
#         }
#         if self.settings.aws_region:
#             client_kwargs["region_name"] = self.settings.aws_region
#         if endpoint_url:
#             client_kwargs["endpoint_url"] = endpoint_url

#         s3 = boto3.client(**client_kwargs)
#         uploaded_files: list[str] = []
#         engine = create_db_engine()

#         with engine.connect() as connection:
#             for table_name in self.TABLES:
#                 df = self._read_latest_table(connection, table_name)
#                 csv_buffer = StringIO()
#                 df.to_csv(csv_buffer, index=False)
#                 key = f"{self.settings.s3_prefix}/{timestamp}/{table_name}_{timestamp}.csv"
#                 s3.put_object(
#                     Bucket=self.settings.s3_bucket_name,
#                     Key=key,
#                     Body=csv_buffer.getvalue().encode("utf-8"),
#                     ContentType="text/csv",
#                     Metadata={
#                         "exported-by": str(user_id),
#                         "environment": str(self.settings.selected_environment),
#                         "export-type": "latest-active-records",
#                     },
#                 )
#                 uploaded_files.append(key)

#         return {
#             "status": "SUCCESS",
#             "bucket": self.settings.s3_bucket_name,
#             "endpoint_url": endpoint_url or "AWS_DEFAULT",
#             "files": uploaded_files,
#             "exported_by": user_id,
#             "exported_at": datetime.now(timezone.utc).isoformat(),
#         }

#     def _read_latest_table(self, connection, table_name: str) -> pd.DataFrame:
#         """Read active/latest records from a table. All target tables have is_active."""
#         return pd.read_sql(f"SELECT * FROM dbo.{table_name} WHERE is_active = 1", connection)

#     def _resolve_endpoint_url(self) -> str:
#         explicit_endpoint = (self.settings.s3_endpoint_url or "").strip()
#         if explicit_endpoint:
#             return self._append_port_if_needed(explicit_endpoint)

#         host = (
#             self.settings.s3_secure_host
#             if self.settings.s3_secure and self.settings.s3_secure_host
#             else self.settings.s3_host
#         ).strip()
#         if not host:
#             return ""

#         if not host.startswith(("http://", "https://")):
#             scheme = "https" if self.settings.s3_secure else "http"
#             host = f"{scheme}://{host}"

#         return self._append_port_if_needed(host)

#     def _append_port_if_needed(self, endpoint_url: str) -> str:
#         port = str(self.settings.s3_port or "").strip()
#         if not port:
#             return endpoint_url.rstrip("/")

#         parsed = urlparse(endpoint_url)
#         if parsed.port:
#             return endpoint_url.rstrip("/")

#         netloc = parsed.netloc
#         if not netloc:
#             return endpoint_url.rstrip("/")

#         rebuilt = parsed._replace(netloc=f"{netloc}:{port}")
#         return rebuilt.geturl().rstrip("/")

#     def export_sample_preview(self) -> dict:
#         """Helper used only by tests/dev when database is disabled."""
#         return {"master_dictionary": get_sample_records()}

from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO
from urllib.parse import urlparse, urlunparse

import pandas as pd

from app.core.config import get_settings
from app.core.database import create_db_engine
from app.utils.sample_data import get_sample_records


class S3ExportService:
    """Export latest active Data Dictionary tables to internal S3-compatible storage.

    This implementation is intentionally endpoint-first for corporate/internal
    S3-compatible storage. It matches the working pattern:

        boto3.client(
            "s3",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_key,
            use_ssl=False,
            verify=False,
            endpoint_url=host,
        )

    It does not fall back to AWS public S3 when an internal host is configured.
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
        bucket_name = self.settings.effective_s3_bucket_name
        simulated_files = [
            f"{self.settings.s3_prefix}/{timestamp}/{name}_{timestamp}.csv"
            for name in self.TABLES
        ]

        if not bucket_name:
            return {
                "status": "SIMULATED_SUCCESS",
                "message": "Bucket name is not configured. Export was simulated so the UI button remains usable in local/dev mode.",
                "bucket": "NOT_CONFIGURED",
                "files": simulated_files,
                "exported_by": user_id,
            }

        if not self.settings.enable_db:
            return {
                "status": "SIMULATED_SUCCESS",
                "message": "ENABLE_DB=false. S3 export was simulated.",
                "bucket": bucket_name,
                "files": simulated_files,
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
                "For your internal cloud bucket, use the same host value that works in boto3 endpoint_url=host."
            )

        client_kwargs = {
            "service_name": "s3",
            "aws_access_key_id": self.settings.effective_aws_access_key_id or None,
            "aws_secret_access_key": self.settings.effective_aws_secret_access_key or None,
            "use_ssl": bool(self.settings.s3_use_ssl),
            "verify": bool(self.settings.s3_verify_ssl),
            "endpoint_url": endpoint_url,
            "config": Config(
                s3={"addressing_style": self.settings.s3_addressing_style or "path"},
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        }
        if self.settings.aws_region:
            client_kwargs["region_name"] = self.settings.aws_region

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
                    Bucket=bucket_name,
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
            "bucket": bucket_name,
            "endpoint_url": endpoint_url,
            "use_ssl": bool(self.settings.s3_use_ssl),
            "verify_ssl": bool(self.settings.s3_verify_ssl),
            "files": uploaded_files,
            "exported_by": user_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

    def _read_latest_table(self, connection, table_name: str) -> pd.DataFrame:
        """Read active/latest records from a table. All target tables have is_active."""
        return pd.read_sql(f"SELECT * FROM dbo.{table_name} WHERE is_active = 1", connection)

    def _resolve_endpoint_url(self) -> str:
        """Resolve internal S3 endpoint URL.

        Priority:
        1. S3_ENDPOINT_URL, if explicitly provided.
        2. HOST/S3_HOST when S3_USE_SSL=false. This matches the user's working
           internal-cloud boto3 code: use_ssl=False, verify=False, endpoint_url=host.
        3. SECURE_HOST/S3_SECURE_HOST when S3_USE_SSL=true.

        This avoids accidentally constructing AWS public HTTPS URLs and avoids
        certificate validation failures from internal/self-signed chains.
        """
        explicit_endpoint = (self.settings.s3_endpoint_url or "").strip()
        if explicit_endpoint:
            return self._normalize_endpoint_scheme(
                self._append_port_if_needed(explicit_endpoint),
                use_ssl=bool(self.settings.s3_use_ssl),
            )

        if self.settings.s3_use_ssl:
            host = self.settings.effective_s3_secure_host or self.settings.effective_s3_host
        else:
            host = self.settings.effective_s3_host or self.settings.effective_s3_secure_host

        host = (host or "").strip()
        if not host:
            return ""

        if not host.startswith(("http://", "https://")):
            scheme = "https" if self.settings.s3_use_ssl else "http"
            host = f"{scheme}://{host}"

        return self._normalize_endpoint_scheme(
            self._append_port_if_needed(host),
            use_ssl=bool(self.settings.s3_use_ssl),
        )

    def _normalize_endpoint_scheme(self, endpoint_url: str, use_ssl: bool) -> str:
        """Keep endpoint scheme consistent with boto3 use_ssl flag.

        For internal object stores with self-signed certs, the required mode is
        use_ssl=False and verify=False. If a https URL is accidentally supplied
        while use_ssl=False, convert it to http so boto3 does not perform SSL
        certificate validation.
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
