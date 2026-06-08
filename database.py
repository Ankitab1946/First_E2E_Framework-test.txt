import os
import subprocess
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


_KERBEROS_INITIALIZED = False


def initialize_kerberos_if_required() -> None:
    """Prepare Kerberos environment for SQL Server keytab authentication.

    This function does not store secrets. It only sets standard Kerberos
    environment variables and, when enabled, runs kinit using the configured
    principal and keytab so pyodbc can use the resulting ticket cache.
    """
    global _KERBEROS_INITIALIZED

    settings = get_settings()
    if settings.effective_sql_auth_mode != "keytab":
        return

    if _KERBEROS_INITIALIZED:
        return

    if settings.krb5_config_path:
        os.environ["KRB5_CONFIG"] = settings.krb5_config_path

    if settings.krb5_keytab_path:
        os.environ["KRB5_CLIENT_KTNAME"] = settings.krb5_keytab_path

    if settings.krb5_cache_path:
        os.environ["KRB5CCNAME"] = settings.krb5_cache_path

    if settings.krb5_kinit_enabled:
        if not settings.krb5_keytab_path or not settings.krb5_principal:
            raise RuntimeError(
                "Kerberos keytab mode requires KRB5_KEYTAB_PATH and KRB5_PRINCIPAL "
                "when KRB5_KINIT_ENABLED=true."
            )

        command = [
            settings.krb5_kinit_command,
            "-kt",
            settings.krb5_keytab_path,
            settings.krb5_principal,
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Kerberos kinit failed. "
                f"Command: {' '.join(command)}. "
                f"stderr: {result.stderr.strip()}"
            )

    _KERBEROS_INITIALIZED = True


def create_db_engine():
    settings = get_settings()
    initialize_kerberos_if_required()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


def get_session_factory():
    engine = create_db_engine()
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)
