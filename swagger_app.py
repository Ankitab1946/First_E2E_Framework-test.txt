# from fastapi import FastAPI, Header, HTTPException, UploadFile, File, Form
# from fastapi.middleware.cors import CORSMiddleware

# from DataDictionaryAdminApp.config import get_settings
# from DataDictionaryAdminApp.api.schemas_api import AttributePayload, AuditFilterRequest, DictionaryFilterRequest, UiDisplayPayload, BusinessRulePayload, PromptPayload
# from DataDictionaryAdminApp.service.audit_service import AuditService
# from DataDictionaryAdminApp.service.dictionary_service import DictionaryService
# from DataDictionaryAdminApp.service.finalization_service import FinalizationService
# from DataDictionaryAdminApp.service.s3_export_service import S3ExportService
# from DataDictionaryAdminApp.service.configuration_service import ConfigurationService
# from DataDictionaryAdminApp.utils.constants import PORTFOLIO_OPTIONS, SECTION_OPTIONS

# settings = get_settings()

# app = FastAPI(
#     title="Data Dictionary Admin API",
#     description="Swagger API for Data Dictionary filters, CRUD, audit search, soft-delete/reactivation, and complete S3 relational snapshot export.",
#     version="1.1.0",
# )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# def _user_id(x_user_id: str | None = Header(default=None)) -> str:
#     return x_user_id or settings.default_user or "sysuser"


# @app.get("/api/v1/health")
# def health_check():
#     return {
#         "status": "UP",
#         "environment": settings.selected_environment,
#         "database_enabled": settings.enable_db,
#         "database": settings.sqlserver_database,
#         "server": settings.sqlserver_server,
#     }


# @app.get("/api/v1/filters/options")
# def filter_options():
#     options = DictionaryService().get_filter_options()
#     return {
#         "portfolio_options": PORTFOLIO_OPTIONS,
#         "section_options": SECTION_OPTIONS,
#         **options,
#     }


# @app.post("/api/v1/dictionary/filter")
# def filter_dictionary(payload: DictionaryFilterRequest):
#     try:
#         rows = DictionaryService().filter_records(payload.model_dump())
#         return {"records": rows, "count": len(rows), "filters": payload.model_dump()}
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc


# @app.post("/api/v1/dictionary/attributes")
# def create_attribute(payload: AttributePayload, x_user_id: str | None = Header(default=None)):
#     try:
#         result = FinalizationService().create_attribute(payload.model_dump(), user_id=_user_id(x_user_id))
#         return result
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc


# @app.put("/api/v1/dictionary/attributes/{prj_id}")
# def update_attribute(prj_id: str, payload: AttributePayload, x_user_id: str | None = Header(default=None)):
#     try:
#         data = payload.model_dump()
#         data["prj_id"] = prj_id
#         result = FinalizationService().update_attribute(data, user_id=_user_id(x_user_id))
#         return result
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc


# @app.delete("/api/v1/dictionary/attributes/{prj_id}")
# def soft_delete_attribute(prj_id: str, x_user_id: str | None = Header(default=None)):
#     try:
#         result = FinalizationService().soft_delete_attribute(prj_id, user_id=_user_id(x_user_id))
#         return result
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc


# @app.post("/api/v1/dictionary/attributes/{prj_id}/reactivate")
# def reactivate_attribute(prj_id: str, x_user_id: str | None = Header(default=None)):
#     try:
#         result = FinalizationService().reactivate_attribute(prj_id, user_id=_user_id(x_user_id))
#         return result
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc


# @app.get("/api/v1/dictionary/soft-deleted")
# def soft_deleted_records():
#     try:
#         rows = DictionaryService().get_soft_deleted_records()
#         return {"records": rows, "count": len(rows)}
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc


# @app.post("/api/v1/audit/filter")
# def filter_audit(payload: AuditFilterRequest):
#     try:
#         rows = AuditService().filter_audit(payload.model_dump())
#         return {"records": rows, "count": len(rows), "filters": payload.model_dump()}
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc


# @app.post("/api/v1/s3/export")
# def export_s3(x_user_id: str | None = Header(default=None)):
#     try:
#         return S3ExportService().export_all_mutable_tables(user_id=_user_id(x_user_id))
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc


# @app.post("/api/v1/configuration/bootstrap-portfolios")
# def bootstrap_portfolios(x_user_id: str | None = Header(default=None)):
#     try:
#         return ConfigurationService().bootstrap_portfolios(_user_id(x_user_id))
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc

# @app.post("/api/v1/ui-display-config")
# def save_ui_display(payload: UiDisplayPayload, x_user_id: str | None = Header(default=None)):
#     try:
#         return ConfigurationService().save_display(payload.model_dump(), _user_id(x_user_id))
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc

