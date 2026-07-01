from io import BytesIO
from datetime import datetime
import re
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.datavalidation import DataValidation


class ExcelService:
    master_columns = [
        'PRJ ID','PRJ Attribute Name','PRJ Attribute Description','PRJ Physical Attribute Name','Editable?',
        'Calculated or Reported?','Percentage(%) / Ratio(X)','Calculation Logic',
        'Where in financial statement is this generally collected from ?','Required by corporates?',
        'Required by banks ?','Required by insurance?','Required by Downstream?','Version Update',
        'Mapping Type (calculated/CAPIQ sourced/Manual Updates/Out of Scope)','Calculated in CFV? (Y/N)',
        'Editable in Historicals screen in UCRS-CFV?(Y/N)','Sign Flipping (multiply by)',
        'GC Template attribute name','S&P Standradisation dataitem id','S&P As-Reported dataitem ID / logic',
        'Calculation Logic Details','Updates','Updated ON','Zeus attribute','Zeus table name','Zeus Description',
        'Commnets','SNL dataitemid','Scanned/Calculated'
    ]

    @staticmethod
    def _identifier(value) -> str:
        return ''.join(ch for ch in str(value).replace('\xa0', ' ').lower() if ch.isalnum())

    def sheets(self, content):
        return pd.ExcelFile(BytesIO(content)).sheet_names

    def read_prompt_workbook(self, content, sheet_name):
        """Read a Prompt worksheet with resilient header discovery.

        Supports the supplied business header ``Attribute Name( to be Viewed on
        Historical and HITL)`` and two-row/merged Excel headers.  CFVID is never
        considered an attribute-name field.
        """
        raw = pd.read_excel(BytesIO(content), sheet_name=sheet_name, header=None, dtype=object)
        scan_limit = min(len(raw.index), 500)

        def cleaned(value):
            return self._identifier(value)
        def has_prj(values):
            return any(v in {'prjid', 'cfvid'} or v.startswith('prjid') or v.startswith('projectid') for v in values)
        def has_attr(values):
            return any(v.startswith('attributename') or ('attribute' in v and 'name' in v) or v.startswith('prjattribute') for v in values)

        candidates=[]
        for idx in range(scan_limit):
            one=[cleaned(v) for v in raw.iloc[idx].tolist() if pd.notna(v) and str(v).strip()]
            if has_prj(one) and has_attr(one):
                candidates.append((idx, one, 3))
            # Excel files sometimes use a merged/split two-row header.
            if idx + 1 < scan_limit:
                combined=[]
                for a,b in zip(raw.iloc[idx].tolist(), raw.iloc[idx+1].tolist()):
                    combined.append(cleaned(f"{'' if pd.isna(a) else a} {'' if pd.isna(b) else b}"))
                if has_prj(combined) and has_attr(combined):
                    candidates.append((idx, combined, 4))
        if not candidates:
            headers=[str(v) for v in raw.iloc[:min(scan_limit,20)].fillna('').values.flatten() if str(v).strip()]
            raise ValueError("Prompt worksheet is missing an Attribute Name column. Expected a header starting with 'Attribute Name', for example 'Attribute Name( to be Viewed on Historical and HITL)'. Detected values: " + ', '.join(headers[:80]))
        # Prefer a two-row header where it contains the full business description,
        # otherwise choose the first valid header row.
        idx, _, rows = max(candidates, key=lambda x: (x[2], sum('attributename' in y for y in x[1])))
        if rows == 4:
            headers=[]
            for a,b in zip(raw.iloc[idx].tolist(), raw.iloc[idx+1].tolist()):
                av='' if pd.isna(a) else str(a).strip(); bv='' if pd.isna(b) else str(b).strip()
                headers.append((av + (' ' if av and bv else '') + bv).strip())
            data=raw.iloc[idx+2:].copy()
        else:
            headers=[str(x).strip() if pd.notna(x) else '' for x in raw.iloc[idx].tolist()]
            data=raw.iloc[idx+1:].copy()
        data.columns=headers
        data=data.loc[:, [str(c).strip() != '' for c in data.columns]]
        return data.reset_index(drop=True)

    @staticmethod
    def normalise_prompt_columns(df):
        """Map flexible Prompt Excel headers into canonical names.

        Header examples supported include ``Attribute Name( to be Viewed on Historical
        and HITL)``, ``Attribute_Name``, and any header containing both words.
        """
        df = df.copy()
        df.columns = [str(c).replace('\xa0', ' ').replace('\u200b', '').replace('\n', ' ').strip() for c in df.columns]
        indexed = [(column, ExcelService._identifier(column)) for column in df.columns]

        def first(predicate):
            for column, ident in indexed:
                if predicate(column, ident):
                    return column
            return None

        attr_col = first(lambda col, ident: str(col).casefold().replace('_', ' ').strip().startswith('attribute name'))
        if not attr_col:
            attr_col = first(lambda col, ident: 'attribute' in ident and 'name' in ident)
        if not attr_col:
            attr_col = first(lambda col, ident: ident.startswith('prjattributename') or ident.startswith('prjattribute'))

        prj_col = first(lambda col, ident: ident in {'prjid', 'cfvid'} or ident.startswith('prjid') or ident.startswith('projectid'))
        mapping = {
            'prj_id': prj_col,
            'attribute_name': attr_col,
            'attribute_description': first(lambda col, ident: ident.startswith('description') or 'description' in ident),
            'section': first(lambda col, ident: ident == 'section' or ident.startswith('section')),
            'sub_section': first(lambda col, ident: ident.startswith('subsection')),
            'data_type': first(lambda col, ident: ident.startswith('datatype')),
            'calculated_or_reported': first(lambda col, ident: ident.startswith('calculatedorreported')),
            'calculation_logic': first(lambda col, ident: ident.startswith('calculationlogic')),
            'segment': first(lambda col, ident: ident.startswith('segment')),
            'display_order': first(lambda col, ident: ident.startswith('displayorder')),
            'examples': first(lambda col, ident: ident.startswith('examples')),
        }
        if not mapping['prj_id']:
            raise ValueError('Prompt worksheet is missing required PRJID/PRJ ID/CFVID column. Detected headers: ' + ', '.join(map(str, df.columns)))
        if not mapping['attribute_name']:
            raise ValueError('Prompt worksheet is missing an Attribute Name column. Detected headers: ' + ', '.join(map(str, df.columns)))
        output = pd.DataFrame({target: (df[column] if column else None) for target, column in mapping.items()})
        output['prj_id'] = output['prj_id'].astype(str).str.strip()
        output = output[(output['prj_id'] != '') & (output['prj_id'].str.lower() != 'nan')]
        return output, mapping

    @staticmethod
    def _format_master_sheet(ws):
        blue = PatternFill(fill_type='solid', fgColor='1F4E78')
        white_bold = Font(color='FFFFFF', bold=True)
        for cell in ws[3]:
            cell.fill = blue
            cell.font = white_bold
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        ws.freeze_panes = 'A4'
        ws.auto_filter.ref = f'A3:{ws.cell(row=max(ws.max_row, 3), column=ws.max_column).coordinate}'
        ws.row_dimensions[3].height = 32
        for column_cells in ws.columns:
            letter = column_cells[0].column_letter
            max_len = max((len(str(c.value or '')) for c in column_cells[:250]), default=12)
            ws.column_dimensions[letter].width = min(max(max_len + 2, 14), 42)

    def build_latest_dicts(self, rows):
        wb = Workbook(); ws = wb.active; ws.title = 'PRJ Data Dictionary Mapping'
        ws['A1'] = 'Data Dictionary Export'
        ws['A2'] = f'Generated: {datetime.utcnow().isoformat()}Z'
        ws.append(self.master_columns)
        for r in rows:
            ws.append([
                r.get('prj_id'), r.get('prj_attribute_name'), r.get('prj_attribute_description'),
                r.get('prj_physical_attribute_name'), r.get('editable'), r.get('calculated_or_reported'),
                r.get('percent_ratio') or r.get('symbol'), r.get('calculation_logic'),
                r.get('where_in_financial_statement'), r.get('required_by_corporates'), r.get('required_by_banks'),
                r.get('required_by_insurance'), r.get('required_by_zeus_downstream'), r.get('version_update'),
                r.get('mapping_type'), r.get('calculated_in_cfv'), r.get('editable_in_historicals'),
                r.get('sign_flipping_value'), None, r.get('sp_standardisation_dataitem_id'),
                r.get('sp_as_reported_dataitem_logic'), r.get('calculation_logic_details'), None, None, None,
                None, None, None, None, None
            ])
        self._format_master_sheet(ws)
        validation = DataValidation(type='list', formula1='"Y,N"', allow_blank=True)
        ws.add_data_validation(validation); validation.add('E4:E1048576'); validation.add('J4:M1048576')
        out = BytesIO(); wb.save(out); return out.getvalue()

    def build_latest(self, rows):
        return self.build_latest_dicts([{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in rows])

    def read_master_workbook(self, content):
        return pd.read_excel(BytesIO(content), sheet_name='PRJ Data Dictionary Mapping', header=2)
