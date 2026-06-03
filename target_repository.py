from sqlalchemy.orm import Session
from app.models.target_tables import PrjAttribute, PrjAttrBusinessLogic, PrjAttrBusinessLogicScope


class TargetRepository:
    def upsert_all(self, db: Session, record: dict, user_id: str) -> None:
        self._upsert_prj_attribute(db, record, user_id)
        self._upsert_business_logic(db, record, user_id)
        self._upsert_scope(db, record, user_id)

    def soft_delete_all(self, db: Session, prj_id: str, user_id: str) -> None:
        for model in [PrjAttribute, PrjAttrBusinessLogic, PrjAttrBusinessLogicScope]:
            entity = db.query(model).filter(model.prj_id == prj_id).one_or_none()
            if entity:
                entity.is_active = False
                entity.updated_by = user_id
                entity.version_no = (entity.version_no or 1) + 1

    def reactivate_all(self, db: Session, prj_id: str, user_id: str) -> None:
        for model in [PrjAttribute, PrjAttrBusinessLogic, PrjAttrBusinessLogicScope]:
            entity = db.query(model).filter(model.prj_id == prj_id).one_or_none()
            if entity:
                entity.is_active = True
                entity.updated_by = user_id
                entity.version_no = (entity.version_no or 1) + 1

    def _upsert_prj_attribute(self, db, record, user_id):
        entity = db.query(PrjAttribute).filter(PrjAttribute.prj_id == record["prj_id"]).one_or_none()
        values = {
            "prj_id": record.get("prj_id"),
            "prj_attribute_id": record.get("prj_attribute_name"),
            "prj_attribute_description": record.get("prj_attribute_description"),
            "prj_physical_attribute_name": record.get("prj_physical_attribute_name"),
            "where_in_financial_statement": record.get("where_in_financial_statement"),
            "version_update": record.get("version_update"),
            "updated_by": user_id,
            "is_active": True,
        }
        if entity is None:
            entity = PrjAttribute(**values, created_by=user_id)
            db.add(entity)
        else:
            for k, v in values.items():
                setattr(entity, k, v)
            entity.version_no = (entity.version_no or 1) + 1

    def _upsert_business_logic(self, db, record, user_id):
        entity = db.query(PrjAttrBusinessLogic).filter(PrjAttrBusinessLogic.prj_id == record["prj_id"]).one_or_none()
        values = {k: record.get(k) for k in [
            "prj_id", "editable", "percentage_ratio", "calculation_logic", "release_scope",
            "mapping_type", "calculation_in_prj", "editable_in_historicals", "sign_flipping",
            "gc_template_attribute_name", "sp_standardisation_attribute_name",
            "sp_standardisation_dataitem_id", "sp_as_reported_dataitem_id", "updates", "updated_on",
            "zeus_attribute", "zeus_table_name", "zeus_description", "comments", "snl_dataitemid", "scanned_calculated"
        ]}
        values.update({"updated_by": user_id, "is_active": True})
        if entity is None:
            entity = PrjAttrBusinessLogic(**values, created_by=user_id)
            db.add(entity)
        else:
            for k, v in values.items():
                setattr(entity, k, v)
            entity.version_no = (entity.version_no or 1) + 1

    def _upsert_scope(self, db, record, user_id):
        entity = db.query(PrjAttrBusinessLogicScope).filter(PrjAttrBusinessLogicScope.prj_id == record["prj_id"]).one_or_none()
        values = {k: record.get(k) for k in [
            "prj_id", "required_by_corporates", "required_by_banks", "required_by_insurance", "required_by_downstream"
        ]}
        values.update({"updated_by": user_id, "is_active": True})
        if entity is None:
            entity = PrjAttrBusinessLogicScope(**values, created_by=user_id)
            db.add(entity)
        else:
            for k, v in values.items():
                setattr(entity, k, v)
            entity.version_no = (entity.version_no or 1) + 1
