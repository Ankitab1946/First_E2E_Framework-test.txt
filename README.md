# Data Dictionary Streamlit Admin - Enhanced Version

This is the enhanced Python-only Streamlit version of the Data Dictionary Admin App.

## Major Enhancements

1. Three-tab UI only:
   - Data Dictionary
   - Audit History
   - Prompts Library
2. Portfolio/Sector filter:
   - FI Banks
   - Corporates
   - FI Insurance
   - Zeus Downstream
   - ALL
3. Role-based access:
   - Admin users can create/edit/upload/soft delete/export to S3.
   - Viewer users can view/search data only.
4. Environment selector in the side panel:
   - LOCAL / DEV / UAT / PROD or any values configured in `.env`.
   - Selected environment controls SQL Server and DB details.
5. Create New Attribute flow.
6. Edit Attribute flow with read-only mode first, then editable mode after clicking Edit.
7. Audit History search by:
   - PRJ_ID
   - Attribute Name
   - Section
   - Portfolio/Sector
   - Full history
8. Prompts Library tab reads from `dbo.prompt_library` in read-only mode.
9. S3 export button exports four CSV files:
   - master_dictionary
   - prj_attribute
   - prj_attr_business_logic
   - prj_attr_business_logic_scope
10. Audit and generic history logging for insert/update/soft delete.

## Important Streamlit Note

Pure Streamlit does not provide a native double-click row event for `st.dataframe` without adding a custom grid component. Therefore, this version provides an equivalent business workflow:

1. Select a PRJ_ID from the dropdown.
2. The Edit Attribute page appears in read-only mode.
3. Click Edit to make fields editable.
4. Click Upload to save changes.

This keeps the solution Python-only and avoids custom JavaScript dependencies.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
streamlit run streamlit_app.py
```

Open:

```text
http://localhost:8501
```

## Database Setup

Create the database manually:

```sql
CREATE DATABASE PRJ_DB;
```

Then run:

```sql
USE PRJ_DB;
```

Execute:

```text
sql/01_schema.sql
sql/02_seed.sql
```

The schema script does not create the database. It creates tables only when they do not already exist.

## Environment Configuration

Example `.env`:

```env
APP_ENVIRONMENTS=LOCAL,DEV,UAT,PROD
SELECTED_ENVIRONMENT=LOCAL

ENV_LOCAL_SQLSERVER_SERVER=localhost\SQLEXPRESS
ENV_LOCAL_SQLSERVER_DATABASE=PRJ_DB
ENV_LOCAL_SQLSERVER_WINDOWS_AUTH=true
ENV_LOCAL_ENABLE_DB=false

ENV_DEV_SQLSERVER_SERVER=DEV_SQL_SERVER_NAME
ENV_DEV_SQLSERVER_DATABASE=PRJ_DB
ENV_DEV_SQLSERVER_WINDOWS_AUTH=true
ENV_DEV_ENABLE_DB=true
```

When the user selects an environment in the side panel, the app applies the matching `ENV_<ENV>_*` database settings.

## Role-Based Access

Configure admin users in `.env`:

```env
ADMIN_USERS=sysuser,AMOLJ,DOMAIN\AMOLJ
```

Only Admin users can access:

- Add New Attribute
- Edit Attribute
- Soft Delete
- Upload Document
- Save Extracts to S3

## S3 Export Configuration

```env
S3_BUCKET_NAME=your-s3-bucket-name
S3_PREFIX=data-dictionary
AWS_REGION=ap-south-1
```

The app uploads four timestamped CSV files under:

```text
s3://<bucket>/<prefix>/<timestamp>/
```

AWS credentials should be supplied using the standard AWS credential chain, such as environment variables, IAM role, or AWS profile.

## Run Tests

```bash
pytest
```

If Allure is not installed in your local Python environment, run:

```bash
pytest -o addopts=''
```

After installing all requirements, Allure output is generated under `allure-results`.

## Modal popup implementation

This enhanced version uses the `streamlit-modal` package for popup-style Create/Edit Attribute forms.

- `Add New Attribute` opens the **Create New Attribute** modal.
- `View / Edit` opens the **Edit Attribute** modal in read-only mode.
- Inside the edit modal, click **Edit** to make fields editable except `PRJ ID`.

Role-based access is controlled through `ADMIN_USERS` in `.env`. The default `.env.example` uses `ADMIN_USERS=*,sysuser` so local/dev users can immediately see admin actions. Replace `*` with real Windows usernames for controlled environments.

## S3-Compatible Export Configuration

The **Save Extracts to S3** button exports the latest active records from these four tables as timestamped CSV files:

- `master_dictionary`
- `prj_attribute`
- `prj_attr_business_logic`
- `prj_attr_business_logic_scope`

For internal S3-compatible storage, configure `.env` like this:

```env
S3_BUCKET_NAME=your_bucket_name
S3_PREFIX=data-dictionary
AWS_REGION=ap-south-1

S3_SECURE=true
S3_HOST=http://your-host:port
S3_SECURE_HOST=https://your-secure-host:port
S3_PORT=
S3_ENDPOINT_URL=

S3_USE_SSL=false
S3_VERIFY_SSL=false
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_key
```

If `S3_ENDPOINT_URL` is provided, the app uses it directly. Otherwise it uses `S3_SECURE_HOST` when `S3_SECURE=true`, else `S3_HOST`. This supports boto3-compatible clients using `endpoint_url`, `use_ssl`, and `verify`.

## Reactivating Soft Deleted Records

On the **Data Dictionary** tab, use **View Soft Deleted Records** to display inactive records. Select a PRJ ID and click **Make Active** to reactivate the record in:

- `master_dictionary`
- `prj_attribute`
- `prj_attr_business_logic`
- `prj_attr_business_logic_scope`

The operation writes audit and history entries with action type `REACTIVATE`.
