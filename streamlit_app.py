"""Streamlit UI for the Data Dictionary Admin App.

The UI calls FastAPI only. Attribute create/edit uses streamlit-modal popups.
"""
from __future__ import annotations

import os
from pathlib import Path
import pandas as pd
import requests
import streamlit as st
from streamlit_modal import Modal


def load_env() -> None:
    for candidate in [Path.cwd() / '.env', *[p / '.env' for p in Path(__file__).resolve().parents]]:
        if candidate.exists():
            for raw in candidate.read_text(encoding='utf-8').splitlines():
                line = raw.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
            return


load_env()


def base_url() -> str:
    value = os.getenv('API_BASE_URL', 'http://localhost:8503/api/v1').rstrip('/')
    return value if value.endswith('/api/v1') else f'{value}/api/v1'


API = base_url()
ENVIRONMENTS = [x.strip().upper() for x in os.getenv('APP_ENVIRONMENTS', 'LOCAL,DEV,UAT,PROD').split(',') if x.strip()]
DEFAULT_ENV = os.getenv('SELECTED_ENVIRONMENT', 'LOCAL').upper()
SECTIONS = ['Income Statement', 'Balance Sheet', 'Cash Flow', 'Ratios', 'Derivatives', 'Miscellaneous', 'Other']
PORTFOLIOS = ['FI Banks', 'Corporates', 'FI Insurance', 'Zeus Downstream', 'ALL']

st.set_page_config(page_title='Data Dictionary Admin App', layout='wide')
st.title(os.getenv('APP_NAME', 'Data Dictionary Streamlit Admin'))

for key, default in {
    'latest_excel': None,
    'prompt_preview': None,
    'selected_attribute': None,
    'show_master_upload': False,
    'create_modal_open': False,
    'edit_modal_open': False,
    'edit_unlocked': False,
}.items():
    st.session_state.setdefault(key, default)


def api(method: str, path: str, quiet: bool = False, **kwargs):
    headers = kwargs.pop('headers', {})
    headers['X-App-Environment'] = st.session_state.get('env', DEFAULT_ENV)
    try:
        response = requests.request(method, f'{API}{path}', headers=headers, timeout=120, **kwargs)
    except requests.RequestException as exc:
        if not quiet:
            st.error(f'API connection failed: {exc}')
        return None
    if not response.ok:
        if not quiet:
            try:
                detail = response.json().get('detail', response.text)
            except Exception:
                detail = response.text
            st.error(f'API error ({response.status_code}): {detail}')
        return None
    return response


def jget(path: str, fallback):
    response = api('GET', path, quiet=True)
    return response.json() if response else fallback


with st.sidebar:
    st.subheader('Connection')
    st.selectbox('Environment', ENVIRONMENTS, index=ENVIRONMENTS.index(DEFAULT_ENV) if DEFAULT_ENV in ENVIRONMENTS else 0, key='env')
    environment = jget('/system/environment', {})
    db_status = jget('/system/connection-status', {'connected': False, 'message': 'FastAPI endpoint unavailable'})
    st.caption(f"Server: {environment.get('server', os.getenv('SQLSERVER_SERVER', 'Not configured'))}")
    st.caption(f"Database: {environment.get('database', os.getenv('SQLSERVER_DATABASE', 'Not configured'))}")
    if db_status.get('connected'):
        st.success(f"DB Connected: {db_status.get('server')} / {db_status.get('database')}")
    else:
        st.error(f"DB Not Connected: {db_status.get('message')}")
    user = st.text_input('Current User', value=os.getenv('USERNAME', os.getenv('DEFAULT_USER', 'sysuser')))
    if st.button('Refresh connection'):
        st.rerun()

sections = jget('/lookups/sections', SECTIONS)
sources = jget('/lookups/sources', [{'source_name': 'S&P CAPIQ AS REPORTED DATA', 'source_code': 'SNPAR'}])
source_names = [item.get('source_name', 'S&P CAPIQ AS REPORTED DATA') for item in sources]


def select_value(label, values, current=None, key=None, disabled=False):
    values = list(values)
    index = values.index(current) if current in values else 0
    return st.selectbox(label, values, index=index, key=key, disabled=disabled)


def required_portfolios_from_record(record: dict) -> list[str]:
    explicit = record.get('required_portfolios')
    if explicit:
        return explicit
    mapping = {
        'required_by_banks': 'FI Banks',
        'required_by_corporates': 'Corporates',
        'required_by_insurance': 'FI Insurance',
        'required_by_zeus_downstream': 'Zeus Downstream',
    }
    return [portfolio for field, portfolio in mapping.items() if str(record.get(field, '')).upper() in {'Y', 'YES', '1', 'TRUE'}]


