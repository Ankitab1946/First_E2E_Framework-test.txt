from app.core.config import get_settings
from app.core.database import get_session_factory
from app.repositories.dictionary_repository import DictionaryRepository
from app.utils.constants import PORTFOLIO_FIELD_MAP
from app.utils.sample_data import get_sample_records


class DictionaryService:
    def __init__(self):
        self.settings = get_settings()
        self.repository = DictionaryRepository()

    def get_latest_records(self, portfolio: str = "ALL") -> list[dict]:
        if not self.settings.enable_db:
            return self._filter_sample(get_sample_records(), portfolio)
        SessionLocal = get_session_factory()
        with SessionLocal() as db:
            return self.repository.get_latest(db, portfolio=portfolio)

    def get_all_records(self) -> list[dict]:
        if not self.settings.enable_db:
            return get_sample_records()
        SessionLocal = get_session_factory()
        with SessionLocal() as db:
            return self.repository.get_all(db)

    def get_soft_deleted_records(self) -> list[dict]:
        if not self.settings.enable_db:
            return []
        SessionLocal = get_session_factory()
        with SessionLocal() as db:
            return self.repository.get_soft_deleted(db)

    def search_records(self, term: str = "", portfolio: str = "ALL", section: str = "") -> list[dict]:
        if not self.settings.enable_db:
            records = self._filter_sample(get_sample_records(), portfolio)
            if section:
                records = [r for r in records if r.get("where_in_financial_statement") == section]
            if term:
                term_lower = term.lower()
                records = [
                    r for r in records
                    if term_lower in str(r.get("prj_id", "")).lower()
                    or term_lower in str(r.get("prj_attribute_name", "")).lower()
                    or term_lower in str(r.get("prj_attribute_description", "")).lower()
                ]
            return records
        SessionLocal = get_session_factory()
        with SessionLocal() as db:
            return self.repository.search(db, term=term, portfolio=portfolio, section=section)

    def _filter_sample(self, records: list[dict], portfolio: str) -> list[dict]:
        field_name = PORTFOLIO_FIELD_MAP.get(portfolio)
        if not field_name:
            return records
        return [record for record in records if bool(record.get(field_name))]