# @app.get("/api/v1/ui-display-config")
# def list_ui_displays(active_only: bool = True):
#     try:
#         rows=ConfigurationService().list_displays(active_only)
#         return {"records":rows,"count":len(rows)}
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc

# @app.delete("/api/v1/ui-display-config/{display_id}")
# def delete_ui_display(display_id: int, x_user_id: str | None = Header(default=None)):
#     try:
#         return ConfigurationService().soft_delete_display(display_id, _user_id(x_user_id))
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc

# @app.post("/api/v1/business-rules")
# def save_business_rule(payload: BusinessRulePayload, x_user_id: str | None = Header(default=None)):
#     try:
#         return ConfigurationService().save_rule(payload.model_dump(), _user_id(x_user_id))
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc

# @app.get("/api/v1/prompts")
# def list_prompts(active_only: bool = True):
#     try:
#         rows=ConfigurationService().list_prompts(active_only)
#         return {"records":rows,"count":len(rows)}
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc

# @app.post("/api/v1/prompts")
# def save_prompt(payload: PromptPayload, x_user_id: str | None = Header(default=None)):
#     try:
#         return ConfigurationService().save_prompt(payload.model_dump(), _user_id(x_user_id))
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc

# @app.delete("/api/v1/prompts/{prompt_id}")
# def delete_prompt(prompt_id: int, x_user_id: str | None = Header(default=None)):
#     try:
#         return ConfigurationService().soft_delete_prompt(prompt_id, _user_id(x_user_id))
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc

# @app.post("/api/v1/prompts/upload")
# async def upload_prompts(file: UploadFile = File(...), sheets: str | None = Form(default=None), x_user_id: str | None = Header(default=None)):
#     try:
#         selected=[x.strip() for x in sheets.split(',')] if sheets else None
#         return ConfigurationService().upload_prompts(await file.read(), selected, _user_id(x_user_id))
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc


# @app.post('/api/v1/ui-display-config/{display_id}/reactivate')
# def reactivate_ui_display(display_id: int, x_user_id: str | None = Header(default=None)):
#     try: return ConfigurationService().reactivate_display(display_id, _user_id(x_user_id))
#     except Exception as exc: raise HTTPException(status_code=500, detail=str(exc)) from exc

# @app.delete('/api/v1/business-rules/{rule_id}')
# def delete_business_rule(rule_id: int, x_user_id: str | None = Header(default=None)):
#     try: return ConfigurationService().soft_delete_rule(rule_id, _user_id(x_user_id))
#     except Exception as exc: raise HTTPException(status_code=500, detail=str(exc)) from exc

# @app.post('/api/v1/business-rules/{rule_id}/reactivate')
# def reactivate_business_rule(rule_id: int, x_user_id: str | None = Header(default=None)):
#     try: return ConfigurationService().reactivate_rule(rule_id, _user_id(x_user_id))
#     except Exception as exc: raise HTTPException(status_code=500, detail=str(exc)) from exc

# @app.post('/api/v1/prompts/{prompt_id}/reactivate')
# def reactivate_prompt(prompt_id: int, x_user_id: str | None = Header(default=None)):
#     try: return ConfigurationService().reactivate_prompt(prompt_id, _user_id(x_user_id))
#     except Exception as exc: raise HTTPException(status_code=500, detail=str(exc)) from exc


from fastapi import FastAPI
from DataDictionaryAdminApp.api.routers import (
    data_dictionary, audit, system, lookups, prompts, master_upload, prompt_upload,
    portfolio_reference, history, s3, admin,
)

app=FastAPI(
    title='Data Dictionary Admin API',
    version='2.1.0',
    description=(
        'API-first administration for the six approved Data Dictionary tables. '
        'Route groups are separated for master data, prompt data, uploads, audit/history, '
        'portfolio reference, S3 exports and administration.'
    ),
)
for router in (data_dictionary.router, master_upload.router, prompts.router, prompt_upload.router,
               portfolio_reference.router, lookups.router, audit.router, history.router,
               s3.router, admin.router, system.router):
    app.include_router(router,prefix='/api/v1')

@app.get('/health', tags=['System'])
def health():
    return {'status': 'UP', 'api_version': app.version, 'api_base_path': '/api/v1'}


@app.get('/api/v1/health', tags=['System'])
def v1_health():
    return {'status': 'UP', 'api_version': app.version, 'api_base_path': '/api/v1'}


@app.get('/api/v1', tags=['System'])
def api_root():
    return {
        'status': 'UP',
        'api_version': app.version,
        'swagger': '/docs',
        'environment_endpoint': '/api/v1/system/environment',
        'route_groups': [
            'data-dictionary', 'master-upload', 'prompts', 'prompt-upload',
            'portfolio-reference', 'lookups', 'audit', 'history', 's3', 'admin', 'system',
        ],
    }
