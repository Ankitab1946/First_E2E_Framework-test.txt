# PRJ Data Dictionary DB Architecture

## 1. Business Problem

The PRJ Data Dictionary Admin App manages financial-data attributes used across PRJ UI, historical data screens, HITL review, scanning prompts, and downstream integrations.

Before this design, attributes were difficult to maintain because attribute metadata, portfolio applicability, business rules, and scanning prompts were mixed across Excel files and application logic. This created common problems:

- Different teams used different versions of the dictionary.
- It was hard to know which attributes applied to Banks, Corporates, Insurance, or Zeus Downstream.
- Bulk Excel uploads could overwrite or duplicate data incorrectly.
- Prompt updates were not always scope-specific.
- Auditability was limited, making it difficult to trace who changed what and when.
- Adding or editing attributes required manual coordination across multiple dependent tables.

The database design solves this by separating the Data Dictionary into clear layers: master attribute definition, portfolio reference, scope applicability, business rules, scanning prompt configuration, and audit history.

---

## 2. High-Level Architecture

The PRJ Data Dictionary system follows a three-tier architecture:

```text
User / Admin
   |
   v
Streamlit UI
   |
   v
FastAPI / Swagger API
   |
   v
Service Layer
   |
   v
Repository Layer
   |
   v
SQL Server Database
```

### Main responsibilities

| Layer | Responsibility |
|---|---|
| Streamlit UI | User interaction, grids, upload/download, modal forms, filters, status messages |
| FastAPI API | Swagger endpoints, request validation, role checks, response contracts |
| Service Layer | Business rules, scope synchronization, Excel processing, audit handling |
| Repository Layer | SQL Server queries, inserts, updates, soft deletes, batch operations |
| SQL Server | Source of truth for attributes, scopes, prompts, and audit history |

---

## 3. Core Concepts

### 3.1 Attribute

An attribute is a business data point such as revenue, cash balance, net debt, total assets, or any financial-statement field.

Each attribute has one master definition in:

```text
prj_attribute_master_test
```

This table answers:

- What is the PRJ ID?
- What is the attribute name?
- What does the attribute mean?
- Where is it collected from in the financial statement?
- What is its physical/internal attribute name?

---

### 3.2 Portfolio / Sector

A portfolio defines the business area where an attribute applies.

Examples:

- FI Banks
- FI Insurance
- Corporates
- Zeus Downstream

Portfolio reference data is stored in:

```text
prj_portfolio_reference_test
```

This table is treated as a reference/static table inside the application.

---

### 3.3 Scope

A scope links one PRJ attribute to one portfolio.

Example:

```text
PRJ_002 + FI Banks      -> scope_id = 101
PRJ_002 + FI Insurance  -> scope_id = 102
```

This means the same attribute can be required by multiple portfolios, but each portfolio has its own scope row.

Scope records are stored in:

```text
prj_attribute_portfolio_scope_test
```

Important rule:

```text
One unique scope exists for each PRJ_ID + port_ref_id combination.
```

---

### 3.4 Business Rule

A business rule stores the source, mapping, editable flag, percentage/ratio flag, calculation logic, and related metadata for a scoped attribute.

Business rules are stored in:

```text
prj_attribute_business_rules_test
```

This table answers:

- Is the attribute editable?
- Is it amount, percentage, or ratio?
- What source is used?
- What mapping logic applies?
- Is the value calculated or reported?

---

### 3.5 Prompt Reference

Prompt records define how the scanning/HITL prompt layer should identify or describe an attribute.

Prompt records are stored in:

```text
prj_scanning_prompt_reference_test
```

This table is scope-aware. If an attribute applies to both FI Banks and FI Insurance, it can have separate prompt records per scope.

This prevents a Bank-specific prompt update from incorrectly changing the Insurance prompt.

---

### 3.6 Audit

All important changes are tracked in:

```text
audit_table_test
```

Audit captures insert, update, soft delete, reactivate, upload, and export activity.

---

## 4. The Four Layers Explained

The database model can be understood as four functional layers.

### Layer 1: Master Attribute Layer

Table:

```text
prj_attribute_master_test
```

Purpose:

Defines the attribute once. This is the canonical business definition.

Example:

```text
PRJ_ID: PRJ_002
Attribute Name: Cash and Cash Equivalents
Description: Cash held by the borrower
Section: Balance Sheet
```

This layer should not contain portfolio-specific duplication.

---

### Layer 2: Portfolio Scope Layer

Tables:

```text
prj_portfolio_reference_test
prj_attribute_portfolio_scope_test
```

Purpose:

Defines where the attribute applies.

Example:

```text
PRJ_002 required by FI Banks      -> one scope row
PRJ_002 required by FI Insurance  -> another scope row
```

This is the key design decision that supports multiple Required By selections without duplicating the master attribute.

