from io import BytesIO
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation

class ExcelService:
    master_columns=['PRJ ID','PRJ Attribute Name','PRJ Attribute Description','PRJ Physical Attribute Name','Editable?','Calculated or Reported?','Percentage(%) / Ratio(X)','Calculation Logic','Where in financial statement is this generally collected from ?','Required by corporates?','Required by banks ?','Required by insurance?','Required by Downstream?','Version Update','Mapping Type (calculated/CAPIQ sourced/Manual Updates/Out of Scope)','Calculated in CFV? (Y/N)','Editable in Historicals screen in UCRS-CFV?(Y/N)','Sign Flipping (multiply by)','GC Template attribute name','S&P Standradisation dataitem id','S&P As-Reported dataitem ID / logic','Calculation Logic Details','Updates','Updated ON','Zeus attribute','Zeus table name','Zeus Description','Commnets','SNL dataitemid','Scanned/Calculated']
    def read_prompt_workbook(self, content, sheet_name): return pd.read_excel(BytesIO(content), sheet_name=sheet_name)
    def sheets(self,content): return pd.ExcelFile(BytesIO(content)).sheet_names
    def build_latest(self, rows):
        wb=Workbook(); ws=wb.active; ws.title='PRJ Data Dictionary Mapping'; ws['A1']='Data Dictionary Export'; ws['A2']=f'Generated: {datetime.utcnow().isoformat()}Z'
        ws.append(self.master_columns)
        for r in rows: ws.append([getattr(r,'prj_id',None),getattr(r,'prj_attribute_name',None),getattr(r,'prj_attribute_description',None),getattr(r,'prj_physical_attribute_name',None),None,getattr(r,'calculated_or_reported',None),None,getattr(r,'calculation_logic',None),getattr(r,'where_in_financial_statement',None),None,None,None,None,getattr(r,'version_update',None),getattr(r,'mapping_type',None),getattr(r,'calculated_in_cfv',None),getattr(r,'editable_in_historicals',None),getattr(r,'sign_flipping_value',None),None,getattr(r,'sp_standardisation_dataitem_id',None),getattr(r,'sp_as_reported_dataitem_logic',None),getattr(r,'calculation_logic_details',None),None,None,None,None,None,None,None,None])
        dv=DataValidation(type='list', formula1='"Y,N"'); ws.add_data_validation(dv); dv.add(f'J4:M1048576')
        for col in ws.columns: ws.column_dimensions[col[0].column_letter].width=24
        out=BytesIO(); wb.save(out); return out.getvalue()


    def build_latest_dicts(self, rows):
        wb=Workbook(); ws=wb.active; ws.title='PRJ Data Dictionary Mapping'; ws['A1']='Data Dictionary Export'; ws['A2']=f'Generated: {datetime.utcnow().isoformat()}Z'
        ws.append(self.master_columns)
        for r in rows:
            ws.append([r.get('prj_id'),r.get('prj_attribute_name'),r.get('prj_attribute_description'),r.get('prj_physical_attribute_name'),None,r.get('calculated_or_reported'),None,r.get('calculation_logic'),r.get('where_in_financial_statement'),None,None,None,None,r.get('version_update'),r.get('mapping_type'),r.get('calculated_in_cfv'),r.get('editable_in_historicals'),r.get('sign_flipping_value'),None,r.get('sp_standardisation_dataitem_id'),r.get('sp_as_reported_dataitem_logic'),r.get('calculation_logic_details'),None,None,None,None,None,None,None,None])
        for col in ws.columns: ws.column_dimensions[col[0].column_letter].width=24
        out=BytesIO(); wb.save(out); return out.getvalue()

    @staticmethod
    def normalise_prompt_columns(df):
        """Normalise Prompt workbook headers without relying on an exact Excel template.

        Attribute name deliberately prefers any header beginning with `Attribute Name`,
        for example `Attribute Name (to be Viewed on Historical and HITL)`.
        This satisfies the agreed workbook contract even when descriptive suffixes change.
        """
        df = df.copy()
        df.columns = [str(c).replace('\xa0', ' ').strip() for c in df.columns]

        def normalise_header(value):
            return ' '.join(str(value).replace('\xa0', ' ').strip().lower().split())

        def first(*names):
            candidates = [(column, normalise_header(column)) for column in df.columns]
            for name in names:
                wanted = normalise_header(name)
                for column, candidate in candidates:
                    if candidate == wanted or candidate.startswith(wanted):
                        return column
            return None

        # Attribute Name must take precedence over the older PRJ Attribute label.
        attribute_name_column = first('Attribute Name') or first('PRJ Attribute')
        mapping = {
            'prj_id': first('prjid', 'prj id'),
            'attribute_name': attribute_name_column,
            'attribute_description': first('Description'),
            'section': first('Section'),
            'sub_section': first('Sub-Section', 'Sub Section'),
            'data_type': first('DATA TYPE', 'Data Type'),
            'calculated_or_reported': first('Calculated or Reported'),
            'calculation_logic': first('Calculation Logic'),
            'segment': first('Segment'),
            'display_order': first('Display Order'),
            'examples': first('Examples'),
        }
        if not mapping['prj_id']:
            raise ValueError('Prompt worksheet is missing required column PRJID/PRJ ID.')
        if not mapping['attribute_name']:
            raise ValueError('Prompt worksheet is missing an Attribute Name column. Use a column beginning with Attribute Name.')

        out = pd.DataFrame()
        for target, column in mapping.items():
            out[target] = df[column] if column else None
        out['prj_id'] = out['prj_id'].astype(str).str.strip()
        out = out[(out['prj_id'] != '') & (out['prj_id'].str.lower() != 'nan')]
        return out, mapping

    def read_master_workbook(self, content):
        """Master sheet has headers in row 3 and data starts at row 4."""
        return pd.read_excel(BytesIO(content), sheet_name='PRJ Data Dictionary Mapping', header=2)
