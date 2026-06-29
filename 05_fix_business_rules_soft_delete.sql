/* Fix for Business Rule tab on existing Part 3 databases.
   Adds soft-delete audit columns expected by the application model. Safe to run repeatedly. */
USE PRJ_DB;
GO
IF OBJECT_ID('dbo.prj_attribute_business_rules_test', 'U') IS NULL
BEGIN
    THROW 50001, 'Table dbo.prj_attribute_business_rules_test does not exist. Run 01_schema.sql first.', 1;
END
GO
IF COL_LENGTH('dbo.prj_attribute_business_rules_test', 'is_active') IS NULL
    ALTER TABLE dbo.prj_attribute_business_rules_test ADD is_active BIT NOT NULL CONSTRAINT DF_prj_attribute_business_rules_test_is_active DEFAULT 1 WITH VALUES;
GO
IF COL_LENGTH('dbo.prj_attribute_business_rules_test', 'is_deleted') IS NULL
    ALTER TABLE dbo.prj_attribute_business_rules_test ADD is_deleted BIT NOT NULL CONSTRAINT DF_prj_attribute_business_rules_test_is_deleted DEFAULT 0 WITH VALUES;
GO
IF COL_LENGTH('dbo.prj_attribute_business_rules_test', 'deleted_at') IS NULL
    ALTER TABLE dbo.prj_attribute_business_rules_test ADD deleted_at DATETIME2 NULL;
GO
IF COL_LENGTH('dbo.prj_attribute_business_rules_test', 'deleted_by') IS NULL
    ALTER TABLE dbo.prj_attribute_business_rules_test ADD deleted_by NVARCHAR(100) NULL;
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='ix_business_rules_active_deleted' AND object_id=OBJECT_ID('dbo.prj_attribute_business_rules_test'))
    CREATE INDEX ix_business_rules_active_deleted ON dbo.prj_attribute_business_rules_test(is_active, is_deleted, scope_id);
GO
PRINT 'Business Rule soft-delete columns verified/created successfully.';
