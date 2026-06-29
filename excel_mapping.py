EXCEL_HEADER_ROW = 3
EXCEL_DATA_START_ROW = 4

EXCEL_TO_FIELD_MAPPING = {
    "PRJ ID": "prj_id",
    "PRJ Attribute Name": "prj_attribute_name",
    "PRJ Attribute Description": "prj_attribute_description",
    "PRJ Physical Attribute Name": "prj_physical_attribute_name",
    "Editable?": "editable",
    "Calculated or Reported?": "calculated_or_reported",
    "Percentage(%) / Ratio(X)": "percentage_ratio",
    "Calculation Logic": "calculation_logic",
    "Calculation Logic Details": "calculation_logic_details",
    "Where in financial statement is this generally collected from ?": "where_in_financial_statement",
    "Required by corporates?": "required_by_corporates",
    "Required by banks ?": "required_by_banks",
    "Required by insurance?": "required_by_insurance",
    "Required by Downstream?": "required_by_downstream",
    "Version Update": "version_update",
    "Release Scope": "release_scope",
    "Mapping Type": "mapping_type",
    "Calculation in PRJ": "calculation_in_prj",
    "Calculated in CFV? (Y/N)": "calculation_in_prj",
    "Editable in Historicals": "editable_in_historicals",
    "Sign Flipping": "sign_flipping",
    "GC Template attribute name": "gc_template_attribute_name",
    "S&P Standradisation attribute name": "sp_standardisation_attribute_name",
    "S&P Standradisation dataitem id": "sp_standardisation_dataitem_id",
    "S&P As-Reported dataitem ID": "sp_as_reported_dataitem_id",
    "S&P As-Reported dataitem ID / logic": "sp_as_reported_dataitem_id",
    "Updates": "updates",
    "Updated ON": "updated_on",
    "Zeus attribute": "zeus_attribute",
    "Zeus table name": "zeus_table_name",
    "Zeus Description": "zeus_description",
    "Commnets": "comments",
    "SNL dataitemid": "snl_dataitemid",
    "Scanned/Calculated": "scanned_calculated",
}

FIELD_TO_EXCEL_MAPPING = {v: k for k, v in EXCEL_TO_FIELD_MAPPING.items()}
MANDATORY_COLUMNS = ["PRJ ID", "PRJ Attribute Name"]
BOOLEAN_FIELDS = {
    "editable",
    "required_by_corporates",
    "required_by_banks",
    "required_by_insurance",
    "required_by_downstream",
    "editable_in_historicals",
}
MASTER_FIELDS = list(EXCEL_TO_FIELD_MAPPING.values())
