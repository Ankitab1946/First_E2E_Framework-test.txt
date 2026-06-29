from typing import Any, Optional
from pydantic import BaseModel, Field


class DictionaryFilterRequest(BaseModel):
    portfolios: list[str] = Field(default_factory=lambda: ["ALL"])
    prj_id: str = ""
    attribute_name: str = ""
    attribute_description: str = ""
    section: str = ""
    portfolio_sector: list[str] = Field(default_factory=list)
    overlapped_attribute: bool = False
    active_only: bool = True
    limit: int = 2000


class AttributePayload(BaseModel):
    prj_id: str
    prj_attribute_name: str
    prj_attribute_description: Optional[str] = None
    prj_physical_attribute_name: Optional[str] = None
    editable: Optional[bool] = None
    percentage_ratio: Optional[str] = None
    calculated_or_reported: Optional[str] = None
    calculation_logic: Optional[str] = None
    calculation_logic_details: Optional[str] = None
    where_in_financial_statement: Optional[str] = None
    required_by_corporates: Optional[bool] = None
    required_by_banks: Optional[bool] = None
    required_by_insurance: Optional[bool] = None
    required_by_downstream: Optional[bool] = None
    version_update: Optional[str] = None
    release_scope: Optional[str] = None
    mapping_type: Optional[str] = None
    calculation_in_prj: Optional[str] = None
    editable_in_historicals: Optional[bool] = None
    sign_flipping: Optional[bool] = None
    gc_template_attribute_name: Optional[str] = None
    sp_standardisation_attribute_name: Optional[str] = None
    sp_standardisation_dataitem_id: Optional[str] = None
    sp_as_reported_dataitem_id: Optional[str] = None
    updates: Optional[str] = None
    updated_on: Optional[Any] = None
    zeus_attribute: Optional[str] = None
    zeus_table_name: Optional[str] = None
    zeus_description: Optional[str] = None
    comments: Optional[str] = None
    snl_dataitemid: Optional[str] = None
    scanned_calculated: Optional[str] = None


class AuditFilterRequest(DictionaryFilterRequest):
    action_type: str = ""
    changed_by: str = ""
    include_full_history: bool = False


class OperationResponse(BaseModel):
    status: str
    batch_id: str | None = None
    message: str | None = None
    records_processed: int | None = None
    data: dict | list[dict] | None = None

class UiDisplayPayload(BaseModel):
    display_id: int | None = None
    prj_id: str
    prj_attribute_name: str | None = None
    sector: str
    display_order: int | None = None
    display_name: str | None = None
    section: str | None = None
    subsection: str | None = None
    view_name: str | None = None
    description: str | None = None

class BusinessRulePayload(BaseModel):
    prj_id: str
    sector: str
    source_abbr_name: str | None = 'SNPAR'
    editable: bool | None = None
    symbol: str | None = None
    mapping_type: str | None = None
    mapping_logic: str | None = None
    calculation_logic: str | None = None
    business_logic: str | None = None

class PromptPayload(BaseModel):
    prj_id: str
    sector: str
    required_by_scope: str | None = None
    attribute_name: str | None = None
    section: str | None = None
    sub_section: str | None = None
    data_type: str | None = None
    calculated_or_reported: str | None = None
    calculation_logic: str | None = None
    segment: str | None = None
    subcomponent_total: str | None = None
    attribute_description: str | None = None
    examples: str | None = None
    source_sheet_name: str | None = None
