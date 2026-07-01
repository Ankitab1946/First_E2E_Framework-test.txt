from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Header
import logging
import traceback
from sqlalchemy import text
from sqlalchemy.orm import Session
from DataDictionaryAdminApp.service.excel_service import ExcelService
from DataDictionaryAdminApp.service.data_dictionary_service import DataDictionaryService
from DataDictionaryAdminApp.api.schemas_api import AttributeUpsert
from DataDictionaryAdminApp.core.database import get_db
from DataDictionaryAdminApp.utils.security import current_user, is_admin_role

router=APIRouter(prefix='/master-upload',tags=['Master Dictionary Upload'])
logger = logging.getLogger(__name__)

def _clean(value):
    if value is None: return None
    text_value=str(value).strip()
    return None if text_value.lower() in ('', 'nan', 'none') else text_value

def _get(row, *prefixes):
    for column, value in row.items():
        name=str(column).strip().lower().replace('_',' ')
        if any(name.startswith(prefix.lower()) for prefix in prefixes):
            return _clean(value)
    return None

def _payload(row):
    required=[]
    if str(_get(row,'Required by corporates') or '').upper()=='Y': required.append('Corporates')
    if str(_get(row,'Required by banks') or '').upper()=='Y': required.append('FI Banks')
    if str(_get(row,'Required by insurance') or '').upper()=='Y': required.append('FI Insurance')
    if str(_get(row,'Required by downstream') or '').upper()=='Y': required.append('Zeus Downstream')
    calculation_logic=_get(row,'Calculation Logic')
    return AttributeUpsert(
        prj_id=_get(row,'PRJ ID') or '',
        prj_attribute_name=_get(row,'PRJ Attribute Name') or '',
        prj_attribute_description=_get(row,'PRJ Attribute Description'),
        prj_physical_attribute_name=_get(row,'PRJ Physical Attribute Name'),
        where_in_financial_statement=_get(row,'Where in financial statement'),
        version_update=_get(row,'Version Update'),
        calculated_or_reported=_get(row,'Calculated or Reported'),
        calculation_logic=calculation_logic,
        calculation_logic_details=_get(row,'Calculation Logic Details'),
        sign_flipping_value=_get(row,'Sign Flipping'),
        mapping_type=_get(row,'Mapping Type'),
        sp_standardisation_dataitem_id=_get(row,'S&P Standradisation','S&P Standardisation'),
        sp_as_reported_dataitem_logic=_get(row,'S&P As-Reported'),
        calculated_in_cfv=_get(row,'Calculated in CFV'),
        editable_in_historicals=_get(row,'Editable in Historicals'),
        required_portfolios=required,
        editable=(_get(row,'Editable?') or '').strip().upper() if _get(row,'Editable?') is not None else None,
        symbol=_get(row,'Percentage(%) / Ratio(X)','Percentage'),
    )

@router.post('/preview')
async def preview_master(file:UploadFile=File(...), x_app_role: str | None = Header(None)):
    if not is_admin_role(x_app_role): raise HTTPException(403, 'Admin role is required for Master Dictionary upload.')
    try:
        df=ExcelService().read_master_workbook(await file.read())
        return {'sheet':'PRJ Data Dictionary Mapping','row_count':len(df),'columns':[str(c) for c in df.columns],'preview':df.head(200).where(df.notna(),None).to_dict(orient='records')}
    except Exception as e: raise HTTPException(400,f'Unable to parse Master Dictionary workbook: {e}')

@router.post('/delta')
async def delta_master(file:UploadFile=File(...), db:Session=Depends(get_db), x_app_role: str | None = Header(None)):
    if not is_admin_role(x_app_role): raise HTTPException(403, 'Admin role is required for Master Dictionary upload.')
    try:
        df=ExcelService().read_master_workbook(await file.read())
        ids={str(r[0]) for r in db.execute(text('SELECT prj_id FROM dbo.prj_attribute_master_test')).all()}
        parsed=[_payload(row) for _,row in df.iterrows()]
        valid=[x for x in parsed if x.prj_id and x.prj_attribute_name]
        return {'rows':len(df),'new':sum(x.prj_id not in ids for x in valid),'update_candidates':sum(x.prj_id in ids for x in valid),'invalid_rows':len(parsed)-len(valid)}
    except Exception as e: raise HTTPException(400,f'Unable to compare Master Dictionary workbook: {e}')

@router.post('/finalize')
async def finalize_master(file:UploadFile=File(...), user:str|None=Query(None), db:Session=Depends(get_db), x_app_role: str | None = Header(None)):
    """Finalize Master Dictionary upload and always return row-level diagnostic details."""
    if not is_admin_role(x_app_role):
        raise HTTPException(403, 'Admin role is required for Master Dictionary upload.')
    try:
        content = await file.read()
        df = ExcelService().read_master_workbook(content)
        service=DataDictionaryService(db)
        inserted=updated=0
        rejected=[]
        for row_no,(_,row) in enumerate(df.iterrows(), start=4):
            row_input={str(k): _clean(v) for k,v in row.to_dict().items()}
            try:
                payload=_payload(row)
                if not payload.prj_id or not payload.prj_attribute_name:
                    rejected.append({'row':row_no,'prj_id':payload.prj_id or None,'error_type':'ValidationError','reason':'PRJ ID and PRJ Attribute Name are mandatory.','input':row_input})
                    continue
                exists=service.repo.get_attribute(payload.prj_id) is not None
                service.upsert_attribute(payload,current_user(user),source='MASTER_EXCEL_UPLOAD')
                if exists: updated += 1
                else: inserted += 1
            except Exception as exc:
                db.rollback()
                logger.exception('Master Dictionary upload failed at Excel row %s', row_no)
                rejected.append({
                    'row':row_no,
                    'prj_id':row_input.get('PRJ ID') or row_input.get('PRJID'),
                    'error_type':type(exc).__name__,
                    'reason':str(getattr(exc, 'orig', exc)),
                    'input':row_input,
                    'trace_hint':'See FastAPI console output for full traceback.',
                })
        return {
            'status':'completed' if not rejected else 'completed_with_rejections',
            'inserted':inserted, 'updated':updated,
            'rejected_count':len(rejected), 'rejected':rejected,
        }
    except Exception as exc:
        db.rollback()
        logger.exception('Master Dictionary finalize failed before row processing')
        raise HTTPException(500, {
            'message':'Master Dictionary upload failed before row processing.',
            'error_type':type(exc).__name__,
            'reason':str(getattr(exc, 'orig', exc)),
            'trace_hint':'See FastAPI console output for full traceback.',
        })

