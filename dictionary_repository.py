from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.master_dictionary import MasterDictionary
from app.utils.constants import PORTFOLIO_FIELD_MAP
from app.utils.excel_mapping import MASTER_FIELDS


class DictionaryRepository:
    def get_latest(self, db: Session, portfolio: str = "ALL") -> list[dict]:
        query = db.query(MasterDictionary).filter(MasterDictionary.is_active == True)  # noqa: E712
        query = self._apply_portfolio_filter(query, portfolio)
        return [self.to_dict(row) for row in query.all()]

    def get_all(self, db: Session) -> list[dict]:
        rows = db.query(MasterDictionary).all()
        return [self.to_dict(row) for row in rows]

    def get_soft_deleted(self, db: Session) -> list[dict]:
        rows = db.query(MasterDictionary).filter(MasterDictionary.is_active == False).all()  # noqa: E712
        return [self.to_dict(row) for row in rows]

    def get_by_prj_id(self, db: Session, prj_id: str):
        return db.query(MasterDictionary).filter(MasterDictionary.prj_id == prj_id).one_or_none()

    def search(self, db: Session, term: str = "", portfolio: str = "ALL", section: str = "") -> list[dict]:
        query = db.query(MasterDictionary).filter(MasterDictionary.is_active == True)  # noqa: E712
        query = self._apply_portfolio_filter(query, portfolio)
        if section:
            query = query.filter(MasterDictionary.where_in_financial_statement == section)
        if term:
            like_value = f"%{term}%"
            query = query.filter(
                or_(
                    MasterDictionary.prj_id.ilike(like_value),
                    MasterDictionary.prj_attribute_name.ilike(like_value),
                    MasterDictionary.prj_attribute_description.ilike(like_value),
                )
            )
        return [self.to_dict(row) for row in query.all()]

    def upsert_master(self, db: Session, record: dict, user_id: str) -> str:
        existing = self.get_by_prj_id(db, record["prj_id"])
        if existing is None:
            entity = MasterDictionary(**{k: record.get(k) for k in MASTER_FIELDS})
            entity.created_by = user_id
            entity.updated_by = user_id
            entity.is_active = True
            db.add(entity)
            return "INSERT"
        for field in MASTER_FIELDS:
            if field == "prj_id":
                continue
            setattr(existing, field, record.get(field))
        existing.updated_by = user_id
        existing.version_no = (existing.version_no or 1) + 1
        existing.is_active = True
        return "UPDATE"

    def soft_delete(self, db: Session, prj_id: str, user_id: str) -> None:
        entity = self.get_by_prj_id(db, prj_id)
        if entity:
            entity.is_active = False
            entity.updated_by = user_id
            entity.version_no = (entity.version_no or 1) + 1

    def reactivate(self, db: Session, prj_id: str, user_id: str) -> None:
        entity = self.get_by_prj_id(db, prj_id)
        if entity:
            entity.is_active = True
            entity.updated_by = user_id
            entity.version_no = (entity.version_no or 1) + 1

    def to_dict(self, entity: MasterDictionary) -> dict:
        data = {field: getattr(entity, field, None) for field in MASTER_FIELDS}
        data.update({
            "is_active": entity.is_active,
            "version_no": entity.version_no,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "created_by": entity.created_by,
            "updated_by": entity.updated_by,
        })
        return data

    def _apply_portfolio_filter(self, query, portfolio: str):
        field_name = PORTFOLIO_FIELD_MAP.get(portfolio)
        if not field_name:
            return query
        field = getattr(MasterDictionary, field_name)
        return query.filter(field == True)  # noqa: E712
