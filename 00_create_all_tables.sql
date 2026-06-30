/*
  Data Dictionary Admin App - idempotent SQL Server bootstrap.
  Safe to rerun. It never drops existing tables/data.
  prj_data_source remains a pre-existing static reference table.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    /* 1. Attribute master */
    IF OBJECT_ID(N'dbo.prj_attribute_master_test', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.prj_attribute_master_test (
            prj_id varchar(80) NOT NULL,
            prj_attribute_name varchar(500) NOT NULL,
            prj_attribute_description nvarchar(max) NULL,
            prj_physical_attribute_name varchar(500) NULL,
            where_in_financial_statement varchar(255) NULL,
            version_update varchar(255) NULL,
            calculated_or_reported varchar(100) NULL,
            calculation_logic nvarchar(max) NULL,
            calculation_logic_details nvarchar(max) NULL,
            sign_flipping_value varchar(50) NULL,
            mapping_type varchar(255) NULL,
            sp_standardisation_dataitem_id varchar(255) NULL,
            sp_as_reported_dataitem_logic nvarchar(max) NULL,
            calculated_in_cfv varchar(5) NULL,
            editable_in_historicals varchar(5) NULL,
            is_active bit NOT NULL CONSTRAINT DF_ddam_attribute_master_active DEFAULT (1),
            created_at datetime2 NOT NULL CONSTRAINT DF_ddam_attribute_master_created_at DEFAULT (sysutcdatetime()),
            updated_at datetime2 NOT NULL CONSTRAINT DF_ddam_attribute_master_updated_at DEFAULT (sysutcdatetime()),
            created_by varchar(128) NOT NULL CONSTRAINT DF_ddam_attribute_master_created_by DEFAULT ('sysuser'),
            updated_by varchar(128) NOT NULL CONSTRAINT DF_ddam_attribute_master_updated_by DEFAULT ('sysuser'),
            CONSTRAINT PK_ddam_attribute_master PRIMARY KEY (prj_id)
        );
    END;

    /* 2. Portfolio reference */
    IF OBJECT_ID(N'dbo.prj_portfolio_reference_test', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.prj_portfolio_reference_test (
            port_ref_id int IDENTITY(1,1) NOT NULL,
            port_name varchar(120) NOT NULL,
            sector_name varchar(120) NULL,
            sub_sector varchar(120) NULL,
            remark varchar(500) NULL,
            is_active bit NOT NULL CONSTRAINT DF_ddam_portfolio_active DEFAULT (1),
            created_at datetime2 NOT NULL CONSTRAINT DF_ddam_portfolio_created_at DEFAULT (sysutcdatetime()),
            updated_at datetime2 NOT NULL CONSTRAINT DF_ddam_portfolio_updated_at DEFAULT (sysutcdatetime()),
            created_by varchar(128) NOT NULL CONSTRAINT DF_ddam_portfolio_created_by DEFAULT ('sysuser'),
            updated_by varchar(128) NOT NULL CONSTRAINT DF_ddam_portfolio_updated_by DEFAULT ('sysuser'),
            CONSTRAINT PK_ddam_portfolio_reference PRIMARY KEY (port_ref_id)
        );
    END;

    /* 3. Attribute portfolio scope */
    IF OBJECT_ID(N'dbo.prj_attribute_portfolio_scope_test', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.prj_attribute_portfolio_scope_test (
            scope_id int IDENTITY(1,1) NOT NULL,
            prj_id varchar(80) NOT NULL,
            port_ref_id int NOT NULL,
            description nvarchar(max) NULL,
            is_active bit NOT NULL CONSTRAINT DF_ddam_attribute_scope_active DEFAULT (1),
            created_at datetime2 NOT NULL CONSTRAINT DF_ddam_attribute_scope_created_at DEFAULT (sysutcdatetime()),
            updated_at datetime2 NOT NULL CONSTRAINT DF_ddam_attribute_scope_updated_at DEFAULT (sysutcdatetime()),
            created_by varchar(128) NOT NULL CONSTRAINT DF_ddam_attribute_scope_created_by DEFAULT ('sysuser'),
            updated_by varchar(128) NOT NULL CONSTRAINT DF_ddam_attribute_scope_updated_by DEFAULT ('sysuser'),
            CONSTRAINT PK_ddam_attribute_scope PRIMARY KEY (scope_id)
        );
    END;

    /* 4. Business rules */
    IF OBJECT_ID(N'dbo.prj_attribute_business_rules_test', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.prj_attribute_business_rules_test (
            id int IDENTITY(1,1) NOT NULL,
            scope_id int NOT NULL,
            source_abbr_name varchar(50) NOT NULL CONSTRAINT DF_ddam_business_rules_source DEFAULT ('SNPAR'),
            editable varchar(20) NULL,
            symbol varchar(50) NULL,
            mapping_type varchar(255) NULL,
            mapping_logic nvarchar(max) NULL,
            calculation_logic nvarchar(max) NULL,
            business_logic nvarchar(max) NULL,
            is_active bit NOT NULL CONSTRAINT DF_ddam_business_rules_active DEFAULT (1),
            created_at datetime2 NOT NULL CONSTRAINT DF_ddam_business_rules_created_at DEFAULT (sysutcdatetime()),
            updated_at datetime2 NOT NULL CONSTRAINT DF_ddam_business_rules_updated_at DEFAULT (sysutcdatetime()),
            created_by varchar(128) NOT NULL CONSTRAINT DF_ddam_business_rules_created_by DEFAULT ('sysuser'),
            updated_by varchar(128) NOT NULL CONSTRAINT DF_ddam_business_rules_updated_by DEFAULT ('sysuser'),
            CONSTRAINT PK_ddam_business_rules PRIMARY KEY (id)
        );
    END;

    /* 5. Prompt reference */
    IF OBJECT_ID(N'dbo.prj_scanning_prompt_reference_test', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.prj_scanning_prompt_reference_test (
            prompt_id int IDENTITY(1,1) NOT NULL,
            scope_id int NULL,
            prj_id varchar(80) NOT NULL,
            port_ref_id int NULL,
            required_by_scope varchar(255) NULL,
            attribute_name varchar(500) NULL,
            section varchar(255) NULL,
            sub_section varchar(255) NULL,
            data_type varchar(100) NULL,
            calculated_or_reported varchar(100) NULL,
            calculation_logic nvarchar(max) NULL,
            segment varchar(255) NULL,
            attribute_description nvarchar(max) NULL,
            examples nvarchar(max) NULL,
            display_order int NULL,
            is_active bit NOT NULL CONSTRAINT DF_ddam_prompt_active DEFAULT (1),
            created_at datetime2 NOT NULL CONSTRAINT DF_ddam_prompt_created_at DEFAULT (sysutcdatetime()),
            updated_at datetime2 NOT NULL CONSTRAINT DF_ddam_prompt_updated_at DEFAULT (sysutcdatetime()),
            created_by varchar(128) NOT NULL CONSTRAINT DF_ddam_prompt_created_by DEFAULT ('sysuser'),
            updated_by varchar(128) NOT NULL CONSTRAINT DF_ddam_prompt_updated_by DEFAULT ('sysuser'),
            CONSTRAINT PK_ddam_prompt_reference PRIMARY KEY (prompt_id)
        );
    END;

    /* 6. Audit */
    IF OBJECT_ID(N'dbo.audit_table_test', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.audit_table_test (
            audit_id bigint IDENTITY(1,1) NOT NULL,
            table_name varchar(255) NOT NULL,
            record_key varchar(255) NOT NULL,
            action varchar(50) NOT NULL,
            before_value nvarchar(max) NULL,
            after_value nvarchar(max) NULL,
            source_operation varchar(100) NULL,
            batch_reference varchar(255) NULL,
            performed_by varchar(128) NOT NULL,
            performed_at datetime2 NOT NULL CONSTRAINT DF_ddam_audit_performed_at DEFAULT (sysutcdatetime()),
            CONSTRAINT PK_ddam_audit PRIMARY KEY (audit_id)
        );
    END;

    /* Unique indexes use application-specific names to avoid collisions with legacy objects such as ug_portfolio_rerenece. */
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.prj_portfolio_reference_test') AND name = N'UX_ddam_portfolio_reference_key')
        CREATE UNIQUE INDEX UX_ddam_portfolio_reference_key
        ON dbo.prj_portfolio_reference_test (port_name, sector_name, sub_sector);

    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.prj_attribute_master_test') AND name = N'UX_ddam_attribute_physical_name')
        CREATE UNIQUE INDEX UX_ddam_attribute_physical_name
        ON dbo.prj_attribute_master_test (prj_physical_attribute_name)
        WHERE prj_physical_attribute_name IS NOT NULL;

    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.prj_attribute_portfolio_scope_test') AND name = N'UX_ddam_attribute_scope_prj_port')
        CREATE UNIQUE INDEX UX_ddam_attribute_scope_prj_port
        ON dbo.prj_attribute_portfolio_scope_test (prj_id, port_ref_id);

    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.prj_attribute_business_rules_test') AND name = N'UX_ddam_business_rules_scope')
        CREATE UNIQUE INDEX UX_ddam_business_rules_scope
        ON dbo.prj_attribute_business_rules_test (scope_id);

    /* Add foreign keys only when absent. Existing legacy foreign keys are left untouched. */
    IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE parent_object_id = OBJECT_ID(N'dbo.prj_attribute_portfolio_scope_test') AND name = N'FK_ddam_scope_attribute')
       AND NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE parent_object_id = OBJECT_ID(N'dbo.prj_attribute_portfolio_scope_test') AND referenced_object_id = OBJECT_ID(N'dbo.prj_attribute_master_test'))
        ALTER TABLE dbo.prj_attribute_portfolio_scope_test WITH CHECK ADD CONSTRAINT FK_ddam_scope_attribute FOREIGN KEY (prj_id) REFERENCES dbo.prj_attribute_master_test(prj_id);

    IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE parent_object_id = OBJECT_ID(N'dbo.prj_attribute_portfolio_scope_test') AND name = N'FK_ddam_scope_portfolio')
       AND NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE parent_object_id = OBJECT_ID(N'dbo.prj_attribute_portfolio_scope_test') AND referenced_object_id = OBJECT_ID(N'dbo.prj_portfolio_reference_test'))
        ALTER TABLE dbo.prj_attribute_portfolio_scope_test WITH CHECK ADD CONSTRAINT FK_ddam_scope_portfolio FOREIGN KEY (port_ref_id) REFERENCES dbo.prj_portfolio_reference_test(port_ref_id);

    IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE parent_object_id = OBJECT_ID(N'dbo.prj_attribute_business_rules_test') AND name = N'FK_ddam_business_rules_scope')
       AND NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE parent_object_id = OBJECT_ID(N'dbo.prj_attribute_business_rules_test') AND referenced_object_id = OBJECT_ID(N'dbo.prj_attribute_portfolio_scope_test'))
        ALTER TABLE dbo.prj_attribute_business_rules_test WITH CHECK ADD CONSTRAINT FK_ddam_business_rules_scope FOREIGN KEY (scope_id) REFERENCES dbo.prj_attribute_portfolio_scope_test(scope_id);

    /* Reference seed data. No deletes, no identity assumptions. */
    IF NOT EXISTS (SELECT 1 FROM dbo.prj_portfolio_reference_test WHERE port_name = 'FI' AND sector_name = 'Banks' AND ISNULL(sub_sector, '') = '')
        INSERT INTO dbo.prj_portfolio_reference_test (port_name, sector_name, sub_sector, remark) VALUES ('FI', 'Banks', NULL, 'Financial Institutes - Banks');
    IF NOT EXISTS (SELECT 1 FROM dbo.prj_portfolio_reference_test WHERE port_name = 'FI' AND sector_name = 'Insurance' AND ISNULL(sub_sector, '') = '')
        INSERT INTO dbo.prj_portfolio_reference_test (port_name, sector_name, sub_sector, remark) VALUES ('FI', 'Insurance', NULL, 'Financial Institutes - Insurance');
    IF NOT EXISTS (SELECT 1 FROM dbo.prj_portfolio_reference_test WHERE port_name = 'Corporate' AND sector_name = 'Corporate' AND ISNULL(sub_sector, '') = '')
        INSERT INTO dbo.prj_portfolio_reference_test (port_name, sector_name, sub_sector, remark) VALUES ('Corporate', 'Corporate', NULL, 'Global Corporates');
    IF NOT EXISTS (SELECT 1 FROM dbo.prj_portfolio_reference_test WHERE port_name = 'Zeus Downstream' AND sector_name = 'Zeus Downstream' AND ISNULL(sub_sector, '') = '')
        INSERT INTO dbo.prj_portfolio_reference_test (port_name, sector_name, sub_sector, remark) VALUES ('Zeus Downstream', 'Zeus Downstream', NULL, 'Zeus Downstream');

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
