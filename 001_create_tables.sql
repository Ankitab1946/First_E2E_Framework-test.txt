/*
 Data Dictionary Admin App - SQL Server idempotent bootstrap.
 Uses explicit table names only. No dynamic SQL / QUOTENAME is used so this runs cleanly
 on SQL Server installations using ODBC Driver 17.
 Only the six approved application tables are created or reconciled.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
  BEGIN TRANSACTION;

  IF OBJECT_ID(N'dbo.prj_attribute_master_test', N'U') IS NULL
  BEGIN
    CREATE TABLE dbo.prj_attribute_master_test (
      prj_id varchar(80) NOT NULL PRIMARY KEY,
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
      is_active bit NOT NULL CONSTRAINT DF_ddam_master_active DEFAULT(1),
      created_at datetime2 NOT NULL CONSTRAINT DF_ddam_master_created DEFAULT(sysutcdatetime()),
      updated_at datetime2 NOT NULL CONSTRAINT DF_ddam_master_updated DEFAULT(sysutcdatetime()),
      created_by varchar(128) NOT NULL CONSTRAINT DF_ddam_master_created_by DEFAULT('sysuser'),
      updated_by varchar(128) NOT NULL CONSTRAINT DF_ddam_master_updated_by DEFAULT('sysuser')
    );
  END;

  IF OBJECT_ID(N'dbo.prj_portfolio_reference_test', N'U') IS NULL
  BEGIN
    CREATE TABLE dbo.prj_portfolio_reference_test (
      port_ref_id int IDENTITY(1,1) NOT NULL PRIMARY KEY,
      port_name varchar(120) NOT NULL,
      sector_name varchar(120) NULL,
      sub_sector varchar(120) NULL,
      remark varchar(500) NULL,
      is_active bit NOT NULL CONSTRAINT DF_ddam_port_active DEFAULT(1),
      created_at datetime2 NOT NULL CONSTRAINT DF_ddam_port_created DEFAULT(sysutcdatetime()),
      updated_at datetime2 NOT NULL CONSTRAINT DF_ddam_port_updated DEFAULT(sysutcdatetime()),
      created_by varchar(128) NOT NULL CONSTRAINT DF_ddam_port_created_by DEFAULT('sysuser'),
      updated_by varchar(128) NOT NULL CONSTRAINT DF_ddam_port_updated_by DEFAULT('sysuser')
    );
  END;

  IF OBJECT_ID(N'dbo.prj_attribute_portfolio_scope_test', N'U') IS NULL
  BEGIN
    CREATE TABLE dbo.prj_attribute_portfolio_scope_test (
      scope_id int IDENTITY(1,1) NOT NULL PRIMARY KEY,
      prj_id varchar(80) NOT NULL,
      port_ref_id int NOT NULL,
      description nvarchar(max) NULL,
      is_active bit NOT NULL CONSTRAINT DF_ddam_scope_active DEFAULT(1),
      created_at datetime2 NOT NULL CONSTRAINT DF_ddam_scope_created DEFAULT(sysutcdatetime()),
      updated_at datetime2 NOT NULL CONSTRAINT DF_ddam_scope_updated DEFAULT(sysutcdatetime()),
      created_by varchar(128) NOT NULL CONSTRAINT DF_ddam_scope_created_by DEFAULT('sysuser'),
      updated_by varchar(128) NOT NULL CONSTRAINT DF_ddam_scope_updated_by DEFAULT('sysuser')
    );
  END;

  IF OBJECT_ID(N'dbo.prj_attribute_business_rules_test', N'U') IS NULL
  BEGIN
    CREATE TABLE dbo.prj_attribute_business_rules_test (
      id int IDENTITY(1,1) NOT NULL PRIMARY KEY,
      scope_id int NOT NULL,
      source_abbr_name varchar(50) NOT NULL CONSTRAINT DF_ddam_rules_source DEFAULT('SNPAR'),
      editable varchar(20) NULL,
      symbol varchar(50) NULL,
      mapping_type varchar(255) NULL,
      mapping_logic nvarchar(max) NULL,
      calculation_logic nvarchar(max) NULL,
      business_logic nvarchar(max) NULL,
      is_active bit NOT NULL CONSTRAINT DF_ddam_rules_active DEFAULT(1),
      created_at datetime2 NOT NULL CONSTRAINT DF_ddam_rules_created DEFAULT(sysutcdatetime()),
      updated_at datetime2 NOT NULL CONSTRAINT DF_ddam_rules_updated DEFAULT(sysutcdatetime()),
      created_by varchar(128) NOT NULL CONSTRAINT DF_ddam_rules_created_by DEFAULT('sysuser'),
      updated_by varchar(128) NOT NULL CONSTRAINT DF_ddam_rules_updated_by DEFAULT('sysuser')
    );
  END;

  IF OBJECT_ID(N'dbo.prj_scanning_prompt_reference_test', N'U') IS NULL
  BEGIN
    CREATE TABLE dbo.prj_scanning_prompt_reference_test (
      prompt_id int IDENTITY(1,1) NOT NULL PRIMARY KEY,
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
      display_order int NULL,
      is_active bit NOT NULL CONSTRAINT DF_ddam_prompt_active DEFAULT(1),
      created_at datetime2 NOT NULL CONSTRAINT DF_ddam_prompt_created DEFAULT(sysutcdatetime()),
      updated_at datetime2 NOT NULL CONSTRAINT DF_ddam_prompt_updated DEFAULT(sysutcdatetime()),
      created_by varchar(128) NOT NULL CONSTRAINT DF_ddam_prompt_created_by DEFAULT('sysuser'),
      updated_by varchar(128) NOT NULL CONSTRAINT DF_ddam_prompt_updated_by DEFAULT('sysuser')
    );
  END;

  IF OBJECT_ID(N'dbo.audit_table_test', N'U') IS NULL
  BEGIN
    CREATE TABLE dbo.audit_table_test (
      audit_id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
      table_name varchar(255) NOT NULL,
      record_key varchar(255) NOT NULL,
      action varchar(50) NOT NULL,
      before_value nvarchar(max) NULL,
      after_value nvarchar(max) NULL,
      source_operation varchar(100) NULL,
      batch_reference varchar(255) NULL,
      performed_by varchar(128) NOT NULL,
      performed_at datetime2 NOT NULL CONSTRAINT DF_ddam_audit_performed DEFAULT(sysutcdatetime())
    );
  END;

  /* Mandatory core-column validation for existing tables. */
  IF COL_LENGTH('dbo.prj_attribute_master_test','prj_id') IS NULL OR COL_LENGTH('dbo.prj_attribute_master_test','prj_attribute_name') IS NULL
    RAISERROR('prj_attribute_master_test must contain prj_id and prj_attribute_name.', 16, 1);
  IF COL_LENGTH('dbo.prj_portfolio_reference_test','port_ref_id') IS NULL OR COL_LENGTH('dbo.prj_portfolio_reference_test','port_name') IS NULL
    RAISERROR('prj_portfolio_reference_test must contain port_ref_id and port_name.', 16, 1);
  IF COL_LENGTH('dbo.prj_attribute_portfolio_scope_test','scope_id') IS NULL OR COL_LENGTH('dbo.prj_attribute_portfolio_scope_test','prj_id') IS NULL OR COL_LENGTH('dbo.prj_attribute_portfolio_scope_test','port_ref_id') IS NULL
    RAISERROR('prj_attribute_portfolio_scope_test must contain scope_id, prj_id and port_ref_id.', 16, 1);
  IF COL_LENGTH('dbo.prj_attribute_business_rules_test','id') IS NULL OR COL_LENGTH('dbo.prj_attribute_business_rules_test','scope_id') IS NULL
    RAISERROR('prj_attribute_business_rules_test must contain id and scope_id.', 16, 1);
  IF COL_LENGTH('dbo.prj_scanning_prompt_reference_test','prompt_id') IS NULL OR COL_LENGTH('dbo.prj_scanning_prompt_reference_test','prj_id') IS NULL
    RAISERROR('prj_scanning_prompt_reference_test must contain prompt_id and prj_id.', 16, 1);

  /* Explicit non-dynamic reconciliation: master. */
  IF COL_LENGTH('dbo.prj_attribute_master_test','prj_attribute_description') IS NULL ALTER TABLE dbo.prj_attribute_master_test ADD prj_attribute_description nvarchar(max) NULL;
  IF COL_LENGTH('dbo.prj_attribute_master_test','prj_physical_attribute_name') IS NULL ALTER TABLE dbo.prj_attribute_master_test ADD prj_physical_attribute_name varchar(500) NULL;
  IF COL_LENGTH('dbo.prj_attribute_master_test','where_in_financial_statement') IS NULL ALTER TABLE dbo.prj_attribute_master_test ADD where_in_financial_statement varchar(255) NULL;
  IF COL_LENGTH('dbo.prj_attribute_master_test','version_update') IS NULL ALTER TABLE dbo.prj_attribute_master_test ADD version_update varchar(255) NULL;
  IF COL_LENGTH('dbo.prj_attribute_master_test','calculated_or_reported') IS NULL ALTER TABLE dbo.prj_attribute_master_test ADD calculated_or_reported varchar(100) NULL;
  IF COL_LENGTH('dbo.prj_attribute_master_test','calculation_logic') IS NULL ALTER TABLE dbo.prj_attribute_master_test ADD calculation_logic nvarchar(max) NULL;
  IF COL_LENGTH('dbo.prj_attribute_master_test','calculation_logic_details') IS NULL ALTER TABLE dbo.prj_attribute_master_test ADD calculation_logic_details nvarchar(max) NULL;
  IF COL_LENGTH('dbo.prj_attribute_master_test','sign_flipping_value') IS NULL ALTER TABLE dbo.prj_attribute_master_test ADD sign_flipping_value varchar(50) NULL;
  IF COL_LENGTH('dbo.prj_attribute_master_test','mapping_type') IS NULL ALTER TABLE dbo.prj_attribute_master_test ADD mapping_type varchar(255) NULL;
  IF COL_LENGTH('dbo.prj_attribute_master_test','sp_standardisation_dataitem_id') IS NULL ALTER TABLE dbo.prj_attribute_master_test ADD sp_standardisation_dataitem_id varchar(255) NULL;
  IF COL_LENGTH('dbo.prj_attribute_master_test','sp_as_reported_dataitem_logic') IS NULL ALTER TABLE dbo.prj_attribute_master_test ADD sp_as_reported_dataitem_logic nvarchar(max) NULL;
  IF COL_LENGTH('dbo.prj_attribute_master_test','calculated_in_cfv') IS NULL ALTER TABLE dbo.prj_attribute_master_test ADD calculated_in_cfv varchar(5) NULL;
  IF COL_LENGTH('dbo.prj_attribute_master_test','editable_in_historicals') IS NULL ALTER TABLE dbo.prj_attribute_master_test ADD editable_in_historicals varchar(5) NULL;

  /* Explicit non-dynamic reconciliation: portfolio/reference. */
  IF COL_LENGTH('dbo.prj_portfolio_reference_test','sector_name') IS NULL ALTER TABLE dbo.prj_portfolio_reference_test ADD sector_name varchar(120) NULL;
  IF COL_LENGTH('dbo.prj_portfolio_reference_test','sub_sector') IS NULL ALTER TABLE dbo.prj_portfolio_reference_test ADD sub_sector varchar(120) NULL;
  IF COL_LENGTH('dbo.prj_portfolio_reference_test','remark') IS NULL ALTER TABLE dbo.prj_portfolio_reference_test ADD remark varchar(500) NULL;
  IF COL_LENGTH('dbo.prj_attribute_portfolio_scope_test','description') IS NULL ALTER TABLE dbo.prj_attribute_portfolio_scope_test ADD description nvarchar(max) NULL;

  /* Explicit non-dynamic reconciliation: business rules. */
  IF COL_LENGTH('dbo.prj_attribute_business_rules_test','source_abbr_name') IS NULL ALTER TABLE dbo.prj_attribute_business_rules_test ADD source_abbr_name varchar(50) NULL;
  IF COL_LENGTH('dbo.prj_attribute_business_rules_test','editable') IS NULL ALTER TABLE dbo.prj_attribute_business_rules_test ADD editable varchar(20) NULL;
  IF COL_LENGTH('dbo.prj_attribute_business_rules_test','symbol') IS NULL ALTER TABLE dbo.prj_attribute_business_rules_test ADD symbol varchar(50) NULL;
  IF COL_LENGTH('dbo.prj_attribute_business_rules_test','mapping_type') IS NULL ALTER TABLE dbo.prj_attribute_business_rules_test ADD mapping_type varchar(255) NULL;
  IF COL_LENGTH('dbo.prj_attribute_business_rules_test','mapping_logic') IS NULL ALTER TABLE dbo.prj_attribute_business_rules_test ADD mapping_logic nvarchar(max) NULL;
  IF COL_LENGTH('dbo.prj_attribute_business_rules_test','calculation_logic') IS NULL ALTER TABLE dbo.prj_attribute_business_rules_test ADD calculation_logic nvarchar(max) NULL;
  IF COL_LENGTH('dbo.prj_attribute_business_rules_test','business_logic') IS NULL ALTER TABLE dbo.prj_attribute_business_rules_test ADD business_logic nvarchar(max) NULL;

  /* Explicit non-dynamic reconciliation: prompts. */
  IF COL_LENGTH('dbo.prj_scanning_prompt_reference_test','scope_id') IS NULL ALTER TABLE dbo.prj_scanning_prompt_reference_test ADD scope_id int NULL;
  IF COL_LENGTH('dbo.prj_scanning_prompt_reference_test','port_ref_id') IS NULL ALTER TABLE dbo.prj_scanning_prompt_reference_test ADD port_ref_id int NULL;
  IF COL_LENGTH('dbo.prj_scanning_prompt_reference_test','required_by_scope') IS NULL ALTER TABLE dbo.prj_scanning_prompt_reference_test ADD required_by_scope varchar(255) NULL;
  IF COL_LENGTH('dbo.prj_scanning_prompt_reference_test','attribute_name') IS NULL ALTER TABLE dbo.prj_scanning_prompt_reference_test ADD attribute_name varchar(500) NULL;
  IF COL_LENGTH('dbo.prj_scanning_prompt_reference_test','section') IS NULL ALTER TABLE dbo.prj_scanning_prompt_reference_test ADD section varchar(255) NULL;
  IF COL_LENGTH('dbo.prj_scanning_prompt_reference_test','sub_section') IS NULL ALTER TABLE dbo.prj_scanning_prompt_reference_test ADD sub_section varchar(255) NULL;
  IF COL_LENGTH('dbo.prj_scanning_prompt_reference_test','data_type') IS NULL ALTER TABLE dbo.prj_scanning_prompt_reference_test ADD data_type varchar(100) NULL;
  IF COL_LENGTH('dbo.prj_scanning_prompt_reference_test','calculated_or_reported') IS NULL ALTER TABLE dbo.prj_scanning_prompt_reference_test ADD calculated_or_reported varchar(100) NULL;
  IF COL_LENGTH('dbo.prj_scanning_prompt_reference_test','calculation_logic') IS NULL ALTER TABLE dbo.prj_scanning_prompt_reference_test ADD calculation_logic nvarchar(max) NULL;
  IF COL_LENGTH('dbo.prj_scanning_prompt_reference_test','segment') IS NULL ALTER TABLE dbo.prj_scanning_prompt_reference_test ADD segment varchar(255) NULL;
  IF COL_LENGTH('dbo.prj_scanning_prompt_reference_test','attribute_description') IS NULL ALTER TABLE dbo.prj_scanning_prompt_reference_test ADD attribute_description nvarchar(max) NULL;
  IF COL_LENGTH('dbo.prj_scanning_prompt_reference_test','examples') IS NOT NULL ALTER TABLE dbo.prj_scanning_prompt_reference_test DROP COLUMN examples;
  IF COL_LENGTH('dbo.prj_scanning_prompt_reference_test','display_order') IS NULL ALTER TABLE dbo.prj_scanning_prompt_reference_test ADD display_order int NULL;

  /* Explicit non-dynamic audit columns, with defaults for existing rows. */
  IF COL_LENGTH('dbo.prj_attribute_master_test','is_active') IS NULL ALTER TABLE dbo.prj_attribute_master_test ADD is_active bit NOT NULL CONSTRAINT DF_ddam_master_active_existing DEFAULT(1) WITH VALUES;
  IF COL_LENGTH('dbo.prj_attribute_master_test','created_at') IS NULL ALTER TABLE dbo.prj_attribute_master_test ADD created_at datetime2 NOT NULL CONSTRAINT DF_ddam_master_created_existing DEFAULT(sysutcdatetime()) WITH VALUES;
  IF COL_LENGTH('dbo.prj_attribute_master_test','updated_at') IS NULL ALTER TABLE dbo.prj_attribute_master_test ADD updated_at datetime2 NOT NULL CONSTRAINT DF_ddam_master_updated_existing DEFAULT(sysutcdatetime()) WITH VALUES;
  IF COL_LENGTH('dbo.prj_attribute_master_test','created_by') IS NULL ALTER TABLE dbo.prj_attribute_master_test ADD created_by varchar(128) NOT NULL CONSTRAINT DF_ddam_master_created_by_existing DEFAULT('sysuser') WITH VALUES;
  IF COL_LENGTH('dbo.prj_attribute_master_test','updated_by') IS NULL ALTER TABLE dbo.prj_attribute_master_test ADD updated_by varchar(128) NOT NULL CONSTRAINT DF_ddam_master_updated_by_existing DEFAULT('sysuser') WITH VALUES;

  IF COL_LENGTH('dbo.prj_portfolio_reference_test','is_active') IS NULL ALTER TABLE dbo.prj_portfolio_reference_test ADD is_active bit NOT NULL CONSTRAINT DF_ddam_port_active_existing DEFAULT(1) WITH VALUES;
  IF COL_LENGTH('dbo.prj_portfolio_reference_test','created_at') IS NULL ALTER TABLE dbo.prj_portfolio_reference_test ADD created_at datetime2 NOT NULL CONSTRAINT DF_ddam_port_created_existing DEFAULT(sysutcdatetime()) WITH VALUES;
  IF COL_LENGTH('dbo.prj_portfolio_reference_test','updated_at') IS NULL ALTER TABLE dbo.prj_portfolio_reference_test ADD updated_at datetime2 NOT NULL CONSTRAINT DF_ddam_port_updated_existing DEFAULT(sysutcdatetime()) WITH VALUES;
  IF COL_LENGTH('dbo.prj_portfolio_reference_test','created_by') IS NULL ALTER TABLE dbo.prj_portfolio_reference_test ADD created_by varchar(128) NOT NULL CONSTRAINT DF_ddam_port_created_by_existing DEFAULT('sysuser') WITH VALUES;
  IF COL_LENGTH('dbo.prj_portfolio_reference_test','updated_by') IS NULL ALTER TABLE dbo.prj_portfolio_reference_test ADD updated_by varchar(128) NOT NULL CONSTRAINT DF_ddam_port_updated_by_existing DEFAULT('sysuser') WITH VALUES;

  IF COL_LENGTH('dbo.prj_attribute_portfolio_scope_test','is_active') IS NULL ALTER TABLE dbo.prj_attribute_portfolio_scope_test ADD is_active bit NOT NULL CONSTRAINT DF_ddam_scope_active_existing DEFAULT(1) WITH VALUES;
  IF COL_LENGTH('dbo.prj_attribute_portfolio_scope_test','created_at') IS NULL ALTER TABLE dbo.prj_attribute_portfolio_scope_test ADD created_at datetime2 NOT NULL CONSTRAINT DF_ddam_scope_created_existing DEFAULT(sysutcdatetime()) WITH VALUES;
  IF COL_LENGTH('dbo.prj_attribute_portfolio_scope_test','updated_at') IS NULL ALTER TABLE dbo.prj_attribute_portfolio_scope_test ADD updated_at datetime2 NOT NULL CONSTRAINT DF_ddam_scope_updated_existing DEFAULT(sysutcdatetime()) WITH VALUES;
  IF COL_LENGTH('dbo.prj_attribute_portfolio_scope_test','created_by') IS NULL ALTER TABLE dbo.prj_attribute_portfolio_scope_test ADD created_by varchar(128) NOT NULL CONSTRAINT DF_ddam_scope_created_by_existing DEFAULT('sysuser') WITH VALUES;
  IF COL_LENGTH('dbo.prj_attribute_portfolio_scope_test','updated_by') IS NULL ALTER TABLE dbo.prj_attribute_portfolio_scope_test ADD updated_by varchar(128) NOT NULL CONSTRAINT DF_ddam_scope_updated_by_existing DEFAULT('sysuser') WITH VALUES;

  IF COL_LENGTH('dbo.prj_attribute_business_rules_test','is_active') IS NULL ALTER TABLE dbo.prj_attribute_business_rules_test ADD is_active bit NOT NULL CONSTRAINT DF_ddam_rules_active_existing DEFAULT(1) WITH VALUES;
  IF COL_LENGTH('dbo.prj_attribute_business_rules_test','created_at') IS NULL ALTER TABLE dbo.prj_attribute_business_rules_test ADD created_at datetime2 NOT NULL CONSTRAINT DF_ddam_rules_created_existing DEFAULT(sysutcdatetime()) WITH VALUES;
  IF COL_LENGTH('dbo.prj_attribute_business_rules_test','updated_at') IS NULL ALTER TABLE dbo.prj_attribute_business_rules_test ADD updated_at datetime2 NOT NULL CONSTRAINT DF_ddam_rules_updated_existing DEFAULT(sysutcdatetime()) WITH VALUES;
  IF COL_LENGTH('dbo.prj_attribute_business_rules_test','created_by') IS NULL ALTER TABLE dbo.prj_attribute_business_rules_test ADD created_by varchar(128) NOT NULL CONSTRAINT DF_ddam_rules_created_by_existing DEFAULT('sysuser') WITH VALUES;
  IF COL_LENGTH('dbo.prj_attribute_business_rules_test','updated_by') IS NULL ALTER TABLE dbo.prj_attribute_business_rules_test ADD updated_by varchar(128) NOT NULL CONSTRAINT DF_ddam_rules_updated_by_existing DEFAULT('sysuser') WITH VALUES;

  IF COL_LENGTH('dbo.prj_scanning_prompt_reference_test','is_active') IS NULL ALTER TABLE dbo.prj_scanning_prompt_reference_test ADD is_active bit NOT NULL CONSTRAINT DF_ddam_prompt_active_existing DEFAULT(1) WITH VALUES;
  IF COL_LENGTH('dbo.prj_scanning_prompt_reference_test','created_at') IS NULL ALTER TABLE dbo.prj_scanning_prompt_reference_test ADD created_at datetime2 NOT NULL CONSTRAINT DF_ddam_prompt_created_existing DEFAULT(sysutcdatetime()) WITH VALUES;
  IF COL_LENGTH('dbo.prj_scanning_prompt_reference_test','updated_at') IS NULL ALTER TABLE dbo.prj_scanning_prompt_reference_test ADD updated_at datetime2 NOT NULL CONSTRAINT DF_ddam_prompt_updated_existing DEFAULT(sysutcdatetime()) WITH VALUES;
  IF COL_LENGTH('dbo.prj_scanning_prompt_reference_test','created_by') IS NULL ALTER TABLE dbo.prj_scanning_prompt_reference_test ADD created_by varchar(128) NOT NULL CONSTRAINT DF_ddam_prompt_created_by_existing DEFAULT('sysuser') WITH VALUES;
  IF COL_LENGTH('dbo.prj_scanning_prompt_reference_test','updated_by') IS NULL ALTER TABLE dbo.prj_scanning_prompt_reference_test ADD updated_by varchar(128) NOT NULL CONSTRAINT DF_ddam_prompt_updated_by_existing DEFAULT('sysuser') WITH VALUES;

  /* One active logical record per required key. */
  IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID(N'dbo.prj_portfolio_reference_test') AND name=N'UX_ddam_portfolio_reference_key')
    CREATE UNIQUE INDEX UX_ddam_portfolio_reference_key ON dbo.prj_portfolio_reference_test(port_name, sector_name, sub_sector);
  IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID(N'dbo.prj_attribute_master_test') AND name=N'UX_ddam_attribute_physical_name')
    CREATE UNIQUE INDEX UX_ddam_attribute_physical_name ON dbo.prj_attribute_master_test(prj_physical_attribute_name) WHERE prj_physical_attribute_name IS NOT NULL;
  IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID(N'dbo.prj_attribute_portfolio_scope_test') AND name=N'UX_ddam_attribute_scope_prj_port')
    CREATE UNIQUE INDEX UX_ddam_attribute_scope_prj_port ON dbo.prj_attribute_portfolio_scope_test(prj_id, port_ref_id);
  IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID(N'dbo.prj_attribute_business_rules_test') AND name=N'UX_ddam_business_rules_scope')
    CREATE UNIQUE INDEX UX_ddam_business_rules_scope ON dbo.prj_attribute_business_rules_test(scope_id);

  /* Reference portfolio seed values. */
  IF NOT EXISTS (SELECT 1 FROM dbo.prj_portfolio_reference_test WHERE port_name='FI' AND sector_name='Banks' AND ISNULL(sub_sector,'')='')
    INSERT INTO dbo.prj_portfolio_reference_test(port_name,sector_name,sub_sector,remark) VALUES('FI','Banks',NULL,'Financial Institutes - Banks');
  IF NOT EXISTS (SELECT 1 FROM dbo.prj_portfolio_reference_test WHERE port_name='FI' AND sector_name='Insurance' AND ISNULL(sub_sector,'')='')
    INSERT INTO dbo.prj_portfolio_reference_test(port_name,sector_name,sub_sector,remark) VALUES('FI','Insurance',NULL,'Financial Institutes - Insurance');
  IF NOT EXISTS (SELECT 1 FROM dbo.prj_portfolio_reference_test WHERE port_name='Corporate' AND sector_name='Corporate' AND ISNULL(sub_sector,'')='')
    INSERT INTO dbo.prj_portfolio_reference_test(port_name,sector_name,sub_sector,remark) VALUES('Corporate','Corporate',NULL,'Global Corporates');
  IF NOT EXISTS (SELECT 1 FROM dbo.prj_portfolio_reference_test WHERE port_name='Zeus Downstream' AND sector_name='Zeus Downstream' AND ISNULL(sub_sector,'')='')
    INSERT INTO dbo.prj_portfolio_reference_test(port_name,sector_name,sub_sector,remark) VALUES('Zeus Downstream','Zeus Downstream',NULL,'Zeus Downstream');

  COMMIT TRANSACTION;
END TRY
BEGIN CATCH
  IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
  DECLARE @ErrorMessage nvarchar(2048) = ERROR_MESSAGE();
  DECLARE @ErrorSeverity int = ERROR_SEVERITY();
  DECLARE @ErrorState int = ERROR_STATE();
  RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
END CATCH;
