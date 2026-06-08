from sqlalchemy import and_, or_, case

from app.models.master_dictionary import MasterDictionary
from app.utils.constants import PORTFOLIO_FIELD_MAP


def normalize_portfolios(portfolios: list[str] | None, portfolio_sector: list[str] | None = None) -> list[str]:
    values: list[str] = []
    for source in (portfolios or []), (portfolio_sector or []):
        for item in source:
            if item and item not in values:
                values.append(item)
    if not values:
        values = ["ALL"]
    if "ALL" in values:
        return ["ALL"]
    return values


def apply_dictionary_filters(
    query,
    *,
    portfolios: list[str] | None = None,
    portfolio_sector: list[str] | None = None,
    prj_id: str = "",
    attribute_name: str = "",
    attribute_description: str = "",
    section: str = "",
    overlapped_attribute: bool = False,
    active_only: bool = True,
):
    if active_only:
        query = query.filter(MasterDictionary.is_active == True)  # noqa: E712

    selected_portfolios = normalize_portfolios(portfolios, portfolio_sector)
    if "ALL" not in selected_portfolios:
        portfolio_conditions = []
        for portfolio in selected_portfolios:
            field_name = PORTFOLIO_FIELD_MAP.get(portfolio)
            if field_name:
                portfolio_conditions.append(getattr(MasterDictionary, field_name) == True)  # noqa: E712
        if portfolio_conditions:
            query = query.filter(or_(*portfolio_conditions))

    if overlapped_attribute:
        # SQLAlchemy/SQL Server safe expression for counting selected sector flags.
        # Do not use field.cast(int) because Python int is not a SQLAlchemy TypeEngine.
        # This works for BIT/boolean columns as well as nullable values.
        overlap_count = None
        for field_name in PORTFOLIO_FIELD_MAP.values():
            field = getattr(MasterDictionary, field_name)
            flag_value = case((field == True, 1), else_=0)  # noqa: E712
            overlap_count = flag_value if overlap_count is None else overlap_count + flag_value
        if overlap_count is not None:
            query = query.filter(overlap_count > 1)

    if prj_id:
        query = query.filter(MasterDictionary.prj_id.ilike(f"%{prj_id.strip()}%"))
    if attribute_name:
        query = query.filter(MasterDictionary.prj_attribute_name.ilike(f"%{attribute_name.strip()}%"))
    if attribute_description:
        query = query.filter(MasterDictionary.prj_attribute_description.ilike(f"%{attribute_description.strip()}%"))
    if section:
        query = query.filter(MasterDictionary.where_in_financial_statement == section)

    return query
