/* Data Dictionary Admin App: idempotent create / upgrade script.
   Creates all mutable tables and upgrades legacy tables for soft-delete support.
   Static/reference tables (prj_portfolio_reference, prompt_library, prj_data_source) are not altered by application CRUD. */
USE PRJ_DB;
GO
:r .\01_schema.sql
GO
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
