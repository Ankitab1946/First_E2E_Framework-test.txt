/* Part 3 revised schema: run after 01_schema.sql / 03_create_tables_all.sql.
   This script is idempotent and preserves existing tables. */
USE PRJ_DB;
GO
/* Master dictionary is the source of truth for every PRJ ID. */
IF COL_LENGTH('dbo.master_dictionary','calculated_or_reported') IS NULL
    ALTER TABLE dbo.master_dictionary ADD calculated_or_reported NVARCHAR(100) NULL;
GO
IF OBJECT_ID('dbo.prj_attribute_master_test','U') IS NULL
CREATE TABLE dbo.prj_attribute_master_test (
 id BIGINT IDENTITY PRIMARY KEY, prj_id NVARCHAR(100) NOT NULL UNIQUE,
 prj_attribute_name NVARCHAR(255) NULL, prj_attribute_description NVARCHAR(MAX) NULL,
 prj_attribute_eg NVARCHAR(MAX) NULL, prj_physical_attribute_name NVARCHAR(255) NULL,
 where_in_finanical_statement NVARCHAR(MAX) NULL, version_update NVARCHAR(100) NULL,
 is_active BIT NOT NULL DEFAULT 1, is_deleted BIT NOT NULL DEFAULT 0,
 created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(), updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
 created_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser', uploaded_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser',
 deleted_at DATETIME2 NULL, deleted_by NVARCHAR(100) NULL);
GO
IF OBJECT_ID('dbo.prj_portfolio_reference_test','U') IS NULL
CREATE TABLE dbo.prj_portfolio_reference_test (
 port_ref_id BIGINT IDENTITY PRIMARY KEY, port_name NVARCHAR(100) NOT NULL, sector_name NVARCHAR(100) NOT NULL,
 sub_sector NVARCHAR(100) NULL, remark NVARCHAR(MAX) NULL, is_active BIT NOT NULL DEFAULT 1,
 created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(), updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
 created_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser', updated_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser',
 CONSTRAINT uq_prj_portfolio_reference_test UNIQUE(port_name,sector_name,sub_sector));
GO
IF OBJECT_ID('dbo.prj_attribute_portfolio_scope_test','U') IS NULL
CREATE TABLE dbo.prj_attribute_portfolio_scope_test (
 scope_id BIGINT IDENTITY PRIMARY KEY, prj_id NVARCHAR(100) NOT NULL, port_ref_id BIGINT NOT NULL,
 description NVARCHAR(MAX) NULL, is_active BIT NOT NULL DEFAULT 1, is_deleted BIT NOT NULL DEFAULT 0,
 created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
 created_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser',updated_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser',
 deleted_at DATETIME2 NULL,deleted_by NVARCHAR(100) NULL,
 CONSTRAINT uq_prj_attribute_portfolio_scope_test UNIQUE(prj_id,port_ref_id),
 CONSTRAINT fk_prj_attribute_portfolio_scope_test_ref FOREIGN KEY(port_ref_id) REFERENCES dbo.prj_portfolio_reference_test(port_ref_id));
GO
IF OBJECT_ID('dbo.prj_scanning_prompt_reference_test','U') IS NULL
CREATE TABLE dbo.prj_scanning_prompt_reference_test (
 prompt_id BIGINT IDENTITY PRIMARY KEY, scope_id BIGINT NOT NULL, prj_id NVARCHAR(100) NOT NULL, port_ref_id BIGINT NOT NULL,
 required_by_scope NVARCHAR(500) NULL, attribute_name NVARCHAR(500) NULL, section NVARCHAR(500) NULL, sub_section NVARCHAR(500) NULL,
 data_type NVARCHAR(100) NULL, calculated_or_reported NVARCHAR(100) NULL, calculation_logic NVARCHAR(MAX) NULL,
 segment NVARCHAR(500) NULL, subcomponent_total NVARCHAR(500) NULL, attribute_description NVARCHAR(MAX) NULL,
 examples NVARCHAR(MAX) NULL, source_sheet_name NVARCHAR(255) NULL, is_active BIT NOT NULL DEFAULT 1, is_deleted BIT NOT NULL DEFAULT 0,
 created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
 created_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser',updated_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser',
 deleted_at DATETIME2 NULL,deleted_by NVARCHAR(100) NULL,
 CONSTRAINT uq_prj_scanning_prompt_reference_test UNIQUE(scope_id,prj_id,port_ref_id),
 CONSTRAINT fk_prj_scanning_prompt_reference_scope FOREIGN KEY(scope_id) REFERENCES dbo.prj_attribute_portfolio_scope_test(scope_id),
 CONSTRAINT fk_prj_scanning_prompt_reference_port FOREIGN KEY(port_ref_id) REFERENCES dbo.prj_portfolio_reference_test(port_ref_id));
