from __future__ import annotations

import logging
import math
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from DataDictionaryAdminApp.api.schemas_api import AttributeUpsert
from DataDictionaryAdminApp.core.database import get_db
from DataDictionaryAdminApp.service.data_dictionary_service import DataDictionaryService
from DataDictionaryAdminApp.service.excel_service import ExcelService
from DataDictionaryAdminApp.utils.security import current_user, is_admin_role

router = APIRouter(prefix='/master-upload', tags=['Master Dictionary Upload'])
logger = logging.getLogger(__name__)


def _clean(value: Any):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, 'item'):
        try:
            return _clean(value.item())
        except Exception:
            pass
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    text_value = str(value).replace('\xa0', ' ').replace('\u200b', '').strip()
    return None if text_value.lower() in ('', 'nan', 'none', 'nat', '<na>') else text_value


def _safe_json(value: Any):
    if isinstance(value, dict):
        return {str(k): _safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_json(v) for v in value]
    return _clean(value)


def _header(value: Any) -> str:
    return ''.join(ch for ch in str(value or '').replace('\xa0', ' ').replace('\u200b', '').lower() if ch.isalnum())


def _get(row, *prefixes):
    normalized = [(_header(column), value) for column, value in row.items()]
    for prefix in prefixes:
        expected = _header(prefix)
        for name, value in normalized:
            if name.startswith(expected):
                return _clean(value)
    return None


def _payload(row):
    required = []
    if str(_get(row, 'Required by corporates') or '').upper() in {'Y', 'YES', '1', 'TRUE'}:
        required.append('Corporates')
    if str(_get(row, 'Required by banks') or '').upper() in {'Y', 'YES', '1', 'TRUE'}:
        required.append('FI Banks')
    if str(_get(row, 'Required by insurance') or '').upper() in {'Y', 'YES', '1', 'TRUE'}:
        required.append('FI Insurance')
    if str(_get(row, 'Required by downstream', 'Required by zeus downstream') or '').upper() in {'Y', 'YES', '1', 'TRUE'}:
        required.append('Zeus Downstream')
    editable = _get(row, 'Editable')
    return AttributeUpsert(
        prj_id=_get(row, 'PRJ ID') or '',
        prj_attribute_name=_get(row, 'PRJ Attribute Name') or '',
        prj_attribute_description=_get(row, 'PRJ Attribute Description'),
        prj_physical_attribute_name=_get(row, 'PRJ Physical Attribute Name'),
        where_in_financial_statement=_get(row, 'Where in financial statement'),
        version_update=_get(row, 'Version Update'),
        calculated_or_reported=_get(row, 'Calculated or Reported'),
        calculation_logic=_get(row, 'Calculation Logic'),
        calculation_logic_details=_get(row, 'Calculation Logic Details'),
        sign_flipping_value=_get(row, 'Sign Flipping'),
        mapping_type=_get(row, 'Mapping Type'),
        sp_standardisation_dataitem_id=_get(row, 'S&P Standradisation', 'S&P Standardisation'),
        sp_as_reported_dataitem_logic=_get(row, 'S&P As-Reported'),
        calculated_in_cfv=_get(row, 'Calculated in CFV'),
        editable_in_historicals=_get(row, 'Editable in Historicals'),
        required_portfolios=required,
        editable=str(editable).strip().upper() if editable is not None else None,
        symbol=_get(row, 'Percentage(%) / Ratio(X)', 'Percentage'),
    )


def _admin(role: str | None):
    if not is_admin_role(role):
        raise HTTPException(403, 'Admin role is required for Master Dictionary upload.')


def _failure(stage: str, exc: Exception, *, row: int | None = None, prj_id: str | None = None, input_row: dict | None = None):
    logger.exception('Master Dictionary %s failure', stage)
    result = {
        'status': 'failed',
        'stage': stage,
        'error_type': type(exc).__name__,
        'reason': str(getattr(exc, 'orig', exc)),
        'trace_hint': 'Check the FastAPI console traceback. This response contains the direct backend reason.',
    }
    if row is not None:
        result['row'] = row
    if prj_id:
        result['prj_id'] = prj_id
    if input_row is not None:
        result['input'] = _safe_json(input_row)
    return result


