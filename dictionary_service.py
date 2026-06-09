from app.core.config import get_settings
from app.core.database import get_session_factory
from app.repositories.dictionary_repository import DictionaryRepository
from app.utils.constants import PORTFOLIO_FIELD_MAP
from app.repositories.filter_utils import normalize_portfolios, resolve_portfolio_fields
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


    def filter_records(self, filters: dict) -> list[dict]:
        if not self.settings.enable_db:
            records = get_sample_records()
            return self._filter_records_in_memory(records, filters)
        SessionLocal = get_session_factory()
        with SessionLocal() as db:
            return self.repository.filter_records(db, filters)

    def get_filter_options(self) -> dict:
        if not self.settings.enable_db:
            records = get_sample_records()
            return {
                "prj_ids": sorted({str(r.get("prj_id")) for r in records if r.get("prj_id")}),
                "attribute_names": sorted({str(r.get("prj_attribute_name")) for r in records if r.get("prj_attribute_name")}),
                "sections": sorted({str(r.get("where_in_financial_statement")) for r in records if r.get("where_in_financial_statement")}),
            }
        SessionLocal = get_session_factory()
        with SessionLocal() as db:
            return {
                "prj_ids": self.repository.get_distinct_prj_ids(db),
                "attribute_names": self.repository.get_distinct_attribute_names(db),
                "sections": self.repository.get_distinct_sections(db),
            }

    def _filter_records_in_memory(self, records: list[dict], filters: dict) -> list[dict]:
        selected_portfolios = normalize_portfolios(filters.get("portfolios"), filters.get("portfolio_sector"))
        selected_fields = resolve_portfolio_fields(selected_portfolios)
        if selected_fields:
            # Multi-select portfolio filtering is intersection/AND.
            # Example: FI Banks + FI Insurance returns only records required by both.
            records = [r for r in records if all(bool(r.get(f)) for f in selected_fields)]
        if filters.get("overlapped_attribute"):
            sector_fields = list(PORTFOLIO_FIELD_MAP.values())
            records = [r for r in records if sum(1 for f in sector_fields if bool(r.get(f))) > 1]
        if filters.get("prj_id"):
            value = str(filters["prj_id"]).lower()
            records = [r for r in records if value in str(r.get("prj_id", "")).lower()]
        if filters.get("attribute_name"):
            value = str(filters["attribute_name"]).lower()
            records = [r for r in records if value in str(r.get("prj_attribute_name", "")).lower()]
        if filters.get("attribute_description"):
            value = str(filters["attribute_description"]).lower()
            records = [r for r in records if value in str(r.get("prj_attribute_description", "")).lower()]
        if filters.get("section"):
            records = [r for r in records if r.get("where_in_financial_statement") == filters.get("section")]
        return records[: int(filters.get("limit") or 2000)]

    def _filter_sample(self, records: list[dict], portfolio: str) -> list[dict]:
        field_name = PORTFOLIO_FIELD_MAP.get(portfolio)
        if not field_name:
            return records
        return [record for record in records if bool(record.get(field_name))]
