"""Streamlit UI for the Data Dictionary Admin App. UI calls FastAPI only."""
from __future__ import annotations
import os
import json
from pathlib import Path
import pandas as pd
import requests
import streamlit as st
from streamlit_modal import Modal


def load_env():
    for path in [Path.cwd()/'.env', *[p/'.env' for p in Path(__file__).resolve().parents]]:
        if path.exists():
            for raw in path.read_text(encoding='utf-8').splitlines():
                raw=raw.strip()
                if raw and not raw.startswith('#') and '=' in raw:
                    k,v=raw.split('=',1); os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))
            break
load_env()

API_BASE=os.getenv('API_BASE_URL','http://localhost:8503/api/v1').rstrip('/')
API=API_BASE if API_BASE.endswith('/api/v1') else API_BASE+'/api/v1'
SECTIONS=['Income Statement','Balance Sheet','Cash Flow','Ratios','Derivatives','Miscellaneous','Other']
PORTFOLIOS=['FI Banks','Corporates','FI Insurance','Zeus Downstream','ALL']
HTTP = requests.Session()
HTTP.headers.update({'Accept': 'application/json'})

st.set_page_config(
    page_title='Data Dictionary Admin App',
    page_icon='📚',
    layout='wide',
    initial_sidebar_state='expanded',
)

# Simple light UI styling. Functional controls and API flows are unchanged.
st.markdown("""
<style>
:root { --dd-primary:#2F5597; --dd-primary-dark:#203864; --dd-border:#B7C9DD; --dd-bg:#F7FAFC; --dd-text:#1F2937; --dd-muted:#52606D; }
.stApp { background:var(--dd-bg); color:var(--dd-text); }
[data-testid="stHeader"] { background:#FFFFFF; border-bottom:1px solid #D9E2EC; }
.block-container { padding-top:1rem; padding-bottom:2rem; max-width:1600px; }
.dd-hero { background:#EAF2FB; border:1px solid #B7C9DD; border-radius:8px; color:#203864; padding:1rem 1.15rem; margin:0 0 1rem 0; }
.dd-hero h1 { font-size:1.45rem; margin:0; font-weight:700; color:#203864; }
.dd-hero p { margin:.25rem 0 0; font-size:.9rem; color:#52606D; }
.dd-section-label { font-size:.76rem; text-transform:uppercase; letter-spacing:.07em; color:#2F5597; font-weight:700; margin-bottom:.3rem; }
.dd-grid-title { color:#203864; font-size:1.05rem; font-weight:700; margin:.15rem 0 .55rem; }
[data-testid="stSidebar"] { background:#F4F7FB; border-right:1px solid #CBD5E1; }
[data-testid="stSidebar"] * { color:#1F2937; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color:#52606D !important; }
[data-testid="stSidebar"] [data-baseweb="select"] > div, [data-testid="stSidebar"] input { background:#FFFFFF !important; color:#1F2937 !important; border-color:#B7C9DD !important; }
.stTabs [data-baseweb="tab-list"] { gap:.25rem; border-bottom:1px solid #C9D6E4; }
.stTabs [data-baseweb="tab"] { height:40px; padding:0 .95rem; color:#52606D; font-weight:650; }
.stTabs [aria-selected="true"] { color:#203864 !important; border-bottom:3px solid #2F5597 !important; }
.stButton > button, .stDownloadButton > button { border-radius:6px; min-height:2.35rem; font-weight:650; border-color:#9FB6CF; color:#203864; background:#FFFFFF; }
.stButton > button[kind="primary"] { background:#2F5597; border-color:#2F5597; color:#FFFFFF; }
.stButton > button:hover, .stDownloadButton > button:hover { border-color:#2F5597 !important; background:#EEF5FC !important; }
[data-testid="stExpander"] { background:#FFFFFF; border:1px solid #C9D6E4; border-radius:6px; }
[data-testid="stDataFrame"] { border:1px solid #9FB6CF; border-radius:4px; overflow:hidden; background:#FFFFFF; }
[data-testid="stDataFrame"] [role="columnheader"] { background:#2F5597 !important; color:#FFFFFF !important; font-weight:700 !important; }
[data-testid="stDataFrame"] [role="gridcell"] { color:#1F2937 !important; background:#FFFFFF !important; border-bottom:1px solid #E5EDF5 !important; }
.dd-grid-header { background:#2F5597; padding:.48rem .5rem; border:1px solid #24457B; }
.dd-grid-header p { color:#FFFFFF !important; font-weight:700; font-size:.78rem; margin:0; }
.dd-grid-row { background:#FFFFFF; padding:.35rem .45rem; border:1px solid #D6E0EB; min-height:34px; }
.dd-grid-row p { color:#1F2937 !important; font-size:.82rem; margin:0; overflow-wrap:anywhere; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color:#D6E0EB !important; border-radius:4px !important; background:#FFFFFF; }
.stAlert, [data-testid="stToast"] { border-radius:6px !important; }
</style>
""", unsafe_allow_html=True)
st.markdown(f"""
<div class="dd-hero">
  <h1>{os.getenv('APP_NAME','Data Dictionary Streamlit Admin')}</h1>
  <p>Master Dictionary, prompt lifecycle, audit controls, and governed data operations.</p>
</div>
""", unsafe_allow_html=True)