@router.get('/diagnostic')
def diagnostic(db: Session = Depends(get_db)):
    """Connectivity + final-table diagnostic used before workbook finalization."""
    try:
        identity = db.execute(text('SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name')).mappings().one()
        count = db.execute(text('SELECT COUNT(*) AS row_count FROM dbo.prj_attribute_master_test')).scalar_one()
        return {'connected': True, 'server': identity['server_name'], 'database': identity['database_name'], 'master_row_count': int(count)}
    except Exception as exc:
        db.rollback()
        return _failure('database_diagnostic', exc)


@router.post('/preview')
async def preview_master(file: UploadFile = File(...), x_app_role: str | None = Header(None)):
    _admin(x_app_role)
    try:
        df = ExcelService().read_master_workbook(await file.read())
        return {
            'status': 'ok',
            'sheet': 'PRJ Data Dictionary Mapping',
            'row_count': len(df),
            'columns': [str(c) for c in df.columns],
            'preview': _safe_json(df.head(200).to_dict(orient='records')),
        }
    except Exception as exc:
        return _failure('preview_parse', exc)


@router.post('/delta')
async def delta_master(file: UploadFile = File(...), db: Session = Depends(get_db), x_app_role: str | None = Header(None)):
    _admin(x_app_role)
    try:
        df = ExcelService().read_master_workbook(await file.read())
        ids = {str(r[0]) for r in db.execute(text('SELECT prj_id FROM dbo.prj_attribute_master_test')).all()}
        parsed = [_payload(row) for _, row in df.iterrows()]
        valid = [x for x in parsed if x.prj_id and x.prj_attribute_name]
        invalid = [index + 1 for index, x in enumerate(parsed) if not x.prj_id or not x.prj_attribute_name]
        return {
            'status': 'ok', 'rows': len(df),
            'new': sum(x.prj_id not in ids for x in valid),
            'update_candidates': sum(x.prj_id in ids for x in valid),
            'invalid_rows': invalid,
        }
    except Exception as exc:
        db.rollback()
        return _failure('delta_compare', exc)


@router.post('/finalize')
async def finalize_master(
    file: UploadFile = File(...), user: str | None = Query(None), db: Session = Depends(get_db), x_app_role: str | None = Header(None)
):
    """Upload valid rows, preserve successful rows, and return detailed rejections for every failed row."""
    _admin(x_app_role)
    try:
        df = ExcelService().read_master_workbook(await file.read())
    except Exception as exc:
        return _failure('workbook_parse', exc)

    service = DataDictionaryService(db)
    inserted = updated = 0
    rejected = []
    for dataframe_index, row in df.iterrows():
        # Excel row is header row + 2 because DataFrame index is zero-based.
        row_no = int(dataframe_index) + 4
        row_input = _safe_json(row.to_dict())
        payload = None
        try:
            payload = _payload(row)
            if not payload.prj_id or not payload.prj_attribute_name:
                raise ValueError('PRJ ID and PRJ Attribute Name are mandatory.')
            exists = service.repo.get_attribute(payload.prj_id) is not None
            service.upsert_attribute(payload, current_user(user), source='MASTER_EXCEL_UPLOAD')
            if exists:
                updated += 1
            else:
                inserted += 1
        except Exception as exc:
            db.rollback()
            rejected.append(_failure('row_upsert', exc, row=row_no, prj_id=(payload.prj_id if payload else None), input_row=row_input))

    return {
        'status': 'completed' if not rejected else 'completed_with_rejections',
        'inserted': inserted,
        'updated': updated,
        'rejected_count': len(rejected),
        'rejected': rejected,
    }