---

### Layer 3: Rule and Prompt Layer

Tables:

```text
prj_attribute_business_rules_test
prj_scanning_prompt_reference_test
```

Purpose:

Stores operational logic for each scope.

Business rules define how the attribute behaves in the application.
Prompt references define how the attribute is scanned, displayed, or mapped in prompt workflows.

---

### Layer 4: Audit and History Layer

Table:

```text
audit_table_test
```

Purpose:

Provides traceability across all business operations.

This answers:

- Who changed the record?
- What changed?
- When did it change?
- Was it created manually or through Excel upload?
- Was it soft deleted or reactivated?

---

## 5. How Data Flows

### 5.1 Create New Attribute

```text
User fills Create Attribute form
   |
   v
Streamlit calls FastAPI create endpoint
   |
   v
Service validates mandatory fields
   |
   v
Insert/update master attribute
   |
   v
For each selected Required By checkbox:
   create/reactivate scope
   create/update business rule
   create blank prompt placeholder
   |
   v
Write audit record
```

If the user selects FI Banks and FI Insurance, the database creates:

```text
1 master attribute row
2 scope rows
2 business rule rows
2 prompt placeholder rows
```

---

### 5.2 Edit Attribute

```text
User selects one active attribute row
   |
   v
Edit modal opens in read-only mode
   |
   v
User clicks Edit Attribute
   |
   v
Fields unlock except PRJ_ID
   |
   v
User updates attribute and Required By selections
   |
   v
API updates master, scope, business rules, prompt placeholders
   |
   v
Audit is written
```

If a Required By value is removed, the related scope is soft-deactivated rather than physically deleted.

---

### 5.3 Bulk Master Dictionary Upload

```text
User uploads Master Dictionary Excel
   |
   v
Application detects header row and maps columns
   |
   v
Preview grid appears
   |
   v
Compare identifies inserts/updates/rejections
   |
   v
Finalize performs batch upsert
   |
   v
Valid rows are inserted/updated
   |
   v
Invalid rows are rejected with detailed reason
   |
   v
Audit is written
```

The upload is batch optimized for large files. A failure in one row should not block the entire upload.

---

### 5.4 Prompt Bulk Upload

```text
User uploads Prompt Excel workbook
   |
   v
User selects worksheet
   |
   v
Application maps prompt columns
   |
   v
Validates PRJ_ID against master table
   |
   v
Derives scope_id and port_ref_id
   |
   v
Updates existing prompt record or inserts new one
   |
   v
Shows rejected PRJ IDs or ambiguous scopes
```

Prompt updates are scope-specific. If the same PRJ ID has Bank and Insurance scopes, the system must know which scope to update.

---

### 5.5 Soft Delete and Reactivate

```text
User selects one active record
   |
   v
Soft Delete
   |
   v
Record is marked inactive
   |
   v
Deleted section shows inactive records
   |
   v
User selects deleted record
   |
   v
Reactivate
   |
   v
Record becomes active again
```

Records are not physically deleted during normal user operations.

---

## 6. Tables and Relationships

### 6.1 Approved Application Tables

Only these six application-managed tables are used:

```text
prj_attribute_master_test
prj_portfolio_reference_test
prj_attribute_portfolio_scope_test
prj_attribute_business_rules_test
prj_scanning_prompt_reference_test
audit_table_test
```

Legacy tables must not be reintroduced.

---

### 6.2 Relationship Diagram

```text
prj_attribute_master_test
        |
        | 1 to many by prj_id
        v
prj_attribute_portfolio_scope_test
        |
        | many to 1 by port_ref_id
        v
prj_portfolio_reference_test

prj_attribute_portfolio_scope_test
        |
        | 1 to 1 or 1 to many by scope_id
        v
prj_attribute_business_rules_test

prj_attribute_portfolio_scope_test
        |
        | 1 to many by scope_id
        v
prj_scanning_prompt_reference_test

All write actions
        |
        v
audit_table_test
```

---

### 6.3 Table Summary

| Table | Main Key | Purpose |
|---|---|---|
| `prj_attribute_master_test` | `prj_id` | Stores canonical attribute definition |
| `prj_portfolio_reference_test` | `port_ref_id` | Stores portfolio/sector reference values |
| `prj_attribute_portfolio_scope_test` | `scope_id` | Links PRJ attribute to portfolio |
| `prj_attribute_business_rules_test` | `id` | Stores business/mapping rules for each scope |
| `prj_scanning_prompt_reference_test` | `prompt_id` | Stores prompt/scanning metadata for each scope |
| `audit_table_test` | `audit_id` | Stores audit trail for changes |

---

### 6.4 Important Constraints

Recommended logical constraints:

```text
prj_attribute_master_test.prj_id should be unique.
prj_attribute_portfolio_scope_test should be unique by prj_id + port_ref_id.
prj_attribute_business_rules_test should be linked to scope_id.
prj_scanning_prompt_reference_test should be linked to scope_id and prj_id.
```

These constraints prevent duplicate scope records and ensure prompt updates can be scope-specific.

---

## 7. Key Design Decisions

### 7.1 Why separate master attribute and scope?

Because an attribute can apply to more than one portfolio.

If portfolio flags were stored only on the master record, then Bank-specific and Insurance-specific behaviour would be difficult to maintain independently.

Separating scope allows this:

```text
One PRJ attribute
Multiple portfolio scopes
Different prompt/rule details per scope
```

---

### 7.2 Why soft delete instead of physical delete?

Soft delete protects history and reduces operational risk.

A deleted record can be reactivated later, and audit can still show what happened.

---

### 7.3 Why keep Prompt records scope-specific?

Because the same PRJ ID can be required by different portfolios.

Example:

```text
PRJ_002 + FI Banks
PRJ_002 + FI Insurance
```

If the user updates the Bank prompt, only the Bank prompt row should change. The Insurance row should remain unchanged.

---

### 7.4 Why use audit table?

Enterprise dictionary changes need traceability.

Audit supports:

- production support
- compliance review
- troubleshooting
- change accountability
- rollback analysis

---

### 7.5 Why avoid legacy tables?

The application is designed around the six approved tables. Legacy tables such as old attribute, logic, or UI-display tables can create confusion, duplicate business logic, and wrong joins.

The current design keeps display order in the prompt table and avoids separate UI display configuration dependencies.

---

## 8. Common Scenarios

### Scenario 1: Add an attribute required by FI Banks and FI Insurance

Expected database result:

```text
prj_attribute_master_test             -> 1 row
prj_attribute_portfolio_scope_test    -> 2 rows
prj_attribute_business_rules_test     -> 2 rows
prj_scanning_prompt_reference_test    -> 2 placeholder rows
audit_table_test                      -> insert audit rows
```

---

### Scenario 2: Remove FI Insurance from an attribute

Expected behaviour:

```text
FI Banks scope remains active.
FI Insurance scope becomes inactive.
Master attribute remains active.
Audit records the update.
```

---

### Scenario 3: Upload Prompt Excel for PRJ with multiple scopes

If the PRJ has multiple active scopes, the upload must identify the target scope.

Accepted inputs:

- UI-selected target portfolio/scope
- Excel column such as `Required By Scope`

If no target can be resolved, the row should be rejected as ambiguous rather than updating all scopes.

---

### Scenario 4: Upload Master Dictionary with some bad rows

Expected behaviour:

```text
Valid rows are committed.
Invalid rows are rejected.
UI shows row-level failure reason.
Audit records successful changes.
```

---

### Scenario 5: Reactivate a deleted attribute

Expected behaviour:

```text
Deleted records are shown separately.
User selects one deleted record.
Reactivate sets is_active = 1.
Audit records reactivation.
```

---

## 9. Scalability and Performance

### 9.1 Current Performance Strategy

The application is optimized for hundreds to low thousands of records through:

- paged Data Dictionary loading
- batched Master Dictionary upload
- set-oriented SQL operations
- row-level rejection only for failed rows
- SQL Server indexes
- API timeout configuration
- Streamlit caching for read-heavy data

---

### 9.2 Important Indexes

Performance script:

```text
src/DataDictionaryAdminApp/sql/004_add_performance_indexes.sql
```

This should be run once per environment after the base schema script.

Recommended indexed areas:

- active attributes by `is_active`
- scopes by `prj_id`, `port_ref_id`, `is_active`
- business rules by `scope_id`
- prompts by `scope_id`, `prj_id`, `is_active`
- audit by table, action, timestamp

---

### 9.3 Bulk Upload Guidance

Recommended `.env` values:

```env
BULK_UPLOAD_BATCH_SIZE=250
DATA_DICTIONARY_DEFAULT_PAGE_SIZE=200
API_READ_TIMEOUT_SECONDS=90
API_WRITE_TIMEOUT_SECONDS=600
SQLALCHEMY_POOL_SIZE=5
SQLALCHEMY_MAX_OVERFLOW=5
SQLALCHEMY_POOL_PRE_PING=false
```

For large uploads, avoid per-row commits. Use batch upsert paths.

---

### 9.4 SQL Server Guidance

For good performance:

- Run performance indexes.
- Keep statistics updated.
- Avoid triggers on the six application tables unless necessary.
- Ensure SQL Server has enough tempdb and transaction log capacity.
- Avoid locking the same dictionary tables through manual SSMS edits during upload.

---

## 10. Troubleshooting

### 10.1 UI shows API connection timeout

Possible causes:

- FastAPI is not running.
- API port is incorrect.
- Upload is taking longer than configured timeout.
- SQL Server query is blocked.

Check:

```text
http://localhost:8503/docs
http://localhost:8503/api/v1/system/environment
```

---

### 10.2 Database schema validation is OK but API still fails

This usually means the issue is not missing tables. Check:

- SQL syntax errors
- bit-column conversion errors
- data-type mismatch
- duplicate key violation
- ambiguous prompt scope
- SQL Server permissions

Use API terminal logs and upload row-level diagnostics.

---

### 10.3 Prompt upload maps `attribute_name` as null

Check that the Excel header is similar to:

```text
Attribute Name( to be Viewed on Historical and HITL)
```

The parser should map any header beginning with `Attribute Name` to:

```text
attribute_name
```

If still null, check for hidden characters, merged cells, or incorrect header row.

---

### 10.4 Prompt update changes both Bank and Insurance records

This means the update was not scope-specific.

Fix by ensuring one of the following exists:

- `Required By Scope` column in Excel
- target portfolio selected in UI
- unique active scope for the PRJ ID

If a PRJ ID has multiple active scopes and no target scope is supplied, the row should be rejected as ambiguous.

---

### 10.5 Upload fails with SQL Server bit conversion error

Example:

```text
Conversion failed when converting nvarchar value 'N' to data type bit
```

Cause:

A Y/N field was inserted into a `bit` column without conversion.

Expected conversion:

```text
Y, Yes, True, 1  -> 1
N, No, False, 0 -> 0
```

---

### 10.6 Docker Kerberos connection fails

Check:

```bash
docker compose exec api klist
```

Also verify:

- `krb5.conf` is mounted correctly
- keytab is mounted correctly
- service principal is correct
- SQL Server SPN is correct
- container DNS can resolve SQL Server host
- SQL Server allows Kerberos/Integrated Authentication

---

## 11. FAQ

### Q1. Why are there multiple rows for the same PRJ ID in scope and prompt tables?

Because the same attribute can be required by multiple portfolios. Each portfolio gets a different `scope_id`.

---

### Q2. Can we physically delete records?

Normal application flow should use soft delete. Physical deletion should only be done by controlled DBA/admin scripts when explicitly approved.

---

### Q3. Why is `prj_portfolio_reference_test` separate?

It avoids hardcoding portfolio IDs in the application and gives a controlled reference source for sector mapping.

---

### Q4. Why is `display_order` in the prompt table?

Because prompt/UI display sequence is related to how attributes appear in scanning/HITL workflows. This avoids maintaining a separate UI display configuration table.

---

### Q5. What happens when Excel has a PRJ ID not in master?

Prompt upload rejects that row and shows that the PRJ ID is not present in `prj_attribute_master_test`.

---

### Q6. How do I add a new portfolio?

Add it through the Portfolio Reference workflow/API so it receives a `port_ref_id`. Then attributes can be scoped to it.

---

### Q7. What is the safest way to extend the schema?

Add new columns through idempotent SQL scripts and update:

1. SQL script
2. SQLAlchemy entity/model
3. API schema
4. service mapping
5. repository query
6. Streamlit UI grid/form
7. audit payload where required

---

### Q8. Which tables should new developers focus on first?

Start with:

```text
prj_attribute_master_test
prj_attribute_portfolio_scope_test
prj_scanning_prompt_reference_test
```

These three explain most of the attribute-to-scope-to-prompt behaviour.

---

## 12. Maintenance Checklist

Before deploying changes:

- Confirm no legacy tables are referenced.
- Run schema validation script.
- Run performance index script if indexes are missing.
- Verify Swagger health endpoints.
- Test create/edit/delete/reactivate attribute.
- Test Master Dictionary upload with valid and invalid rows.
- Test Prompt upload for a PRJ with multiple scopes.
- Verify audit entries are written.
- Verify S3 export produces all required files.
- Restart API and Streamlit after deployment.

---

## 13. Extension Guidelines

When adding new business functionality:

1. Keep master attribute data separate from portfolio-specific data.
2. Do not duplicate attributes for each portfolio in the master table.
3. Use scope rows for portfolio applicability.
4. Keep prompt updates scope-specific.
5. Use soft delete instead of physical delete.
6. Add audit records for every write operation.
7. Prefer batch SQL for uploads.
8. Keep the UI API-driven; avoid direct database writes from Streamlit.

---

## 14. Summary

The PRJ Data Dictionary design provides a maintainable, auditable, and extensible database structure for enterprise attribute management.

The most important idea is this:

```text
One master attribute can have many portfolio scopes.
Each scope can have its own business rules and prompt configuration.
All changes are audited.
```

This design allows the application to support manual CRUD, Excel upload, prompt management, soft delete/reactivation, S3 export, and future portfolio expansion without reintroducing legacy table complexity.