for key,value in {'latest_excel':None,'rows':[],'selected_attribute':None,'prompt_preview':None,'prompt_delta':None,'show_master_upload':False,'active_prompt':None,'app_role':'Admin','open_create_attribute_modal':False,'create_modal_generation':0}.items():
    st.session_state.setdefault(key,value)

@st.cache_data(ttl=30, show_spinner=False)
def cached_get_json(path: str, env: str, role: str):
    """Cache read-only API requests to reduce grid refresh churn."""
    headers = {'X-App-Environment': env, 'X-App-Role': role}
    try:
        response = HTTP.get(API + path, headers=headers, timeout=45)
        if not response.ok:
            return {'__api_error__': response.text, '__status__': response.status_code}
        return response.json()
    except requests.RequestException as exc:
        return {'__api_error__': str(exc), '__status__': 0}

@st.cache_data(ttl=15, show_spinner=False)
def cached_filter_json(payload_json: str, env: str, role: str):
    headers = {'X-App-Environment': env, 'X-App-Role': role}
    try:
        response = HTTP.post(API + '/data-dictionary/filter', headers=headers, json=json.loads(payload_json), timeout=60)
        if not response.ok:
            return {'__api_error__': response.text, '__status__': response.status_code}
        return response.json()
    except requests.RequestException as exc:
        return {'__api_error__': str(exc), '__status__': 0}

def clear_read_cache():
    cached_get_json.clear()
    cached_filter_json.clear()

def api(method,path,quiet=False,activity=None,**kwargs):
    headers=kwargs.pop('headers',{})
    headers['X-App-Environment']=st.session_state.get('env',os.getenv('SELECTED_ENVIRONMENT','LOCAL'))
    headers['X-App-Role']=st.session_state.get('app_role','Admin')
    try:
        if activity:
            with st.spinner(activity):
                response=HTTP.request(method,API+path,headers=headers,timeout=180,**kwargs)
        else:
            response=HTTP.request(method,API+path,headers=headers,timeout=180,**kwargs)
    except requests.RequestException as exc:
        if not quiet: st.error(f'API connection failed: {exc}')
        return None
    if not response.ok:
        if not quiet:
            try:
                payload = response.json()
                detail = payload.get('detail', payload)
                if isinstance(detail, (dict, list)):
                    st.error(f'API error ({response.status_code}). Detailed failure response:')
                    st.json(detail)
                else:
                    st.error(f'API error ({response.status_code}): {detail}')
            except Exception:
                st.error(f'API error ({response.status_code}): {response.text}')
        return None
    if method.upper() != 'GET':
        clear_read_cache()
        if activity:
            st.toast(f'{activity} completed.', icon='✅')
    return response

def json_get(path,fallback):
    payload = cached_get_json(path, st.session_state.get('env', os.getenv('SELECTED_ENVIRONMENT','LOCAL')), st.session_state.get('app_role','Admin'))
    return fallback if isinstance(payload, dict) and payload.get('__api_error__') else payload

def flag(value): return str(value or '').strip().upper() in {'Y','YES','1','TRUE'}

