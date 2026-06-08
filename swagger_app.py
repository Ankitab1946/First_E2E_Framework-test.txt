from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.schemas_api import AttributePayload, AuditFilterRequest, DictionaryFilterRequest
from app.services.audit_service import AuditService
from app.services.dictionary_service import DictionaryService
from app.services.finalization_service import FinalizationService
from app.services.s3_export_service import S3ExportService
from app.utils.constants import PORTFOLIO_OPTIONS, SECTION_OPTIONS

settings = get_settings()


def apply_request_runtime_config(
    x_db_auth_mode: str | None = Header(default=None),
    x_krb5_config_path: str | None = Header(default=None),
    x_krb5_keytab_path: str | None = Header(default=None),
    x_krb5_principal: str | None = Header(default=None),
    x_krb5_cache_path: str | None = Header(default=None),
    x_krb5_kinit_enabled: str | None = Header(default=None),
) -> None:
    """Allow Streamlit runtime DB-auth selection to drive API requests.

    The API still defaults to .env values. These headers are optional and are
    mainly used when Streamlit and FastAPI are run together locally or on the
    same app host.
    """
    import os

    if x_db_auth_mode:
        auth_mode = x_db_auth_mode.strip().lower()
        if auth_mode in {"windows", "keytab", "sql"}:
            os.environ["SQLSERVER_AUTH_MODE"] = auth_mode
            os.environ["SQLSERVER_WINDOWS_AUTH"] = "true" if auth_mode in {"windows", "keytab"} else "false"

    optional_values = {
        "KRB5_CONFIG_PATH": x_krb5_config_path,
        "KRB5_KEYTAB_PATH": x_krb5_keytab_path,
        "KRB5_PRINCIPAL": x_krb5_principal,
        "KRB5_CACHE_PATH": x_krb5_cache_path,
    }
    for key, value in optional_values.items():
        if value not in (None, ""):
            os.environ[key] = value

    if x_krb5_kinit_enabled not in (None, ""):
        os.environ["KRB5_KINIT_ENABLED"] = "true" if str(x_krb5_kinit_enabled).lower() in {"true", "1", "yes", "y"} else "false"

    get_settings.cache_clear()


app = FastAPI(
    dependencies=[Depends(apply_request_runtime_config)],
    title="Data Dictionary Admin API",
    description="Swagger API for Data Dictionary filters, CRUD, audit search, soft-delete/reactivation, and S3 export.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _user_id(x_user_id: str | None = Header(default=None)) -> str:
    return x_user_id or settings.default_user or "sysuser"


@app.get("/api/v1/health")
def health_check():
    live_settings = get_settings()
    return {
        "status": "UP",
        "environment": live_settings.selected_environment,
        "database_enabled": live_settings.enable_db,
        "database": live_settings.sqlserver_database,
        "server": live_settings.sqlserver_server,
        "db_auth_mode": live_settings.effective_sql_auth_mode,
    }


@app.get("/api/v1/filters/options")
def filter_options():
    options = DictionaryService().get_filter_options()
    return {
        "portfolio_options": PORTFOLIO_OPTIONS,
        "section_options": SECTION_OPTIONS,
        **options,
    }


@app.post("/api/v1/dictionary/filter")
def filter_dictionary(payload: DictionaryFilterRequest):
    try:
        rows = DictionaryService().filter_records(payload.model_dump())
        return {"records": rows, "count": len(rows), "filters": payload.model_dump()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/dictionary/attributes")
def create_attribute(payload: AttributePayload, x_user_id: str | None = Header(default=None)):
    try:
        result = FinalizationService().create_attribute(payload.model_dump(), user_id=_user_id(x_user_id))
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.put("/api/v1/dictionary/attributes/{prj_id}")
def update_attribute(prj_id: str, payload: AttributePayload, x_user_id: str | None = Header(default=None)):
    try:
        data = payload.model_dump()
        data["prj_id"] = prj_id
        result = FinalizationService().update_attribute(data, user_id=_user_id(x_user_id))
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/api/v1/dictionary/attributes/{prj_id}")
def soft_delete_attribute(prj_id: str, x_user_id: str | None = Header(default=None)):
    try:
        result = FinalizationService().soft_delete_attribute(prj_id, user_id=_user_id(x_user_id))
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/dictionary/attributes/{prj_id}/reactivate")
def reactivate_attribute(prj_id: str, x_user_id: str | None = Header(default=None)):
    try:
        result = FinalizationService().reactivate_attribute(prj_id, user_id=_user_id(x_user_id))
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/v1/dictionary/soft-deleted")
def soft_deleted_records():
    try:
        rows = DictionaryService().get_soft_deleted_records()
        return {"records": rows, "count": len(rows)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/audit/filter")
def filter_audit(payload: AuditFilterRequest):
    try:
        rows = AuditService().filter_audit(payload.model_dump())
        return {"records": rows, "count": len(rows), "filters": payload.model_dump()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/s3/export")
def export_s3(x_user_id: str | None = Header(default=None)):
    try:
        return S3ExportService().export_four_files(user_id=_user_id(x_user_id))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
