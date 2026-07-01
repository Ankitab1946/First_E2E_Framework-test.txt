import json
from sqlalchemy import text, select
from sqlalchemy.orm import Session
from DataDictionaryAdminApp.model.entities import AttributeMaster, PortfolioReference, ScanningPromptReference, AuditTable

PORTFOLIO_ALIASES = {"FI Banks": "FI Banks", "FI Insurance": "FI Insurance", "Corporates": "Corporates", "Zeus Downstream": "Zeus Downstream"}

class DataDictionaryRepository:
    def __init__(self, db: Session): self.db = db
    def audit(self, table, key, action, before, after, user, source="UI", batch=None):
        self.db.add(AuditTable(table_name=table, record_key=str(key), action=action, before_value=json.dumps(before, default=str) if before else None, after_value=json.dumps(after, default=str) if after else None, source_operation=source, batch_reference=batch, performed_by=user))
    def source_code(self, source_name: str | None):
        if not source_name: return "SNPAR"
        try:
            row=self.db.execute(text("SELECT source_code FROM dbo.prj_data_source WHERE source_name=:name"), {"name":source_name}).mappings().first()
            return row["source_code"] if row else "SNPAR"
        except Exception: return "SNPAR"
    def list_attributes_dict(self, filters):
        """Return the exact View Latest projection using SQL Server-safe text SQL only."""
        params = {}; conditions = []
        if not filters.include_deleted:
            conditions.append("m.is_active = 1")
        for value, column, key in [
            (filters.prj_id, 'm.prj_id', 'prj_id'),
            (filters.attribute_name, 'm.prj_attribute_name', 'attribute_name'),
            (filters.attribute_description, 'm.prj_attribute_description', 'attribute_description'),
        ]:
            if value:
                conditions.append(f"{column} LIKE :{key}")
                params[key] = f"%{value}%"
        if filters.section:
            conditions.append("m.where_in_financial_statement = :section")
            params['section'] = filters.section
        if filters.portfolios:
            # AND semantics: FI Banks + FI Insurance returns only attributes applicable to both.
            names = [PORTFOLIO_ALIASES.get(x, x) for x in filters.portfolios]
            params['portfolio_count'] = len(names)
            placeholders = []
            for index, name in enumerate(names):
                key = f'portfolio_{index}'
                params[key] = name
                placeholders.append(f':{key}')
            # FI Banks / FI Insurance are represented by port_name='FI' and sector_name.
            conditions.append("""(
                SELECT COUNT(DISTINCT CASE
                    WHEN LOWER(p.port_name)='fi' AND LOWER(p.sector_name)='banks' THEN 'FI Banks'
                    WHEN LOWER(p.port_name)='fi' AND LOWER(p.sector_name)='insurance' THEN 'FI Insurance'
                    WHEN LOWER(p.port_name)='corporate' THEN 'Corporates'
                    WHEN LOWER(p.port_name)='zeus downstream' THEN 'Zeus Downstream'
                    ELSE p.port_name END)
                FROM dbo.prj_attribute_portfolio_scope_test AS s
                INNER JOIN dbo.prj_portfolio_reference_test AS p ON p.port_ref_id = s.port_ref_id
                WHERE s.prj_id = m.prj_id AND s.is_active = 1
                  AND (CASE
                    WHEN LOWER(p.port_name)='fi' AND LOWER(p.sector_name)='banks' THEN 'FI Banks'
                    WHEN LOWER(p.port_name)='fi' AND LOWER(p.sector_name)='insurance' THEN 'FI Insurance'
                    WHEN LOWER(p.port_name)='corporate' THEN 'Corporates'
                    WHEN LOWER(p.port_name)='zeus downstream' THEN 'Zeus Downstream'
                    ELSE p.port_name END) IN (""" + ','.join(placeholders) + ") ) = :portfolio_count")
        if filters.overlapped_only:
            conditions.append("(SELECT COUNT(*) FROM dbo.prj_attribute_portfolio_scope_test AS os WHERE os.prj_id=m.prj_id AND os.is_active=1) > 1")
        where_clause = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
        sql = text("""
            SELECT
                m.prj_id,
                m.prj_attribute_name,
                m.prj_attribute_description,
                m.prj_physical_attribute_name,
                CASE WHEN MAX(CAST(COALESCE(br.editable, 0) AS int)) = 1 THEN 'Y' ELSE 'N' END AS editable,
                MAX(CASE WHEN br.symbol IS NOT NULL THEN br.symbol END) AS percent_ratio,
                MAX(CASE WHEN br.source_abbr_name IS NOT NULL THEN br.source_abbr_name END) AS source,
                m.version_update,
                m.where_in_financial_statement,
                MAX(CASE WHEN pr.port_name='Corporate' AND s.is_active=1 THEN 'Y' ELSE 'N' END) AS required_by_corporates,
                MAX(CASE WHEN pr.port_name='FI' AND pr.sector_name='Banks' AND s.is_active=1 THEN 'Y' ELSE 'N' END) AS required_by_fi_banks,
                MAX(CASE WHEN pr.port_name='FI' AND pr.sector_name='Insurance' AND s.is_active=1 THEN 'Y' ELSE 'N' END) AS required_by_fi_insurance,
                MAX(CASE WHEN pr.port_name='Zeus Downstream' AND s.is_active=1 THEN 'Y' ELSE 'N' END) AS required_by_zeus_downstream,
                m.calculated_or_reported,
                m.calculation_logic,
                m.is_active,
                m.created_at,
                m.updated_at,
                m.created_by,
                m.updated_by
            FROM dbo.prj_attribute_master_test AS m
            LEFT JOIN dbo.prj_attribute_portfolio_scope_test AS s ON s.prj_id=m.prj_id
            LEFT JOIN dbo.prj_portfolio_reference_test AS pr ON pr.port_ref_id=s.port_ref_id
            LEFT JOIN dbo.prj_attribute_business_rules_test AS br ON br.scope_id=s.scope_id AND br.is_active=1
        """ + where_clause + """
            GROUP BY m.prj_id,m.prj_attribute_name,m.prj_attribute_description,m.prj_physical_attribute_name,
                     m.version_update,m.where_in_financial_statement,m.calculated_or_reported,m.calculation_logic,
                     m.is_active,m.created_at,m.updated_at,m.created_by,m.updated_by
            ORDER BY m.prj_id
        """)
        return [dict(row) for row in self.db.execute(sql, params).mappings().all()]
    def get_attribute_projection(self, prj_id):
        rows = self.list_attributes_dict(type('Filters', (), {'include_deleted': True, 'prj_id': prj_id, 'attribute_name': None, 'attribute_description': None, 'section': None, 'portfolios': [], 'overlapped_only': False})())
        return rows[0] if rows else None
    def list_attributes(self, filters): return self.list_attributes_dict(filters)
    def get_portfolios(self, active_only: bool = True):
        """Return the static portfolio reference rows used to derive attribute scopes."""
        stmt = select(PortfolioReference)
        if active_only:
            stmt = stmt.where(PortfolioReference.is_active == 1)
        return list(self.db.scalars(stmt.order_by(PortfolioReference.port_ref_id)).all())

    def get_attribute(self, prj_id): return self.db.get(AttributeMaster, prj_id)
    def prompt(self, prompt_id): return self.db.get(ScanningPromptReference, prompt_id)