def render_row_radio_grid(rows, *, key: str, title: str, id_field: str, label_builder):
    """Render a table-aligned single-select control.

    Streamlit cannot place an interactive native ``st.radio`` inside a
    ``st.dataframe`` cell. This renderer therefore builds the table row-by-row:
    the first column contains a radio-styled native control and every following
    cell is rendered in the same row. State callbacks make the controls mutually
    exclusive, so only one record can be selected at a time.
    """
    if not rows:
        st.info('No records found.')
        return ''

    selectable = [row for row in rows if row.get(id_field) not in (None, '')]
    if not selectable:
        st.info('No selectable records found.')
        return ''

    # Keep the grid compact and readable while preserving the important columns.
    if id_field == 'prompt_id':
        preferred = ['prompt_id', 'prj_id', 'attribute_name', 'section', 'sub_section', 'display_order']
    else:
        preferred = [
            'prj_id', 'prj_attribute_name', 'prj_attribute_description',
            'source', 'where_in_financial_statement', 'editable', 'percent_ratio',
            'required_by_fi_banks', 'required_by_corporates',
            'required_by_fi_insurance', 'required_by_zeus_downstream'
        ]
    display_columns = [col for col in preferred if any(col in row for row in selectable)]
    if not display_columns:
        display_columns = [col for col in selectable[0].keys() if col != 'Select'][:5]

    # Render a small scoped CSS rule for each row selector, making the checkbox
    # visually circular while retaining native Streamlit click behaviour.
    css_rules = []
    state_keys = []
    for index, _row in enumerate(selectable):
        state_key = f'{key}__row_{index}'
        state_keys.append(state_key)
        css_rules.append(
            f".st-key-{state_key} [data-testid=\"stCheckbox\"] label > div:first-child "
            "{border-radius:50% !important;}"
        )
    st.markdown('<style>' + ''.join(css_rules) + '</style>', unsafe_allow_html=True)

    selected_state_key = f'{key}__selected'

    def choose_row(changed_key: str):
        if st.session_state.get(changed_key):
            for other_key in state_keys:
                if other_key != changed_key:
                    st.session_state[other_key] = False
            st.session_state[selected_state_key] = changed_key
        elif st.session_state.get(selected_state_key) == changed_key:
            st.session_state[selected_state_key] = None

    # Header row in a visible grid treatment.
    widths = [0.65] + [1.75 if col in {'prj_attribute_description', 'attribute_name'} else 1.15 for col in display_columns]
    header = st.columns(widths, gap='small')
    header[0].markdown('<div class="dd-grid-header"><p>Select</p></div>', unsafe_allow_html=True)
    for col, cell in zip(display_columns, header[1:]):
        cell.markdown(f'<div class="dd-grid-header"><p>{ {'required_by_fi_banks':'Required FI Banks', 'required_by_corporates':'Required Corporates', 'required_by_fi_insurance':'Required FI Insurance', 'required_by_zeus_downstream':'Required Zeus Downstream', 'where_in_financial_statement':'Section', 'prj_attribute_name':'Attribute Name', 'prj_attribute_description':'Attribute Description', 'percent_ratio':'Percent / Ratio'}.get(col, col.replace("_", " ").title())}</p></div>', unsafe_allow_html=True)

    selected_value = ''
    for index, row in enumerate(selectable):
        state_key = state_keys[index]
        if state_key not in st.session_state:
            st.session_state[state_key] = False
        with st.container(border=True):
            row_cells = st.columns(widths, gap='small')
            with row_cells[0]:
                st.checkbox(
                    '',
                    key=state_key,
                    label_visibility='collapsed',
                    on_change=choose_row,
                    args=(state_key,),
                )
            for col, cell in zip(display_columns, row_cells[1:]):
                value = row.get(col, '')
                if value is None:
                    value = ''
                cell.markdown(f'<div class="dd-grid-row"><p>{str(value)}</p></div>', unsafe_allow_html=True)
        if st.session_state.get(state_key):
            selected_value = str(row.get(id_field, ''))

    st.caption('Select exactly one record. Selecting another row automatically clears the earlier selection.')
    return selected_value


def keep_one_active_attribute_selection():
    """Retain only the most recently selected grid checkbox."""
    state = st.session_state.get('active_attribute_grid')
    if not isinstance(state, dict):
        return
    edited = state.get('edited_rows', {})
    selected = [idx for idx, values in edited.items() if values.get('Select') is True]
    if len(selected) <= 1:
        return
    keep = selected[-1]
    for idx in selected:
        if idx != keep:
            edited.setdefault(idx, {})['Select'] = False


