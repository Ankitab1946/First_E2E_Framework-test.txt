import json
from datetime import datetime, timezone
from uuid import uuid4
from DataDictionaryAdminApp.config import get_settings
from DataDictionaryAdminApp.core.database import get_session_factory
from DataDictionaryAdminApp.model.target_tables import PrjAttribute, PrjAttrBusinessLogic, PrjAttrBusinessLogicScope
from DataDictionaryAdminApp.repositories.audit_repository import AuditRepository
from DataDictionaryAdminApp.repositories.dictionary_repository import DictionaryRepository
from DataDictionaryAdminApp.repositories.target_repository import TargetRepository
from DataDictionaryAdminApp.service.configuration_service import ConfigurationService


class FinalizationService:
    def __init__(self):
        self.settings = get_settings()
        self.dictionary_repo = DictionaryRepository()
        self.target_repo = TargetRepository()
        self.audit_repo = AuditRepository()

    def finalize(self, changes: list[dict], user_id: str, source_module: str) -> dict:
        batch_id = str(uuid4())
        if not changes:
            return {"status": "NO_CHANGES", "batch_id": batch_id, "records_processed": 0}
        if not self.settings.enable_db:
            return {"status":"SIMULATED_SUCCESS","batch_id":batch_id,"records_processed":len(changes),"message":"ENABLE_DB=false, so no database write was performed."}
        SessionLocal = get_session_factory()
        prj_ids = list(dict.fromkeys(str(x["prj_id"]).strip() for x in changes if x.get("prj_id")))
        with SessionLocal() as db:
            try:
                existing = {x.prj_id: x for x in db.query(__import__('DataDictionaryAdminApp.model.master_dictionary', fromlist=['MasterDictionary']).MasterDictionary).filter(__import__('DataDictionaryAdminApp.model.master_dictionary', fromlist=['MasterDictionary']).MasterDictionary.prj_id.in_(prj_ids)).all()}
                target_cache = self.target_repo.build_cache(db, prj_ids)
                for change in changes:
                    self._finalize_one(db, batch_id=batch_id, record=change, user_id=user_id, source_module=source_module, existing_cache=existing, target_cache=target_cache)
                self._sync_scopes_in_transaction(db, prj_ids, user_id)
                db.commit()
                return {"status":"SUCCESS","batch_id":batch_id,"records_processed":len(changes),"finalized_at":datetime.now(timezone.utc).isoformat()}
            except Exception:
                db.rollback(); raise

    def _sync_scopes_in_transaction(self, db, prj_ids: list[str], user_id: str) -> None:
        """Synchronise every portfolio scope in one DB transaction and a fixed number of queries."""
        if not prj_ids:
            return
        from DataDictionaryAdminApp.model.master_dictionary import MasterDictionary
        from DataDictionaryAdminApp.model.configuration_tables import PortfolioReference, AttributePortfolioScope
        from DataDictionaryAdminApp.service.configuration_service import FLAG_TO_SECTOR
        masters = {x.prj_id:x for x in db.query(MasterDictionary).filter(MasterDictionary.prj_id.in_(prj_ids)).all()}
        refs = {(x.port_name, x.sector_name):x.port_ref_id for x in db.query(PortfolioReference).filter(PortfolioReference.is_active == True).all()}
        existing = {(x.prj_id,x.port_ref_id):x for x in db.query(AttributePortfolioScope).filter(AttributePortfolioScope.prj_id.in_(prj_ids)).all()}
        for prj_id, master in masters.items():
            wanted={refs[p] for field,p in FLAG_TO_SECTOR.items() if bool(getattr(master,field)) and p in refs}
            for port_ref_id in wanted:
                entity=existing.get((prj_id,port_ref_id))
                if entity:
                    entity.is_active=True;entity.is_deleted=False;entity.deleted_at=None;entity.deleted_by=None;entity.description=master.prj_attribute_description;entity.updated_by=user_id
                else:
                    db.add(AttributePortfolioScope(prj_id=prj_id,port_ref_id=port_ref_id,description=master.prj_attribute_description,created_by=user_id,updated_by=user_id))
            for (existing_prj, port_ref_id), entity in existing.items():
                if existing_prj == prj_id and port_ref_id not in wanted:
                    entity.is_active=False;entity.is_deleted=True;entity.updated_by=user_id

    def create_attribute(self, record: dict, user_id: str) -> dict:
        record = {**record, "delta_type": "NEW"}
        return self.finalize([record], user_id=user_id, source_module="CREATE_ATTRIBUTE")

    def update_attribute(self, record: dict, user_id: str) -> dict:
        record = {**record, "delta_type": "UPDATED"}
        return self.finalize([record], user_id=user_id, source_module="EDIT_ATTRIBUTE")

    def soft_delete_attribute(self, prj_id: str, user_id: str) -> dict:
        return self.finalize([{"prj_id": prj_id, "delta_type": "DELETED"}], user_id=user_id, source_module="EDIT_ATTRIBUTE")

    def reactivate_attribute(self, prj_id: str, user_id: str) -> dict:
        return self.finalize([{"prj_id": prj_id, "delta_type": "REACTIVATED"}], user_id=user_id, source_module="REACTIVATE_ATTRIBUTE")

    def _finalize_one(self, db, *, batch_id: str, record: dict, user_id: str, source_module: str, existing_cache: dict | None = None, target_cache: dict | None = None) -> None:
        delta_type = record.get("delta_type", "UPDATED")
        prj_id = record["prj_id"]
        existing = existing_cache.get(prj_id) if existing_cache is not None else self.dictionary_repo.get_by_prj_id(db, prj_id)
        if delta_type == "NEW" and existing is not None:
            raise ValueError(f"PRJ ID already exists: {prj_id}. Refresh Create New Attribute to generate a new PRJ ID.")
        old_value = self.dictionary_repo.to_dict(existing) if existing else None

        self.audit_repo.log_history(
            db,
            batch_id=batch_id,
            prj_id=prj_id,
            table_name="master_dictionary",
            action_type=delta_type,
            snapshot=old_value,
            changed_by=user_id,
        )
        self._archive_target_history(db, batch_id=batch_id, prj_id=prj_id, action_type=delta_type, changed_by=user_id, target_cache=target_cache)

        if delta_type == "DELETED":
            self.dictionary_repo.soft_delete(db, prj_id, user_id)
            self.target_repo.soft_delete_all(db, prj_id, user_id, target_cache)
            action = "DELETE"
            new_value = {"prj_id": prj_id, "is_active": False}
        elif delta_type == "REACTIVATED":
            self.dictionary_repo.reactivate(db, prj_id, user_id)
            self.target_repo.reactivate_all(db, prj_id, user_id, target_cache)
            action = "REACTIVATE"
            new_value = {"prj_id": prj_id, "is_active": True}
        else:
            # Preserve the physical name supplied in Excel. If Excel leaves it blank,
            # preserve an existing name; only new blank records receive a short unique name.
            supplied_physical_name = str(record.get("prj_physical_attribute_name") or "").strip()
            if supplied_physical_name:
                record["prj_physical_attribute_name"] = supplied_physical_name[:255]
            elif existing and getattr(existing, "prj_physical_attribute_name", None):
                record["prj_physical_attribute_name"] = existing.prj_physical_attribute_name
            else:
                record["prj_physical_attribute_name"] = self._next_unique_physical_name(
                    db, record.get("prj_attribute_name", ""), prj_id
                )
            action = self.dictionary_repo.upsert_master(db, record, user_id, existing=existing)
            if existing is None and existing_cache is not None:
                existing_cache[prj_id] = db.new and next((x for x in db.new if getattr(x, "prj_id", None) == prj_id), None)
            self.target_repo.upsert_all(db, record, user_id, target_cache)
            new_value = record

        self.audit_repo.log_audit(
            db,
            batch_id=batch_id,
            prj_id=prj_id,
            table_name="ALL_TARGET_TABLES",
            action_type=action,
            source_module=source_module,
            old_value=old_value,
            new_value=new_value,
            changed_by=user_id,
        )

    @staticmethod
    def _short_physical_name(attribute_name: str, prj_id: str) -> str:
        import re
        abbreviations = {"buildings": "bldgs", "building": "bldg", "property": "prop", "financial": "fin", "statement": "stmt", "calculation": "calc"}
        words = re.sub(r"[^a-z0-9]+", " ", str(attribute_name or "").lower()).split()
        base = "_".join(abbreviations.get(word, word) for word in words).strip("_")
        return (base or f"prj_{str(prj_id).lower()}")[:240]

    def _next_unique_physical_name(self, db, attribute_name: str, prj_id: str) -> str:
        from DataDictionaryAdminApp.model.master_dictionary import MasterDictionary
        base = self._short_physical_name(attribute_name, prj_id)
        existing_names = {str(x[0]).lower() for x in db.query(MasterDictionary.prj_physical_attribute_name).filter(MasterDictionary.prj_physical_attribute_name.isnot(None)).all()}
        candidate, counter = base, 2
        while candidate.lower() in existing_names:
            suffix = f"_{counter}"
            candidate = f"{base[:240-len(suffix)]}{suffix}"
            counter += 1
        return candidate

    def _archive_target_history(self, db, *, batch_id: str, prj_id: str, action_type: str, changed_by: str, target_cache: dict | None = None) -> None:
        targets = [
            ("prj_attribute", PrjAttribute),
            ("prj_attr_business_logic", PrjAttrBusinessLogic),
            ("prj_attr_business_logic_scope", PrjAttrBusinessLogicScope),
        ]
        for table_name, model in targets:
            cache_key = {"prj_attribute": "attribute", "prj_attr_business_logic": "logic", "prj_attr_business_logic_scope": "scope"}[table_name]
            entity = target_cache[cache_key].get(prj_id) if target_cache is not None else db.query(model).filter(model.prj_id == prj_id).one_or_none()
            snapshot = self._entity_to_dict(entity) if entity else None
            self.audit_repo.log_history(
                db,
                batch_id=batch_id,
                prj_id=prj_id,
                table_name=table_name,
                action_type=action_type,
                snapshot=snapshot,
                changed_by=changed_by,
            )

    def _entity_to_dict(self, entity) -> dict | None:
        if entity is None:
            return None
        return {column.name: getattr(entity, column.name, None) for column in entity.__table__.columns}