GO
/* Compatible requested test2 copies. These are populated by deployment ETL or database trigger if required by consumers. */
IF OBJECT_ID('dbo.Prj_attribute_test2','U') IS NULL
CREATE TABLE dbo.Prj_attribute_test2 (
 id BIGINT IDENTITY PRIMARY KEY, prj_id NVARCHAR(100) NOT NULL UNIQUE, prj_attribute_id NVARCHAR(255) NULL,
 prj_attribute_description NVARCHAR(MAX) NULL, prj_attribute_eg NVARCHAR(MAX) NULL, prj_physical_attribute_name NVARCHAR(255) NULL,
 where_in_finanical_statement NVARCHAR(MAX) NULL, version_update NVARCHAR(100) NULL,
 created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(), updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
 created_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser', uploaded_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser');
GO
IF OBJECT_ID('dbo.PRJ_attr_business_logic_test2','U') IS NULL
CREATE TABLE dbo.PRJ_attr_business_logic_test2 (
 id BIGINT IDENTITY PRIMARY KEY, prj_id NVARCHAR(100) NOT NULL UNIQUE, s_number INT NULL, editable BIT NULL,
 percentage_ratio NVARCHAR(50) NULL, calculation_logic NVARCHAR(MAX) NULL, release_scope NVARCHAR(255) NULL,
 mapping_type NVARCHAR(255) NULL, calculation_in_prj NVARCHAR(MAX) NULL, editable_in_historicals BIT NULL,
 sign_flipping NVARCHAR(100) NULL, gc_template_attribute_name NVARCHAR(255) NULL,
 sp_standardize_attribute_name NVARCHAR(255) NULL, sp_standardize_dataitem_id NVARCHAR(100) NULL,
 sp_asreported_dataitem_id NVARCHAR(100) NULL, calculation_logic_details NVARCHAR(MAX) NULL,
 updates NVARCHAR(MAX) NULL, updated_on DATETIME2 NULL, zeus_attribute NVARCHAR(255) NULL,
 zeus_table_name NVARCHAR(255) NULL, zeus_description NVARCHAR(MAX) NULL, comments NVARCHAR(MAX) NULL,
 snl_dataitemid NVARCHAR(100) NULL, scanned_calculated NVARCHAR(100) NULL,
 created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
 created_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser',uploaded_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser');
GO
IF OBJECT_ID('dbo.PRJ_attr_business_logic_Scope_test2','U') IS NULL
CREATE TABLE dbo.PRJ_attr_business_logic_Scope_test2 (
 id BIGINT IDENTITY PRIMARY KEY, prj_id NVARCHAR(100) NOT NULL UNIQUE, required_by_corporates BIT NULL,
 required_by_banks BIT NULL, required_by_insurance BIT NULL, required_by_downstream BIT NULL,
 created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
 created_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser',uploaded_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser');
GO
/* Static reference data; prj_data_source is deliberately not created or altered by the app. */
IF NOT EXISTS (SELECT 1 FROM dbo.prj_portfolio_reference_test WHERE port_name='FI' AND sector_name='Banks')
INSERT dbo.prj_portfolio_reference_test(port_name,sector_name,remark) VALUES ('FI','Banks','Financial Institutes - Banks');
IF NOT EXISTS (SELECT 1 FROM dbo.prj_portfolio_reference_test WHERE port_name='FI' AND sector_name='Insurance')
INSERT dbo.prj_portfolio_reference_test(port_name,sector_name,remark) VALUES ('FI','Insurance','Financial Institutes - Insurance');
IF NOT EXISTS (SELECT 1 FROM dbo.prj_portfolio_reference_test WHERE port_name='Corporate' AND sector_name='Corporate')
INSERT dbo.prj_portfolio_reference_test(port_name,sector_name,remark) VALUES ('Corporate','Corporate','Global Corporates');
IF NOT EXISTS (SELECT 1 FROM dbo.prj_portfolio_reference_test WHERE port_name='UKC' AND sector_name='UKC')
INSERT dbo.prj_portfolio_reference_test(port_name,sector_name,remark) VALUES ('UKC','UKC','UK Corporate');
IF NOT EXISTS (SELECT 1 FROM dbo.prj_portfolio_reference_test WHERE port_name='SnP' AND sector_name='SnP')
INSERT dbo.prj_portfolio_reference_test(port_name,sector_name,remark) VALUES ('SnP','SnP','Standard & Poor''s');
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='ix_prompt_master_validation' AND object_id=OBJECT_ID('dbo.prj_scanning_prompt_reference_test'))
CREATE INDEX ix_prompt_master_validation ON dbo.prj_scanning_prompt_reference_test(prj_id,is_active,is_deleted);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='ix_scope_prj_active' AND object_id=OBJECT_ID('dbo.prj_attribute_portfolio_scope_test'))
CREATE INDEX ix_scope_prj_active ON dbo.prj_attribute_portfolio_scope_test(prj_id,port_ref_id,is_active,is_deleted);
GO
PRINT 'Part 3 revised Prompt/UI configuration schema created successfully.';