def payload_for_attribute(existing=None):
    """Render attribute inputs without st.form to avoid modal submit lifecycle errors."""
    existing = existing or {}
    is_edit = bool(existing)
    readonly = is_edit and not st.session_state.get('edit_unlocked', False)
    prefix = 'edit_attr' if is_edit else 'create_attr'
    st.subheader('Edit Attribute' if is_edit else 'Create New Attribute')
    if readonly:
        st.info('Read-only mode. Click Edit Attribute to unlock fields. PRJ ID remains read-only.')
    c = st.columns(3)
    prj_id = c[0].text_input('PRJ ID *', value=str(existing.get('prj_id', '')), disabled=readonly or is_edit, key=f'{prefix}_prj_id')
    name = c[1].text_input('PRJ Attribute Name *', value=str(existing.get('prj_attribute_name', '')), disabled=readonly, key=f'{prefix}_name')
    physical = c[2].text_input('PRJ Physical Attribute Name', value=str(existing.get('prj_physical_attribute_name') or ''), disabled=readonly, key=f'{prefix}_physical')
    description = st.text_area('PRJ Attribute Description', value=str(existing.get('prj_attribute_description') or ''), disabled=readonly, key=f'{prefix}_description')
    c = st.columns(3)
    section = c[0].selectbox('Where in financial statement *', SECTIONS, index=SECTIONS.index(existing.get('where_in_financial_statement')) if existing.get('where_in_financial_statement') in SECTIONS else 0, disabled=readonly, key=f'{prefix}_section')
    version = c[1].text_input('Version Update', value=str(existing.get('version_update') or ''), disabled=readonly, key=f'{prefix}_version')
    calculated = c[2].selectbox('Calculated or Reported?', ['', 'Calculated', 'Reported'], index=['', 'Calculated', 'Reported'].index(existing.get('calculated_or_reported')) if existing.get('calculated_or_reported') in ['', 'Calculated', 'Reported'] else 0, disabled=readonly, key=f'{prefix}_calculated')
    c = st.columns(3)
    editable = c[0].selectbox('Editable?', ['', 'Y', 'N'], index=['', 'Y', 'N'].index(existing.get('editable')) if existing.get('editable') in ['', 'Y', 'N'] else 0, disabled=readonly, key=f'{prefix}_editable')
    symbol = c[1].text_input('Percentage (%) / Ratio (X)', value=str(existing.get('percent_ratio') or existing.get('symbol') or ''), disabled=readonly, key=f'{prefix}_symbol')
    source_options = [x.get('source_name') for x in json_get('/lookups/sources', [{'source_name':'S&P CAPIQ AS REPORTED DATA'}])]
    source = c[2].selectbox('Source Name', source_options, index=source_options.index(existing.get('source_name')) if existing.get('source_name') in source_options else 0, disabled=readonly, key=f'{prefix}_source')
    st.markdown('**Required By**')
    c = st.columns(4)
    banks = c[0].checkbox('Required by FI Banks', value=flag(existing.get('required_by_banks') or existing.get('required_by_fi_banks')) or 'FI Banks' in existing.get('required_portfolios', []), disabled=readonly, key=f'{prefix}_banks')
    corporates = c[1].checkbox('Required by Corporates', value=flag(existing.get('required_by_corporates')) or 'Corporates' in existing.get('required_portfolios', []), disabled=readonly, key=f'{prefix}_corporates')
    insurance = c[2].checkbox('Required by FI Insurance', value=flag(existing.get('required_by_insurance') or existing.get('required_by_fi_insurance')) or 'FI Insurance' in existing.get('required_portfolios', []), disabled=readonly, key=f'{prefix}_insurance')
    zeus = c[3].checkbox('Required by Zeus Downstream', value=flag(existing.get('required_by_zeus_downstream')) or 'Zeus Downstream' in existing.get('required_portfolios', []), disabled=readonly, key=f'{prefix}_zeus')
    c = st.columns(2)
    calc_logic = c[0].text_area('Calculation Logic', value=str(existing.get('calculation_logic') or ''), disabled=readonly, key=f'{prefix}_calc_logic')
    calc_details = c[1].text_area('Calculation Logic Details', value=str(existing.get('calculation_logic_details') or ''), disabled=readonly, key=f'{prefix}_calc_details')
    c = st.columns(2)
    mapping_type = c[0].text_input('Mapping Type', value=str(existing.get('mapping_type') or ''), disabled=readonly, key=f'{prefix}_mapping_type')
    business_logic = c[1].text_area('Business Logic', value=str(existing.get('business_logic') or ''), disabled=readonly, key=f'{prefix}_business_logic')
    c = st.columns(3)
    cfv = c[0].selectbox('Calculated in CFV?', ['', 'Y', 'N'], index=['', 'Y', 'N'].index(existing.get('calculated_in_cfv')) if existing.get('calculated_in_cfv') in ['', 'Y', 'N'] else 0, disabled=readonly, key=f'{prefix}_cfv')
    historical = c[1].selectbox('Editable in Historicals?', ['', 'Y', 'N'], index=['', 'Y', 'N'].index(existing.get('editable_in_historicals')) if existing.get('editable_in_historicals') in ['', 'Y', 'N'] else 0, disabled=readonly, key=f'{prefix}_historical')
    sign = c[2].text_input('Sign Flipping (multiply by)', value=str(existing.get('sign_flipping_value') or ''), disabled=readonly, key=f'{prefix}_sign')
    save = st.button('Upload Changes' if is_edit else 'Create Attribute', type='primary', disabled=readonly, key=f'{prefix}_save')
    if not save:
        return False
    scopes = []
    if banks: scopes.append('FI Banks')
    if corporates: scopes.append('Corporates')
    if insurance: scopes.append('FI Insurance')
    if zeus: scopes.append('Zeus Downstream')
    if not prj_id or not name:
        st.error('PRJ ID and PRJ Attribute Name are mandatory.')
        return False
    p = {'prj_id':prj_id or existing.get('prj_id'),'prj_attribute_name':name,'prj_attribute_description':description,'prj_physical_attribute_name':physical,'where_in_financial_statement':section,'version_update':version,'calculated_or_reported':calculated,'calculation_logic':calc_logic,'calculation_logic_details':calc_details,'sign_flipping_value':sign,'mapping_type':mapping_type,'calculated_in_cfv':cfv,'editable_in_historicals':historical,'required_portfolios':scopes,'source_name':source,'editable':editable,'symbol':symbol,'business_logic':business_logic}
    endpoint = f"/data-dictionary/attributes/{p['prj_id']}?user={st.session_state.get('current_user','sysuser')}" if is_edit else f"/data-dictionary/attributes?user={st.session_state.get('current_user','sysuser')}"
    r = api('PUT' if is_edit else 'POST', endpoint, json=p, activity='Updating attribute' if is_edit else 'Creating attribute')
    if r:
        st.success('Attribute saved successfully.')
        return True
    return False

