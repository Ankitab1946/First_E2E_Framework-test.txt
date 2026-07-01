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
        """Synchronise scopes using explicit SQL Server-safe SQL.

        This avoids ORM-generated SELECT TOP/LIMIT variants and fixes the SQL Server
        "Incorrect syntax near '1'" failure in Create Attribute.
        """
        wanted={PORTFOLIO_ALIASES.get(x,x) for x in payload.required_portfolios}
        portfolios=self.db.execute(text("SELECT port_ref_id, port_name FROM dbo.prj_portfolio_reference_test WHERE is_active=1 ORDER BY port_ref_id")).mappings().all()
        for portfolio in portfolios:
            port_id=int(portfolio['port_ref_id']); port_name=portfolio['port_name']; should=port_name in wanted
            scope=self.db.execute(text("SELECT scope_id FROM dbo.prj_attribute_portfolio_scope_test WHERE prj_id=:prj AND port_ref_id=:port"), {'prj':master.prj_id,'port':port_id}).mappings().first()
            if should and not scope:
                self.db.execute(text("""INSERT INTO dbo.prj_attribute_portfolio_scope_test
                    (prj_id,port_ref_id,description,is_active,created_at,updated_at,created_by,updated_by)
                    VALUES (:prj,:port,:description,1,SYSUTCDATETIME(),SYSUTCDATETIME(),:user,:user)"""), {'prj':master.prj_id,'port':port_id,'description':master.prj_attribute_description,'user':user})
                scope=self.db.execute(text("SELECT scope_id FROM dbo.prj_attribute_portfolio_scope_test WHERE prj_id=:prj AND port_ref_id=:port"), {'prj':master.prj_id,'port':port_id}).mappings().first()
            if not scope:
                continue
            scope_id=int(scope['scope_id'])
            self.db.execute(text("UPDATE dbo.prj_attribute_portfolio_scope_test SET is_active=:active, description=:description, updated_at=SYSUTCDATETIME(), updated_by=:user WHERE scope_id=:scope"), {'active':1 if should else 0,'description':master.prj_attribute_description,'user':user,'scope':scope_id})
            rule=self.db.execute(text("SELECT id FROM dbo.prj_attribute_business_rules_test WHERE scope_id=:scope"), {'scope':scope_id}).mappings().first()
            if should and not rule:
                self.db.execute(text("""INSERT INTO dbo.prj_attribute_business_rules_test
                    (scope_id,source_abbr_name,editable,symbol,mapping_type,mapping_logic,calculation_logic,business_logic,is_active,created_at,updated_at,created_by,updated_by)
                    VALUES (:scope,:source,:editable,:symbol,:mapping_type,:mapping_logic,:calculation_logic,:business_logic,1,SYSUTCDATETIME(),SYSUTCDATETIME(),:user,:user)"""), {'scope':scope_id,'source':self._source_code(payload.source_name),'editable':payload.editable,'symbol':payload.symbol,'mapping_type':master.mapping_type,'mapping_logic':master.sp_as_reported_dataitem_logic,'calculation_logic':master.calculation_logic,'business_logic':payload.business_logic,'user':user})
            elif rule:
                self.db.execute(text("UPDATE dbo.prj_attribute_business_rules_test SET is_active=:active, updated_at=SYSUTCDATETIME(), updated_by=:user WHERE scope_id=:scope"), {'active':1 if should else 0,'user':user,'scope':scope_id})
            prompt=self.db.execute(text("SELECT prompt_id FROM dbo.prj_scanning_prompt_reference_test WHERE prj_id=:prj AND scope_id=:scope"), {'prj':master.prj_id,'scope':scope_id}).mappings().first()
            if should and not prompt:
                self.db.execute(text("""INSERT INTO dbo.prj_scanning_prompt_reference_test
                    (scope_id,prj_id,port_ref_id,required_by_scope,is_active,created_at,updated_at,created_by,updated_by)
                    VALUES (:scope,:prj,:port,:required,1,SYSUTCDATETIME(),SYSUTCDATETIME(),:user,:user)"""), {'scope':scope_id,'prj':master.prj_id,'port':port_id,'required':port_name,'user':user})
            elif prompt:
                self.db.execute(text("UPDATE dbo.prj_scanning_prompt_reference_test SET is_active=:active, port_ref_id=:port, required_by_scope=:required, updated_at=SYSUTCDATETIME(), updated_by=:user WHERE prompt_id=:id"), {'active':1 if should else 0,'port':port_id,'required':port_name,'user':user,'id':int(prompt['prompt_id'])})

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
        for scope in self.db.scalars(select(AttributePortfolioScope).where(AttributePortfolioScope.prj_id==prj_id)).all():
            # Restore only scopes that were previously created; explicit portfolio choices can be adjusted through Edit.
            scope.is_active = True; scope.updated_by = user
        self.repo.audit(row.__tablename__,prj_id,'REACTIVATE',before,self._serialize(row),user)
        self.db.commit(); return row
    def upsert_prompt(self,payload,user,prompt_id=None,source='UI'):
        if not self.repo.get_attribute(payload.prj_id): raise ValueError(f'PRJ ID {payload.prj_id} does not exist in prj_attribute_master_test')
        # Derive scope_id / port_ref_id from the active scope whenever a caller did not send them.
        if payload.scope_id is None:
            scope = self.db.scalar(select(AttributePortfolioScope).where(
                AttributePortfolioScope.prj_id == payload.prj_id,
                AttributePortfolioScope.is_active.is_(True),
            ).order_by(AttributePortfolioScope.scope_id))
            if scope:
                payload.scope_id = scope.scope_id
                payload.port_ref_id = scope.port_ref_id
        elif payload.port_ref_id is None:
            scope = self.db.get(AttributePortfolioScope, payload.scope_id)
            if scope:
                payload.port_ref_id = scope.port_ref_id
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
