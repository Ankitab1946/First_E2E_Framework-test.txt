from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from DataDictionaryAdminApp.core.database import Base


class PrjAttribute(Base):
    __tablename__ = "prj_attribute"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    prj_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    prj_attribute_id: Mapped[str | None] = mapped_column(String(255))
    prj_attribute_description: Mapped[str | None] = mapped_column(Text)
    prj_attribute_eg: Mapped[str | None] = mapped_column(Text)
    prj_physical_attribute_name: Mapped[str | None] = mapped_column(String(255))
    where_in_financial_statement: Mapped[str | None] = mapped_column(Text)
    version_update: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[object | None] = mapped_column(DateTime)
    deleted_by: Mapped[str | None] = mapped_column(String(100))
    version_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.sysutcdatetime())
    updated_at: Mapped[object] = mapped_column(DateTime, server_default=func.sysutcdatetime(), onupdate=func.sysutcdatetime())
    created_by: Mapped[str] = mapped_column(String(100), default="sysuser")
    updated_by: Mapped[str] = mapped_column(String(100), default="sysuser")


class PrjAttrBusinessLogic(Base):
    __tablename__ = "prj_attr_business_logic"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    prj_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    s_number: Mapped[int | None] = mapped_column(Integer)
    editable: Mapped[bool | None] = mapped_column(Boolean)
    percentage_ratio: Mapped[str | None] = mapped_column(String(50))
    calculation_logic: Mapped[str | None] = mapped_column(Text)
    release_scope: Mapped[str | None] = mapped_column(String(255))
    mapping_type: Mapped[str | None] = mapped_column(String(255))
    calculation_in_prj: Mapped[str | None] = mapped_column(Text)
    editable_in_historicals: Mapped[bool | None] = mapped_column(Boolean)
    sign_flipping: Mapped[bool | None] = mapped_column(Boolean)
    gc_template_attribute_name: Mapped[str | None] = mapped_column(String(255))
    sp_standardisation_attribute_name: Mapped[str | None] = mapped_column(String(255))
    sp_standardisation_dataitem_id: Mapped[str | None] = mapped_column(String(100))
    sp_as_reported_dataitem_id: Mapped[str | None] = mapped_column(String(100))
    updates: Mapped[str | None] = mapped_column(Text)
    updated_on: Mapped[object | None] = mapped_column(DateTime)
    zeus_attribute: Mapped[str | None] = mapped_column(String(255))
    zeus_table_name: Mapped[str | None] = mapped_column(String(255))
    zeus_description: Mapped[str | None] = mapped_column(Text)
    comments: Mapped[str | None] = mapped_column(Text)
    snl_dataitemid: Mapped[str | None] = mapped_column(String(100))
    scanned_calculated: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[object | None] = mapped_column(DateTime)
    deleted_by: Mapped[str | None] = mapped_column(String(100))
    version_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.sysutcdatetime())
    updated_at: Mapped[object] = mapped_column(DateTime, server_default=func.sysutcdatetime(), onupdate=func.sysutcdatetime())
    created_by: Mapped[str] = mapped_column(String(100), default="sysuser")
    updated_by: Mapped[str] = mapped_column(String(100), default="sysuser")


class PrjAttrBusinessLogicScope(Base):
    __tablename__ = "prj_attr_business_logic_scope"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    prj_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    required_by_corporates: Mapped[bool | None] = mapped_column(Boolean)
    required_by_banks: Mapped[bool | None] = mapped_column(Boolean)
    required_by_insurance: Mapped[bool | None] = mapped_column(Boolean)
    required_by_downstream: Mapped[bool | None] = mapped_column(Boolean)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[object | None] = mapped_column(DateTime)
    deleted_by: Mapped[str | None] = mapped_column(String(100))
    version_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.sysutcdatetime())
    updated_at: Mapped[object] = mapped_column(DateTime, server_default=func.sysutcdatetime(), onupdate=func.sysutcdatetime())
    created_by: Mapped[str] = mapped_column(String(100), default="sysuser")
    updated_by: Mapped[str] = mapped_column(String(100), default="sysuser")


# Backward-compatible name retained for legacy services.
CFVAttrBusinessLogic = PrjAttrBusinessLogic
