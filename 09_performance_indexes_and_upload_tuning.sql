/* Part 3 performance upgrade. Safe to rerun. Run against PRJ_DB. */
SET NOCOUNT ON;

/* Master Dictionary: upload and active-record lookup */
IF OBJECT_ID('dbo.master_dictionary','U') IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.master_dictionary') AND name='IX_master_dictionary_prj_id_active')
    CREATE NONCLUSTERED INDEX IX_master_dictionary_prj_id_active ON dbo.master_dictionary(prj_id, is_active, is_deleted);

/* Legacy target tables: batch lookup by PRJ ID */
IF OBJECT_ID('dbo.prj_attribute','U') IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.prj_attribute') AND name='IX_prj_attribute_prj_id')
    CREATE NONCLUSTERED INDEX IX_prj_attribute_prj_id ON dbo.prj_attribute(prj_id);
IF OBJECT_ID('dbo.prj_attr_business_logic','U') IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.prj_attr_business_logic') AND name='IX_prj_attr_business_logic_prj_id')
    CREATE NONCLUSTERED INDEX IX_prj_attr_business_logic_prj_id ON dbo.prj_attr_business_logic(prj_id);
IF OBJECT_ID('dbo.prj_attr_business_logic_scope','U') IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.prj_attr_business_logic_scope') AND name='IX_prj_attr_business_logic_scope_prj_id')
    CREATE NONCLUSTERED INDEX IX_prj_attr_business_logic_scope_prj_id ON dbo.prj_attr_business_logic_scope(prj_id);

/* Part 3 scope sync and prompt operations */
IF OBJECT_ID('dbo.prj_attribute_portfolio_scope_test','U') IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.prj_attribute_portfolio_scope_test') AND name='IX_scope_test_prj_port')
    CREATE NONCLUSTERED INDEX IX_scope_test_prj_port ON dbo.prj_attribute_portfolio_scope_test(prj_id, port_ref_id, is_active, is_deleted);
IF OBJECT_ID('dbo.prj_scanning_prompt_reference_test','U') IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.prj_scanning_prompt_reference_test') AND name='IX_prompt_reference_test_prj_port')
    CREATE NONCLUSTERED INDEX IX_prompt_reference_test_prj_port ON dbo.prj_scanning_prompt_reference_test(prj_id, port_ref_id, is_active, is_deleted);

/* Audit retrieval without table scans */
IF OBJECT_ID('dbo.audit_log','U') IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.audit_log') AND name='IX_audit_log_prj_changed_at')
    CREATE NONCLUSTERED INDEX IX_audit_log_prj_changed_at ON dbo.audit_log(prj_id, changed_at DESC);
IF OBJECT_ID('dbo.history_log','U') IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.history_log') AND name='IX_history_log_prj_changed_at')
    CREATE NONCLUSTERED INDEX IX_history_log_prj_changed_at ON dbo.history_log(prj_id, changed_at DESC);
GO
