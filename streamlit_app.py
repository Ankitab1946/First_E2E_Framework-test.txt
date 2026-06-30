"""API-only Streamlit UI for the Data Dictionary Admin App."""
from __future__ import annotations

import os
from pathlib import Path
from io import BytesIO

import pandas as pd
import requests
import streamlit as st
from streamlit_modal import Modal


def load_local_env() -> None:
    """Allow Streamlit to read .env without requiring a duplicate config module."""
    for candidate in [Path.cwd() / '.env', *[parent / '.env' for parent in Path(__file__).resolve().parents]]:
        if candidate.exists():
            for raw in candidate.read_text(encoding='utf-8').splitlines():
                line = raw.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
            return


load_local_env()
def normalize_api_base_url(value: str) -> str:
    """Normalise user configuration to the FastAPI v1 route root."""
    base = (value or 'http://localhost:8503/api/v1').strip().rstrip('/')
    if base.endswith('/docs') or base.endswith('/redoc'):
        base = base.rsplit('/', 1)[0]
    if not base.endswith('/api/v1'):
        base = f"{base}/api/v1"
    return base


API = normalize_api_base_url(os.getenv('API_BASE_URL', os.getenv('STREAMLIT_API_BASE_URL', 'http://localhost:8503/api/v1')))
ENVIRONMENTS = [x.strip().upper() for x in os.getenv('APP_ENVIRONMENTS', 'LOCAL,DEV,UAT,PROD').split(',') if x.strip()]
DEFAULT_ENV = os.getenv('SELECTED_ENVIRONMENT', os.getenv('APP_ENV', 'LOCAL')).upper()
SECTIONS = ['Income Statement', 'Balance Sheet', 'Cash Flow', 'Ratios', 'Derivatives', 'Miscellaneous', 'Other']
PORTFOLIOS = ['FI Banks', 'Corporates', 'FI Insurance', 'Zeus Downstream', 'ALL']

st.set_page_config(page_title='Data Dictionary Admin App', layout='wide')
st.title(os.getenv('APP_NAME', 'Data Dictionary Streamlit Admin'))


def _candidate_api_bases() -> list[str]:
    configured = normalize_api_base_url(os.getenv('API_BASE_URL', os.getenv('STREAMLIT_API_BASE_URL', API)))
    candidates = [configured]
    # Allow an accidental duplicate /api/v1 in a local .env without causing 404 calls.
    if configured.endswith('/api/v1/api/v1'):
        candidates.append(configured[:-7])
    return list(dict.fromkeys(candidates))


def api(method: str, path: str, *, quiet: bool = False, alternatives: list[str] | None = None, **kwargs):
    """Call the current API contract, retrying supported compatibility paths on 404 only."""
    headers = kwargs.pop('headers', {})
    headers['X-App-Environment'] = st.session_state.get('selected_environment', DEFAULT_ENV)
    paths = [path, *(alternatives or [])]
    last_response = None
    for base in _candidate_api_bases():
        for candidate_path in paths:
            try:
                response = requests.request(method, f'{base}{candidate_path}', timeout=60, headers=headers, **kwargs)
            except requests.RequestException as exc:
                last_response = exc
                continue
            if response.status_code == 404:
                last_response = response
                continue
            if response.ok:
                return response
            last_response = response
            break
    if not quiet:
        if isinstance(last_response, requests.Response):
            try:
                detail = last_response.json().get('detail', last_response.text)
            except Exception:
                detail = last_response.text
            st.error(f'API error ({last_response.status_code}): {detail}')
        elif last_response:
            st.error(f'API connection failed: {last_response}')
        else:
            st.error('API connection failed: no response from FastAPI.')
    return None


def lookup(path: str, fallback, alternatives: list[str] | None = None):
    response = api('GET', path, quiet=True, alternatives=alternatives)
    return response.json() if response else fallback


