/* Run this only to inspect pre-existing legacy objects before bootstrap. */
SELECT
    s.name AS schema_name,
    o.name AS object_name,
    o.type_desc,
    o.create_date,
    o.modify_date
FROM sys.objects o
JOIN sys.schemas s ON s.schema_id = o.schema_id
WHERE o.name IN (N'ug_portfolio_rerenece', N'prj_portfolio_reference_test')
   OR o.name LIKE N'%portfolio%reference%'
ORDER BY s.name, o.name;

SELECT
    s.name AS schema_name,
    t.name AS table_name,
    i.name AS index_or_constraint_name,
    i.type_desc,
    i.is_unique
FROM sys.indexes i
JOIN sys.tables t ON t.object_id = i.object_id
JOIN sys.schemas s ON s.schema_id = t.schema_id
WHERE i.name IN (N'ug_portfolio_rerenece', N'uq_portfolio_reference')
   OR i.name LIKE N'%portfolio%reference%'
ORDER BY s.name, t.name, i.name;
