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

        The business workbook is allowed to vary in descriptive suffixes. The
        selected worksheet is accepted when it has a PRJ identifier header;
        attribute-name mapping is then resolved independently and never mapped
        from CFVID.
        """
        raw = pd.read_excel(BytesIO(content), sheet_name=sheet_name, header=None, dtype=object)
        scan_limit = min(len(raw.index), 500)

        def cleaned(value):
            return self._identifier(value)

        def has_prj(values):
            return any(v in {'prjid', 'cfvid'} or v.startswith('prjid') or v.startswith('projectid') for v in values)

        candidates = []
        for idx in range(scan_limit):
            one = [cleaned(v) for v in raw.iloc[idx].tolist() if pd.notna(v) and str(v).strip()]
            if has_prj(one):
                score = sum(1 for v in one if v.startswith('attributename') or ('attribute' in v and 'name' in v))
                candidates.append((idx, 1, score))
            if idx + 1 < scan_limit:
                combined = []
                for a, b in zip(raw.iloc[idx].tolist(), raw.iloc[idx + 1].tolist()):
                    combined.append(cleaned(f"{'' if pd.isna(a) else a} {'' if pd.isna(b) else b}"))
                if has_prj(combined):
                    score = sum(1 for v in combined if v.startswith('attributename') or ('attribute' in v and 'name' in v))
                    candidates.append((idx, 2, score))
        if not candidates:
            headers = [str(v) for v in raw.iloc[:min(scan_limit, 30)].fillna('').values.flatten() if str(v).strip()]
            raise ValueError("Prompt worksheet is missing required PRJID/PRJ ID/CFVID column. Detected values: " + ', '.join(headers[:120]))

        # Prefer a row that has an Attribute Name-like header, then choose a normal
        # one-row header over a merged two-row header when tied.
        idx, rows, _ = max(candidates, key=lambda x: (x[2], -x[1], -x[0]))
        if rows == 2:
            headers = []
            for a, b in zip(raw.iloc[idx].tolist(), raw.iloc[idx + 1].tolist()):
                av = '' if pd.isna(a) else str(a).strip()
                bv = '' if pd.isna(b) else str(b).strip()
                headers.append((av + (' ' if av and bv else '') + bv).strip())
            data = raw.iloc[idx + 2:].copy()
        else:
            headers = [str(x).strip() if pd.notna(x) else '' for x in raw.iloc[idx].tolist()]
            data = raw.iloc[idx + 1:].copy()
        data.columns = headers
        data = data.loc[:, [str(c).strip() != '' for c in data.columns]]
        return data.reset_index(drop=True)

    @staticmethod
    def normalise_prompt_columns(df):
        """Map Prompt Excel business headings to DB fields.

        Required business heading examples:
        - Attribute Name( to be Viewed on Historical and HITL)
        - Display Order(to be used in showing)
        - Section(to be used in PRJ UI)
        - Description (Proposed one-shot prompt) based on which PRJID will be Mapped (used in Scanning)
        """
        df = df.copy()
        df.columns = [str(c).replace('\xa0', ' ').replace('\u200b', '').replace('\n', ' ').strip() for c in df.columns]
        indexed = [(column, ExcelService._identifier(column)) for column in df.columns]

        def first(*predicates):
            for predicate in predicates:
                for column, ident in indexed:
                    if predicate(column, ident):
                        return column
            return None

        mapping = {
            'prj_id': first(lambda c,i: i in {'prjid','cfvid'} or i.startswith('prjid') or i.startswith('projectid')),
            'attribute_name': first(lambda c,i: i.startswith('attributename'), lambda c,i: 'attributename' in i, lambda c,i: ('attribute' in i and 'name' in i), lambda c,i: i.startswith('prjattribute')),
            'display_order': first(lambda c,i: i.startswith('displayorder')),
            'section': first(lambda c,i: i.startswith('section')),
            'sub_section': first(lambda c,i: i.startswith('subsection')),
            'data_type': first(lambda c,i: i.startswith('datatype')),
            'calculated_or_reported': first(lambda c,i: i.startswith('calculatedorreported')),
            'calculation_logic': first(lambda c,i: i.startswith('calculationlogic')),
            'segment': first(lambda c,i: i.startswith('segment')),
            'attribute_description': first(lambda c,i: i.startswith('description') or 'proposedoneshotprompt' in i or 'description' in i),
        }
        if not mapping['prj_id']:
            raise ValueError('Prompt worksheet is missing required PRJID/PRJ ID/CFVID column. Detected headers: ' + ', '.join(map(str, df.columns)))
        # Explicit business-header fallback. This covers spaces/punctuation variants such as
        # "Attribute Name( to be Viewed on Historical and HITL)".
        if not mapping['attribute_name']:
            for column, ident in indexed:
                printable = re.sub(r'[^a-z0-9]+', ' ', str(column).lower()).strip()
                if printable.startswith('attribute name') or 'attribute name' in printable:
                    mapping['attribute_name'] = column
                    break

        # Do not block the full preview only because a workbook uses an unexpected
        # attribute heading. Return an empty attribute_name with a mapping warning.
        # This enables the user to preview/validate headers and see the real sheet.
        output = pd.DataFrame({target: (df[column] if column else None) for target, column in mapping.items()})
        output['prj_id'] = output['prj_id'].astype(str).str.strip()
        output = output[(output['prj_id'] != '') & (output['prj_id'].str.lower() != 'nan')]
        mapping['_warning'] = None if mapping['attribute_name'] else "No Attribute Name-like column was matched. Preview was loaded; inspect the mapping before finalizing."
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
