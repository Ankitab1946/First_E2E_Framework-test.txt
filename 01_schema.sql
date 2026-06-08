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
