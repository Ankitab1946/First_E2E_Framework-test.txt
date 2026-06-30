"""Central, environment-aware application configuration."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_name: str = "Data Dictionary Streamlit Admin"
    app_env: str = "LOCAL"
    app_debug: bool = False
    api_base_url: str = "http://localhost:8503/api/v1"
    use_api_for_filters: bool = True
    app_environments: str = "LOCAL,DEV,UAT,PROD"
    selected_environment: str = "LOCAL"

    sqlserver_server: str = r"localhost\SQLEXPRESS"
    sqlserver_database: str = "PRJ_DB"
    sqlserver_windows_auth: bool = True
    sqlserver_user: str = ""
    sqlserver_password: str = ""
    sqlserver_driver: str = "ODBC Driver 17 for SQL Server"
    sqlserver_trust_cert: str = "yes"
    enable_db: bool = False

    admin_users: str = "*,sysuser"
    default_user: str = "sysuser"
    local_auto_admin: bool = True
    excel_template_version: str = "1.0"
    max_upload_size_mb: int = 20

    s3_bucket_name: str = ""
    bucket_name: str = ""
    s3_prefix: str = "data-dictionary"
    aws_region: str = "ap-south-1"
    s3_host: str = ""
    host: str = ""
    s3_secure_host: str = ""
    secure_host: str = ""
    s3_port: str = ""
    s3_endpoint_url: str = ""
    s3_use_ssl: bool = False
    s3_verify_ssl: bool = False
    s3_addressing_style: str = "path"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    access_key_id: str = ""
    secret_key: str = ""

    def available_environments(self) -> list[str]:
        return [item.strip().upper() for item in self.app_environments.split(",") if item.strip()]

    def resolve_environment(self, environment: str | None = None) -> str:
        candidate = (environment or self.selected_environment or self.app_env).upper()
        return candidate if candidate in self.available_environments() else self.app_env.upper()

    def _env_value(self, environment: str, suffix: str, default: Any) -> Any:
        value = os.getenv(f"ENV_{environment}_{suffix}")
        return default if value is None or value == "" else value

    @staticmethod
    def _as_bool(value: Any) -> bool:
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

    def database_config(self, environment: str | None = None) -> dict[str, Any]:
        env = self.resolve_environment(environment)
        return {
            "environment": env,
            "server": self._env_value(env, "SQLSERVER_SERVER", self.sqlserver_server),
            "database": self._env_value(env, "SQLSERVER_DATABASE", self.sqlserver_database),
            "windows_auth": self._as_bool(self._env_value(env, "SQLSERVER_WINDOWS_AUTH", self.sqlserver_windows_auth)),
            "user": self._env_value(env, "SQLSERVER_USER", self.sqlserver_user),
            "password": self._env_value(env, "SQLSERVER_PASSWORD", self.sqlserver_password),
            "driver": self._env_value(env, "SQLSERVER_DRIVER", self.sqlserver_driver),
            "trust_cert": self._env_value(env, "SQLSERVER_TRUST_CERT", self.sqlserver_trust_cert),
            "enabled": self._as_bool(self._env_value(env, "ENABLE_DB", self.enable_db)),
        }

    def connection_string(self, environment: str | None = None) -> str:
        cfg = self.database_config(environment)
        common = (
            f"DRIVER={{{cfg['driver']}}};SERVER={cfg['server']};DATABASE={cfg['database']};"
            f"Encrypt=no;TrustServerCertificate={cfg['trust_cert']};"
        )
        if cfg["windows_auth"]:
            return common + "Trusted_Connection=yes;"
        return common + f"UID={cfg['user']};PWD={cfg['password']};"

    @property
    def effective_s3_bucket_name(self) -> str:
        return self.s3_bucket_name or self.bucket_name

    @property
    def effective_s3_access_key_id(self) -> str:
        return self.aws_access_key_id or self.access_key_id

    @property
    def effective_s3_secret_key(self) -> str:
        return self.aws_secret_access_key or self.secret_key

    @property
    def effective_s3_endpoint_url(self) -> str:
        endpoint = self.s3_endpoint_url or self.s3_host or self.host
        if not endpoint and self.s3_secure_host:
            endpoint = self.s3_secure_host
        if not endpoint and self.secure_host:
            endpoint = self.secure_host
        if endpoint and self.s3_port and ":" not in endpoint.rsplit("/", 1)[-1]:
            endpoint = f"{endpoint.rstrip('/')}:{self.s3_port}"
        return endpoint

    def is_admin(self, username: str) -> bool:
        users = {value.strip().lower() for value in self.admin_users.split(",") if value.strip()}
        return "*" in users or username.lower() in users


@lru_cache
def get_settings() -> Settings:
    return Settings()