def attribute_editor(initial: dict | None, read_only: bool, form_key: str) -> None:
    initial = initial or {}
    is_existing = bool(initial.get('prj_id'))
    default_required = required_portfolios_from_record(initial)

    with st.form(form_key, clear_on_submit=False):
        st.subheader('Edit Attribute' if is_existing else 'Create New Attribute')
        if is_existing and read_only:
            st.info('This attribute is read-only. Select Edit Attribute to unlock all fields except PRJ ID.')

        row1 = st.columns(3)
        prj_id = row1[0].text_input('PRJ ID *', value=str(initial.get('prj_id', '')), disabled=read_only or is_existing)
        attribute_name = row1[1].text_input('PRJ Attribute Name *', value=str(initial.get('prj_attribute_name', '')), disabled=read_only)
        physical_name = row1[2].text_input('PRJ Physical Attribute Name', value=str(initial.get('prj_physical_attribute_name') or ''), disabled=read_only)
        description = st.text_area('PRJ Attribute Description', value=str(initial.get('prj_attribute_description') or ''), disabled=read_only)

        row2 = st.columns(3)
        section = row2[0].selectbox('Where in financial statement *', sections, index=sections.index(initial.get('where_in_financial_statement')) if initial.get('where_in_financial_statement') in sections else 0, disabled=read_only)
        version = row2[1].text_input('Version Update', value=str(initial.get('version_update') or ''), disabled=read_only)
        calculated = row2[2].selectbox('Calculated or Reported?', ['', 'Calculated', 'Reported'], index=['', 'Calculated', 'Reported'].index(initial.get('calculated_or_reported')) if initial.get('calculated_or_reported') in ['', 'Calculated', 'Reported'] else 0, disabled=read_only)

        row3 = st.columns(3)
        editable = row3[0].selectbox('Editable?', ['', 'Y', 'N'], index=['', 'Y', 'N'].index(initial.get('editable')) if initial.get('editable') in ['', 'Y', 'N'] else 0, disabled=read_only)
        symbol = row3[1].text_input('Percentage (%) / Ratio (X)', value=str(initial.get('percent_ratio') or initial.get('symbol') or ''), disabled=read_only)
        source_name = row3[2].selectbox('Source Name', source_names, index=source_names.index(initial.get('source_name')) if initial.get('source_name') in source_names else 0, disabled=read_only)

        st.markdown('**Required By**')
        req_cols = st.columns(4)
        required_by_banks = req_cols[0].checkbox('Required by FI Banks', value='FI Banks' in default_required, disabled=read_only)
        required_by_corporates = req_cols[1].checkbox('Required by Corporates', value='Corporates' in default_required, disabled=read_only)
        required_by_insurance = req_cols[2].checkbox('Required by FI Insurance', value='FI Insurance' in default_required, disabled=read_only)
        required_by_zeus = req_cols[3].checkbox('Required by Zeus Downstream', value='Zeus Downstream' in default_required, disabled=read_only)

        row4 = st.columns(2)
        calculation_logic = row4[0].text_area('Calculation Logic', value=str(initial.get('calculation_logic') or ''), disabled=read_only)
        calculation_logic_details = row4[1].text_area('Calculation Logic Details', value=str(initial.get('calculation_logic_details') or ''), disabled=read_only)
        row5 = st.columns(2)
        mapping_type = row5[0].text_input('Mapping Type', value=str(initial.get('mapping_type') or ''), disabled=read_only)
        sp_standardisation = row5[1].text_input('S&P Standardisation Dataitem ID', value=str(initial.get('sp_standardisation_dataitem_id') or ''), disabled=read_only)
        row6 = st.columns(2)
        sp_as_reported = row6[0].text_area('S&P As-Reported Dataitem ID / Logic', value=str(initial.get('sp_as_reported_dataitem_logic') or ''), disabled=read_only)
        business_logic = row6[1].text_area('Business Logic', value=str(initial.get('business_logic') or ''), disabled=read_only)
        row7 = st.columns(3)
        calculated_in_cfv = row7[0].selectbox('Calculated in CFV?', ['', 'Y', 'N'], index=['', 'Y', 'N'].index(initial.get('calculated_in_cfv')) if initial.get('calculated_in_cfv') in ['', 'Y', 'N'] else 0, disabled=read_only)
        editable_in_historicals = row7[1].selectbox('Editable in Historicals?', ['', 'Y', 'N'], index=['', 'Y', 'N'].index(initial.get('editable_in_historicals')) if initial.get('editable_in_historicals') in ['', 'Y', 'N'] else 0, disabled=read_only)
        sign_flipping = row7[2].text_input('Sign Flipping (multiply by)', value=str(initial.get('sign_flipping_value') or ''), disabled=read_only)

        if read_only:
            submit = False
        else:
            submit = st.form_submit_button('Upload Changes' if is_existing else 'Create Attribute', type='primary')

    if submit:
        required = []
        if required_by_banks:
            required.append('FI Banks')
        if required_by_corporates:
            required.append('Corporates')
        if required_by_insurance:
            required.append('FI Insurance')
        if required_by_zeus:
            required.append('Zeus Downstream')
        payload = {
            'prj_id': prj_id or initial.get('prj_id', ''),
            'prj_attribute_name': attribute_name,
            'prj_attribute_description': description,
            'prj_physical_attribute_name': physical_name,
            'where_in_financial_statement': section,
            'version_update': version,
            'calculated_or_reported': calculated,
            'calculation_logic': calculation_logic,
            'calculation_logic_details': calculation_logic_details,
            'sign_flipping_value': sign_flipping,
            'mapping_type': mapping_type,
            'sp_standardisation_dataitem_id': sp_standardisation,
            'sp_as_reported_dataitem_logic': sp_as_reported,
            'calculated_in_cfv': calculated_in_cfv,
            'editable_in_historicals': editable_in_historicals,
            'required_portfolios': required,
            'source_name': source_name,
            'editable': editable,
            'symbol': symbol,
            'business_logic': business_logic,
        }
        if not payload['prj_id'] or not payload['prj_attribute_name']:
            st.error('PRJ ID and PRJ Attribute Name are mandatory.')
            return
        endpoint = '/data-dictionary/attributes' if not is_existing else f"/data-dictionary/attributes/{payload['prj_id']}?user={user}"
        response = api('POST' if not is_existing else 'PUT', endpoint, json=payload)
        if response:
            st.success('Attribute saved successfully.')
            st.session_state['create_modal_open'] = False
            st.session_state['edit_modal_open'] = False
            st.session_state['edit_unlocked'] = False
            st.rerun()


