from io import BytesIO
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation

class ExcelService:
    master_columns=['PRJ ID','PRJ Attribute Name','PRJ Attribute Description','PRJ Physical Attribute Name','Editable?','Calculated or Reported?','Percentage(%) / Ratio(X)','Calculation Logic','Where in financial statement is this generally collected from ?','Required by corporates?','Required by banks ?','Required by insurance?','Required by Downstream?','Version Update','Mapping Type (calculated/CAPIQ sourced/Manual Updates/Out of Scope)','Calculated in CFV? (Y/N)','Editable in Historicals screen in UCRS-CFV?(Y/N)','Sign Flipping (multiply by)','GC Template attribute name','S&P Standradisation dataitem id','S&P As-Reported dataitem ID / logic','Calculation Logic Details','Updates','Updated ON','Zeus attribute','Zeus table name','Zeus Description','Commnets','SNL dataitemid','Scanned/Calculated']
    def read_prompt_workbook(self, content, sheet_name):
        """Read prompt sheets with resilient header-row detection.

        A header can appear after title rows and may use spaces, underscores,
        punctuation or descriptive text. We inspect the first 150 rows and select
        the row containing a PRJ ID-like header plus an Attribute Name-like header.
        """
        raw = pd.read_excel(BytesIO(content), sheet_name=sheet_name, header=None, nrows=150)

        def norm(value):
            return ''.join(ch for ch in str(value).replace('\xa0', ' ').lower() if ch.isalnum())

        best_row, best_score = 0, -1
        for index, row in raw.iterrows():
            values = [norm(value) for value in row.tolist() if pd.notna(value) and str(value).strip()]
            has_prj = any('prjid' in value or value.startswith('projectid') for value in values)
            has_attribute = any(('attribute' in value and 'name' in value) or value.startswith('prjattribute') for value in values)
            has_description = any('description' in value for value in values)
            score = (5 if has_prj else 0) + (5 if has_attribute else 0) + (2 if has_description else 0)
            if score > best_score:
                best_row, best_score = int(index), score
        # Do not fail here: normalise_prompt_columns provides a precise mapping error.
        return pd.read_excel(BytesIO(content), sheet_name=sheet_name, header=best_row)
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
        """Map Prompt Excel headers flexibly.

        Any header containing both ``attribute`` and ``name`` maps to
        ``attribute_name``. This covers current and future descriptive suffixes,
        spaces, underscores and punctuation.
        """
        df = df.copy()
        df.columns = [str(c).replace('\xa0', ' ').strip() for c in df.columns]

        def ident(value):
            return ''.join(ch for ch in str(value).replace('\xa0', ' ').lower() if ch.isalnum())

        indexed = [(column, ident(column)) for column in df.columns]

        def match(*predicates):
            for column, value in indexed:
                if any(predicate(value) for predicate in predicates):
                    return column
            return None

        attribute_column = match(
            lambda value: 'attribute' in value and 'name' in value,
            lambda value: value.startswith('prjattribute'),
            lambda value: value in {'attribute', 'prjattribute'},
        )
        mapping = {
            'prj_id': match(lambda value: 'prjid' in value, lambda value: value.startswith('projectid')),
            'attribute_name': attribute_column,
            'attribute_description': match(lambda value: value.startswith('description'), lambda value: 'description' in value),
            'section': match(lambda value: value == 'section' or value.startswith('section')),
            'sub_section': match(lambda value: value.startswith('subsection')),
            'data_type': match(lambda value: value.startswith('datatype')),
            'calculated_or_reported': match(lambda value: value.startswith('calculatedorreported')),
            'calculation_logic': match(lambda value: value.startswith('calculationlogic')),
            'segment': match(lambda value: value.startswith('segment')),
            'display_order': match(lambda value: value.startswith('displayorder')),
            'examples': match(lambda value: value.startswith('examples')),
        }
        if not mapping['prj_id']:
            raise ValueError('Prompt worksheet is missing required column PRJID/PRJ ID. Detected headers: ' + ', '.join(map(str, df.columns)))
        # Permit an attribute name to be absent for unusual legacy sheets: use the
        # first descriptive attribute-like column or an empty value instead of
        # preventing preview. The UI displays the selected mapping for review.
        if not mapping['attribute_name']:
            fallback = match(lambda value: 'attribute' in value, lambda value: 'prj' in value and 'displayorder' not in value)
            mapping['attribute_name'] = fallback
        out = pd.DataFrame()
        for target, column in mapping.items():
            out[target] = df[column] if column else None
        out['prj_id'] = out['prj_id'].astype(str).str.strip()
        out = out[(out['prj_id'] != '') & (out['prj_id'].str.lower() != 'nan')]
        return out, mapping

    def read_master_workbook(self, content):
        """Master sheet has headers in row 3 and data starts at row 4."""
        return pd.read_excel(BytesIO(content), sheet_name='PRJ Data Dictionary Mapping', header=2)
