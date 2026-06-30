from fastapi import APIRouter, Header, Depends, HTTPException
from DataDictionaryAdminApp.config import get_settings
from sqlalchemy import text
from sqlalchemy.orm import Session
from DataDictionaryAdminApp.core.database import get_db

router = APIRouter(prefix='/system', tags=['System'])

@router.get('/environment')
def environment_details(x_app_environment: str | None = Header(default=None)):
    settings = get_settings()
    cfg = settings.database_config(x_app_environment)
    return {
        'application_name': settings.app_name,
        'environment': cfg['environment'],
        'server': cfg['server'],
        'database': cfg['database'],
        'windows_auth': cfg['windows_auth'],
        'database_enabled': cfg['enabled'],
        'api_base_url': settings.api_base_url,
        's3_configured': bool(settings.effective_s3_bucket_name and settings.effective_s3_endpoint_url),
        'available_environments': settings.available_environments(),
    }


@router.get('/env', include_in_schema=False)
def environment_details_legacy(x_app_environment: str | None = Header(default=None)):
    return environment_details(x_app_environment)


@router.get('/database-diagnostic')
def database_diagnostic(db: Session = Depends(get_db)):
    """Confirms the active connection and SQL Server database context."""
    try:
        row = db.execute(text("SELECT DB_NAME() AS database_name, @@SERVERNAME AS server_name")).mappings().one()
        return {"status": "UP", "database": row["database_name"], "server": row["server_name"]}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database connection diagnostic failed: {exc}") from exc