create_modal = Modal('Create New Attribute', key='create_attribute_modal', max_width=1200)
edit_modal = Modal('Edit Attribute', key='edit_attribute_modal', max_width=1200)

tab1, tab2, tab3 = st.tabs(['Data Dictionary', 'Prompt Management', 'Audit History'])

with tab1:
    st.subheader('View Latest Data Dictionary')
    filter_cols = st.columns(4)
    selected_portfolios = filter_cols[0].multiselect('Portfolio/Sector', PORTFOLIOS)
    prj_filter = filter_cols[1].text_input('PRJ ID filter')
    name_filter = filter_cols[2].text_input('Attribute Name filter')
    section_filter = filter_cols[3].selectbox('Section filter', [''] + sections)
    filter_cols2 = st.columns(2)
    desc_filter = filter_cols2[0].text_input('Attribute Description filter')
    include_deleted = filter_cols2[1].checkbox('View soft deleted records')
    overlap = filter_cols2[1].checkbox('Overlapped Attribute only')
    filters = {
        'portfolios': [] if 'ALL' in selected_portfolios else selected_portfolios,
        'prj_id': prj_filter or None,
        'attribute_name': name_filter or None,
        'attribute_description': desc_filter or None,
        'section': section_filter or None,
        'include_deleted': include_deleted,
        'overlapped_only': overlap,
    }
    response = api('POST', '/data-dictionary/filter', json=filters)
    rows = response.json() if response else []
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    actions = st.columns(4)
    if actions[0].button('Add New Attribute', use_container_width=True):
        st.session_state['create_modal_open'] = True
        create_modal.open()
    if actions[1].button('Generate Latest Excel', use_container_width=True):
        response = api('GET', '/data-dictionary/download-latest')
        if response:
            st.session_state['latest_excel'] = response.content
    if st.session_state['latest_excel']:
        actions[1].download_button('Download Latest Data', st.session_state['latest_excel'], 'data_dictionary_latest.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)
    selected = actions[2].selectbox('Selected PRJ ID', [''] + [str(row.get('prj_id', '')) for row in rows], key='selected_prj')
    if actions[3].button('Open / Edit Selected Attribute', disabled=not selected, use_container_width=True):
        response = api('GET', f'/data-dictionary/attributes/{selected}')
        if response:
            st.session_state['selected_attribute'] = response.json()
            st.session_state['edit_unlocked'] = False
            st.session_state['edit_modal_open'] = True
            edit_modal.open()

    actions2 = st.columns(3)
    if actions2[0].button('Upload Data Dictionary', use_container_width=True):
        st.session_state['show_master_upload'] = not st.session_state['show_master_upload']
    if actions2[1].button('Soft Delete Attribute', disabled=not selected, use_container_width=True):
        if api('DELETE', f'/data-dictionary/attributes/{selected}?user={user}'):
            st.success('Attribute soft deleted.')
            st.rerun()
    if actions2[2].button('Export to S3', use_container_width=True):
        if api('POST', f'/s3/export?user={user}'):
            st.success('S3 export completed.')

    if st.session_state['show_master_upload']:
        st.markdown('### Upload Master Dictionary')
        master = st.file_uploader('Master Dictionary Excel (.xlsx)', type=['xlsx'], key='master_dictionary_upload')
        if master:
            files = {'file': (master.name, master.getvalue(), master.type or 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            preview = api('POST', '/master-upload/preview', files=files)
            if preview:
                st.dataframe(pd.DataFrame(preview.json().get('preview', [])), use_container_width=True, hide_index=True)
            up_cols = st.columns(2)
            if up_cols[0].button('Compare Master Dictionary'):
                delta = api('POST', '/master-upload/delta', files=files)
                if delta:
                    st.info(str(delta.json()))
            if up_cols[1].button('Finalize Master Upload'):
                finalized = api('POST', f'/master-upload/finalize?user={user}', files=files)
                if finalized:
                    st.success(str(finalized.json()))

# Modal rendering must occur after buttons set session state.
if st.session_state.get('create_modal_open'):
    create_modal.open()
if create_modal.is_open():
    with create_modal.container():
        attribute_editor(None, False, 'create_attribute_form')
        if st.button('Close', key='close_create_modal'):
            st.session_state['create_modal_open'] = False
            create_modal.close()
            st.rerun()

if st.session_state.get('edit_modal_open'):
    edit_modal.open()
if edit_modal.is_open():
    with edit_modal.container():
        if not st.session_state.get('edit_unlocked'):
            attribute_editor(st.session_state.get('selected_attribute'), True, 'view_attribute_form')
            if st.button('Edit Attribute', key='unlock_edit_attribute', type='primary'):
                st.session_state['edit_unlocked'] = True
                st.rerun()
        else:
            attribute_editor(st.session_state.get('selected_attribute'), False, 'edit_attribute_form')
        if st.button('Close', key='close_edit_modal'):
            st.session_state['edit_modal_open'] = False
            st.session_state['edit_unlocked'] = False
            edit_modal.close()
            st.rerun()

with tab2:
    bulk, manual = st.tabs(['Bulk Upload', 'Edit/Insert Prompts'])
    with bulk:
        uploaded = st.file_uploader('Upload Prompt Excel', type=['xlsx'], key='prompt_upload_file')
        if uploaded:
            files = {'file': (uploaded.name, uploaded.getvalue(), uploaded.type or 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            sheets_response = api('POST', '/prompt-upload/sheets', files=files)
            sheets = sheets_response.json().get('sheets', []) if sheets_response else []
            sheet = st.selectbox('Workbook sheet', sheets, key='prompt_sheet') if sheets else None
            if sheet and st.button('Load Selected Data', key='load_prompt_sheet'):
                preview = api('POST', '/prompt-upload/preview', files=files, data={'sheet_name': sheet})
                if preview:
                    st.session_state['prompt_preview'] = preview.json()
            if st.session_state.get('prompt_preview'):
                st.caption(f"Detected mapping: {st.session_state['prompt_preview'].get('column_mapping', {})}")
                st.dataframe(pd.DataFrame(st.session_state['prompt_preview'].get('preview', [])), use_container_width=True, hide_index=True)
            bulk_actions = st.columns(3)
            if sheet and bulk_actions[0].button('Validate and Compare Delta'):
                result = api('POST', '/prompt-upload/delta', files=files, data={'sheet_name': sheet})
                if result:
                    st.session_state['prompt_delta'] = result.json()
                    st.info(str(result.json()))
            if sheet and bulk_actions[1].button('Generate SQL Script'):
                result = api('POST', '/prompt-upload/generate-sql?mode=MERGE', files=files, data={'sheet_name': sheet})
                if result:
                    st.download_button('Download MERGE SQL', result.content, 'prompt_merge.sql', mime='text/sql')
            if sheet and bulk_actions[2].button('Commit Valid Rows'):
                result = api('POST', f'/prompt-upload/finalize?user={user}', files=files, data={'sheet_name': sheet})
                if result:
                    st.success(str(result.json()))
    with manual:
        st.info('Prompt CRUD is available through Swagger route /api/v1/prompts. The bulk flow derives scope and portfolio automatically.')

with tab3:
    audit = api('GET', '/audit')
    if audit:
        st.dataframe(pd.DataFrame(audit.json()), use_container_width=True, hide_index=True)
