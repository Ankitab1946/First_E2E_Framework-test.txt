from __future__ import annotations
from datetime import datetime, timezone
from io import BytesIO
from typing import Any
from openpyxl import load_workbook
from sqlalchemy.orm import Session
from DataDictionaryAdminApp.config import get_settings
from DataDictionaryAdminApp.core.database import get_session_factory
from DataDictionaryAdminApp.model.configuration_tables import AttributePortfolioScope, AttributeBusinessRule, PortfolioReference, PromptReference, UiDisplayConfig
from DataDictionaryAdminApp.model.master_dictionary import MasterDictionary
from DataDictionaryAdminApp.utils.physical_name_generator import unique_physical_name

SECTOR_MAP = {'banks':('FI','Banks'),'bank':('FI','Banks'),'insurance':('FI','Insurance'),'corporates':('Corporate','Corporate'),'corporate':('Corporate','Corporate'),'downstream':('UKC','UKC'),'ukc':('UKC','UKC'),'snp':('SnP','SnP'),'s&p':('SnP','SnP')}
FLAG_TO_SECTOR = {'required_by_banks':('FI','Banks'),'required_by_insurance':('FI','Insurance'),'required_by_corporates':('Corporate','Corporate'),'required_by_downstream':('UKC','UKC')}

class ConfigurationService:
    def __init__(self): self.settings=get_settings()
    def _session(self): return get_session_factory()()
    @staticmethod
    def _as_dict(entity): return {c.name:getattr(entity,c.name) for c in entity.__table__.columns}
    @staticmethod
    def _actor(user_id): return user_id or 'sysuser'
    def bootstrap_portfolios(self, user_id='sysuser'):
        if not self.settings.enable_db: return {'status':'SIMULATED_SUCCESS','records_processed':5}
        seeds=[('FI','Banks','Financial Institutes - Banks'),('FI','Insurance','Financial Institutes - Insurance'),('Corporate','Corporate','Global Corporates'),('UKC','UKC','UK Corporate'),('SnP','SnP','Standard & Poor\'s')]
        with self._session() as db:
            for pn,sn,remark in seeds:
                if not db.query(PortfolioReference).filter_by(port_name=pn,sector_name=sn,sub_sector=None).first(): db.add(PortfolioReference(port_name=pn,sector_name=sn,remark=remark,created_by=self._actor(user_id),updated_by=self._actor(user_id)))
            db.commit()
        return {'status':'SUCCESS','records_processed':len(seeds)}
    def _portfolio(self, db:Session, sector:str):
        key=(sector or '').strip().lower(); mapped=SECTOR_MAP.get(key)
        if not mapped: raise ValueError(f'Unsupported sector: {sector}')
        ref=db.query(PortfolioReference).filter_by(port_name=mapped[0],sector_name=mapped[1],is_active=True).first()
        if not ref: raise ValueError(f'Portfolio reference missing for sector: {sector}. Run bootstrap first.')
        return ref
    def sync_scopes(self, prj_id:str, user_id='sysuser'):
        if not self.settings.enable_db: return []
        with self._session() as db:
            master=db.query(MasterDictionary).filter_by(prj_id=prj_id).first()
            if not master: raise ValueError(f'PRJ ID not found: {prj_id}')
            desired=[]
            for flag, portfolio in FLAG_TO_SECTOR.items():
                if bool(getattr(master,flag)): desired.append(portfolio)
            references={(r.port_name,r.sector_name):r for r in db.query(PortfolioReference).filter(PortfolioReference.is_active==True).all()}
            existing={(s.port_ref_id):s for s in db.query(AttributePortfolioScope).filter_by(prj_id=prj_id).all()}
            for portfolio in desired:
                ref=references.get(portfolio)
                if not ref: continue
                scope=existing.get(ref.port_ref_id)
                if scope:
                    scope.is_active=True; scope.is_deleted=False; scope.description=master.prj_attribute_description; scope.updated_by=self._actor(user_id)
                else: db.add(AttributePortfolioScope(prj_id=prj_id,port_ref_id=ref.port_ref_id,description=master.prj_attribute_description,created_by=self._actor(user_id),updated_by=self._actor(user_id)))
            desired_ids={references[p].port_ref_id for p in desired if p in references}
            for port_id,scope in existing.items():
                if port_id not in desired_ids: scope.is_active=False; scope.updated_by=self._actor(user_id)
            db.commit()
            return [self._as_dict(x) for x in db.query(AttributePortfolioScope).filter_by(prj_id=prj_id).all()]
    def ensure_physical_name(self, prj_id:str, attribute_name:str, current_value:str|None, user_id='sysuser') -> str:
        if current_value: return current_value
        if not self.settings.enable_db: return unique_physical_name(attribute_name, lambda _:False)
        with self._session() as db:
            master=db.query(MasterDictionary).filter_by(prj_id=prj_id).first()
            if master and master.prj_physical_attribute_name: return master.prj_physical_attribute_name
            value=unique_physical_name(attribute_name, lambda x: db.query(MasterDictionary).filter(MasterDictionary.prj_physical_attribute_name==x,MasterDictionary.prj_id!=prj_id).first() is not None)
            if master: master.prj_physical_attribute_name=value; master.updated_by=self._actor(user_id); db.commit()
            return value
    def _scope(self, db, prj_id, sector):
        ref=self._portfolio(db, sector)
        scope=db.query(AttributePortfolioScope).filter_by(prj_id=prj_id,port_ref_id=ref.port_ref_id).first()
        if not scope: raise ValueError(f'No scope for PRJ ID {prj_id} and sector {sector}. Synchronize scopes or mark the relevant required flag as Yes.')
        return scope,ref
    def list_displays(self, active_only=True):
        if not self.settings.enable_db:return []
        with self._session() as db:
            q=db.query(UiDisplayConfig)
            if active_only:q=q.filter(UiDisplayConfig.is_active==True,UiDisplayConfig.is_deleted==False)
            return [self._as_dict(x) for x in q.order_by(UiDisplayConfig.section,UiDisplayConfig.display_order).all()]
    def save_display(self,data,user_id='sysuser'):
        if not self.settings.enable_db:return {'status':'SIMULATED_SUCCESS'}
        with self._session() as db:
            scope,_=self._scope(db,data['prj_id'],data['sector'])
            entity=db.query(UiDisplayConfig).filter_by(display_id=data.get('display_id')).first() if data.get('display_id') else None
            vals={k:data.get(k) for k in ['display_order','display_name','section','subsection','view_name','description']}; vals['display_name']=vals['display_name'] or data.get('prj_attribute_name') or data['prj_id']
            if entity is None: entity=UiDisplayConfig(scope_id=scope.scope_id,created_by=self._actor(user_id),updated_by=self._actor(user_id),**vals); db.add(entity)
            else:
                entity.scope_id=scope.scope_id; entity.is_active=True;entity.is_deleted=False;entity.updated_by=self._actor(user_id)
                for k,v in vals.items():setattr(entity,k,v)
            db.commit(); db.refresh(entity); return self._as_dict(entity)
    def soft_delete_display(self,display_id,user_id='sysuser'):
        return self._soft_delete(UiDisplayConfig,'display_id',display_id,user_id)
    def _soft_delete(self, model,key,value,user_id):
        if not self.settings.enable_db:return {'status':'SIMULATED_SUCCESS'}
        with self._session() as db:
            x=db.query(model).filter(getattr(model,key)==value).first()
            if not x:raise ValueError('Record not found')
            x.is_active=False;x.is_deleted=True;x.deleted_by=self._actor(user_id);x.deleted_at=datetime.now(timezone.utc);x.updated_by=self._actor(user_id);db.commit();return self._as_dict(x)
    def save_rule(self,data,user_id='sysuser'):
        if not self.settings.enable_db:return {'status':'SIMULATED_SUCCESS'}
        with self._session() as db:
            scope,_=self._scope(db,data['prj_id'],data['sector']); x=db.query(AttributeBusinessRule).filter_by(scope_id=scope.scope_id).first()
            vals={k:data.get(k) for k in ['source_abbr_name','editable','symbol','mapping_type','mapping_logic','calculation_logic','business_logic']}
            vals['source_abbr_name']=vals['source_abbr_name'] or 'SNPAR'
            if not x:x=AttributeBusinessRule(scope_id=scope.scope_id,created_by=self._actor(user_id),updated_by=self._actor(user_id),**vals);db.add(x)
            else:
                for k,v in vals.items():setattr(x,k,v)
                x.is_active=True;x.is_deleted=False;x.updated_by=self._actor(user_id)
            db.commit();db.refresh(x);return self._as_dict(x)
    def list_prompts(self,active_only=True):
        if not self.settings.enable_db:return []
        with self._session() as db:
            q=db.query(PromptReference)
            if active_only:q=q.filter(PromptReference.is_active==True,PromptReference.is_deleted==False)
            return [self._as_dict(x) for x in q.order_by(PromptReference.cfv_id).all()]
    def save_prompt(self,data,user_id='sysuser'):
        if not self.settings.enable_db:return {'status':'SIMULATED_SUCCESS'}
        with self._session() as db:
            scope,ref=self._scope(db,data['prj_id'],data['sector'])
            x=db.query(PromptReference).filter_by(scope_id=scope.scope_id,cfv_id=str(data.get('cfv_id') or data['prj_id']),port_ref_id=ref.port_ref_id).first()
            vals={'attribute_description':data.get('attribute_description'),'examples':data.get('examples'),'segment':data.get('segment'),'source_sheet_name':data.get('source_sheet_name')}
            if not x:x=PromptReference(scope_id=scope.scope_id,cfv_id=str(data.get('cfv_id') or data['prj_id']),port_ref_id=ref.port_ref_id,created_by=self._actor(user_id),updated_by=self._actor(user_id),**vals);db.add(x)
            else:
                for k,v in vals.items():setattr(x,k,v)
                x.is_active=True;x.is_deleted=False;x.updated_by=self._actor(user_id)
            db.commit();db.refresh(x);return self._as_dict(x)
    def soft_delete_prompt(self,prompt_id,user_id='sysuser'):return self._soft_delete(PromptReference,'prompt_id',prompt_id,user_id)
    def soft_delete_rule(self, rule_id, user_id='sysuser'): return self._soft_delete(AttributeBusinessRule, 'id', rule_id, user_id)
    def reactivate(self, model, key, value, user_id='sysuser'):
        if not self.settings.enable_db: return {'status':'SIMULATED_SUCCESS'}
        with self._session() as db:
            x=db.query(model).filter(getattr(model,key)==value).first()
            if not x: raise ValueError('Record not found')
            x.is_active=True; x.is_deleted=False; x.deleted_at=None; x.deleted_by=None; x.updated_by=self._actor(user_id)
            db.commit(); return self._as_dict(x)
    def reactivate_display(self, display_id, user_id='sysuser'): return self.reactivate(UiDisplayConfig,'display_id',display_id,user_id)
    def reactivate_prompt(self, prompt_id, user_id='sysuser'): return self.reactivate(PromptReference,'prompt_id',prompt_id,user_id)
    def reactivate_rule(self, rule_id, user_id='sysuser'): return self.reactivate(AttributeBusinessRule,'id',rule_id,user_id)
    def upload_prompts(self,file_bytes:bytes,sheets:list[str]|None,user_id='sysuser'):
        wb=load_workbook(BytesIO(file_bytes),data_only=True); selected=sheets or wb.sheetnames; results=[]; errors=[]
        for name in selected:
            if name not in wb.sheetnames: errors.append({'sheet':name,'error':'Worksheet not found'});continue
            ws=wb[name]; headers=[str(ws.cell(1,c).value or '').strip().lower() for c in range(1,ws.max_column+1)]; lookup={h:i+1 for i,h in enumerate(headers)}
            required={'prjid','prj attribute','description (proposed one-shot prompting)'}
            if not required.issubset(lookup): errors.append({'sheet':name,'error':'Missing mandatory prompt columns'});continue
            for r in range(2,ws.max_row+1):
                prjid=ws.cell(r,lookup['prjid']).value
                if not prjid:continue
                sector=ws.cell(r,lookup.get('sector',0)).value if lookup.get('sector') else 'SnP'
                try: results.append(self.save_prompt({'prj_id':str(prjid).strip(),'cfv_id':str(prjid).strip(),'sector':str(sector or 'SnP'),'attribute_description':ws.cell(r,lookup['description (proposed one-shot prompting)']).value,'examples':ws.cell(r,lookup.get('examples',0)).value if lookup.get('examples') else None,'segment':ws.cell(r,lookup.get('segment',0)).value if lookup.get('segment') else None,'source_sheet_name':name},user_id))
                except Exception as exc: errors.append({'sheet':name,'row':r,'error':str(exc)})
        return {'processed':len(results),'errors':errors,'records':results}
