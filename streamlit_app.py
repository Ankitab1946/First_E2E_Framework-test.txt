"""Streamlit UI for the Data Dictionary Admin App. UI calls FastAPI only."""
from __future__ import annotations
import os
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
st.set_page_config(page_title='Data Dictionary Admin App',layout='wide')
st.title(os.getenv('APP_NAME','Data Dictionary Streamlit Admin'))
st.caption('Build: modal-parser-fix-verified')

for key,value in {'latest_excel':None,'rows':[],'selected_attribute':None,'prompt_preview':None,'prompt_delta':None,'show_master_upload':False,'active_prompt':None,'app_role':'Admin','open_create_attribute_modal':False,'create_modal_generation':0}.items():
    st.session_state.setdefault(key,value)

def api(method,path,quiet=False,**kwargs):
    headers=kwargs.pop('headers',{})
    headers['X-App-Environment']=st.session_state.get('env',os.getenv('SELECTED_ENVIRONMENT','LOCAL'))
    headers['X-App-Role']=st.session_state.get('app_role','Admin')
    try:
        response=requests.request(method,API+path,headers=headers,timeout=180,**kwargs)
    except requests.RequestException as exc:
        if not quiet: st.error(f'API connection failed: {exc}')
        return None
    if not response.ok:
        if not quiet:
            try: detail=response.json().get('detail',response.text)
            except Exception: detail=response.text
            st.error(f'API error ({response.status_code}): {detail}')
        return None
    return response

def json_get(path,fallback):
    r=api('GET',path,quiet=True)
    return r.json() if r else fallback

def flag(value): return str(value or '').strip().upper() in {'Y','YES','1','TRUE'}

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
    banks = c[0].checkbox('Required by FI Banks', value=flag(existing.get('required_by_banks')) or 'FI Banks' in existing.get('required_portfolios', []), disabled=readonly, key=f'{prefix}_banks')
    corporates = c[1].checkbox('Required by Corporates', value=flag(existing.get('required_by_corporates')) or 'Corporates' in existing.get('required_portfolios', []), disabled=readonly, key=f'{prefix}_corporates')
    insurance = c[2].checkbox('Required by FI Insurance', value=flag(existing.get('required_by_insurance')) or 'FI Insurance' in existing.get('required_portfolios', []), disabled=readonly, key=f'{prefix}_insurance')
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
    r = api('PUT' if is_edit else 'POST', endpoint, json=p)
    if r:
        st.success('Attribute saved successfully.')
        return True
    return False

create_modal=Modal('Create New Attribute',key='create_attribute_modal',max_width=1200)
edit_modal=Modal('Edit Attribute',key='edit_attribute_modal',max_width=1200)

with st.sidebar:
    st.subheader('Connection')
    envs=[x.strip().upper() for x in os.getenv('APP_ENVIRONMENTS','LOCAL,DEV,UAT,PROD').split(',') if x.strip()]
    default=os.getenv('SELECTED_ENVIRONMENT','LOCAL').upper()
    st.selectbox('Environment',envs,index=envs.index(default) if default in envs else 0,key='env')
    env=json_get('/system/environment',{})
    status=json_get('/system/connection-status',{'connected':False,'message':'FastAPI endpoint unavailable'})
    st.caption('Server: '+str(env.get('server',os.getenv('SQLSERVER_SERVER','Not configured'))))
    st.caption('Database: '+str(env.get('database',os.getenv('SQLSERVER_DATABASE','Not configured'))))
    (st.success if status.get('connected') else st.error)('DB Connected' if status.get('connected') else 'DB Not Connected: '+str(status.get('message','Unknown error')))
    st.selectbox('Role', ['Admin','User'], key='app_role', help='Admin can upload/compare the Master Dictionary and export to S3. User can see these controls but cannot execute them.')
    st.text_input('Current User',value=os.getenv('USERNAME',os.getenv('DEFAULT_USER','sysuser')),key='current_user')
    if st.button('Refresh connection'): st.rerun()

sections=json_get('/lookups/sections',SECTIONS)
tab1,tab2,tab3=st.tabs(['Data Dictionary','Prompt Management','Audit History'])

