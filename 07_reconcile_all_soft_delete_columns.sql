/*
  Part 3 full schema reconciliation for existing databases.
  Safe to run repeatedly. It only ADDs missing columns / indexes and does not delete data.
  Run this once against PRJ_DB after deploying the revised application.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;
BEGIN TRANSACTION;

/* Generic reconciliation for every table that the revised UI queries with soft-delete fields. */
DECLARE @tables TABLE (table_name SYSNAME NOT NULL, key_column SYSNAME NULL);
INSERT INTO @tables(table_name, key_column) VALUES
 ('master_dictionary', 'prj_id'),
 ('prj_attribute_master_test', 'prj_id'),
 ('prj_attribute_portfolio_scope_test', 'scope_id'),
 ('prj_attribute_business_rules_test', 'id'),
 ('prj_ui_display_config_test', 'display_id'),
 ('prj_scanning_prompt_reference_test', 'prompt_id');

DECLARE @table SYSNAME, @key SYSNAME, @sql NVARCHAR(MAX);
DECLARE reconcile_cursor CURSOR LOCAL FAST_FORWARD FOR SELECT table_name, key_column FROM @tables;
OPEN reconcile_cursor;
FETCH NEXT FROM reconcile_cursor INTO @table, @key;
WHILE @@FETCH_STATUS = 0
BEGIN
    IF OBJECT_ID(N'dbo.' + QUOTENAME(@table), 'U') IS NOT NULL
    BEGIN
        IF COL_LENGTH(N'dbo.' + @table, 'is_active') IS NULL
        BEGIN
            SET @sql = N'ALTER TABLE dbo.' + QUOTENAME(@table) + N' ADD is_active BIT NOT NULL CONSTRAINT ' + QUOTENAME(N'DF_' + @table + N'_is_active') + N' DEFAULT 1 WITH VALUES;';
            EXEC sys.sp_executesql @sql;
        END;
        IF COL_LENGTH(N'dbo.' + @table, 'is_deleted') IS NULL
        BEGIN
            SET @sql = N'ALTER TABLE dbo.' + QUOTENAME(@table) + N' ADD is_deleted BIT NOT NULL CONSTRAINT ' + QUOTENAME(N'DF_' + @table + N'_is_deleted') + N' DEFAULT 0 WITH VALUES;';
            EXEC sys.sp_executesql @sql;
        END;
        IF COL_LENGTH(N'dbo.' + @table, 'deleted_at') IS NULL
        BEGIN
            SET @sql = N'ALTER TABLE dbo.' + QUOTENAME(@table) + N' ADD deleted_at DATETIME2 NULL;';
            EXEC sys.sp_executesql @sql;
        END;
        IF COL_LENGTH(N'dbo.' + @table, 'deleted_by') IS NULL
        BEGIN
            SET @sql = N'ALTER TABLE dbo.' + QUOTENAME(@table) + N' ADD deleted_by NVARCHAR(100) NULL;';
            EXEC sys.sp_executesql @sql;
        END;
    END
    FETCH NEXT FROM reconcile_cursor INTO @table, @key;
END
CLOSE reconcile_cursor;
DEALLOCATE reconcile_cursor;

/* Reconcile all Master Dictionary columns referenced by the revised model/upload mapping. */
IF OBJECT_ID('dbo.master_dictionary', 'U') IS NULL
    THROW 50001, 'dbo.master_dictionary does not exist. Run 01_schema.sql first.', 1;

DECLARE @master_columns TABLE (column_name SYSNAME NOT NULL, data_type NVARCHAR(200) NOT NULL);
INSERT INTO @master_columns(column_name, data_type) VALUES
 ('calculated_or_reported', 'NVARCHAR(100) NULL'),
 ('calculation_logic_details', 'NVARCHAR(MAX) NULL'),
 ('release_scope', 'NVARCHAR(255) NULL'),
 ('calculation_in_prj', 'NVARCHAR(MAX) NULL'),
 ('editable_in_historicals', 'BIT NULL'),
 ('gc_template_attribute_name', 'NVARCHAR(255) NULL'),
 ('sp_standardisation_attribute_name', 'NVARCHAR(255) NULL'),
 ('sp_standardisation_dataitem_id', 'NVARCHAR(100) NULL'),
 ('sp_as_reported_dataitem_id', 'NVARCHAR(MAX) NULL'),
 ('updates', 'NVARCHAR(MAX) NULL'),
 ('updated_on', 'DATETIME2 NULL'),
 ('zeus_attribute', 'NVARCHAR(255) NULL'),
 ('zeus_table_name', 'NVARCHAR(255) NULL'),
 ('zeus_description', 'NVARCHAR(MAX) NULL'),
 ('comments', 'NVARCHAR(MAX) NULL'),
 ('snl_dataitemid', 'NVARCHAR(100) NULL'),
 ('scanned_calculated', 'NVARCHAR(100) NULL'),
 ('version_no', 'INT NOT NULL CONSTRAINT DF_master_dictionary_version_no DEFAULT 1 WITH VALUES'),
 ('created_by', 'NVARCHAR(100) NOT NULL CONSTRAINT DF_master_dictionary_created_by DEFAULT ''sysuser'' WITH VALUES'),
 ('updated_by', 'NVARCHAR(100) NOT NULL CONSTRAINT DF_master_dictionary_updated_by DEFAULT ''sysuser'' WITH VALUES');

DECLARE @col SYSNAME, @type NVARCHAR(200);
DECLARE master_cursor CURSOR LOCAL FAST_FORWARD FOR SELECT column_name, data_type FROM @master_columns;
OPEN master_cursor;
FETCH NEXT FROM master_cursor INTO @col, @type;
WHILE @@FETCH_STATUS = 0
BEGIN
    IF COL_LENGTH('dbo.master_dictionary', @col) IS NULL
    BEGIN
       SET @sql = N'ALTER TABLE dbo.master_dictionary ADD ' + QUOTENAME(@col) + N' ' + @type + N';';
       EXEC sys.sp_executesql @sql;
    END
    FETCH NEXT FROM master_cursor INTO @col, @type;
END
CLOSE master_cursor;
DEALLOCATE master_cursor;

/* sign_flipping is a text multiplier, e.g. -1, 1, or formula. */
IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.master_dictionary') AND name = 'sign_flipping' AND system_type_id = 104)
    ALTER TABLE dbo.master_dictionary ALTER COLUMN sign_flipping NVARCHAR(100) NULL;

/* Helpful indexes used by active-record load and PRJ ID validation. */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='ix_master_dictionary_active_deleted' AND object_id=OBJECT_ID('dbo.master_dictionary'))
    CREATE INDEX ix_master_dictionary_active_deleted ON dbo.master_dictionary(is_active, is_deleted, prj_id);
IF OBJECT_ID('dbo.prj_attribute_business_rules_test','U') IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='ix_business_rules_active_deleted' AND object_id=OBJECT_ID('dbo.prj_attribute_business_rules_test'))
    CREATE INDEX ix_business_rules_active_deleted ON dbo.prj_attribute_business_rules_test(is_active, is_deleted, scope_id);

COMMIT TRANSACTION;
PRINT 'Part 3 schema reconciliation complete: all required soft-delete columns and Master Dictionary mapping columns are present.';