with st.sidebar:
    st.subheader('Connection')
    selected = st.selectbox('Environment', ENVIRONMENTS, index=ENVIRONMENTS.index(DEFAULT_ENV) if DEFAULT_ENV in ENVIRONMENTS else 0, key='selected_environment')
    info = api('GET', '/system/environment', quiet=True, alternatives=['/system/env', '/environment'])
    details = info.json() if info else {
        'server': os.getenv(f'ENV_{selected}_SQLSERVER_SERVER', os.getenv('SQLSERVER_SERVER', 'Not configured')),
        'database': os.getenv(f'ENV_{selected}_SQLSERVER_DATABASE', os.getenv('SQLSERVER_DATABASE', 'PRJ_DB')),
        'database_enabled': os.getenv(f'ENV_{selected}_ENABLE_DB', os.getenv('ENABLE_DB', 'false')),
    }
    st.caption(f"Server: {details.get('server') or 'Not configured'}")
    st.caption(f"Database: {details.get('database') or 'Not configured'}")
    st.caption(f"Database enabled: {details.get('database_enabled')}")
    if not info:
        st.warning('API environment endpoint is unavailable. Server details are shown from .env. Verify that FastAPI is started from this same project folder.')
    st.caption(f"API: {API}")
    user = st.text_input('Current User', value=os.getenv('USERNAME', os.getenv('DEFAULT_USER', 'sysuser')))
    if st.button('Refresh'):
        st.cache_data.clear()
        st.rerun()

sections = lookup('/lookups/sections', SECTIONS, alternatives=['/data-dictionary/sections'])
sources = lookup('/lookups/sources', [{'source_name': 'S&P CAPIQ AS REPORTED DATA', 'source_code': 'SNPAR'}], alternatives=['/data-dictionary/sources'])
source_names = [x['source_name'] for x in sources]


def attribute_payload(prefix: str) -> dict:
    return {
        'prj_id': st.session_state.get(f'{prefix}_prj_id', '').strip(),
        'prj_attribute_name': st.session_state.get(f'{prefix}_name', '').strip(),
        'prj_attribute_description': st.session_state.get(f'{prefix}_description', ''),
        'prj_physical_attribute_name': st.session_state.get(f'{prefix}_physical', ''),
        'where_in_financial_statement': st.session_state.get(f'{prefix}_section'),
        'version_update': st.session_state.get(f'{prefix}_version', ''),
        'calculated_or_reported': st.session_state.get(f'{prefix}_calculated_reported'),
        'calculation_logic': st.session_state.get(f'{prefix}_calculation_logic', ''),
        'calculation_logic_details': st.session_state.get(f'{prefix}_calculation_details', ''),
        'sign_flipping_value': st.session_state.get(f'{prefix}_sign_flipping', ''),
        'mapping_type': st.session_state.get(f'{prefix}_mapping_type', ''),
        'sp_standardisation_dataitem_id': st.session_state.get(f'{prefix}_sp_standardisation', ''),
        'sp_as_reported_dataitem_logic': st.session_state.get(f'{prefix}_sp_as_reported', ''),
        'calculated_in_cfv': st.session_state.get(f'{prefix}_cfv'),
        'editable_in_historicals': st.session_state.get(f'{prefix}_historicals'),
        'required_portfolios': st.session_state.get(f'{prefix}_portfolios', []),
        'source_name': st.session_state.get(f'{prefix}_source'),
        'editable': st.session_state.get(f'{prefix}_editable'),
        'symbol': st.session_state.get(f'{prefix}_symbol', ''),
        'business_logic': st.session_state.get(f'{prefix}_business_logic', ''),
    }