with tab1:
    st.subheader('View Latest Data Dictionary')
    a,b,c,d=st.columns(4)
    pf=a.multiselect('Portfolio/Sector',PORTFOLIOS)
    prj=b.text_input('PRJ ID filter'); name=c.text_input('Attribute Name filter'); section=d.selectbox('Section filter',['']+sections)
    e,f=st.columns(2); desc=e.text_input('Attribute Description filter'); include_deleted=f.checkbox('View soft deleted records'); overlap=f.checkbox('Overlapped Attribute only')
    r=api('POST','/data-dictionary/filter',json={'portfolios':[] if 'ALL' in pf else pf,'prj_id':prj or None,'attribute_name':name or None,'attribute_description':desc or None,'section':section or None,'include_deleted':include_deleted,'overlapped_only':overlap})
    rows=r.json() if r else []
    st.session_state['rows']=rows
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    x1,x2,x3,x4=st.columns(4)
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
    selected=x3.selectbox('Selected PRJ ID',['']+[str(x.get('prj_id','')) for x in rows])
    if x4.button('Open / Edit Selected Attribute',disabled=not selected,use_container_width=True):
        rr=api('GET',f'/data-dictionary/attributes/{selected}')
        if rr: st.session_state['selected_attribute']=rr.json(); st.session_state['edit_unlocked']=False; edit_modal.open()
    y1,y2,y3=st.columns(3)
    is_admin = st.session_state.get('app_role','Admin') == 'Admin'
    if y1.button('Upload and Compare Master Dictionary',use_container_width=True, disabled=not is_admin): st.session_state['show_master_upload']=not st.session_state['show_master_upload']
    if y2.button('Soft Delete Attribute',disabled=not selected,use_container_width=True):
        if api('DELETE',f'/data-dictionary/attributes/{selected}?user={st.session_state.current_user}'): st.success('Attribute soft deleted.')
    if y3.button('Export to S3',use_container_width=True, disabled=not is_admin):
        if api('POST',f'/s3/export?user={st.session_state.current_user}'): st.success('S3 export completed.')
    if not is_admin:
        st.caption('Master Dictionary upload/compare and S3 export are visible to User role but can be executed only by Admin role.')
    if st.session_state['show_master_upload'] and is_admin:
        with st.expander('Upload, Compare and Finalize Master Dictionary',expanded=True):
            master=st.file_uploader('Master Dictionary Excel (.xlsx)',type=['xlsx'],key='master_upload')
            if master:
                files={'file':(master.name,master.getvalue(),master.type or 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                p=api('POST','/master-upload/preview',files=files)
                if p: st.dataframe(pd.DataFrame(p.json().get('preview',[])),use_container_width=True,hide_index=True)
                m1,m2=st.columns(2)
                if m1.button('Compare Master Dictionary'):
                    q=api('POST','/master-upload/delta',files=files)
                    if q: st.json(q.json())
                if m2.button('Finalize and Upload to Database'):
                    q=api('POST',f'/master-upload/finalize?user={st.session_state.current_user}',files=files)
                    if q: st.success(str(q.json()))

if st.session_state.get('open_create_attribute_modal', False):
    if not create_modal.is_open():
        create_modal.open()
    if create_modal.is_open():
        with create_modal.container():
            saved=payload_for_attribute()
            if saved:
                st.session_state['open_create_attribute_modal']=False
                create_modal.close()
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
            edit_modal.close(); st.session_state['edit_unlocked']=False; st.rerun()

with tab2:
    bulk,manual=st.tabs(['Bulk Upload','Edit/Insert Prompts'])
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
                p=api('POST',f'/prompt-upload/finalize?user={st.session_state.current_user}',files=files,data={'sheet_name':sheet})
                if p: st.success(str(p.json()))
    with manual:
        st.subheader('Edit / Insert Prompts')
        prompts=json_get('/prompts',[])
        choices=['Create new prompt']+[f"{p.get('prompt_id')} | {p.get('prj_id')} | {p.get('attribute_name') or ''}" for p in prompts]
        choice=st.selectbox('Prompt record',choices)
        current=None if choice=='Create new prompt' else prompts[choices.index(choice)-1]
        with st.form('prompt_manual_form'):
            ids=[str(x.get('prj_id')) for x in rows if x.get('prj_id')] or ['']
            pid=st.selectbox('PRJ ID *',ids,index=ids.index(str(current.get('prj_id'))) if current and str(current.get('prj_id')) in ids else 0,disabled=bool(current))
            derived=json_get(f'/data-dictionary/attributes/{pid}',{}) if pid else {}
            st.caption(f"Scope and Portfolio are derived from the active scope for PRJ ID {pid or '-'}.")
            name=st.text_input('Attribute Name',value=str((current or {}).get('attribute_name') or derived.get('prj_attribute_name') or ''))
            c=st.columns(3); sec=c[0].selectbox('Section',sections,index=sections.index((current or {}).get('section')) if (current or {}).get('section') in sections else 0); sub=c[1].text_input('Sub-Section',value=str((current or {}).get('sub_section') or '')); dtype=c[2].text_input('Data Type',value=str((current or {}).get('data_type') or ''))
            calc=st.text_area('Calculation Logic',value=str((current or {}).get('calculation_logic') or ''))
            c=st.columns(2); segment=c[0].text_input('Segment',value=str((current or {}).get('segment') or '')); required_scope=c[1].text_input('Required By Scope',value=str((current or {}).get('required_by_scope') or ''))
            description=st.text_area('Attribute Description',value=str((current or {}).get('attribute_description') or derived.get('prj_attribute_description') or ''))
            submit=st.form_submit_button('Update Prompt' if current else 'Create Prompt',type='primary')
        if submit:
            pp={'prj_id':pid,'attribute_name':name,'section':sec,'sub_section':sub,'data_type':dtype,'calculation_logic':calc,'segment':segment,'required_by_scope':required_scope,'attribute_description':description}
            path=f"/prompts/{current['prompt_id']}?user={st.session_state.current_user}" if current else f"/prompts?user={st.session_state.current_user}"
            rr=api('PUT' if current else 'POST',path,json=pp)
            if rr: st.success('Prompt saved successfully.'); st.rerun()
        if current:
            d1,d2=st.columns(2)
            if d1.button('Soft Delete Prompt') and api('DELETE',f"/prompts/{current['prompt_id']}?user={st.session_state.current_user}"): st.success('Prompt soft deleted.'); st.rerun()
            if d2.button('Reactivate Prompt') and api('POST',f"/prompts/{current['prompt_id']}/reactivate?user={st.session_state.current_user}"): st.success('Prompt reactivated.'); st.rerun()

with tab3:
    audit=api('GET','/audit')
    if audit: st.dataframe(pd.DataFrame(audit.json()),use_container_width=True,hide_index=True)
