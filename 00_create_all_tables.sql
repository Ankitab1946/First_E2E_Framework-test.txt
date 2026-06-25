/*
 Data Dictionary Admin App - Complete idempotent database setup.
 Run this script once against PRJ_DB in SSMS/Azure Data Studio.
 It creates existing and Part 3 tables, indexes, and upgrades legacy mutable
 tables with soft-delete metadata. Static/reference data is not deleted by the app.
*/

USE PRJ_DB;
GO

IF OBJECT_ID('dbo.master_dictionary', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.master_dictionary (
        id BIGINT IDENTITY(1,1) PRIMARY KEY,
        prj_id NVARCHAR(100) NOT NULL UNIQUE,
        prj_attribute_name NVARCHAR(255) NULL,
        prj_attribute_description NVARCHAR(MAX) NULL,
        prj_physical_attribute_name NVARCHAR(255) NULL,
        editable BIT NULL,
        percentage_ratio NVARCHAR(50) NULL,
        calculation_logic NVARCHAR(MAX) NULL,
        where_in_financial_statement NVARCHAR(MAX) NULL,
        required_by_corporates BIT NULL,
        required_by_banks BIT NULL,
        required_by_insurance BIT NULL,
        required_by_downstream BIT NULL,
        version_update NVARCHAR(100) NULL,
        release_scope NVARCHAR(255) NULL,
        mapping_type NVARCHAR(255) NULL,
        calculation_in_prj NVARCHAR(MAX) NULL,
        editable_in_historicals BIT NULL,
        sign_flipping BIT NULL,
        gc_template_attribute_name NVARCHAR(255) NULL,
        sp_standardisation_attribute_name NVARCHAR(255) NULL,
        sp_standardisation_dataitem_id NVARCHAR(100) NULL,
        sp_as_reported_dataitem_id NVARCHAR(100) NULL,
        updates NVARCHAR(MAX) NULL,
        updated_on DATETIME2 NULL,
        zeus_attribute NVARCHAR(255) NULL,
        zeus_table_name NVARCHAR(255) NULL,
        zeus_description NVARCHAR(MAX) NULL,
        comments NVARCHAR(MAX) NULL,
        snl_dataitemid NVARCHAR(100) NULL,
        scanned_calculated NVARCHAR(100) NULL,
        is_active BIT NOT NULL DEFAULT 1,
        version_no INT NOT NULL DEFAULT 1,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        created_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser',
        updated_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser'
    );
END
GO

IF OBJECT_ID('dbo.prj_attribute', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.prj_attribute (
        id BIGINT IDENTITY(1,1) PRIMARY KEY,
        prj_id NVARCHAR(100) NOT NULL UNIQUE,
        prj_attribute_id NVARCHAR(255) NULL,
        prj_attribute_description NVARCHAR(MAX) NULL,
        prj_attribute_eg NVARCHAR(MAX) NULL,
        prj_physical_attribute_name NVARCHAR(255) NULL,
        where_in_financial_statement NVARCHAR(MAX) NULL,
        version_update NVARCHAR(100) NULL,
        is_active BIT NOT NULL DEFAULT 1,
        version_no INT NOT NULL DEFAULT 1,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        created_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser',
        updated_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser'
    );
END
GO

IF OBJECT_ID('dbo.prj_attr_business_logic', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.prj_attr_business_logic (
        id BIGINT IDENTITY(1,1) PRIMARY KEY,
        prj_id NVARCHAR(100) NOT NULL UNIQUE,
        s_number INT NULL,
        editable BIT NULL,
        percentage_ratio NVARCHAR(50) NULL,
        calculation_logic NVARCHAR(MAX) NULL,
        release_scope NVARCHAR(255) NULL,
        mapping_type NVARCHAR(255) NULL,
        calculation_in_prj NVARCHAR(MAX) NULL,
        editable_in_historicals BIT NULL,
        sign_flipping BIT NULL,
        gc_template_attribute_name NVARCHAR(255) NULL,
        sp_standardisation_attribute_name NVARCHAR(255) NULL,
        sp_standardisation_dataitem_id NVARCHAR(100) NULL,
        sp_as_reported_dataitem_id NVARCHAR(100) NULL,
        updates NVARCHAR(MAX) NULL,
        updated_on DATETIME2 NULL,
        zeus_attribute NVARCHAR(255) NULL,
        zeus_table_name NVARCHAR(255) NULL,
        zeus_description NVARCHAR(MAX) NULL,
        comments NVARCHAR(MAX) NULL,
        snl_dataitemid NVARCHAR(100) NULL,
        scanned_calculated NVARCHAR(100) NULL,
        is_active BIT NOT NULL DEFAULT 1,
        version_no INT NOT NULL DEFAULT 1,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        created_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser',
        updated_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser'
    );
END
GO

IF OBJECT_ID('dbo.prj_attr_business_logic_scope', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.prj_attr_business_logic_scope (
        id BIGINT IDENTITY(1,1) PRIMARY KEY,
        prj_id NVARCHAR(100) NOT NULL UNIQUE,
        required_by_corporates BIT NULL,
        required_by_banks BIT NULL,
        required_by_insurance BIT NULL,
        required_by_downstream BIT NULL,
        is_active BIT NOT NULL DEFAULT 1,
        version_no INT NOT NULL DEFAULT 1,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        created_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser',
        updated_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser'
    );
END
GO

IF OBJECT_ID('dbo.audit_log', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.audit_log (
        id BIGINT IDENTITY(1,1) PRIMARY KEY,
        batch_id NVARCHAR(36) NOT NULL,
        prj_id NVARCHAR(100) NOT NULL,
        table_name NVARCHAR(255) NOT NULL,
        action_type NVARCHAR(50) NOT NULL,
        source_module NVARCHAR(100) NOT NULL,
        old_value NVARCHAR(MAX) NULL,
        new_value NVARCHAR(MAX) NULL,
        changed_by NVARCHAR(100) NOT NULL,
        changed_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_master_dictionary_prj_id' AND object_id = OBJECT_ID('dbo.master_dictionary'))
BEGIN
    CREATE INDEX ix_master_dictionary_prj_id ON dbo.master_dictionary(prj_id);
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_master_dictionary_active' AND object_id = OBJECT_ID('dbo.master_dictionary'))
BEGIN
    CREATE INDEX ix_master_dictionary_active ON dbo.master_dictionary(is_active);
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_audit_log_batch_id' AND object_id = OBJECT_ID('dbo.audit_log'))
BEGIN
    CREATE INDEX ix_audit_log_batch_id ON dbo.audit_log(batch_id);
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_audit_log_prj_id' AND object_id = OBJECT_ID('dbo.audit_log'))
BEGIN
    CREATE INDEX ix_audit_log_prj_id ON dbo.audit_log(prj_id);
END
GO

IF OBJECT_ID('dbo.history_log', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.history_log (
        id BIGINT IDENTITY(1,1) PRIMARY KEY,
        batch_id NVARCHAR(36) NOT NULL,
        prj_id NVARCHAR(100) NOT NULL,
        table_name NVARCHAR(255) NOT NULL,
        action_type NVARCHAR(50) NOT NULL,
        snapshot_json NVARCHAR(MAX) NULL,
        changed_by NVARCHAR(100) NOT NULL,
        changed_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END
GO

IF OBJECT_ID('dbo.prompt_library', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.prompt_library (
        id BIGINT IDENTITY(1,1) PRIMARY KEY,
        prompt_name NVARCHAR(255) NOT NULL,
        prompt_category NVARCHAR(100) NULL,
        prompt_text NVARCHAR(MAX) NULL,
        is_active BIT NOT NULL DEFAULT 1,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_history_log_prj_id' AND object_id = OBJECT_ID('dbo.history_log'))
BEGIN
    CREATE INDEX ix_history_log_prj_id ON dbo.history_log(prj_id);
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_history_log_batch_id' AND object_id = OBJECT_ID('dbo.history_log'))
BEGIN
    CREATE INDEX ix_history_log_batch_id ON dbo.history_log(batch_id);
END
GO

-- Performance indexes for filter-heavy Streamlit/API screens.
-- Safe to run repeatedly. These do not change table structure or data.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_master_dictionary_filter_core' AND object_id = OBJECT_ID('dbo.master_dictionary'))
BEGIN
    CREATE INDEX ix_master_dictionary_filter_core
    ON dbo.master_dictionary(is_active, prj_id, prj_attribute_name, where_in_financial_statement);
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_master_dictionary_portfolio_flags' AND object_id = OBJECT_ID('dbo.master_dictionary'))
BEGIN
    CREATE INDEX ix_master_dictionary_portfolio_flags
    ON dbo.master_dictionary(
        is_active,
        required_by_corporates,
        required_by_banks,
        required_by_insurance,
        required_by_downstream
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_audit_log_prj_changed_at' AND object_id = OBJECT_ID('dbo.audit_log'))
BEGIN
    CREATE INDEX ix_audit_log_prj_changed_at
    ON dbo.audit_log(prj_id, changed_at DESC);
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_history_log_prj_changed_at' AND object_id = OBJECT_ID('dbo.history_log'))
BEGIN
    CREATE INDEX ix_history_log_prj_changed_at
    ON dbo.history_log(prj_id, changed_at DESC);
END
GO

-- Part 3 normalized configuration tables. Safe creation for new deployments.
IF OBJECT_ID('dbo.prj_portfolio_reference', 'U') IS NULL
CREATE TABLE dbo.prj_portfolio_reference (
 port_ref_id BIGINT IDENTITY(1,1) PRIMARY KEY, port_name NVARCHAR(100) NOT NULL, sector_name NVARCHAR(100) NOT NULL, sub_sector NVARCHAR(100) NULL,
 remark NVARCHAR(MAX) NULL, is_active BIT NOT NULL DEFAULT 1, created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(), updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(), created_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser', updated_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser',
 CONSTRAINT uq_portfolio_reference UNIQUE(port_name,sector_name,sub_sector));
GO
IF OBJECT_ID('dbo.prj_attribute_portfolio_scope', 'U') IS NULL
CREATE TABLE dbo.prj_attribute_portfolio_scope (
 scope_id BIGINT IDENTITY(1,1) PRIMARY KEY, prj_id NVARCHAR(100) NOT NULL, port_ref_id BIGINT NOT NULL, description NVARCHAR(MAX) NULL, is_active BIT NOT NULL DEFAULT 1, is_deleted BIT NOT NULL DEFAULT 0,
 created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(), updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(), created_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser', updated_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser', deleted_at DATETIME2 NULL, deleted_by NVARCHAR(100) NULL,
 CONSTRAINT uq_attribute_portfolio_scope UNIQUE(prj_id,port_ref_id), CONSTRAINT fk_scope_portfolio FOREIGN KEY(port_ref_id) REFERENCES dbo.prj_portfolio_reference(port_ref_id));
GO
IF OBJECT_ID('dbo.prj_ui_display_config_test', 'U') IS NULL
CREATE TABLE dbo.prj_ui_display_config_test (
 display_id BIGINT IDENTITY(1,1) PRIMARY KEY, scope_id BIGINT NOT NULL, display_order INT NULL, display_name NVARCHAR(500) NOT NULL, section NVARCHAR(500) NULL, subsection NVARCHAR(500) NULL, view_name NVARCHAR(500) NULL, description NVARCHAR(MAX) NULL,
 is_active BIT NOT NULL DEFAULT 1, is_deleted BIT NOT NULL DEFAULT 0, created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(), updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(), created_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser', updated_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser', deleted_at DATETIME2 NULL, deleted_by NVARCHAR(100) NULL,
 CONSTRAINT fk_display_scope FOREIGN KEY(scope_id) REFERENCES dbo.prj_attribute_portfolio_scope(scope_id));
GO
IF OBJECT_ID('dbo.prj_attribute_business_rules_test', 'U') IS NULL
CREATE TABLE dbo.prj_attribute_business_rules_test (
 id BIGINT IDENTITY(1,1) PRIMARY KEY, scope_id BIGINT NOT NULL UNIQUE, source_abbr_name NVARCHAR(100) NOT NULL DEFAULT 'SNPAR', editable BIT NULL, symbol NVARCHAR(50) NULL, mapping_type NVARCHAR(255) NULL, mapping_logic NVARCHAR(MAX) NULL, calculation_logic NVARCHAR(MAX) NULL, business_logic NVARCHAR(MAX) NULL,
 is_active BIT NOT NULL DEFAULT 1, is_deleted BIT NOT NULL DEFAULT 0, created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(), updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(), created_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser', updated_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser',
 CONSTRAINT fk_business_rule_scope FOREIGN KEY(scope_id) REFERENCES dbo.prj_attribute_portfolio_scope(scope_id));
GO
IF OBJECT_ID('dbo.prj_prompt_reference', 'U') IS NULL
CREATE TABLE dbo.prj_prompt_reference (
 prompt_id BIGINT IDENTITY(1,1) PRIMARY KEY, scope_id BIGINT NOT NULL, cfv_id NVARCHAR(100) NOT NULL, port_ref_id BIGINT NOT NULL, attribute_description NVARCHAR(MAX) NULL, examples NVARCHAR(MAX) NULL, segment NVARCHAR(500) NULL, source_sheet_name NVARCHAR(255) NULL,
 is_active BIT NOT NULL DEFAULT 1, is_deleted BIT NOT NULL DEFAULT 0, created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(), updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(), created_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser', updated_by NVARCHAR(100) NOT NULL DEFAULT 'sysuser', deleted_at DATETIME2 NULL, deleted_by NVARCHAR(100) NULL,
 CONSTRAINT uq_prompt_reference_scope_cfv_port UNIQUE(scope_id,cfv_id,port_ref_id), CONSTRAINT fk_prompt_scope FOREIGN KEY(scope_id) REFERENCES dbo.prj_attribute_portfolio_scope(scope_id), CONSTRAINT fk_prompt_port FOREIGN KEY(port_ref_id) REFERENCES dbo.prj_portfolio_reference(port_ref_id));
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='ix_scope_prj_port' AND object_id=OBJECT_ID('dbo.prj_attribute_portfolio_scope')) CREATE INDEX ix_scope_prj_port ON dbo.prj_attribute_portfolio_scope(prj_id, port_ref_id, is_active);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='ix_display_scope_order' AND object_id=OBJECT_ID('dbo.prj_ui_display_config_test')) CREATE INDEX ix_display_scope_order ON dbo.prj_ui_display_config_test(scope_id, display_order, is_active);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='ix_prompt_scope_cfv' AND object_id=OBJECT_ID('dbo.prj_prompt_reference')) CREATE INDEX ix_prompt_scope_cfv ON dbo.prj_prompt_reference(scope_id, cfv_id, is_active);
GO


/* Soft-delete upgrade section */
/* Data Dictionary Admin App: idempotent create / upgrade script.
   Creates all mutable tables and upgrades legacy tables for soft-delete support.
   Static/reference tables (prj_portfolio_reference, prompt_library, prj_data_source) are not altered by application CRUD. */
/* Legacy mutable-table soft delete fields. Safe for environments that already have data. */
DECLARE @tables TABLE (name SYSNAME);
INSERT INTO @tables VALUES ('master_dictionary'),('prj_attribute'),('prj_attr_business_logic'),('prj_attr_business_logic_scope');
DECLARE @t SYSNAME, @sql NVARCHAR(MAX);
DECLARE c CURSOR LOCAL FAST_FORWARD FOR SELECT name FROM @tables;
OPEN c; FETCH NEXT FROM c INTO @t;
WHILE @@FETCH_STATUS = 0
BEGIN
  IF COL_LENGTH('dbo.' + @t, 'is_deleted') IS NULL
  BEGIN SET @sql = N'ALTER TABLE dbo.'+QUOTENAME(@t)+N' ADD is_deleted BIT NOT NULL CONSTRAINT DF_'+@t+N'_is_deleted DEFAULT 0 WITH VALUES;'; EXEC sp_executesql @sql; END
  IF COL_LENGTH('dbo.' + @t, 'deleted_at') IS NULL
  BEGIN SET @sql = N'ALTER TABLE dbo.'+QUOTENAME(@t)+N' ADD deleted_at DATETIME2 NULL;'; EXEC sp_executesql @sql; END
  IF COL_LENGTH('dbo.' + @t, 'deleted_by') IS NULL
  BEGIN SET @sql = N'ALTER TABLE dbo.'+QUOTENAME(@t)+N' ADD deleted_by NVARCHAR(100) NULL;'; EXEC sp_executesql @sql; END
  FETCH NEXT FROM c INTO @t;
END
CLOSE c; DEALLOCATE c;
GO
/* Indexes for active/deleted screens and full snapshot export. */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='ix_master_dictionary_active_deleted' AND object_id=OBJECT_ID('dbo.master_dictionary'))
  CREATE INDEX ix_master_dictionary_active_deleted ON dbo.master_dictionary(is_active,is_deleted,prj_id);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='ix_prj_attribute_active_deleted' AND object_id=OBJECT_ID('dbo.prj_attribute'))
  CREATE INDEX ix_prj_attribute_active_deleted ON dbo.prj_attribute(is_active,is_deleted,prj_id);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='ix_prj_business_logic_active_deleted' AND object_id=OBJECT_ID('dbo.prj_attr_business_logic'))
  CREATE INDEX ix_prj_business_logic_active_deleted ON dbo.prj_attr_business_logic(is_active,is_deleted,prj_id);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='ix_prj_business_scope_active_deleted' AND object_id=OBJECT_ID('dbo.prj_attr_business_logic_scope'))
  CREATE INDEX ix_prj_business_scope_active_deleted ON dbo.prj_attr_business_logic_scope(is_active,is_deleted,prj_id);
GO
PRINT 'Data Dictionary mutable tables and soft-delete columns are ready.';
