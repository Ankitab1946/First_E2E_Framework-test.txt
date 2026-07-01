from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from DataDictionaryAdminApp.service.excel_service import ExcelService
from DataDictionaryAdminApp.core.database import get_db
from DataDictionaryAdminApp.service.data_dictionary_service import DataDictionaryService
from DataDictionaryAdminApp.api.schemas_api import PromptUpsert
from DataDictionaryAdminApp.utils.security import current_user

router=APIRouter(prefix='/prompt-upload',tags=['Prompt Upload'])

def _load(content: bytes, sheet_name: str):
    raw=ExcelService().read_prompt_workbook(content,sheet_name)
    return ExcelService.normalise_prompt_columns(raw)[0]

@router.post('/sheets')
async def sheets(file:UploadFile=File(...)):
    return {'sheets':ExcelService().sheets(await file.read())}

@router.post('/preview')
async def preview(file:UploadFile=File(...),sheet_name:str=Form(...)):
    try:
        content = await file.read()
        raw = ExcelService().read_prompt_workbook(content, sheet_name)
        df, mapping = ExcelService.normalise_prompt_columns(raw)
        return {
            'sheet': sheet_name,
            'row_count': len(df),
            'columns': list(df.columns),
            'column_mapping': mapping,
            'preview': df.head(200).where(df.notna(), None).to_dict(orient='records'),
        }
    except Exception as e:
        raise HTTPException(400, f'Unable to parse Prompt workbook: {e}')

@router.post('/delta')
async def delta(file:UploadFile=File(...),sheet_name:str=Form(...),db:Session=Depends(get_db)):
    try:
        df=_load(await file.read(),sheet_name)
        valid={r[0] for r in db.execute(text('SELECT prj_id FROM dbo.prj_attribute_master_test')).all()}
        invalid=sorted(set(df.prj_id)-valid)
        existing={r[0] for r in db.execute(text('SELECT DISTINCT prj_id FROM dbo.prj_scanning_prompt_reference_test WHERE is_active=1')).all()}
        return {'sheet':sheet_name,'rows':len(df),'new':int((~df.prj_id.isin(existing)).sum()),'update_candidates':int(df.prj_id.isin(existing).sum()),'invalid_prj_ids':invalid,'valid_rows':int(df.prj_id.isin(valid).sum()),'preview':df.head(200).where(df.notna(),None).to_dict(orient='records')}
    except Exception as e: raise HTTPException(400,f'Unable to calculate prompt delta: {e}')

