import json
from datetime import datetime, timezone
from uuid import uuid4
from app.core.config import get_settings
from app.core.database import get_session_factory
from app.models.target_tables import PrjAttribute, PrjAttrBusinessLogic, PrjAttrBusinessLogicScope
from app.repositories.audit_repository import AuditRepository
from app.repositories.dictionary_repository import DictionaryRepository
from app.repositories.target_repository import TargetRepository


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
            return {
                "status": "SIMULATED_SUCCESS",
                "batch_id": batch_id,
                "records_processed": len(changes),
                "message": "ENABLE_DB=false, so no database write was performed.",
            }

        SessionLocal = get_session_factory()
        with SessionLocal() as db:
            try:
                for change in changes:
                    self._finalize_one(db, batch_id=batch_id, record=change, user_id=user_id, source_module=source_module)
                db.commit()
                return {
                    "status": "SUCCESS",
                    "batch_id": batch_id,
                    "records_processed": len(changes),
                    "finalized_at": datetime.now(timezone.utc).isoformat(),
                }
            except Exception:
                db.rollback()
                raise

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

    def _finalize_one(self, db, *, batch_id: str, record: dict, user_id: str, source_module: str) -> None:
        delta_type = record.get("delta_type", "UPDATED")
        prj_id = record["prj_id"]
        existing = self.dictionary_repo.get_by_prj_id(db, prj_id)
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
        self._archive_target_history(db, batch_id=batch_id, prj_id=prj_id, action_type=delta_type, changed_by=user_id)

        if delta_type == "DELETED":
            self.dictionary_repo.soft_delete(db, prj_id, user_id)
            self.target_repo.soft_delete_all(db, prj_id, user_id)
            action = "DELETE"
            new_value = {"prj_id": prj_id, "is_active": False}
        elif delta_type == "REACTIVATED":
            self.dictionary_repo.reactivate(db, prj_id, user_id)
            self.target_repo.reactivate_all(db, prj_id, user_id)
            action = "REACTIVATE"
            new_value = {"prj_id": prj_id, "is_active": True}
        else:
            action = self.dictionary_repo.upsert_master(db, record, user_id)
            self.target_repo.upsert_all(db, record, user_id)
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

    def _archive_target_history(self, db, *, batch_id: str, prj_id: str, action_type: str, changed_by: str) -> None:
        targets = [
            ("prj_attribute", PrjAttribute),
            ("prj_attr_business_logic", PrjAttrBusinessLogic),
            ("prj_attr_business_logic_scope", PrjAttrBusinessLogicScope),
        ]
        for table_name, model in targets:
            entity = db.query(model).filter(model.prj_id == prj_id).one_or_none()
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