def render_attribute_form(mode: str, initial: dict | None = None):
    prefix = 'new_attribute' if mode == 'create' else 'edit_attribute'
    initial = initial or {}
    disabled = mode == 'edit-readonly'
    with st.form(f'{prefix}_form'):
        row1 = st.columns(3)
        row1[0].text_input('PRJ ID *', value=initial.get('prj_id', ''), key=f'{prefix}_prj_id', disabled=mode != 'create')
        row1[1].text_input('PRJ Attribute Name *', value=initial.get('prj_attribute_name', ''), key=f'{prefix}_name', disabled=disabled)
        row1[2].text_input('PRJ Physical Attribute Name', value=initial.get('prj_physical_attribute_name', ''), key=f'{prefix}_physical', disabled=disabled)
        st.text_area('PRJ Attribute Description', value=initial.get('prj_attribute_description', ''), key=f'{prefix}_description', disabled=disabled)
        row2 = st.columns(3)
        row2[0].selectbox('Where in financial statement', sections, index=sections.index(initial.get('where_in_financial_statement')) if initial.get('where_in_financial_statement') in sections else 0, key=f'{prefix}_section', disabled=disabled)
        row2[1].text_input('Version Update', value=initial.get('version_update', ''), key=f'{prefix}_version', disabled=disabled)
        row2[2].selectbox('Calculated or Reported?', ['', 'Calculated', 'Reported'], index=['', 'Calculated', 'Reported'].index(initial.get('calculated_or_reported')) if initial.get('calculated_or_reported') in ['', 'Calculated', 'Reported'] else 0, key=f'{prefix}_calculated_reported', disabled=disabled)
        row3 = st.columns(3)
        row3[0].selectbox('Editable?', ['', 'Y', 'N'], index=['', 'Y', 'N'].index(initial.get('editable')) if initial.get('editable') in ['', 'Y', 'N'] else 0, key=f'{prefix}_editable', disabled=disabled)
        row3[1].text_input('Percentage (%) / Ratio (X)', value=initial.get('symbol', ''), key=f'{prefix}_symbol', disabled=disabled)
        row3[2].selectbox('Source Name', source_names, index=source_names.index(initial.get('source_name')) if initial.get('source_name') in source_names else 0, key=f'{prefix}_source', disabled=disabled)
        st.multiselect('Required By', PORTFOLIOS[:-1], default=initial.get('required_portfolios', []), key=f'{prefix}_portfolios', disabled=disabled)
        row4 = st.columns(2)
        row4[0].text_area('Calculation Logic', value=initial.get('calculation_logic', ''), key=f'{prefix}_calculation_logic', disabled=disabled)
        row4[1].text_area('Calculation Logic Details', value=initial.get('calculation_logic_details', ''), key=f'{prefix}_calculation_details', disabled=disabled)
        row5 = st.columns(2)
        row5[0].text_input('Mapping Type', value=initial.get('mapping_type', ''), key=f'{prefix}_mapping_type', disabled=disabled)
        row5[1].text_input('S&P Standardisation Dataitem ID', value=initial.get('sp_standardisation_dataitem_id', ''), key=f'{prefix}_sp_standardisation', disabled=disabled)
        row6 = st.columns(2)
        row6[0].text_area('S&P As-Reported Dataitem ID / Logic', value=initial.get('sp_as_reported_dataitem_logic', ''), key=f'{prefix}_sp_as_reported', disabled=disabled)
        row6[1].text_area('Business Logic', value=initial.get('business_logic', ''), key=f'{prefix}_business_logic', disabled=disabled)
        row7 = st.columns(3)
        row7[0].selectbox('Calculated in CFV?', ['', 'Y', 'N'], key=f'{prefix}_cfv', disabled=disabled)
        row7[1].selectbox('Editable in Historicals?', ['', 'Y', 'N'], key=f'{prefix}_historicals', disabled=disabled)
        row7[2].text_input('Sign Flipping (multiply by)', value=initial.get('sign_flipping_value', ''), key=f'{prefix}_sign_flipping', disabled=disabled)
        submitted = st.form_submit_button('Create Attribute' if mode == 'create' else 'Upload Changes', disabled=disabled)
    if submitted:
        payload = attribute_payload(prefix)
        if not payload['prj_id'] or not payload['prj_attribute_name']:
            st.error('PRJ ID and PRJ Attribute Name are mandatory.')
        elif api('POST' if mode == 'create' else 'PUT', '/data-dictionary/attributes' if mode == 'create' else f"/data-dictionary/attributes/{payload['prj_id']}?user={user}", json=payload if mode == 'create' else payload):
            st.success('Attribute saved successfully.')
            st.rerun()


