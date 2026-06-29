from io import BytesIO
from typing import Any
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.datavalidation import DataValidation
from DataDictionaryAdminApp.utils.excel_mapping import (
    BOOLEAN_FIELDS,
    EXCEL_DATA_START_ROW,
    EXCEL_HEADER_ROW,
    EXCEL_TO_FIELD_MAPPING,
    FIELD_TO_EXCEL_MAPPING,
    MANDATORY_COLUMNS,
    MASTER_FIELDS,
)


class ExcelService:
    def generate_template(self, records: list[dict[str, Any]], template_version: str = "1.0") -> BytesIO:
        wb = Workbook()
        ws = wb.active
        ws.title = "Data Dictionary"
        ws["A1"] = "Data Dictionary Template"
        ws["A2"] = f"Template Version: {template_version}"
        headers = list(EXCEL_TO_FIELD_MAPPING.keys())

        for col_index, header in enumerate(headers, start=1):
            cell = ws.cell(row=EXCEL_HEADER_ROW, column=col_index)
            cell.value = header
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F4E78")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            ws.column_dimensions[cell.column_letter].width = 28

        yes_no_validation = DataValidation(type="list", formula1='"Yes,No,True,False,1,0"', allow_blank=True)
        ws.add_data_validation(yes_no_validation)

        for row_index, record in enumerate(records, start=EXCEL_DATA_START_ROW):
            for col_index, header in enumerate(headers, start=1):
                field = EXCEL_TO_FIELD_MAPPING[header]
                value = record.get(field)
                if field in BOOLEAN_FIELDS and value is not None:
                    value = "Yes" if bool(value) else "No"
                ws.cell(row=row_index, column=col_index).value = value

        for col_index, header in enumerate(headers, start=1):
            field = EXCEL_TO_FIELD_MAPPING[header]
            if field in BOOLEAN_FIELDS:
                yes_no_validation.add(
                    f"{ws.cell(row=EXCEL_DATA_START_ROW, column=col_index).coordinate}:"
                    f"{ws.cell(row=5000, column=col_index).coordinate}"
                )

        ws.freeze_panes = "A4"
        stream = BytesIO()
        wb.save(stream)
        stream.seek(0)
        return stream

    def parse_uploaded_file(self, file_bytes: bytes) -> list[dict[str, Any]]:
        """Parse master uploads in read-only streaming mode.

        Using ``iter_rows(values_only=True)`` avoids materialising every Excel cell
        object, which is materially faster for large workbooks.
        """
        wb = load_workbook(BytesIO(file_bytes), data_only=True, read_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        for _ in range(EXCEL_HEADER_ROW - 1):
            next(rows_iter, None)
        raw_headers = list(next(rows_iter, ()) or ())
        header_to_field = self._resolve_headers(raw_headers)
        self.validate_headers(list(header_to_field.keys()))
        column_fields = [header_to_field.get(self._canonical_header(h)) for h in raw_headers]

        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for values in rows_iter:
            record = {
                field: self._normalize_value(field, values[idx] if idx < len(values) else None)
                for idx, field in enumerate(column_fields) if field
            }
            prj_id = self._normalize_prj_id(record.get("prj_id"))
            if not prj_id:
                continue
            if prj_id in seen:
                raise ValueError(f"Duplicate PRJ ID in upload: {prj_id}")
            record["prj_id"] = prj_id
            seen.add(prj_id)
            for field in MASTER_FIELDS:
                record.setdefault(field, None)
            rows.append(record)
        wb.close()
        return rows

    def validate_headers(self, canonical_headers: list[str]) -> None:
        mandatory = {self._canonical_header(c) for c in MANDATORY_COLUMNS}
        present = set(canonical_headers)
        missing = [c for c in MANDATORY_COLUMNS if self._canonical_header(c) not in present]
        if missing:
            raise ValueError(f"Missing mandatory columns: {', '.join(missing)}")

    def _resolve_headers(self, raw_headers: list[Any]) -> dict[str, str]:
        mapping_by_canonical_header = {
            self._canonical_header(header): field
            for header, field in EXCEL_TO_FIELD_MAPPING.items()
        }

        resolved: dict[str, str] = {}
        for raw_header in raw_headers:
            canonical_header = self._canonical_header(raw_header)
            if canonical_header in mapping_by_canonical_header:
                resolved[canonical_header] = mapping_by_canonical_header[canonical_header]

        return resolved

    @staticmethod
    def _canonical_header(value: Any) -> str:
        if value is None:
            return ""
        return " ".join(str(value).replace("\xa0", " ").strip().split()).lower()

    @staticmethod
    def _normalize_prj_id(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return str(value).replace("\xa0", " ").strip()

    @staticmethod
    def _normalize_value(field_name: str, value: Any) -> Any:
        if field_name == "prj_id":
            return ExcelService._normalize_prj_id(value)

        if field_name in BOOLEAN_FIELDS:
            if value is None or str(value).strip() == "":
                return None
            normalized = str(value).strip().lower()
            if normalized in {"yes", "true", "1", "y"}:
                return True
            if normalized in {"no", "false", "0", "n"}:
                return False
        return value

    @staticmethod
    def to_excel_columns(records: list[dict[str, Any]]):
        return [{FIELD_TO_EXCEL_MAPPING.get(k, k): v for k, v in record.items() if k in FIELD_TO_EXCEL_MAPPING} for record in records]
