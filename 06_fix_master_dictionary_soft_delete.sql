/* Compatibility upgrade for existing master_dictionary tables.
   Safe to run repeatedly. Preserves all existing data. */
SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF OBJECT_ID('dbo.master_dictionary', 'U') IS NULL
BEGIN
    THROW 50001, 'dbo.master_dictionary does not exist. Run 01_schema.sql before this compatibility script.', 1;
END;

IF COL_LENGTH('dbo.master_dictionary','is_active') IS NULL
BEGIN
    ALTER TABLE dbo.master_dictionary
      ADD is_active BIT NOT NULL CONSTRAINT DF_master_dictionary_is_active DEFAULT 1 WITH VALUES;
END;

IF COL_LENGTH('dbo.master_dictionary','is_deleted') IS NULL
BEGIN
    ALTER TABLE dbo.master_dictionary
      ADD is_deleted BIT NOT NULL CONSTRAINT DF_master_dictionary_is_deleted DEFAULT 0 WITH VALUES;
END;

IF COL_LENGTH('dbo.master_dictionary','deleted_at') IS NULL
BEGIN
    ALTER TABLE dbo.master_dictionary ADD deleted_at DATETIME2 NULL;
END;

IF COL_LENGTH('dbo.master_dictionary','deleted_by') IS NULL
BEGIN
    ALTER TABLE dbo.master_dictionary ADD deleted_by NVARCHAR(100) NULL;
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'ix_master_dictionary_active_deleted'
      AND object_id = OBJECT_ID('dbo.master_dictionary')
)
BEGIN
    CREATE INDEX ix_master_dictionary_active_deleted
      ON dbo.master_dictionary(is_active, is_deleted, prj_id);
END;

COMMIT TRANSACTION;
GO
