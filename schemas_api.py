from pydantic import BaseModel, Field

class AttributeUpsert(BaseModel):
    prj_id: str
    prj_attribute_name: str
    prj_attribute_description: str | None = None
    prj_physical_attribute_name: str | None = None
    where_in_financial_statement: str | None = None
    version_update: str | None = None
    calculated_or_reported: str | None = None
    calculation_logic: str | None = None
    calculation_logic_details: str | None = None
    sign_flipping_value: str | None = None
    mapping_type: str | None = None
    sp_standardisation_dataitem_id: str | None = None
    sp_as_reported_dataitem_logic: str | None = None
    calculated_in_cfv: str | None = None
    editable_in_historicals: str | None = None
    required_portfolios: list[str] = Field(default_factory=list)
    source_name: str | None = 'S&P CAPIQ AS REPORTED DATA'
    editable: str | None = None
    symbol: str | None = None
    business_logic: str | None = None

class FilterRequest(BaseModel):
    portfolios: list[str] = Field(default_factory=list)
    prj_id: str | None = None
    attribute_name: str | None = None
    attribute_description: str | None = None
    section: str | None = None
    overlapped_only: bool = False
    include_deleted: bool = False

class PromptUpsert(BaseModel):
    scope_id: int | None = None
    prj_id: str
    port_ref_id: int | None = None
    required_by_scope: str | None = None
    attribute_name: str | None = None
    section: str | None = None
    sub_section: str | None = None
    data_type: str | None = None
    calculated_or_reported: str | None = None
    calculation_logic: str | None = None
    segment: str | None = None
    attribute_description: str | None = None
    display_order: int | None = None

class AuditFilterRequest(BaseModel):
    table_name: str | None = None
    record_key: str | None = None
    action: str | None = None
    performed_by: str | None = None
    source_operation: str | None = None

class PortfolioUpsert(BaseModel):
    port_name: str
    sector_name: str | None = None
    sub_sector: str | None = None
    remark: str | None = None

class UploadFinalizeRequest(BaseModel):
    batch_reference: str | None = None
    confirm: bool = False

class AdminUserRequest(BaseModel):
    username: str | None = None
