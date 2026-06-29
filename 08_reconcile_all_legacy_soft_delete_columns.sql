/*
  Part 3 - Full legacy/base/test table soft-delete reconciliation
  Safe to rerun. Adds only missing columns and indexes.
*/
SET NOCOUNT ON;

DECLARE @tables TABLE (table_name SYSNAME PRIMARY KEY, key_column SYSNAME NULL);
INSERT INTO @tables(table_name, key_column) VALUES
 -- Master and original runtime tables
 ('master_dictionary', 'prj_id'),
 ('prj_attribute', 'prj_id'),
 ('prj_attr_business_logic', 'prj_id'),
 ('prj_attr_business_logic_scope', 'prj_id'),
 ('prompt_library', 'prompt_id'),
 -- Legacy / user-created test tables
 ('prj_attribute_test', 'prj_id'),
 ('prj_attribute_test2', 'prj_id'),
 ('prj_attribute_master_test', 'prj_id'),
 ('prj_attr_business_logic_test', 'prj_id'),
 ('prj_attr_business_logic_test2', 'prj_id'),
 ('prj_attr_business_logic_scope_test', 'prj_id'),
 ('prj_attr_business_logic_scope_test2', 'prj_id'),
 -- Revised Part 3 configuration tables
 ('prj_portfolio_reference_test', 'port_ref_id'),
 ('prj_attribute_portfolio_scope_test', 'scope_id'),
 ('prj_attribute_business_rules_test', 'id'),
 ('prj_ui_display_config_test', 'display_id'),
 ('prj_scanning_prompt_reference_test', 'prompt_id');

DECLARE @table SYSNAME, @key SYSNAME, @sql NVARCHAR(MAX);
DECLARE reconcile_cursor CURSOR LOCAL FAST_FORWARD FOR
 SELECT table_name, key_column FROM @tables;
OPEN reconcile_cursor;
FETCH NEXT FROM reconcile_cursor INTO @table, @key;
WHILE @@FETCH_STATUS = 0
BEGIN
  IF OBJECT_ID(N'dbo.' + QUOTENAME(@table), N'U') IS NOT NULL
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

    -- Create a generic active/deleted index only when its key column exists.
    IF @key IS NOT NULL
       AND COL_LENGTH(N'dbo.' + @table, @key) IS NOT NULL
       AND NOT EXISTS (
          SELECT 1 FROM sys.indexes
          WHERE object_id = OBJECT_ID(N'dbo.' + QUOTENAME(@table))
            AND name = N'IX_' + @table + N'_active_deleted')
    BEGIN
      SET @sql = N'CREATE INDEX ' + QUOTENAME(N'IX_' + @table + N'_active_deleted')
               + N' ON dbo.' + QUOTENAME(@table)
               + N'(is_active, is_deleted, ' + QUOTENAME(@key) + N');';
      EXEC sys.sp_executesql @sql;
    END;

    PRINT N'Reconciled dbo.' + @table;
  END
  ELSE
    PRINT N'Skipped dbo.' + @table + N' because table does not exist.';

  FETCH NEXT FROM reconcile_cursor INTO @table, @key;
END
CLOSE reconcile_cursor;
DEALLOCATE reconcile_cursor;
GO

