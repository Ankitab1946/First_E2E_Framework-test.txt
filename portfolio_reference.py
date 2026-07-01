from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from DataDictionaryAdminApp.core.database import get_db
from DataDictionaryAdminApp.model.entities import PortfolioReference
from DataDictionaryAdminApp.api.schemas_api import PortfolioUpsert
from DataDictionaryAdminApp.repositories.data_dictionary_repository import DataDictionaryRepository
from DataDictionaryAdminApp.utils.security import current_user

router=APIRouter(prefix='/portfolio-reference',tags=['Portfolio Reference'])
def serial(row): return {c.name:getattr(row,c.name) for c in row.__table__.columns}

@router.get('')
def list_portfolios(include_deleted:bool=False,db:Session=Depends(get_db)):
    stmt=select(PortfolioReference)
    if not include_deleted: stmt=stmt.where(PortfolioReference.is_active == True)
    return [serial(x) for x in db.scalars(stmt.order_by(PortfolioReference.port_ref_id)).all()]

@router.post('')
def create_portfolio(payload:PortfolioUpsert,user:str|None=Query(None),db:Session=Depends(get_db)):
    row=PortfolioReference(**payload.model_dump(),created_by=current_user(user),updated_by=current_user(user)); db.add(row); db.flush()
    DataDictionaryRepository(db).audit(row.__tablename__,row.port_ref_id,'INSERT',None,serial(row),current_user(user),'UI')
    db.commit(); return serial(row)

@router.put('/{port_ref_id}')
def update_portfolio(port_ref_id:int,payload:PortfolioUpsert,user:str|None=Query(None),db:Session=Depends(get_db)):
    row=db.get(PortfolioReference,port_ref_id)
    if not row: raise HTTPException(404,'Portfolio not found')
    before=serial(row)
    for k,v in payload.model_dump().items(): setattr(row,k,v)
    row.updated_by=current_user(user); DataDictionaryRepository(db).audit(row.__tablename__,port_ref_id,'UPDATE',before,serial(row),current_user(user),'UI'); db.commit(); return serial(row)

@router.delete('/{port_ref_id}')
def delete_portfolio(port_ref_id:int,user:str|None=Query(None),db:Session=Depends(get_db)):
    row=db.get(PortfolioReference,port_ref_id)
    if not row: raise HTTPException(404,'Portfolio not found')
    before=serial(row); row.is_active=False; row.updated_by=current_user(user); DataDictionaryRepository(db).audit(row.__tablename__,port_ref_id,'SOFT_DELETE',before,serial(row),current_user(user),'UI'); db.commit(); return {'status':'soft_deleted','port_ref_id':port_ref_id}
