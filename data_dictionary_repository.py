import json
from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session
from DataDictionaryAdminApp.model.entities import AttributeMaster, PortfolioReference, AttributePortfolioScope, AttributeBusinessRule, ScanningPromptReference, AuditTable

PORTFOLIO_ALIASES = {"FI Banks": "Banks", "FI Insurance": "Insurance", "Corporates": "Corporate", "Zeus Downstream": "Zeus Downstream"}

class DataDictionaryRepository:
    def __init__(self, db: Session): self.db = db
    def audit(self, table, key, action, before, after, user, source="UI", batch=None):
        self.db.add(AuditTable(table_name=table, record_key=str(key), action=action, before_value=json.dumps(before, default=str) if before else None, after_value=json.dumps(after, default=str) if after else None, source_operation=source, batch_reference=batch, performed_by=user))
    def get_portfolios(self): return self.db.scalars(select(PortfolioReference).where(PortfolioReference.is_active.is_(True))).all()
    def source_code(self, source_name: str | None):
        """Resolve static source name to source code without SQL Server TOP/LIMIT syntax."""
        if not source_name:
            return "SNPAR"
        from sqlalchemy import text
        try:
            row = self.db.execute(
                text("SELECT source_code FROM dbo.prj_data_source WHERE source_name = :name"),
                {"name": source_name},
            ).first()
            return row[0] if row else "SNPAR"
        except Exception:
            return "SNPAR"
    def list_attributes(self, filters):
        stmt = select(AttributeMaster)
        if not filters.include_deleted: stmt = stmt.where(AttributeMaster.is_active.is_(True))
        if filters.prj_id: stmt = stmt.where(AttributeMaster.prj_id.ilike(f"%{filters.prj_id}%"))
        if filters.attribute_name: stmt = stmt.where(AttributeMaster.prj_attribute_name.ilike(f"%{filters.attribute_name}%"))
        if filters.attribute_description: stmt = stmt.where(AttributeMaster.prj_attribute_description.ilike(f"%{filters.attribute_description}%"))
        if filters.section: stmt = stmt.where(AttributeMaster.where_in_financial_statement == filters.section)
        rows = self.db.scalars(stmt).all()
        if filters.portfolios:
            names = [PORTFOLIO_ALIASES.get(x, x) for x in filters.portfolios]
            filtered=[]
            for row in rows:
                active_names=set(self.db.scalars(select(PortfolioReference.port_name).join(AttributePortfolioScope, AttributePortfolioScope.port_ref_id==PortfolioReference.port_ref_id).where(AttributePortfolioScope.prj_id==row.prj_id, AttributePortfolioScope.is_active.is_(True))).all())
                if set(names).issubset(active_names): filtered.append(row)
            rows=filtered
        if filters.overlapped_only:
            rows=[r for r in rows if self.db.scalar(select(func.count()).select_from(AttributePortfolioScope).where(AttributePortfolioScope.prj_id==r.prj_id, AttributePortfolioScope.is_active.is_(True))) > 1]
        return rows
    def get_attribute(self, prj_id): return self.db.get(AttributeMaster, prj_id)
    def prompt(self, prompt_id): return self.db.get(ScanningPromptReference, prompt_id)