tab1, tab2, tab3 = st.tabs(['Data Dictionary', 'Prompt Management', 'Audit History'])
with tab1:
    st.subheader('View Latest Data Dictionary')
    f1, f2, f3, f4 = st.columns(4)
    selected_portfolios = f1.multiselect('Portfolio/Sector', PORTFOLIOS)
    filter_prj = f2.text_input('PRJ ID filter')
    filter_name = f3.text_input('Attribute Name filter')
    filter_section = f4.selectbox('Section filter', [''] + sections)
    f5, f6 = st.columns(2)
    filter_desc = f5.text_input('Attribute Description filter')
    include_deleted = f6.checkbox('View soft deleted records')
    overlapped = f6.checkbox('Overlapped Attribute only')
    filters = {'portfolios': [] if 'ALL' in selected_portfolios else selected_portfolios, 'prj_id': filter_prj or None, 'attribute_name': filter_name or None, 'attribute_description': filter_desc or None, 'section': filter_section or None, 'overlapped_only': overlapped, 'include_deleted': include_deleted}
    result = api('POST', '/data-dictionary/filter', json=filters, alternatives=['/data-dictionary/attributes/filter'])
    rows = result.json() if result else []
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    b1, b2 = st.columns(2)
    if b1.button('Add New Attribute'):
        st.session_state['attribute_modal'] = 'create'
    latest = api('GET', '/data-dictionary/download-latest', alternatives=['/data-dictionary/latest/download']) if b2.button('Generate Latest Excel') else None
    if latest:
        st.download_button('Download Latest Data', latest.content, 'data_dictionary_latest.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    modal = Modal('Create New Attribute', key='create-attribute-modal')
    if st.session_state.get('attribute_modal') == 'create':
        modal.open()
    if modal.is_open():
        with modal.container():
            render_attribute_form('create')
            if st.button('Close Create Form'):
                modal.close(); st.session_state.pop('attribute_modal', None); st.rerun()

with tab2:
    bulk, manual = st.tabs(['Bulk Upload', 'Edit/Insert Prompts'])
    with bulk:
        uploaded = st.file_uploader('Upload Prompt Excel', type=['xlsx'])
        if uploaded:
            r = api('POST', '/prompt-upload/sheets', quiet=False, files={'file': (uploaded.name, uploaded.getvalue(), uploaded.type)})
            if r:
                st.selectbox('Workbook sheet', r.json().get('sheets', []))
                st.info('Sheet discovery is available. The final bulk preview, validation, delta and commit endpoints must be executed after the Excel mapping is finalized.')
    with manual:
        with st.form('prompt-form'):
            p1,p2,p3 = st.columns(3)
            prj_id = p1.text_input('PRJ ID *')
            prompt_id = p2.number_input('Prompt ID (leave 0 for new)', min_value=0, step=1)
            scope_id = p3.number_input('Scope ID', min_value=0, step=1)
            p4,p5,p6 = st.columns(3)
            attr = p4.text_input('Attribute Name')
            section = p5.selectbox('Section', [''] + sections)
            sub_section = p6.text_input('Sub-Section')
            p7,p8,p9 = st.columns(3)
            data_type = p7.selectbox('DATA TYPE', ['', 'Amount', '%', 'Ratio', 'Actual'])
            calc_report = p8.selectbox('Calculated or Reported', ['', 'Calculated', 'Reported'])
            display = p9.number_input('Display Order', min_value=0, step=1)
            calculation_logic = st.text_area('Calculation Logic')
            segment = st.text_input('Segment')
            description = st.text_area('Description')
            examples = st.text_area('Examples')
            required_scope = st.text_input('Required By Scope')
            submitted = st.form_submit_button('Save Prompt')
        if submitted:
            payload = {'scope_id': scope_id or None, 'prj_id': prj_id, 'required_by_scope': required_scope, 'attribute_name': attr, 'section': section, 'sub_section': sub_section, 'data_type': data_type, 'calculated_or_reported': calc_report, 'calculation_logic': calculation_logic, 'segment': segment, 'attribute_description': description, 'examples': examples, 'display_order': display}
            endpoint = '/prompts' if prompt_id == 0 else f'/prompts/{prompt_id}?user={user}'
            method = 'POST' if prompt_id == 0 else 'PUT'
            if api(method, endpoint, json=payload): st.success('Prompt saved successfully.')

with tab3:
    st.subheader('Audit History')
    a1,a2,a3,a4 = st.columns(4)
    table_name = a1.text_input('Table name')
    record_key = a2.text_input('PRJ ID / Record Key')
    action = a3.selectbox('Action', ['', 'INSERT', 'UPDATE', 'SOFT_DELETE', 'REACTIVATE', 'S3_EXPORT'])
    performed_by = a4.text_input('Performed by')
    audit = api('GET', '/audit', params={'table_name': table_name or None, 'record_key': record_key or None, 'action': action or None, 'performed_by': performed_by or None})
    if audit:
        st.dataframe(pd.DataFrame(audit.json()), use_container_width=True, hide_index=True)
