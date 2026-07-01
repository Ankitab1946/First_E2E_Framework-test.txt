from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from DataDictionaryAdminApp.core.database import Base

class AuditMixin:
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), default="sysuser", nullable=False)
    updated_by: Mapped[str] = mapped_column(String(128), default="sysuser", nullable=False)

class AttributeMaster(Base, AuditMixin):
    __tablename__ = "prj_attribute_master_test"
    prj_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    prj_attribute_name: Mapped[str] = mapped_column(String(500), nullable=False)
    prj_attribute_description: Mapped[str | None] = mapped_column(Text)
    prj_physical_attribute_name: Mapped[str | None] = mapped_column(String(500), unique=True)
    where_in_financial_statement: Mapped[str | None] = mapped_column(String(255))
    version_update: Mapped[str | None] = mapped_column(String(255))
    calculated_or_reported: Mapped[str | None] = mapped_column(String(100))
    calculation_logic: Mapped[str | None] = mapped_column(Text)
    calculation_logic_details: Mapped[str | None] = mapped_column(Text)
    sign_flipping_value: Mapped[str | None] = mapped_column(String(50))
    mapping_type: Mapped[str | None] = mapped_column(String(255))
    sp_standardisation_dataitem_id: Mapped[str | None] = mapped_column(String(255))
    sp_as_reported_dataitem_logic: Mapped[str | None] = mapped_column(Text)
    calculated_in_cfv: Mapped[str | None] = mapped_column(String(5))
    editable_in_historicals: Mapped[str | None] = mapped_column(String(5))

class PortfolioReference(Base, AuditMixin):
    __tablename__ = "prj_portfolio_reference_test"
    port_ref_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    port_name: Mapped[str] = mapped_column(String(120), nullable=False)
    sector_name: Mapped[str | None] = mapped_column(String(120))
    sub_sector: Mapped[str | None] = mapped_column(String(120))
    remark: Mapped[str | None] = mapped_column(String(500))
    __table_args__ = (UniqueConstraint("port_name", "sector_name", "sub_sector", name="uq_portfolio_reference"),)

class AttributePortfolioScope(Base, AuditMixin):
    __tablename__ = "prj_attribute_portfolio_scope_test"
    scope_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prj_id: Mapped[str] = mapped_column(String(80), nullable=False)
    port_ref_id: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("prj_id", "port_ref_id", name="uq_attribute_scope"),)

class AttributeBusinessRule(Base, AuditMixin):
    __tablename__ = "prj_attribute_business_rules_test"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    source_abbr_name: Mapped[str] = mapped_column(String(50), default="SNPAR", nullable=False)
    editable: Mapped[str | None] = mapped_column(String(20))
    symbol: Mapped[str | None] = mapped_column(String(50))
    mapping_type: Mapped[str | None] = mapped_column(String(255))
    mapping_logic: Mapped[str | None] = mapped_column(Text)
    calculation_logic: Mapped[str | None] = mapped_column(Text)
    business_logic: Mapped[str | None] = mapped_column(Text)

class ScanningPromptReference(Base, AuditMixin):
    __tablename__ = "prj_scanning_prompt_reference_test"
    prompt_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope_id: Mapped[int | None] = mapped_column(Integer)
    prj_id: Mapped[str] = mapped_column(String(80), nullable=False)
    port_ref_id: Mapped[int | None] = mapped_column(Integer)
    required_by_scope: Mapped[str | None] = mapped_column(String(255))
    attribute_name: Mapped[str | None] = mapped_column(String(500))
    section: Mapped[str | None] = mapped_column(String(255))
    sub_section: Mapped[str | None] = mapped_column(String(255))
    data_type: Mapped[str | None] = mapped_column(String(100))
    calculated_or_reported: Mapped[str | None] = mapped_column(String(100))
    calculation_logic: Mapped[str | None] = mapped_column(Text)
    segment: Mapped[str | None] = mapped_column(String(255))
    attribute_description: Mapped[str | None] = mapped_column(Text)
    display_order: Mapped[int | None] = mapped_column(Integer)

class AuditTable(Base):
    __tablename__ = "audit_table_test"
    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    record_key: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    before_value: Mapped[str | None] = mapped_column(Text)
    after_value: Mapped[str | None] = mapped_column(Text)
    source_operation: Mapped[str | None] = mapped_column(String(100))
    batch_reference: Mapped[str | None] = mapped_column(String(255))
    performed_by: Mapped[str] = mapped_column(String(128), nullable=False)
    performed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
