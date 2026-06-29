/*
  Part 3 - Master Dictionary text-length reconciliation
  Purpose: Fix SQL Server "String or binary data would be truncated" errors
  reported against legacy generic columns such as p25, p26 and p27.
  Safe to re-run. Existing data is preserved.
*/
SET NOCOUNT ON;

DECLARE @TableName sysname = N'master_dictionary';
DECLARE @ColumnName sysname;
DECLARE @Sql nvarchar(max);

IF OBJECT_ID(N'dbo.master_dictionary', N'U') IS NULL
BEGIN
    THROW 51000, 'dbo.master_dictionary does not exist. Run base schema first.', 1;
END;

DECLARE @Columns TABLE (column_name sysname NOT NULL PRIMARY KEY);

/* Legacy generic columns seen in older Master Dictionary schema versions. */
INSERT INTO @Columns (column_name)
VALUES
(N'p25'), (N'p26'), (N'p27'),
(N'prj_attribute_name'),
(N'prj_attribute_description'),
(N'prj_physical_attribute_name'),
(N'calculated_or_reported'),
(N'calculation_logic'),
(N'calculation_logic_details'),
(N'where_in_financial_statement'),
(N'version_update'),
(N'release_scope'),
(N'mapping_type'),
(N'calculation_in_prj'),
(N'sign_flipping'),
(N'gc_template_attribute_name'),
(N'sp_standardisation_attribute_name'),
(N'sp_standardisation_dataitem_id'),
(N'sp_as_reported_dataitem_id'),
(N'updates'),
(N'zeus_attribute'),
(N'zeus_table_name'),
(N'zeus_description'),
(N'comments'),
(N'snl_dataitemid'),
(N'scanned_calculated');

DECLARE column_cursor CURSOR LOCAL FAST_FORWARD FOR
SELECT c.column_name
FROM @Columns c
JOIN sys.columns sc
  ON sc.object_id = OBJECT_ID(N'dbo.master_dictionary')
 AND sc.name = c.column_name
JOIN sys.types st
  ON st.user_type_id = sc.user_type_id
WHERE st.name IN (N'varchar', N'nvarchar', N'char', N'nchar')
  AND sc.max_length <> -1;

OPEN column_cursor;
FETCH NEXT FROM column_cursor INTO @ColumnName;

WHILE @@FETCH_STATUS = 0
BEGIN
    /* Do not change indexed columns here; legacy p25/p26/p27 and long text fields are non-key fields. */
    IF NOT EXISTS (
        SELECT 1
        FROM sys.index_columns ic
        JOIN sys.indexes i
          ON i.object_id = ic.object_id
         AND i.index_id = ic.index_id
        WHERE ic.object_id = OBJECT_ID(N'dbo.master_dictionary')
          AND ic.column_id = COLUMNPROPERTY(OBJECT_ID(N'dbo.master_dictionary'), @ColumnName, 'ColumnId')
          AND i.is_primary_key = 1
    )
    BEGIN
        SET @Sql = N'ALTER TABLE dbo.master_dictionary ALTER COLUMN ' + QUOTENAME(@ColumnName) + N' NVARCHAR(MAX) NULL;';
        PRINT @Sql;
        EXEC sp_executesql @Sql;
    END;
    FETCH NEXT FROM column_cursor INTO @ColumnName;
END;

CLOSE column_cursor;
DEALLOCATE column_cursor;
GO
