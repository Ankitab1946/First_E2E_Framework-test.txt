from sqlalchemy import select, text
from sqlalchemy.orm import Session
from DataDictionaryAdminApp.model.entities import AttributeMaster, ScanningPromptReference, AuditTable
from DataDictionaryAdminApp.repositories.data_dictionary_repository import DataDictionaryRepository
from DataDictionaryAdminApp.utils.normalizers import physical_name


def _bit(value):
    return 1 if str(value or '').strip().upper() in {'Y', 'YES', 'TRUE', '1'} else 0


def _scope_label(port_name, sector_name):
    """Resolve portfolio-reference variants to the canonical UI labels."""
    port = str(port_name or '').strip().lower()
    sector = str(sector_name or '').strip().lower()
    combined = f"{port} {sector}".strip()
    if port == 'fi' and ('bank' in sector or 'bank' in combined): return 'FI Banks'
    if port == 'fi' and ('insurance' in sector or 'insurance' in combined): return 'FI Insurance'
    if port in {'corporate', 'corporates'} or 'corporate' in combined: return 'Corporates'
    if 'zeus' in combined and ('downstream' in combined or port == 'zeus'): return 'Zeus Downstream'
    return str(port_name or sector_name or '').strip()


class DataDictionaryService:
    def __init__(self, db: Session):
        self.db, self.repo = db, DataDictionaryRepository(db)
        self._source_code_cache: dict[str, str] = {}

    def _serialize(self, row):
        return {c.name: getattr(row, c.name) for c in row.__table__.columns}

    def upsert_attribute(self, payload, user, source='UI', *, commit=True, portfolio_refs=None):
        row = self.repo.get_attribute(payload.prj_id)
        before = self._serialize(row) if row else None
        if not row:
            row = AttributeMaster(prj_id=payload.prj_id, created_by=user, updated_by=user)
            self.db.add(row)
        for k, v in payload.model_dump(exclude={'required_portfolios','source_name','editable','symbol','business_logic'}).items():
            if k == 'prj_physical_attribute_name' and not v and row.prj_physical_attribute_name:
                continue
            setattr(row, k, v)
        if not row.prj_physical_attribute_name:
            row.prj_physical_attribute_name = physical_name(row.prj_attribute_name)
        row.is_active, row.updated_by = True, user
        self.db.flush()
        self._sync_scopes(row, payload, user, portfolio_refs=portfolio_refs)
        self.repo.audit(row.__tablename__, row.prj_id, 'INSERT' if before is None else 'UPDATE', before, self._serialize(row), user, source)
        if commit:
            self.db.commit()
        return row

    def _sync_scopes(self, master, payload, user, *, portfolio_refs=None):
        """Creates/reactivates one scope for every selected Required By checkbox."""
        # Canonicalise selections so the UI labels match existing portfolio-reference variants.
        wanted = {str(x).strip().lower() for x in (payload.required_portfolios or [])}
        refs = portfolio_refs if portfolio_refs is not None else self.db.execute(text("SELECT port_ref_id,port_name,sector_name FROM dbo.prj_portfolio_reference_test WHERE is_active=1 ORDER BY port_ref_id")).mappings().all()
        for ref in refs:
            port_id = int(ref['port_ref_id']); label = _scope_label(ref['port_name'], ref['sector_name']); active = label.strip().lower() in wanted
            scope = self.db.execute(text("SELECT scope_id FROM dbo.prj_attribute_portfolio_scope_test WHERE prj_id=:prj AND port_ref_id=:port"), {'prj':master.prj_id,'port':port_id}).mappings().first()
            if active and not scope:
                self.db.execute(text("""INSERT INTO dbo.prj_attribute_portfolio_scope_test
                    (prj_id,port_ref_id,description,is_active,created_at,updated_at,created_by,updated_by)
                    VALUES (:prj,:port,:description,1,SYSUTCDATETIME(),SYSUTCDATETIME(),:user,:user)"""),
                    {'prj':master.prj_id,'port':port_id,'description':master.prj_attribute_description,'user':user})
                scope = self.db.execute(text("SELECT scope_id FROM dbo.prj_attribute_portfolio_scope_test WHERE prj_id=:prj AND port_ref_id=:port"), {'prj':master.prj_id,'port':port_id}).mappings().first()
            if not scope:
                continue
            scope_id = int(scope['scope_id'])
            self.db.execute(text("""UPDATE dbo.prj_attribute_portfolio_scope_test
              SET is_active=:active,description=:description,updated_at=SYSUTCDATETIME(),updated_by=:user WHERE scope_id=:scope"""),
              {'active':1 if active else 0,'description':master.prj_attribute_description,'user':user,'scope':scope_id})
            rule = self.db.execute(text("SELECT id FROM dbo.prj_attribute_business_rules_test WHERE scope_id=:scope"), {'scope':scope_id}).mappings().first()
            vals={'scope':scope_id,'source':self._source_code(payload.source_name),'editable':_bit(payload.editable),'symbol':payload.symbol,'mapping_type':master.mapping_type,'mapping_logic':master.sp_as_reported_dataitem_logic,'calculation_logic':master.calculation_logic,'business_logic':payload.business_logic,'user':user}
            if active and not rule:
                self.db.execute(text("""INSERT INTO dbo.prj_attribute_business_rules_test
                    (scope_id,source_abbr_name,editable,symbol,mapping_type,mapping_logic,calculation_logic,business_logic,is_active,created_at,updated_at,created_by,updated_by)
                    VALUES (:scope,:source,:editable,:symbol,:mapping_type,:mapping_logic,:calculation_logic,:business_logic,1,SYSUTCDATETIME(),SYSUTCDATETIME(),:user,:user)"""), vals)
            elif rule:
                self.db.execute(text("""UPDATE dbo.prj_attribute_business_rules_test SET is_active=:active,source_abbr_name=:source,editable=:editable,symbol=:symbol,mapping_type=:mapping_type,mapping_logic=:mapping_logic,calculation_logic=:calculation_logic,business_logic=:business_logic,updated_at=SYSUTCDATETIME(),updated_by=:user WHERE scope_id=:scope"""), {**vals,'active':1 if active else 0})
            prompt = self.db.execute(text("SELECT prompt_id FROM dbo.prj_scanning_prompt_reference_test WHERE prj_id=:prj AND scope_id=:scope"), {'prj':master.prj_id,'scope':scope_id}).mappings().first()
            if active and not prompt:
                self.db.execute(text("""INSERT INTO dbo.prj_scanning_prompt_reference_test
                  (scope_id,prj_id,port_ref_id,required_by_scope,is_active,created_at,updated_at,created_by,updated_by)
                  VALUES (:scope,:prj,:port,:required,1,SYSUTCDATETIME(),SYSUTCDATETIME(),:user,:user)"""),
                  {'scope':scope_id,'prj':master.prj_id,'port':port_id,'required':label,'user':user})
            elif prompt:
                self.db.execute(text("UPDATE dbo.prj_scanning_prompt_reference_test SET is_active=:active,port_ref_id=:port,required_by_scope=:required,updated_at=SYSUTCDATETIME(),updated_by=:user WHERE prompt_id=:id"),
                  {'active':1 if active else 0,'port':port_id,'required':label,'user':user,'id':int(prompt['prompt_id'])})

    def _source_code(self, name):
        cache_key = str(name or '__default__').strip().lower()
        if cache_key in self._source_code_cache:
            return self._source_code_cache[cache_key]
        try:
            row = self.db.execute(text("SELECT source_code FROM dbo.prj_data_source WHERE source_name=:name"), {'name': name}).first() if name else None
            code = row[0] if row else 'SNPAR'
        except Exception:
            code = 'SNPAR'
        self._source_code_cache[cache_key] = code
        return code

    def active_scopes(self, prj_id):
        return self.db.execute(text("""SELECT s.scope_id,s.port_ref_id,p.port_name,p.sector_name FROM dbo.prj_attribute_portfolio_scope_test s JOIN dbo.prj_portfolio_reference_test p ON p.port_ref_id=s.port_ref_id WHERE s.prj_id=:prj AND s.is_active=1 ORDER BY s.scope_id"""), {'prj':prj_id}).mappings().all()

    def soft_delete_attribute(self, prj_id, user):
        row=self.repo.get_attribute(prj_id)
        if not row:return None
        before=self._serialize(row)
        self.db.execute(text("UPDATE dbo.prj_attribute_master_test SET is_active=0,updated_at=SYSUTCDATETIME(),updated_by=:user WHERE prj_id=:prj"),{'user':user,'prj':prj_id})
        self.db.execute(text("UPDATE dbo.prj_attribute_portfolio_scope_test SET is_active=0,updated_at=SYSUTCDATETIME(),updated_by=:user WHERE prj_id=:prj"),{'user':user,'prj':prj_id})
        self.repo.audit(row.__tablename__,prj_id,'SOFT_DELETE',before,{**before,'is_active':False},user);self.db.commit();return row

    def reactivate_attribute(self, prj_id, user):
        row=self.repo.get_attribute(prj_id)
        if not row:return None
        before=self._serialize(row)
        self.db.execute(text("UPDATE dbo.prj_attribute_master_test SET is_active=1,updated_at=SYSUTCDATETIME(),updated_by=:user WHERE prj_id=:prj"),{'user':user,'prj':prj_id})
        self.db.execute(text("UPDATE dbo.prj_attribute_portfolio_scope_test SET is_active=1,updated_at=SYSUTCDATETIME(),updated_by=:user WHERE prj_id=:prj"),{'user':user,'prj':prj_id})
        self.repo.audit(row.__tablename__,prj_id,'REACTIVATE',before,{**before,'is_active':True},user);self.db.commit();return self.repo.get_attribute(prj_id)

    def upsert_prompt(self, payload, user, prompt_id=None, source='UI', *, commit=True):
        if not self.repo.get_attribute(payload.prj_id): raise ValueError(f'PRJ ID {payload.prj_id} does not exist in prj_attribute_master_test')
        direct = self.repo.prompt(prompt_id) if prompt_id else None
        if direct and direct.prj_id != payload.prj_id: raise ValueError('PRJ ID is read-only during prompt edit')
        scopes = [s for s in self.active_scopes(payload.prj_id) if not payload.scope_id or int(s['scope_id'])==int(payload.scope_id)]
        if not scopes: raise ValueError(f'No active portfolio scope exists for PRJ ID {payload.prj_id}')
        targets=[]
        if direct:
            targets=[(direct,scopes[0])]
        else:
            for scope in scopes:
                found=self.db.execute(text("SELECT prompt_id FROM dbo.prj_scanning_prompt_reference_test WHERE prj_id=:prj AND scope_id=:scope ORDER BY prompt_id"),{'prj':payload.prj_id,'scope':int(scope['scope_id'])}).mappings().first()
                targets.append((self.repo.prompt(int(found['prompt_id'])) if found else None,scope))
        first=None
        for target,scope in targets:
            before=self._serialize(target) if target else None
            if not target:
                target=ScanningPromptReference(prj_id=payload.prj_id,created_by=user,updated_by=user);self.db.add(target)
            target.prj_id=payload.prj_id;target.scope_id=int(scope['scope_id']);target.port_ref_id=int(scope['port_ref_id']);target.required_by_scope=payload.required_by_scope or _scope_label(scope['port_name'],scope['sector_name'])
            for k,v in payload.model_dump(exclude={'prj_id','scope_id','port_ref_id','required_by_scope'}).items(): setattr(target,k,v)
            target.is_active=True;target.updated_by=user;self.db.flush();self.repo.audit(target.__tablename__,target.prompt_id,'INSERT' if before is None else 'UPDATE',before,self._serialize(target),user,source);first=target
        if commit:
            self.db.commit()
        return first

    def soft_delete_prompt(self,prompt_id,user):
        row=self.repo.prompt(prompt_id)
        if not row:return None
        before=self._serialize(row);row.is_active=False;row.updated_by=user;self.repo.audit(row.__tablename__,prompt_id,'SOFT_DELETE',before,self._serialize(row),user);self.db.commit();return row

    def audit_rows(self,table_name=None,record_key=None):
        stmt=select(AuditTable).order_by(AuditTable.performed_at.desc())
        if table_name:stmt=stmt.where(AuditTable.table_name==table_name)
        if record_key:stmt=stmt.where(AuditTable.record_key.ilike(f'%{record_key}%'))
        return self.db.scalars(stmt).all()

    def bulk_upsert_attributes(self, payloads, user, source='MASTER_EXCEL_UPLOAD', *, portfolio_refs=None):
        """High-throughput set-oriented attribute upsert for workbook imports.

        This method intentionally bypasses the interactive row-by-row ORM path.
        It preserves the same six-table behaviour, including audit records and
        scope/business-rule/prompt placeholder synchronisation, while reducing
        SQL Server round trips from dozens per row to a small number per batch.
        """
        if not payloads:
            return {'inserted': 0, 'updated': 0}

        # A workbook may contain the same PRJ ID more than once. SQL Server
        # executemany updates can otherwise issue duplicate scope/rule writes
        # in one transaction. Keep the last occurrence, matching Excel's
        # natural 'last row wins' expectation.
        deduplicated: dict[str, object] = {}
        for payload in payloads:
            deduplicated[str(payload.prj_id).strip()] = payload
        payloads = list(deduplicated.values())

        refs = portfolio_refs if portfolio_refs is not None else self.db.execute(text(
            "SELECT port_ref_id, port_name, sector_name FROM dbo.prj_portfolio_reference_test WHERE is_active=1"
        )).mappings().all()
        ref_rows = [dict(r) for r in refs]
        ref_by_label = {_scope_label(r['port_name'], r['sector_name']).strip().lower(): r for r in ref_rows}

        prj_ids = [str(p.prj_id).strip() for p in payloads]
        bind_names = ','.join(f':id_{idx}' for idx in range(len(prj_ids)))
        bind = {f'id_{idx}': value for idx, value in enumerate(prj_ids)}

        existing_master = {
            row['prj_id']: dict(row)
            for row in self.db.execute(text(
                "SELECT prj_id, prj_physical_attribute_name FROM dbo.prj_attribute_master_test "
                f"WHERE prj_id IN ({bind_names})"
            ), bind).mappings().all()
        }

        master_insert, master_update = [], []
        audit_rows = []
        for payload in payloads:
            values = payload.model_dump(exclude={'required_portfolios', 'source_name', 'editable', 'symbol', 'business_logic'})
            prj_id = str(values['prj_id']).strip()
            existing = existing_master.get(prj_id)
            physical = values.get('prj_physical_attribute_name') or (existing or {}).get('prj_physical_attribute_name') or physical_name(values['prj_attribute_name'])
            common = {
                **values,
                'prj_id': prj_id,
                'prj_physical_attribute_name': physical,
                'updated_by': user,
            }
            if existing:
                master_update.append(common)
                action = 'UPDATE'
            else:
                master_insert.append({**common, 'created_by': user})
                action = 'INSERT'
            audit_rows.append({
                'table_name': 'prj_attribute_master_test',
                'record_key': prj_id,
                'action': action,
                'before_value': None,
                'after_value': __import__('json').dumps({k: v for k, v in common.items() if k != 'updated_by'}, default=str),
                'source_operation': source,
                'performed_by': user,
            })

        if master_insert:
            self.db.execute(text("""
                INSERT INTO dbo.prj_attribute_master_test
                (prj_id,prj_attribute_name,prj_attribute_description,prj_physical_attribute_name,
                 where_in_financial_statement,version_update,calculated_or_reported,calculation_logic,
                 calculation_logic_details,sign_flipping_value,mapping_type,sp_standardisation_dataitem_id,
                 sp_as_reported_dataitem_logic,calculated_in_cfv,editable_in_historicals,is_active,
                 created_at,updated_at,created_by,updated_by)
                VALUES
                (:prj_id,:prj_attribute_name,:prj_attribute_description,:prj_physical_attribute_name,
                 :where_in_financial_statement,:version_update,:calculated_or_reported,:calculation_logic,
                 :calculation_logic_details,:sign_flipping_value,:mapping_type,:sp_standardisation_dataitem_id,
                 :sp_as_reported_dataitem_logic,:calculated_in_cfv,:editable_in_historicals,1,
                 SYSUTCDATETIME(),SYSUTCDATETIME(),:created_by,:updated_by)
            """), master_insert)
        if master_update:
            self.db.execute(text("""
                UPDATE dbo.prj_attribute_master_test
                SET prj_attribute_name=:prj_attribute_name,
                    prj_attribute_description=:prj_attribute_description,
                    prj_physical_attribute_name=:prj_physical_attribute_name,
                    where_in_financial_statement=:where_in_financial_statement,
                    version_update=:version_update,
                    calculated_or_reported=:calculated_or_reported,
                    calculation_logic=:calculation_logic,
                    calculation_logic_details=:calculation_logic_details,
                    sign_flipping_value=:sign_flipping_value,
                    mapping_type=:mapping_type,
                    sp_standardisation_dataitem_id=:sp_standardisation_dataitem_id,
                    sp_as_reported_dataitem_logic=:sp_as_reported_dataitem_logic,
                    calculated_in_cfv=:calculated_in_cfv,
                    editable_in_historicals=:editable_in_historicals,
                    is_active=1,updated_at=SYSUTCDATETIME(),updated_by=:updated_by
                WHERE prj_id=:prj_id
            """), master_update)

        # Fetch scopes once for the whole batch, then build batched insert/update operations.
        scope_rows = self.db.execute(text(
            "SELECT scope_id,prj_id,port_ref_id FROM dbo.prj_attribute_portfolio_scope_test "
            f"WHERE prj_id IN ({bind_names})"
        ), bind).mappings().all()
        scope_by_pair = {(str(row['prj_id']), int(row['port_ref_id'])): int(row['scope_id']) for row in scope_rows}
        scope_inserts, scope_updates = [], []
        desired_scope_meta = []
        payload_by_prj = {str(p.prj_id).strip(): p for p in payloads}
        for prj_id, payload in payload_by_prj.items():
            wanted = {str(x).strip().lower() for x in (payload.required_portfolios or [])}
            description = payload.prj_attribute_description
            for ref in ref_rows:
                label = _scope_label(ref['port_name'], ref['sector_name'])
                active = 1 if label.strip().lower() in wanted else 0
                pair = (prj_id, int(ref['port_ref_id']))
                scope_id = scope_by_pair.get(pair)
                if scope_id is None:
                    if active:
                        scope_inserts.append({'prj_id': prj_id, 'port_ref_id': int(ref['port_ref_id']), 'description': description, 'user': user})
                else:
                    scope_updates.append({'scope_id': scope_id, 'is_active': active, 'description': description, 'user': user})

        if scope_inserts:
            self.db.execute(text("""
                INSERT INTO dbo.prj_attribute_portfolio_scope_test
                (prj_id,port_ref_id,description,is_active,created_at,updated_at,created_by,updated_by)
                VALUES (:prj_id,:port_ref_id,:description,1,SYSUTCDATETIME(),SYSUTCDATETIME(),:user,:user)
            """), scope_inserts)
        if scope_updates:
            self.db.execute(text("""
                UPDATE dbo.prj_attribute_portfolio_scope_test
                SET is_active=:is_active,description=:description,updated_at=SYSUTCDATETIME(),updated_by=:user
                WHERE scope_id=:scope_id
            """), scope_updates)

        # Re-read IDs only once after possible scope insertions.
        all_scopes = self.db.execute(text(
            "SELECT scope_id,prj_id,port_ref_id,is_active FROM dbo.prj_attribute_portfolio_scope_test "
            f"WHERE prj_id IN ({bind_names})"
        ), bind).mappings().all()
        scope_by_pair = {(str(row['prj_id']), int(row['port_ref_id'])): dict(row) for row in all_scopes}
        scope_ids = [int(row['scope_id']) for row in all_scopes]
        if not scope_ids:
            if audit_rows:
                self.db.execute(text("""
                    INSERT INTO dbo.audit_table_test
                    (table_name,record_key,action,before_value,after_value,source_operation,performed_by,performed_at)
                    VALUES (:table_name,:record_key,:action,:before_value,:after_value,:source_operation,:performed_by,SYSUTCDATETIME())
                """), audit_rows)
            return {'inserted': len(master_insert), 'updated': len(master_update)}

        scope_bind = {f'scope_{idx}': scope_id for idx, scope_id in enumerate(scope_ids)}
        scope_placeholders = ','.join(f':{key}' for key in scope_bind)
        existing_rules = {int(row['scope_id']): int(row['id']) for row in self.db.execute(text(
            "SELECT id,scope_id FROM dbo.prj_attribute_business_rules_test "
            f"WHERE scope_id IN ({scope_placeholders})"
        ), scope_bind).mappings().all()}
        existing_prompts = {int(row['scope_id']): int(row['prompt_id']) for row in self.db.execute(text(
            "SELECT prompt_id,scope_id FROM dbo.prj_scanning_prompt_reference_test "
            f"WHERE scope_id IN ({scope_placeholders})"
        ), scope_bind).mappings().all()}

        rule_inserts, rule_updates, prompt_inserts, prompt_updates = [], [], [], []
        for (prj_id, port_ref_id), scope in scope_by_pair.items():
            payload = payload_by_prj[prj_id]
            ref = next((r for r in ref_rows if int(r['port_ref_id']) == int(port_ref_id)), None)
            label = _scope_label(ref['port_name'], ref['sector_name']) if ref else ''
            active = int(scope['is_active'])
            sid = int(scope['scope_id'])
            values = {
                'scope_id': sid, 'source_abbr_name': self._source_code(payload.source_name),
                'editable': _bit(payload.editable), 'symbol': payload.symbol,
                'mapping_type': payload.mapping_type, 'mapping_logic': payload.sp_as_reported_dataitem_logic,
                'calculation_logic': payload.calculation_logic, 'business_logic': payload.business_logic,
                'is_active': active, 'user': user,
            }
            if sid in existing_rules:
                rule_updates.append(values)
            elif active:
                rule_inserts.append(values)
            prompt_values = {
                'scope_id': sid, 'prj_id': prj_id, 'port_ref_id': int(port_ref_id),
                'required_by_scope': label, 'is_active': active, 'user': user,
            }
            if sid in existing_prompts:
                prompt_updates.append(prompt_values)
            elif active:
                prompt_inserts.append(prompt_values)
        if rule_inserts:
            self.db.execute(text("""
                INSERT INTO dbo.prj_attribute_business_rules_test
                (scope_id,source_abbr_name,editable,symbol,mapping_type,mapping_logic,calculation_logic,business_logic,is_active,created_at,updated_at,created_by,updated_by)
                VALUES (:scope_id,:source_abbr_name,:editable,:symbol,:mapping_type,:mapping_logic,:calculation_logic,:business_logic,:is_active,SYSUTCDATETIME(),SYSUTCDATETIME(),:user,:user)
            """), rule_inserts)
        if rule_updates:
            self.db.execute(text("""
                UPDATE dbo.prj_attribute_business_rules_test
                SET source_abbr_name=:source_abbr_name,editable=:editable,symbol=:symbol,mapping_type=:mapping_type,
                    mapping_logic=:mapping_logic,calculation_logic=:calculation_logic,business_logic=:business_logic,
                    is_active=:is_active,updated_at=SYSUTCDATETIME(),updated_by=:user
                WHERE scope_id=:scope_id
            """), rule_updates)
        if prompt_inserts:
            self.db.execute(text("""
                INSERT INTO dbo.prj_scanning_prompt_reference_test
                (scope_id,prj_id,port_ref_id,required_by_scope,is_active,created_at,updated_at,created_by,updated_by)
                VALUES (:scope_id,:prj_id,:port_ref_id,:required_by_scope,:is_active,SYSUTCDATETIME(),SYSUTCDATETIME(),:user,:user)
            """), prompt_inserts)
        if prompt_updates:
            self.db.execute(text("""
                UPDATE dbo.prj_scanning_prompt_reference_test
                SET port_ref_id=:port_ref_id,required_by_scope=:required_by_scope,is_active=:is_active,
                    updated_at=SYSUTCDATETIME(),updated_by=:user
                WHERE scope_id=:scope_id
            """), prompt_updates)

        if audit_rows:
            self.db.execute(text("""
                INSERT INTO dbo.audit_table_test
                (table_name,record_key,action,before_value,after_value,source_operation,performed_by,performed_at)
                VALUES (:table_name,:record_key,:action,:before_value,:after_value,:source_operation,:performed_by,SYSUTCDATETIME())
            """), audit_rows)
        return {'inserted': len(master_insert), 'updated': len(master_update)}