@router.post('/finalize')
async def finalize(file: UploadFile = File(...), sheet_name: str = Form(...), target_scope: str | None = Form(None), user: str | None = Query(None), db: Session = Depends(get_db)):
    """Upserts selected workbook rows into the existing prompt placeholder for every active scope."""
    try:
        df = _load(await file.read(), sheet_name)
        valid = {str(r[0]) for r in db.execute(text('SELECT prj_id FROM dbo.prj_attribute_master_test WHERE is_active=1')).all()}
        service = DataDictionaryService(db)
        inserted = updated = 0; rejected = []
        for excel_row, row in df.iterrows():
            prj = str(row.get('prj_id') or '').strip()
            if not prj or prj.lower() == 'nan' or prj not in valid:
                rejected.append({'row': int(excel_row)+1, 'prj_id':prj or None, 'reason':'PRJ ID does not exist in active prj_attribute_master_test'})
                continue
            try:
                def value(name):
                    v=row.get(name)
                    return None if v is None or str(v).strip().lower() in {'','nan','none'} else str(v).strip()
                scopes = service.active_scopes(prj)
                # Resolve the target scope from the Excel Required By Scope column first,
                # then the UI selection. A multi-scope PRJ must never be updated across
                # all scopes by accident.
                requested_scope = value('required_by_scope') or (target_scope or '').strip() or None
                if requested_scope:
                    requested_norm = requested_scope.strip().lower()
                    matching = [scope for scope in scopes if (
                        ('fi banks' if str(scope['port_name']).lower() == 'fi' and str(scope['sector_name']).lower() == 'banks'
                         else 'fi insurance' if str(scope['port_name']).lower() == 'fi' and str(scope['sector_name']).lower() == 'insurance'
                         else 'corporates' if str(scope['port_name']).lower() == 'corporate'
                         else 'zeus downstream' if str(scope['port_name']).lower() == 'zeus downstream'
                         else str(scope['port_name'])).lower() == requested_norm)]
                    if not matching:
                        raise ValueError(f"No active scope matching '{requested_scope}' exists for PRJ ID {prj}")
                    scope = matching[0]
                elif len(scopes) == 1:
                    scope = scopes[0]
                else:
                    raise ValueError(f"PRJ ID {prj} has multiple active scopes. Select Target Portfolio/Scope or add a Required By Scope column to the workbook.")
                existing_count = db.execute(text('SELECT COUNT(*) FROM dbo.prj_scanning_prompt_reference_test WHERE prj_id=:prj AND scope_id=:scope AND is_active=1'), {'prj':prj, 'scope':int(scope['scope_id'])}).scalar() or 0
                display = value('display_order')
                payload=PromptUpsert(scope_id=int(scope['scope_id']), prj_id=prj, attribute_name=value('attribute_name'),display_order=int(float(display)) if display else None,
                    section=value('section'),sub_section=value('sub_section'),data_type=value('data_type'),calculated_or_reported=value('calculated_or_reported'),calculation_logic=value('calculation_logic'),segment=value('segment'),attribute_description=value('attribute_description'), required_by_scope=requested_scope)
                service.upsert_prompt(payload,current_user(user),source='PROMPT_BULK_UPLOAD')
                if existing_count: updated += 1
                else: inserted += 1
            except Exception as exc:
                db.rollback(); rejected.append({'row':int(excel_row)+1,'prj_id':prj,'reason':f'{type(exc).__name__}: {getattr(exc,"orig",exc)}'})
        return {'status':'completed' if not rejected else 'completed_with_rejections','inserted':inserted,'updated':updated,'rejected':rejected,'rejected_count':len(rejected)}
    except Exception as exc:
        db.rollback(); raise HTTPException(400, f'Prompt bulk commit failed: {type(exc).__name__}: {getattr(exc,"orig",exc)}')

@router.post('/generate-sql')
async def generate_sql(file: UploadFile = File(...), sheet_name: str = Form(...), mode: str = Query('INSERT_ONLY')):
    """Generate reviewable SQL only. It never executes the generated script."""
    try:
        df = _load(await file.read(), sheet_name)
        statements = ["-- Generated by Data Dictionary Admin App", f"-- Mode: {mode}", "SET NOCOUNT ON;", ""]
        for _, row in df.iterrows():
            prj = str(row.get('prj_id', '')).replace("'", "''")
            name = str(row.get('attribute_name', '') or '').replace("'", "''")
            description = str(row.get('attribute_description', '') or '').replace("'", "''")
            if mode.upper() == 'MERGE':
                statements.append("MERGE dbo.prj_scanning_prompt_reference_test AS target USING (SELECT '" + prj + "' AS prj_id, '" + name + "' AS attribute_name) AS source ON target.prj_id=source.prj_id AND ISNULL(target.attribute_name,'')=source.attribute_name WHEN MATCHED THEN UPDATE SET attribute_description='" + description + "', updated_at=GETDATE() WHEN NOT MATCHED THEN INSERT (prj_id,attribute_name,attribute_description,is_active,created_at,updated_at,created_by,updated_by) VALUES ('" + prj + "','" + name + "','" + description + "',1,GETDATE(),GETDATE(),'sysuser','sysuser');")
            else:
                statements.append("INSERT INTO dbo.prj_scanning_prompt_reference_test (prj_id,attribute_name,attribute_description,is_active,created_at,updated_at,created_by,updated_by) SELECT '" + prj + "','" + name + "','" + description + "',1,GETDATE(),GETDATE(),'sysuser','sysuser' WHERE NOT EXISTS (SELECT 1 FROM dbo.prj_scanning_prompt_reference_test WHERE prj_id='" + prj + "' AND ISNULL(attribute_name,'')='" + name + "' AND is_active=1);")
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse('\n'.join(statements), media_type='text/sql', headers={'Content-Disposition': 'attachment; filename=prompt_upload.sql'})
    except Exception as exc:
        raise HTTPException(400, f'Unable to generate SQL: {exc}')
