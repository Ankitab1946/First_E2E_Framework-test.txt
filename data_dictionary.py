from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File, Query
import logging
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from DataDictionaryAdminApp.core.database import get_db
from DataDictionaryAdminApp.api.schemas_api import AttributeUpsert, FilterRequest, PromptUpsert
from DataDictionaryAdminApp.service.data_dictionary_service import DataDictionaryService
from DataDictionaryAdminApp.repositories.data_dictionary_repository import DataDictionaryRepository
from DataDictionaryAdminApp.service.excel_service import ExcelService
from DataDictionaryAdminApp.utils.security import current_user

logger = logging.getLogger(__name__)
router=APIRouter(prefix='/data-dictionary',tags=['Data Dictionary'])
def serial(row): return {c.name:getattr(row,c.name) for c in row.__table__.columns}
def _filter_rows(request: FilterRequest, db: Session):
    try:
        return DataDictionaryRepository(db).list_attributes_dict(request)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception('Data Dictionary filter query failed')
        return JSONResponse(
            status_code=200,
            content=[],
            headers={
                'X-Data-Dictionary-Warning': 'Database query failed. Run 003_validate_final_schema.sql in the database selected in the sidebar.',
                'X-Data-Dictionary-Error': str(getattr(exc, 'orig', exc))[:1500],
            },
        )

@router.post('/attributes/filter', include_in_schema=False)
def filter_rows_compat(request:FilterRequest,db:Session=Depends(get_db)):
    return _filter_rows(request, db)

@router.post('/filter')
def filter_rows(request:FilterRequest,db:Session=Depends(get_db)):
    return _filter_rows(request, db)
@router.get('/attributes/{prj_id}')
def get_attribute(prj_id: str, db: Session = Depends(get_db)):
    row = DataDictionaryRepository(db).get_attribute_projection(prj_id)
    if not row:
        raise HTTPException(404, 'Attribute not found')
    return row

@router.post('/attributes')
def create_attribute(payload: AttributeUpsert, user: str | None = Query(None), db: Session = Depends(get_db)):
    try:
        return serial(DataDictionaryService(db).upsert_attribute(payload, current_user(user)))
    except Exception as exc:
        db.rollback()
        logger.exception('Create Attribute failed')
        raise HTTPException(400, f'Unable to create attribute: {getattr(exc, "orig", exc)}') from exc
@router.put('/attributes/{prj_id}')
def update_attribute(prj_id: str, payload: AttributeUpsert, user: str | None = Query(None), db: Session = Depends(get_db)):
    if prj_id != payload.prj_id:
        raise HTTPException(400, 'PRJ ID cannot be changed')
    try:
        return serial(DataDictionaryService(db).upsert_attribute(payload, current_user(user)))
    except Exception as exc:
        db.rollback()
        logger.exception('Update Attribute failed')
        raise HTTPException(400, f'Unable to update attribute: {getattr(exc, "orig", exc)}') from exc
@router.delete('/attributes/{prj_id}')
def delete_attribute(prj_id:str,user:str|None=Query(None),db:Session=Depends(get_db)):
    row=DataDictionaryService(db).soft_delete_attribute(prj_id,current_user(user));
    if not row: raise HTTPException(404,'Attribute not found')
    return {'status':'soft_deleted','prj_id':prj_id}
@router.post('/attributes/{prj_id}/reactivate')
def reactivate(prj_id:str,user:str|None=Query(None),db:Session=Depends(get_db)):
    row=DataDictionaryService(db).reactivate_attribute(prj_id,current_user(user));
    if not row: raise HTTPException(404,'Attribute not found')
    return serial(row)
@router.get('/latest/download', include_in_schema=False)
def download_latest_compat(db:Session=Depends(get_db)):
    return download_latest(db)

@router.get('/download-latest')
def download_latest(db:Session=Depends(get_db)):
    try:
        rows = DataDictionaryRepository(db).list_attributes_dict(FilterRequest())
        payload = ExcelService().build_latest_dicts(rows)
        return Response(payload, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition':'attachment; filename=data_dictionary_latest.xlsx'})
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(503, 'Unable to generate the latest workbook because the selected database schema is unavailable. Run src/DataDictionaryAdminApp/sql/001_create_tables.sql for the selected environment.') from exc
@router.post('/prompts')
def create_prompt(payload:PromptUpsert,user:str|None=Query(None),db:Session=Depends(get_db)):
    try:return serial(DataDictionaryService(db).upsert_prompt(payload,current_user(user)))
    except ValueError as e:raise HTTPException(400,str(e))
@router.put('/prompts/{prompt_id}')
def update_prompt(prompt_id:int,payload:PromptUpsert,user:str|None=Query(None),db:Session=Depends(get_db)):
    try:return serial(DataDictionaryService(db).upsert_prompt(payload,current_user(user),prompt_id))
    except ValueError as e:raise HTTPException(400,str(e))
@router.delete('/prompts/{prompt_id}')
def delete_prompt(prompt_id:int,user:str|None=Query(None),db:Session=Depends(get_db)):
    if not DataDictionaryService(db).soft_delete_prompt(prompt_id,current_user(user)):raise HTTPException(404,'Prompt not found')
    return {'status':'soft_deleted','prompt_id':prompt_id}
@router.post('/prompts/sheets')
async def prompt_sheets(file:UploadFile=File(...)): return {'sheets':ExcelService().sheets(await file.read())}
