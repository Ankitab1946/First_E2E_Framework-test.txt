/* Part 3: Master upload mapping compatibility. Safe to re-run. */
SET NOCOUNT ON;

/* Ensure legacy business-logic target contains fields used by Master Dictionary. */
IF OBJECT_ID(N'dbo.prj_attr_business_logic', N'U') IS NOT NULL
BEGIN
    IF COL_LENGTH(N'dbo.prj_attr_business_logic', N'sp_standardisation_attribute_name') IS NULL
        ALTER TABLE dbo.prj_attr_business_logic ADD sp_standardisation_attribute_name NVARCHAR(255) NULL;
    IF COL_LENGTH(N'dbo.prj_attr_business_logic', N'sp_standardisation_dataitem_id') IS NULL
        ALTER TABLE dbo.prj_attr_business_logic ADD sp_standardisation_dataitem_id NVARCHAR(100) NULL;
    IF COL_LENGTH(N'dbo.prj_attr_business_logic', N'sp_as_reported_dataitem_id') IS NULL
        ALTER TABLE dbo.prj_attr_business_logic ADD sp_as_reported_dataitem_id NVARCHAR(100) NULL;
END
GO