create_modal=Modal('Create New Attribute',key='create_attribute_modal',max_width=1200)
edit_modal=Modal('Edit Attribute',key='edit_attribute_modal',max_width=1200)

with st.sidebar:
    st.markdown('### Workspace')
    st.caption('Connection, environment, access and user context')
    st.divider()
    st.markdown('**Connection**')
    envs=[x.strip().upper() for x in os.getenv('APP_ENVIRONMENTS','LOCAL,DEV,UAT,PROD').split(',') if x.strip()]
    default=os.getenv('SELECTED_ENVIRONMENT','LOCAL').upper()
    st.selectbox('Environment',envs,index=envs.index(default) if default in envs else 0,key='env')
    env=json_get('/system/environment',{})
    status=json_get('/system/connection-status',{'connected':False,'message':'FastAPI endpoint unavailable'})
    st.caption('Server: '+str(env.get('server',os.getenv('SQLSERVER_SERVER','Not configured'))))
    st.caption('Database: '+str(env.get('database',os.getenv('SQLSERVER_DATABASE','Not configured'))))
    (st.success if status.get('connected') else st.error)('Database connected' if status.get('connected') else 'Database not connected: '+str(status.get('message','Unknown error')))
    st.selectbox('Role', ['Admin','User'], key='app_role', help='Admin can upload/compare the Master Dictionary and export to S3. User can see these controls but cannot execute them.')
    st.text_input('Current User',value=os.getenv('USERNAME',os.getenv('DEFAULT_USER','sysuser')),key='current_user')
    if st.button('Refresh connection'): st.rerun()

sections=json_get('/lookups/sections',SECTIONS)
tab1,tab2,tab3=st.tabs(['Data Dictionary','Prompt Management','Audit History'])

