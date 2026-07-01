from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from DataDictionaryAdminApp.core.database import get_db
from DataDictionaryAdminApp.model.entities import AttributeMaster, PortfolioReference

router = APIRouter(prefix='/lookups', tags=['Lookups'])

@router.get('/sections')
def sections(db: Session = Depends(get_db)):
    defaults = ['Income Statement', 'Balance Sheet', 'Cash Flow', 'Ratios', 'Derivatives', 'Miscellaneous', 'Other']
    try:
        values = db.scalars(select(AttributeMaster.where_in_financial_statement).where(
            AttributeMaster.where_in_financial_statement.is_not(None)
        ).distinct()).all()
        return sorted(set(defaults + [x for x in values if x]))
    except Exception:
        db.rollback()
        return defaults

@router.get('/portfolios')
def portfolios(db: Session = Depends(get_db)):
    try:
        rows = db.scalars(select(PortfolioReference).where(PortfolioReference.is_active == True).order_by(PortfolioReference.port_ref_id)).all()
        return [{'port_ref_id': r.port_ref_id, 'port_name': r.port_name, 'sector_name': r.sector_name, 'sub_sector': r.sub_sector, 'remark': r.remark} for r in rows]
    except Exception:
        db.rollback()
        return []

@router.get('/sources')
def sources(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text('SELECT DISTINCT source_name, source_code FROM prj_data_source ORDER BY source_name')).mappings().all()
        return [dict(r) for r in rows]
    except Exception:
        return [{'source_name': 'S&P CAPIQ AS REPORTED DATA', 'source_code': 'SNPAR'}]
