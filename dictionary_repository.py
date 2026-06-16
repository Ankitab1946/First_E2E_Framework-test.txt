from sqlalchemy import or_, distinct
from sqlalchemy.orm import Session
from app.models.master_dictionary import MasterDictionary
from app.repositories.filter_utils import apply_dictionary_filters
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


    def filter_records(self, db: Session, filters: dict) -> list[dict]:
        query = db.query(MasterDictionary)
        query = apply_dictionary_filters(
            query,
            portfolios=filters.get("portfolios"),
            portfolio_sector=filters.get("portfolio_sector"),
            prj_id=filters.get("prj_id", ""),
            attribute_name=filters.get("attribute_name", ""),
            attribute_description=filters.get("attribute_description", ""),
            section=filters.get("section", ""),
            overlapped_attribute=bool(filters.get("overlapped_attribute", False)),
            active_only=bool(filters.get("active_only", True)),
        )
        limit = int(filters.get("limit") or 2000)
        return [self.to_dict(row) for row in query.order_by(MasterDictionary.prj_id).limit(limit).all()]


    def get_next_prj_id(self, db: Session, prefix: str = "PRJ", width: int = 3) -> str:
        """Generate the next unique PRJ ID from values already stored in DB.

        Existing IDs such as PRJ001, PRJ002 produce PRJ003. If the table
        contains mixed formats, the largest numeric suffix for the selected
        prefix is used and the configured width is preserved as a minimum.
        """
        rows = db.query(MasterDictionary.prj_id).all()
        max_number = 0
        normalized_prefix = (prefix or "PRJ").strip().upper()
        for row in rows:
            value = str(row[0] or "").strip().upper()
            if not value.startswith(normalized_prefix):
                continue
            suffix = value[len(normalized_prefix):]
            if suffix.isdigit():
                max_number = max(max_number, int(suffix))

        next_number = max_number + 1
        while True:
            candidate = f"{normalized_prefix}{next_number:0{width}d}"
            if self.get_by_prj_id(db, candidate) is None:
                return candidate
            next_number += 1

    def get_distinct_prj_ids(self, db: Session) -> list[str]:
        rows = db.query(MasterDictionary.prj_id).order_by(MasterDictionary.prj_id).all()
        return [row[0] for row in rows if row[0]]

    def get_distinct_attribute_names(self, db: Session) -> list[str]:
        rows = db.query(distinct(MasterDictionary.prj_attribute_name)).order_by(MasterDictionary.prj_attribute_name).all()
        return [row[0] for row in rows if row[0]]

    def get_distinct_sections(self, db: Session) -> list[str]:
        rows = db.query(distinct(MasterDictionary.where_in_financial_statement)).order_by(MasterDictionary.where_in_financial_statement).all()
        return [row[0] for row in rows if row[0]]

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
