from __future__ import annotations
import os, re, tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse
import pandas as pd
from DataDictionaryAdminApp.config import get_settings
from DataDictionaryAdminApp.core.database import create_db_engine

class S3ExportService:
    """Exports a complete, relational Data Dictionary snapshot to S3.

    Every mutable table is exported with active and soft-deleted rows. Static/reference
    tables are deliberately excluded. The timestamp folder makes each export immutable.
    """
    MUTABLE_TABLES = [
        'master_dictionary','prj_attribute','prj_attr_business_logic',
        'prj_attr_business_logic_scope','prj_attribute_portfolio_scope',
        'prj_ui_display_config_test','prj_attribute_business_rules_test',
        'prj_prompt_reference','audit_log','history_log'
    ]
    # Backwards-compatible name retained for existing UI/API callers.
    TABLES = MUTABLE_TABLES
    def __init__(self): self.settings=get_settings()
    def export_four_files(self, user_id:str)->dict: return self.export_all_mutable_tables(user_id)
    def export_all_mutable_tables(self,user_id:str)->dict:
        timestamp=self._safe_timestamp(); bucket=(self.settings.effective_s3_bucket_name or '').strip()
        keys={t:self._build_object_key(t,timestamp) for t in self.MUTABLE_TABLES}
        simulated=not bucket or not self.settings.enable_db
        if simulated:
            why='Bucket name is not configured.' if not bucket else 'ENABLE_DB=false.'
            return {'status':'SIMULATED_SUCCESS','message':f'{why} Complete relational snapshot was simulated.','bucket':bucket or 'NOT_CONFIGURED','files':list(keys.values()),'exported_by':user_id,'table_count':len(keys)}
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc: raise RuntimeError('boto3 is required for S3 export. Run poetry install again.') from exc
        endpoint=self._resolve_endpoint_url()
        if not endpoint: raise RuntimeError('Internal S3 endpoint is not configured. Set HOST or S3_HOST in .env.')
        os.environ.setdefault('AWS_REQUEST_CHECKSUM_CALCULATION','when_required'); os.environ.setdefault('AWS_RESPONSE_CHECKSUM_VALIDATION','when_required')
        kwargs={'service_name':'s3','aws_access_key_id':self.settings.effective_aws_access_key_id or None,'aws_secret_access_key':self.settings.effective_aws_secret_access_key or None,'use_ssl':bool(self.settings.s3_use_ssl),'verify':bool(self.settings.s3_verify_ssl),'endpoint_url':endpoint,'config':Config(signature_version='s3v4',s3={'addressing_style':self.settings.s3_addressing_style or 'path','payload_signing_enabled':False},retries={'max_attempts':3,'mode':'standard'},connect_timeout=30,read_timeout=120)}
        if self.settings.aws_region: kwargs['region_name']=self.settings.aws_region
        s3=boto3.client(**kwargs); uploaded=[]; row_counts={}; engine=create_db_engine()
        with engine.connect() as con, tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for table in self.MUTABLE_TABLES:
                df=pd.read_sql(f'SELECT * FROM dbo.{table}',con)
                row_counts[table]=len(df); local=root/f'{table}_{timestamp}.csv'; df.to_csv(local,index=False,encoding='utf-8')
                s3.upload_file(str(local),bucket,keys[table]); uploaded.append(keys[table])
        return {'status':'SUCCESS','bucket':bucket,'endpoint_url':endpoint,'files':uploaded,'table_count':len(uploaded),'row_counts':row_counts,'exported_by':user_id,'exported_at':datetime.now(timezone.utc).isoformat()}
    def _safe_timestamp(self): return datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    def _build_object_key(self,timestamp_table,timestamp):
        prefix=self._sanitize_prefix(self.settings.s3_prefix or 'data-dictionary'); table=re.sub(r'[^A-Za-z0-9_.-]','_',timestamp_table.strip()); return f'{prefix}/{timestamp}/full_snapshot/{table}_{timestamp}.csv'
    def _sanitize_prefix(self,prefix):
        parts=[self._sanitize_key_part(x) for x in str(prefix or 'data-dictionary').strip().strip('/').replace('\\','/').split('/') if x.strip()]; return '/'.join(parts) or 'data-dictionary'
    def _sanitize_key_part(self,v): return re.sub(r'[^A-Za-z0-9_.=-]','_',re.sub(r'\s+','_',v.strip()))
    def _resolve_endpoint_url(self):
        endpoint=(self.settings.s3_endpoint_url or (self.settings.effective_s3_secure_host if self.settings.s3_use_ssl else self.settings.effective_s3_host) or '').strip().strip('"').strip("'")
        if not endpoint:return ''
        if not endpoint.startswith(('http://','https://')): endpoint=('https' if self.settings.s3_use_ssl else 'http')+'://'+endpoint
        parsed=urlparse(endpoint); scheme='https' if self.settings.s3_use_ssl else 'http'; parsed=parsed._replace(scheme=scheme)
        if self.settings.s3_port and not parsed.port: parsed=parsed._replace(netloc=f'{parsed.netloc}:{self.settings.s3_port}')
        return urlunparse(parsed).rstrip('/')
