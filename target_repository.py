from sqlalchemy.orm import Session


def _model_values(model, values: dict) -> dict:
    """Keep only columns actually defined by the SQLAlchemy model.

    This prevents Master Dictionary Excel fields from being passed as invalid
    keyword arguments to legacy model variants during an upload.
    """
    allowed = {column.name for column in model.__table__.columns}
    return {key: value for key, value in values.items() if key in allowed}
from DataDictionaryAdminApp.model.target_tables import PrjAttribute, PrjAttrBusinessLogic, PrjAttrBusinessLogicScope


class TargetRepository:
    def build_cache(self, db: Session, prj_ids: list[str]) -> dict:
        if not prj_ids:
            return {"attribute": {}, "logic": {}, "scope": {}}
        return {
            "attribute": {x.prj_id: x for x in db.query(PrjAttribute).filter(PrjAttribute.prj_id.in_(prj_ids)).all()},
            "logic": {x.prj_id: x for x in db.query(PrjAttrBusinessLogic).filter(PrjAttrBusinessLogic.prj_id.in_(prj_ids)).all()},
            "scope": {x.prj_id: x for x in db.query(PrjAttrBusinessLogicScope).filter(PrjAttrBusinessLogicScope.prj_id.in_(prj_ids)).all()},
        }

    def upsert_all(self, db: Session, record: dict, user_id: str, cache: dict | None = None) -> None:
        self._upsert_prj_attribute(db, record, user_id, None if cache is None else cache["attribute"])
        self._upsert_business_logic(db, record, user_id, None if cache is None else cache["logic"])
        self._upsert_scope(db, record, user_id, None if cache is None else cache["scope"])

    def soft_delete_all(self, db: Session, prj_id: str, user_id: str, cache: dict | None = None) -> None:
        from datetime import datetime, timezone
        for key, model in [("attribute", PrjAttribute), ("logic", PrjAttrBusinessLogic), ("scope", PrjAttrBusinessLogicScope)]:
            entity = cache[key].get(prj_id) if cache else db.query(model).filter(model.prj_id == prj_id).one_or_none()
            if entity:
                entity.is_active=False; entity.is_deleted=True; entity.deleted_at=datetime.now(timezone.utc); entity.deleted_by=user_id; entity.updated_by=user_id; entity.version_no=(entity.version_no or 1)+1

    def reactivate_all(self, db: Session, prj_id: str, user_id: str, cache: dict | None = None) -> None:
        for key, model in [("attribute", PrjAttribute), ("logic", PrjAttrBusinessLogic), ("scope", PrjAttrBusinessLogicScope)]:
            entity = cache[key].get(prj_id) if cache else db.query(model).filter(model.prj_id == prj_id).one_or_none()
            if entity:
                entity.is_active=True; entity.is_deleted=False; entity.deleted_at=None; entity.deleted_by=None; entity.updated_by=user_id; entity.version_no=(entity.version_no or 1)+1

    def _upsert_prj_attribute(self, db, record, user_id, cache=None):
        entity = cache.get(record["prj_id"]) if cache is not None else db.query(PrjAttribute).filter(PrjAttribute.prj_id == record["prj_id"]).one_or_none()
        values={"prj_id":record.get("prj_id"),"prj_attribute_id":record.get("prj_attribute_name"),"prj_attribute_description":record.get("prj_attribute_description"),"prj_physical_attribute_name":record.get("prj_physical_attribute_name"),"where_in_financial_statement":record.get("where_in_financial_statement"),"version_update":record.get("version_update"),"updated_by":user_id,"is_active":True,"is_deleted":False,"deleted_at":None,"deleted_by":None}
        if entity is None:
            entity=PrjAttribute(**_model_values(PrjAttribute, {**values, "created_by": user_id}));db.add(entity)
            if cache is not None: cache[record["prj_id"]]=entity
        else:
            for k,v in _model_values(PrjAttribute, values).items(): setattr(entity,k,v)
            entity.version_no=(entity.version_no or 1)+1

    def _upsert_business_logic(self, db, record, user_id, cache=None):
        entity = cache.get(record["prj_id"]) if cache is not None else db.query(PrjAttrBusinessLogic).filter(PrjAttrBusinessLogic.prj_id == record["prj_id"]).one_or_none()
        values={k:record.get(k) for k in ["prj_id","editable","percentage_ratio","calculation_logic","release_scope","mapping_type","calculation_in_prj","editable_in_historicals","sign_flipping","gc_template_attribute_name","sp_standardisation_attribute_name","sp_standardisation_dataitem_id","sp_as_reported_dataitem_id","updates","updated_on","zeus_attribute","zeus_table_name","zeus_description","comments","snl_dataitemid","scanned_calculated"]};values.update({"updated_by":user_id,"is_active":True,"is_deleted":False,"deleted_at":None,"deleted_by":None})
        if entity is None:
            entity=PrjAttrBusinessLogic(**_model_values(PrjAttrBusinessLogic, {**values, "created_by": user_id}));db.add(entity)
            if cache is not None: cache[record["prj_id"]]=entity
        else:
            for k,v in _model_values(PrjAttrBusinessLogic, values).items(): setattr(entity,k,v)
            entity.version_no=(entity.version_no or 1)+1

    def _upsert_scope(self, db, record, user_id, cache=None):
        entity = cache.get(record["prj_id"]) if cache is not None else db.query(PrjAttrBusinessLogicScope).filter(PrjAttrBusinessLogicScope.prj_id == record["prj_id"]).one_or_none()
        values={k:record.get(k) for k in ["prj_id","required_by_corporates","required_by_banks","required_by_insurance","required_by_downstream"]};values.update({"updated_by":user_id,"is_active":True,"is_deleted":False,"deleted_at":None,"deleted_by":None})
        if entity is None:
            entity=PrjAttrBusinessLogicScope(**_model_values(PrjAttrBusinessLogicScope, {**values, "created_by": user_id}));db.add(entity)
            if cache is not None: cache[record["prj_id"]]=entity
        else:
            for k,v in _model_values(PrjAttrBusinessLogicScope, values).items(): setattr(entity,k,v)
            entity.version_no=(entity.version_no or 1)+1
