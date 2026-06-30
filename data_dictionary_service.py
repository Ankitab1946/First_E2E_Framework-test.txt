from dataclasses import asdict
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from DataDictionaryAdminApp.model.entities import AttributeMaster, PortfolioReference, AttributePortfolioScope, AttributeBusinessRule, ScanningPromptReference, AuditTable
from DataDictionaryAdminApp.repositories.data_dictionary_repository import DataDictionaryRepository, PORTFOLIO_ALIASES
from DataDictionaryAdminApp.utils.normalizers import physical_name

class DataDictionaryService:
    def __init__(self, db: Session): self.db, self.repo = db, DataDictionaryRepository(db)
    def _serialize(self, row): return {c.name: getattr(row,c.name) for c in row.__table__.columns}
    def upsert_attribute(self, payload, user, source='UI'):
        existing=self.repo.get_attribute(payload.prj_id)
        before=self._serialize(existing) if existing else None
        if not existing:
            existing=AttributeMaster(prj_id=payload.prj_id, created_by=user, updated_by=user)
            self.db.add(existing)
        for k,v in payload.model_dump(exclude={'required_portfolios','source_name','editable','symbol','business_logic'}).items():
            if k=='prj_physical_attribute_name' and not v and existing.prj_physical_attribute_name: continue
            setattr(existing,k,v)
        if not existing.prj_physical_attribute_name: existing.prj_physical_attribute_name=physical_name(existing.prj_attribute_name)
        existing.is_active=True; existing.updated_by=user
        self.db.flush()
        self._sync_scopes(existing,payload,user,source)
        self.repo.audit(existing.__tablename__, existing.prj_id, 'INSERT' if before is None else 'UPDATE', before, self._serialize(existing), user, source)
        self.db.commit(); return existing
    def _sync_scopes(self, master, payload, user, source):
        wanted={PORTFOLIO_ALIASES.get(x,x) for x in payload.required_portfolios}
        portfolios=self.repo.get_portfolios()
        for portfolio in portfolios:
            scope=self.db.scalar(select(AttributePortfolioScope).where(AttributePortfolioScope.prj_id==master.prj_id, AttributePortfolioScope.port_ref_id==portfolio.port_ref_id))
            should=portfolio.port_name in wanted
            if should and not scope:
                scope=AttributePortfolioScope(prj_id=master.prj_id,port_ref_id=portfolio.port_ref_id,description=master.prj_attribute_description,created_by=user,updated_by=user)
                self.db.add(scope); self.db.flush()
            if scope:
                prior=scope.is_active; scope.is_active=should; scope.description=master.prj_attribute_description; scope.updated_by=user
                rule=self.db.scalar(select(AttributeBusinessRule).where(AttributeBusinessRule.scope_id==scope.scope_id))
                if should and not rule:
                    source_code=self._source_code(payload.source_name)
                    rule=AttributeBusinessRule(scope_id=scope.scope_id,source_abbr_name=source_code,editable=payload.editable,symbol=payload.symbol,mapping_type=master.mapping_type,mapping_logic=master.sp_as_reported_dataitem_logic,calculation_logic=master.calculation_logic,business_logic=payload.business_logic,created_by=user,updated_by=user)
                    self.db.add(rule)
                elif rule:
                    rule.is_active=should; rule.updated_by=user
    def _source_code(self,name):
        try:
            row=self.db.execute(text('SELECT source_code FROM dbo.prj_data_source WHERE source_name = :name'), {'name':name}).first() if name else None
            return row[0] if row else 'SNPAR'
        except Exception: return 'SNPAR'
    def soft_delete_attribute(self, prj_id,user):
        row=self.repo.get_attribute(prj_id)
        if not row: return None
        before=self._serialize(row); row.is_active=False; row.updated_by=user
        for scope in self.db.scalars(select(AttributePortfolioScope).where(AttributePortfolioScope.prj_id==prj_id)).all(): scope.is_active=False; scope.updated_by=user
        self.repo.audit(row.__tablename__,prj_id,'SOFT_DELETE',before,self._serialize(row),user)
        self.db.commit(); return row
    def reactivate_attribute(self, prj_id,user):
        row=self.repo.get_attribute(prj_id)
        if not row: return None
        before=self._serialize(row); row.is_active=True; row.updated_by=user
        self.repo.audit(row.__tablename__,prj_id,'REACTIVATE',before,self._serialize(row),user)
        self.db.commit(); return row
    def upsert_prompt(self,payload,user,prompt_id=None,source='UI'):
        if not self.repo.get_attribute(payload.prj_id): raise ValueError(f'PRJ ID {payload.prj_id} does not exist in prj_attribute_master_test')
        row=self.repo.prompt(prompt_id) if prompt_id else None; before=self._serialize(row) if row else None
        if not row: row=ScanningPromptReference(prj_id=payload.prj_id,created_by=user,updated_by=user); self.db.add(row)
        elif row.prj_id != payload.prj_id: raise ValueError('PRJ ID is read-only during prompt edit')
        for k,v in payload.model_dump().items():
            if k!='prj_id': setattr(row,k,v)
        row.updated_by=user; row.is_active=True; self.db.flush()
        self.repo.audit(row.__tablename__,row.prompt_id,'INSERT' if before is None else 'UPDATE',before,self._serialize(row),user,source)
        self.db.commit(); return row
    def soft_delete_prompt(self,prompt_id,user):
        row=self.repo.prompt(prompt_id)
        if not row:return None
        before=self._serialize(row);row.is_active=False;row.updated_by=user;self.repo.audit(row.__tablename__,prompt_id,'SOFT_DELETE',before,self._serialize(row),user);self.db.commit();return row
    def audit_rows(self, table_name=None, record_key=None):
        stmt=select(AuditTable).order_by(AuditTable.performed_at.desc())
        if table_name: stmt=stmt.where(AuditTable.table_name==table_name)
        if record_key: stmt=stmt.where(AuditTable.record_key.ilike(f'%{record_key}%'))
        return self.db.scalars(stmt).all()