with tab1:
    st.markdown('<div class="dd-section-label">Data Dictionary</div>', unsafe_allow_html=True)
    st.markdown('<div class="dd-grid-title">Latest Active Attributes</div>', unsafe_allow_html=True)
    with st.container(border=True):
        a,b,c,d=st.columns(4)
        pf=a.multiselect('Portfolio / Sector',PORTFOLIOS, help='Use ALL for all active attributes or select one or more portfolios.')
        prj=b.text_input('PRJ ID', placeholder='e.g. PRJ_001'); name=c.text_input('Attribute Name', placeholder='Search name'); section=d.selectbox('Section',['']+sections)
        e,f,g=st.columns([2,1,1]); desc=e.text_input('Attribute Description', placeholder='Search description'); overlap=f.checkbox('Overlapped Attribute', help='Show attributes required by multiple selected portfolios.'); g.button('Refresh Grid', type='primary', use_container_width=True, on_click=clear_read_cache)
    # View Latest is intentionally active-only. Cached for quick widget reruns.
    filter_payload={'portfolios':[] if 'ALL' in pf else pf,'prj_id':prj or None,'attribute_name':name or None,'attribute_description':desc or None,'section':section or None,'include_deleted':False,'overlapped_only':overlap}
    filter_result = cached_filter_json(json.dumps(filter_payload, sort_keys=True, default=str), st.session_state.get('env', os.getenv('SELECTED_ENVIRONMENT','LOCAL')), st.session_state.get('app_role','Admin'))
    if isinstance(filter_result, dict) and filter_result.get('__api_error__'):
        st.error(f"Unable to load Data Dictionary ({filter_result.get('__status__')}): {filter_result.get('__api_error__')}")
        rows=[]
    else:
        rows=filter_result or []
    st.session_state['rows']=rows
    grid_df = pd.DataFrame(rows)
    if not grid_df.empty:
        selected = render_row_radio_grid(
            rows,
            key='active_attribute_selector_radio',
            title='Select Attribute row',
            id_field='prj_id',
            label_builder=lambda row: f"{row.get('prj_id')} | {row.get('prj_attribute_name') or row.get('attribute_name') or ''}",
        )
    else:
        st.info('No active records found for the selected filters.')
        selected = ''
    st.caption('Only one active attribute can be selected at a time for Edit or Soft Delete.')
    st.markdown('<div class="dd-section-label">Actions</div>', unsafe_allow_html=True)
    x1,x2,x3,x4=st.columns([1.2,1.2,1.2,1.2])
    if x1.button('Add New Attribute',use_container_width=True):
        st.session_state['open_create_attribute_modal'] = True
        st.session_state['create_modal_generation'] += 1
        st.session_state['selected_attribute'] = None
        create_modal.open()
    if x2.button('Generate Latest Excel',use_container_width=True):
        rr=api('GET','/data-dictionary/download-latest')
        if rr: st.session_state['latest_excel']=rr.content
    if st.session_state['latest_excel']:
        x2.download_button('Download Latest Data',st.session_state['latest_excel'],'data_dictionary_latest.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',use_container_width=True)
    if x4.button('Open / Edit Selected Attribute',disabled=not selected,use_container_width=True):
        rr=api('GET',f'/data-dictionary/attributes/{selected}')
        if rr: st.session_state['selected_attribute']=rr.json(); st.session_state['edit_unlocked']=False; edit_modal.open()
    y1,y2,y3=st.columns([1.2,1.2,1.2])
    is_admin = st.session_state.get('app_role','Admin') == 'Admin'
    if y1.button('Upload and Compare Master Dictionary',use_container_width=True, disabled=not is_admin): st.session_state['show_master_upload']=not st.session_state['show_master_upload']
    if y2.button('Soft Delete Attribute',disabled=not selected,use_container_width=True):
        if api('DELETE',f'/data-dictionary/attributes/{selected}?user={st.session_state.current_user}', activity='Soft deleting attribute'):
            st.success('Attribute soft deleted.'); st.rerun()
    if y3.button('Export to S3',use_container_width=True, disabled=not is_admin):
        if api('POST',f'/s3/export?user={st.session_state.current_user}', activity='Exporting data to S3'): st.success('S3 export completed.')
    if not is_admin:
        st.caption('Master Dictionary upload/compare and S3 export are visible to User role but can be executed only by Admin role.')
    if st.session_state['show_master_upload'] and is_admin:
        with st.expander('Upload, Compare and Finalize Master Dictionary',expanded=True):
            master=st.file_uploader('Master Dictionary Excel (.xlsx)',type=['xlsx'],key='master_upload')
            diagnostic = api('GET', '/master-upload/diagnostic', quiet=True)
            if diagnostic:
                diagnostic_payload = diagnostic.json()
                if diagnostic_payload.get('connected'):
                    st.caption(f"Upload target: {diagnostic_payload.get('server')} / {diagnostic_payload.get('database')} | Existing master rows: {diagnostic_payload.get('master_row_count')}")
                else:
                    st.error('Master upload database diagnostic failed:')
                    st.json(diagnostic_payload)
            if master:
                files={'file':(master.name,master.getvalue(),master.type or 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                p=api('POST','/master-upload/preview',files=files)
                if p:
                    preview_result = p.json()
                    if preview_result.get('status') == 'failed':
                        st.error('Master Dictionary preview failed. Detailed root cause:')
                        st.json(preview_result)
                    else:
                        st.dataframe(pd.DataFrame(preview_result.get('preview',[])),use_container_width=True,hide_index=True)
                m1,m2=st.columns(2)
                if m1.button('Compare Master Dictionary'):
                    q=api('POST','/master-upload/delta',files=files)
                    if q:
                        comparison = q.json()
                        if comparison.get('status') == 'failed':
                            st.error('Master Dictionary comparison failed. Detailed root cause:')
                        st.json(comparison)
                if m2.button('Finalize and Upload to Database'):
                    q=api('POST',f'/master-upload/finalize?user={st.session_state.current_user}',files=files)
                    if q:
                        result=q.json()
                        if result.get('status') == 'failed':
                            st.error('Master Dictionary upload failed. Detailed root cause:')
                            st.json(result)
                        else:
                            st.success(f"Master Dictionary upload completed. Inserted: {result.get('inserted',0)}, Updated: {result.get('updated',0)}, Rejected: {result.get('rejected_count',0)}")
                            if result.get('rejected'):
                                st.error('Rejected rows with detailed root cause:')
                                st.dataframe(pd.DataFrame(result['rejected']),use_container_width=True,hide_index=True)
                            st.rerun()
    with st.expander('View Deleted Attributes and Reactivate'):
        deleted_response=api('POST','/data-dictionary/filter',json={'portfolios':[],'include_deleted':True})
        deleted=[x for x in (deleted_response.json() if deleted_response else []) if not x.get('is_active')]
        deleted_id = render_row_radio_grid(
            deleted,
            key='deleted_attribute_selector_radio',
            title='Select deleted Attribute row to make active',
            id_field='prj_id',
            label_builder=lambda row: f"{row.get('prj_id')} | {row.get('prj_attribute_name') or row.get('attribute_name') or ''}",
        ) if deleted else ''
        if st.button('Reactivate Selected Attribute',disabled=not deleted_id):
            if api('POST',f'/data-dictionary/attributes/{deleted_id}/reactivate?user={st.session_state.current_user}', activity='Reactivating attribute'):
                st.success('Attribute reactivated.'); st.rerun()

if st.session_state.get('open_create_attribute_modal', False):
    if not create_modal.is_open():
        create_modal.open()
    if create_modal.is_open():
        with create_modal.container():
            saved=payload_for_attribute()
            if saved:
                st.session_state['open_create_attribute_modal']=False
                create_modal.close()
                st.toast('Create Attribute window closed.', icon='ℹ️')
                st.rerun()
            if st.button('Close', key='create_close'):
                # Clear the request flag first. This guarantees that a Streamlit rerun
                # cannot reopen the modal after the user closes it.
                st.session_state['open_create_attribute_modal']=False
                create_modal.close()
                st.rerun()
if edit_modal.is_open():
    with edit_modal.container():
        if not st.session_state.get('edit_unlocked'):
            payload_for_attribute(st.session_state.get('selected_attribute'))
            if st.button('Edit Attribute',key='edit_unlock',type='primary'):
                st.session_state['edit_unlocked']=True; st.rerun()
        else:
            saved=payload_for_attribute(st.session_state.get('selected_attribute'))
            if saved: edit_modal.close(); st.session_state['edit_unlocked']=False; st.rerun()
        if st.button('Close',key='edit_close'):
            edit_modal.close(); st.session_state['edit_unlocked']=False; st.toast('Edit Attribute window closed.', icon='ℹ️'); st.rerun()

with tab2:
    st.markdown('<div class="dd-section-label">Prompt Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="dd-grid-title">Bulk upload, scope-aware prompt updates and manual maintenance</div>', unsafe_allow_html=True)
    bulk,manual=st.tabs(['Bulk Upload','Edit / Insert Prompts'])
    with bulk:
        pb1, pb2 = st.columns([2,1])
        with pb2:
            if st.button('Download Latest Prompt File', use_container_width=True):
                prompt_download = api('GET','/prompts/download-latest')
                if prompt_download:
                    st.session_state['latest_prompt_excel'] = prompt_download.content
            if st.session_state.get('latest_prompt_excel'):
                st.download_button('Download Prompt Excel', st.session_state['latest_prompt_excel'], 'prompt_latest.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)
        with pb1:
            upload=st.file_uploader('Upload Prompt Excel',type=['xlsx'],key='prompt_file')
        if upload:
            signature=f'{upload.name}:{upload.size}'
            if st.session_state.get('prompt_file_signature') != signature:
                st.session_state['prompt_file_signature']=signature
                st.session_state['prompt_preview']=None
                st.session_state['prompt_delta']=None
            files={'file':(upload.name,upload.getvalue(),upload.type or 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            sr=api('POST','/prompt-upload/sheets',files=files); sheets=sr.json().get('sheets',[]) if sr else []
            sheet=st.selectbox('Workbook sheet',sheets,key='prompt_sheet') if sheets else None
            target_scope=st.selectbox('Target Portfolio / Scope for bulk update', ['Auto from Excel / single-scope PRJ','FI Banks','Corporates','FI Insurance','Zeus Downstream'], key='prompt_target_scope', help='For PRJ IDs with multiple active scopes, choose the one scope to update. Excel Required By Scope overrides this selection.')
            target_scope_value = '' if target_scope == 'Auto from Excel / single-scope PRJ' else target_scope
            if sheet and st.button('Load Selected Data'):
                p=api('POST','/prompt-upload/preview',files=files,data={'sheet_name':sheet})
                if p: st.session_state['prompt_preview']=p.json()
            if st.session_state.get('prompt_preview'):
                st.caption('Detected mapping: '+str(st.session_state['prompt_preview'].get('column_mapping',{})))
                st.dataframe(pd.DataFrame(st.session_state['prompt_preview'].get('preview',[])),use_container_width=True,hide_index=True)
            c1,c2,c3=st.columns(3)
            if sheet and c1.button('Validate and Compare Delta'):
                p=api('POST','/prompt-upload/delta',files=files,data={'sheet_name':sheet})
                if p: st.session_state['prompt_delta']=p.json(); st.json(p.json())
            if sheet and c2.button('Generate SQL Script'):
                p=api('POST','/prompt-upload/generate-sql?mode=MERGE',files=files,data={'sheet_name':sheet})
                if p: st.download_button('Download MERGE SQL',p.content,'prompt_merge.sql',mime='text/sql')
            if sheet and c3.button('Commit Valid Rows'):
                p=api('POST',f'/prompt-upload/finalize?user={st.session_state.current_user}',files=files,data={'sheet_name':sheet, 'target_scope':target_scope_value}, activity='Uploading prompt records')
                if p: st.success(str(p.json())); st.rerun()
    with manual:
        st.subheader('Edit / Insert Prompts')
        prompts=json_get('/prompts',[])
        st.caption('Active Prompt Records')
        selected_prompt_id = render_row_radio_grid(
            prompts,
            key='prompt_record_option',
            title='Select Prompt row to edit',
            id_field='prompt_id',
            label_builder=lambda row: f"Prompt {row.get('prompt_id')} | {row.get('prj_id')} | {row.get('attribute_name') or ''}",
        ) if prompts else ''
        if st.button('Create New Prompt', key='create_new_prompt_button'):
            selected_prompt_id = ''
            st.session_state['prompt_record_option'] = None
        current=next((p for p in prompts if str(p.get('prompt_id')) == selected_prompt_id), None)
        with st.form('prompt_manual_form'):
            ids=[str(x.get('prj_id')) for x in rows if x.get('prj_id')] or ['']
            pid=st.selectbox('PRJ ID *',ids,index=ids.index(str(current.get('prj_id'))) if current and str(current.get('prj_id')) in ids else 0,disabled=bool(current))
            derived=json_get(f'/data-dictionary/attributes/{pid}',{}) if pid else {}
            st.caption(f"Scope and Portfolio are derived from the active scope for PRJ ID {pid or '-' }.")
            name=st.text_input('Attribute Name',value=str((current or {}).get('attribute_name') or derived.get('prj_attribute_name') or ''))
            c=st.columns(3); sec=c[0].selectbox('Section',sections,index=sections.index((current or {}).get('section')) if (current or {}).get('section') in sections else 0); sub=c[1].text_input('Sub-Section',value=str((current or {}).get('sub_section') or '')); dtype=c[2].text_input('Data Type',value=str((current or {}).get('data_type') or ''))
            calc=st.text_area('Calculation Logic',value=str((current or {}).get('calculation_logic') or ''))
            c=st.columns(2); segment=c[0].text_input('Segment',value=str((current or {}).get('segment') or '')); required_scope=c[1].text_input('Required By Scope',value=str((current or {}).get('required_by_scope') or ''))
            description=st.text_area('Attribute Description',value=str((current or {}).get('attribute_description') or derived.get('prj_attribute_description') or ''))
            submit=st.form_submit_button('Update Prompt' if current else 'Create Prompt',type='primary')
        if submit:
            pp={'prj_id':pid,'attribute_name':name,'section':sec,'sub_section':sub,'data_type':dtype,'calculation_logic':calc,'segment':segment,'required_by_scope':required_scope,'attribute_description':description}
            path=f"/prompts/{current['prompt_id']}?user={st.session_state.current_user}" if current else f"/prompts?user={st.session_state.current_user}"
            rr=api('PUT' if current else 'POST',path,json=pp, activity='Updating prompt' if current else 'Creating prompt')
            if rr: st.success('Prompt saved successfully.'); st.rerun()
        if current:
            d1,d2=st.columns(2)
            if d1.button('Soft Delete Prompt') and api('DELETE',f"/prompts/{current['prompt_id']}?user={st.session_state.current_user}", activity='Soft deleting prompt'): st.success('Prompt soft deleted.'); st.rerun()
            if d2.button('Reactivate Prompt') and api('POST',f"/prompts/{current['prompt_id']}/reactivate?user={st.session_state.current_user}", activity='Reactivating prompt'): st.success('Prompt reactivated.'); st.rerun()

with tab3:
    st.markdown('<div class="dd-section-label">Audit History</div>', unsafe_allow_html=True)
    st.markdown('<div class="dd-grid-title">Traceable change history</div>', unsafe_allow_html=True)
    audit=api('GET','/audit')
    if audit: st.dataframe(pd.DataFrame(audit.json()),use_container_width=True,hide_index=True)
