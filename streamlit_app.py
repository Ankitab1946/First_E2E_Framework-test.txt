# import os
# import json
# from io import BytesIO
# from typing import Any
# from urllib.parse import quote

# import requests
# import pandas as pd
# import streamlit as st
# from streamlit_modal import Modal

# from DataDictionaryAdminApp.config import get_settings
# from DataDictionaryAdminApp.core.database import reset_database_cache
# from DataDictionaryAdminApp.service.audit_service import AuditService
# from DataDictionaryAdminApp.service.dictionary_service import DictionaryService
# from DataDictionaryAdminApp.service.excel_service import ExcelService
# from DataDictionaryAdminApp.service.finalization_service import FinalizationService
# from DataDictionaryAdminApp.service.s3_export_service import S3ExportService
# from DataDictionaryAdminApp.service.configuration_service import ConfigurationService
# from DataDictionaryAdminApp.utils.constants import LIMITED_DICTIONARY_FIELDS, PORTFOLIO_OPTIONS, SECTION_OPTIONS
# from DataDictionaryAdminApp.utils.excel_mapping import BOOLEAN_FIELDS, MASTER_FIELDS
# from DataDictionaryAdminApp.utils.sample_data import get_sample_records


# st.set_page_config(page_title="Data Dictionary Admin", layout="wide", initial_sidebar_state="expanded")


# def apply_modal_css() -> None:
#     """Make streamlit-modal dialogs centered and scrollable across laptop/monitor sizes."""
#     st.markdown(
#         """
#         <style>
#         /* streamlit-modal / common modal wrappers */
#         div[data-testid="stModal"],
#         div[data-modal-container="true"],
#         div[class*="modal"],
#         div[class*="Modal"] {
#             box-sizing: border-box;
#         }

#         /* Main dialog body: keep it centered and within viewport */
#         div[data-testid="stModal"] > div,
#         div[data-modal-container="true"] > div,
#         div[class*="modal-content"],
#         div[class*="ModalContent"],
#         div[class*="streamlit-modal"] {
#             position: fixed !important;
#             top: 50% !important;
#             left: 50% !important;
#             transform: translate(-50%, -50%) !important;
#             width: min(92vw, 1400px) !important;
#             max-width: 92vw !important;
#             max-height: 86vh !important;
#             overflow-y: auto !important;
#             overflow-x: hidden !important;
#             border-radius: 12px !important;
#             padding: 1rem 1.25rem !important;
#             z-index: 100000 !important;
#         }

#         /* Streamlit forms and blocks inside popup should not exceed modal height */
#         div[data-testid="stModal"] section,
#         div[data-testid="stModal"] div[data-testid="stVerticalBlock"],
#         div[data-modal-container="true"] section,
#         div[data-modal-container="true"] div[data-testid="stVerticalBlock"],
#         div[class*="modal-content"] section,
#         div[class*="modal-content"] div[data-testid="stVerticalBlock"] {
#             max-height: none !important;
#             overflow: visible !important;
#         }

#         /* Ensure long select boxes/text areas behave inside modal */
#         div[data-testid="stModal"] textarea,
#         div[data-testid="stModal"] input,
#         div[class*="modal-content"] textarea,
#         div[class*="modal-content"] input {
#             max-width: 100% !important;
#         }

#         @media (max-width: 900px) {
#             div[data-testid="stModal"] > div,
#             div[data-modal-container="true"] > div,
#             div[class*="modal-content"],
#             div[class*="ModalContent"],
#             div[class*="streamlit-modal"] {
#                 width: 96vw !important;
#                 max-width: 96vw !important;
#                 max-height: 90vh !important;
#                 padding: 0.75rem !important;
#             }
#         }
#         </style>
#         """,
#         unsafe_allow_html=True,
#     )



# def apply_sidebar_css() -> None:
#     """Keep sidebar clean, collapsible, and horizontally resizable in supported browsers."""
#     st.markdown(
#         """
#         <style>
#         section[data-testid="stSidebar"] {
#             resize: horizontal;
#             overflow: auto !important;
#             min-width: 260px !important;
#             max-width: 520px !important;
#         }
#         section[data-testid="stSidebar"] > div:first-child {
#             overflow-x: hidden;
#         }
#         div[data-testid="stSidebarCollapseButton"] {
#             visibility: visible !important;
#         }
#         </style>
#         """,
#         unsafe_allow_html=True,
#     )

# apply_modal_css()
# apply_sidebar_css()


# def current_user() -> str:
#     settings = get_settings()
#     return os.getenv("USERNAME") or os.getenv("USER") or settings.default_user


# def apply_selected_environment(environment_name: str) -> None:
#     """Apply selected environment details from .env into standard SQLSERVER_* variables."""
#     env_key = environment_name.upper().replace(" ", "_")
#     mapping = {
#         "SQLSERVER_SERVER": f"ENV_{env_key}_SQLSERVER_SERVER",
#         "SQLSERVER_DATABASE": f"ENV_{env_key}_SQLSERVER_DATABASE",
#         "SQLSERVER_WINDOWS_AUTH": f"ENV_{env_key}_SQLSERVER_WINDOWS_AUTH",
#         "SQLSERVER_USER": f"ENV_{env_key}_SQLSERVER_USER",
#         "SQLSERVER_PASSWORD": f"ENV_{env_key}_SQLSERVER_PASSWORD",
#         "ENABLE_DB": f"ENV_{env_key}_ENABLE_DB",
#     }
#     for target_name, source_name in mapping.items():
#         value = os.getenv(source_name)
#         if value not in (None, ""):
#             os.environ[target_name] = value
#     previous_environment = os.environ.get("SELECTED_ENVIRONMENT")
#     os.environ["SELECTED_ENVIRONMENT"] = environment_name.upper()
#     os.environ["APP_ENV"] = environment_name.upper()
#     get_settings.cache_clear()
#     if previous_environment and previous_environment.upper() != environment_name.upper():
#         reset_database_cache()
#         st.session_state.pop("dictionary_records_cache_key", None)
#         st.session_state.pop("dictionary_records_cache", None)


# def is_admin_user(user_id: str) -> bool:
#     """Return True when the current user has admin rights.

#     Local/dev mode can auto-enable admin actions through LOCAL_AUTO_ADMIN=true.
#     For controlled environments, set LOCAL_AUTO_ADMIN=false and maintain ADMIN_USERS.
#     Matching supports plain usernames, DOMAIN\\user values, and wildcard '*'.
#     """
#     settings = get_settings()
#     if settings.local_auto_admin and settings.selected_environment.upper() in {"LOCAL", "DEV"}:
#         return True

#     admin_users = settings.admin_user_list
#     normalized_user = (user_id or settings.default_user or "sysuser").strip().lower()
#     short_user = normalized_user.split("\\")[-1]

#     return (
#         "*" in admin_users
#         or normalized_user in admin_users
#         or short_user in admin_users
#     )


# def normalize_bool(value: Any) -> bool | None:
#     if value is None or value == "":
#         return None
#     if isinstance(value, bool):
#         return value
#     return str(value).strip().lower() in {"true", "1", "yes", "y"}


# def records_to_df(records: list[dict], limited: bool = False) -> pd.DataFrame:
#     fields = LIMITED_DICTIONARY_FIELDS if limited else MASTER_FIELDS
#     if not records:
#         return pd.DataFrame(columns=fields)
#     df = pd.DataFrame(records)
#     for field in fields:
#         if field not in df.columns:
#             df[field] = None
#     extra_cols = [c for c in ["delta_type", "changed_fields", "is_active", "version_no", "created_at", "updated_at"] if c in df.columns]
#     return df[fields + extra_cols]


# def df_to_records(df: pd.DataFrame) -> list[dict]:
#     return df.where(pd.notnull(df), None).to_dict(orient="records")



# def call_api_post(endpoint: str, payload: dict, timeout: int = 30) -> dict:
#     settings = get_settings()
#     base_url = (settings.api_base_url or "").rstrip("/")
#     # Streamlit normally runs on 8501; the FastAPI/Swagger service runs on 8502.
#     # If a copied .env accidentally points API_BASE_URL to 8501, correct it here
#     # to avoid calling Streamlit's internal endpoints and receiving 403 Forbidden.
#     if base_url.startswith("http://localhost:8501") or base_url.startswith("http://127.0.0.1:8501"):
#         base_url = base_url.replace(":8501", ":8502", 1)
#     if not base_url:
#         raise RuntimeError("API_BASE_URL is not configured.")
#     response = requests.post(
#         f"{base_url}{endpoint}",
#         json=payload,
#         headers={"X-User-Id": current_user()},
#         timeout=timeout,
#     )
#     response.raise_for_status()
#     return response.json()


# def safe_filter_records(dictionary_service: DictionaryService, filters: dict) -> list[dict]:
#     """Fetch Data Dictionary records through Swagger API filters when available.

#     If the FastAPI process is not running, the app falls back to the existing
#     in-process service so current edit/add/delete/S3 workflows remain usable.
#     """
#     settings = get_settings()
#     if settings.use_api_for_filters:
#         try:
#             api_result = call_api_post("/dictionary/filter", filters)
#             return api_result.get("records", [])
#         except Exception as exc:
#             st.warning(f"Filter API is not available. Falling back to local service. Details: {exc}")
#     try:
#         return dictionary_service.filter_records(filters)
#     except Exception as exc:
#         st.warning(f"Could not fetch filtered records from configured database. Showing sample data. Details: {exc}")
#         fallback = DictionaryService()
#         fallback.settings.enable_db = False
#         return fallback.filter_records(filters)


# def _cache_key(payload: dict) -> str:
#     """Stable cache key for Streamlit session-state data caches."""
#     return json.dumps(payload, sort_keys=True, default=str)


# def invalidate_dictionary_cache() -> None:
#     """Force the next grid render to reload records from API/DB."""
#     st.session_state.pop("dictionary_records_cache_key", None)
#     st.session_state.pop("dictionary_records_cache", None)


# def disable_submit_button(state_key: str) -> None:
#     """Disable a submit button immediately after the first click."""
#     if state_key:
#         st.session_state[state_key] = True


# def reset_create_submit_state(scope: str) -> None:
#     st.session_state[f"create_attribute_{scope}_submit_disabled"] = False


# def clear_generated_create_prj_id(scope: str) -> None:
#     st.session_state.pop(f"create_attribute_{scope}_generated_prj_id", None)


# def get_or_generate_create_prj_id(dictionary_service: DictionaryService, scope: str) -> str:
#     """Use one generated PRJ ID per create form instance until create succeeds/cancels."""
#     state_key = f"create_attribute_{scope}_generated_prj_id"
#     existing_value = str(st.session_state.get(state_key) or "").strip()
#     if existing_value:
#         return existing_value
#     try:
#         generated_prj_id = dictionary_service.generate_next_prj_id()
#     except Exception as exc:
#         st.warning(f"Could not generate PRJ ID from database. Using sample fallback. Details: {exc}")
#         generated_prj_id = DictionaryService._generate_next_prj_id_from_values(
#             [record.get("prj_id") for record in get_sample_records()]
#         )
#     st.session_state[state_key] = generated_prj_id
#     return generated_prj_id


# def get_cached_filter_records(
#     dictionary_service: DictionaryService,
#     filters: dict,
#     force_refresh: bool = False,
# ) -> list[dict]:
#     """Return filtered records without re-calling API/DB on every Streamlit rerun.

#     This makes modal open/close actions fast because they no longer reload the
#     main grid unless filters changed or a write operation invalidated the cache.
#     """
#     key = _cache_key({
#         "filters": filters,
#         "env": get_settings().selected_environment,
#         "api_base_url": get_settings().api_base_url,
#         "enable_db": get_settings().enable_db,
#     })
#     if (
#         not force_refresh
#         and st.session_state.get("dictionary_records_cache_key") == key
#         and "dictionary_records_cache" in st.session_state
#     ):
#         return st.session_state.dictionary_records_cache

#     records = safe_filter_records(dictionary_service, filters)
#     st.session_state.dictionary_records_cache_key = key
#     st.session_state.dictionary_records_cache = records
#     return records


# def safe_filter_audit(audit_service: AuditService, filters: dict) -> list[dict]:
#     settings = get_settings()
#     if settings.use_api_for_filters:
#         try:
#             api_result = call_api_post("/audit/filter", filters)
#             return api_result.get("records", [])
#         except Exception as exc:
#             st.warning(f"Audit Filter API is not available. Falling back to local service. Details: {exc}")
#     return audit_service.filter_audit(filters)

# def safe_search_records(dictionary_service: DictionaryService, term: str = "", portfolio: str = "ALL", section: str = "") -> list[dict]:
#     """Load records without leaving the main grid blank because of connection/config issues.

#     In DB-enabled mode the DB remains the primary source. If the DB call fails, the UI
#     shows sample records plus a warning so users can still verify screens/buttons.
#     """
#     try:
#         return dictionary_service.search_records(term=term, portfolio=portfolio, section=section)
#     except Exception as exc:
#         st.warning(f"Could not fetch records from configured database. Showing sample data. Details: {exc}")
#         records = get_sample_records()
#         portfolio_field_map = {
#             "FI Banks": "required_by_banks",
#             "Corporates": "required_by_corporates",
#             "FI Insurance": "required_by_insurance",
#             "Zeus Downstream": "required_by_downstream",
#         }
#         field_name = portfolio_field_map.get(portfolio)
#         if field_name:
#             records = [record for record in records if bool(record.get(field_name))]
#         if section:
#             records = [record for record in records if record.get("where_in_financial_statement") == section]
#         if term:
#             term_lower = term.lower()
#             records = [
#                 record for record in records
#                 if term_lower in str(record.get("prj_id", "")).lower()
#                 or term_lower in str(record.get("prj_attribute_name", "")).lower()
#                 or term_lower in str(record.get("prj_attribute_description", "")).lower()
#             ]
#         return records




# def safe_soft_deleted_records(dictionary_service: DictionaryService) -> list[dict]:
#     """Load inactive master records for reactivate workflow without breaking the UI."""
#     try:
#         return dictionary_service.get_soft_deleted_records()
#     except Exception as exc:
#         st.warning(f"Could not fetch soft deleted records from configured database. Details: {exc}")
#         return []


# def get_selected_prj_id_from_grid(selection_event, grid_records: list[dict]) -> str:
#     """Return PRJ ID selected from a Streamlit dataframe selection event.

#     Streamlit reruns the script after row selection. This helper keeps the UI
#     independent of a separate dropdown and uses the selected row from the grid.
#     """
#     try:
#         selected_rows = selection_event.selection.rows
#     except Exception:
#         try:
#             selected_rows = selection_event.get("selection", {}).get("rows", [])
#         except Exception:
#             selected_rows = []

#     if not selected_rows:
#         return ""

#     selected_index = selected_rows[0]
#     if selected_index is None or selected_index >= len(grid_records):
#         return ""

#     return str(grid_records[selected_index].get("prj_id") or "").strip()


# def boolean_label(value: bool | None) -> str:
#     if value is None:
#         return ""
#     return "Yes" if bool(value) else "No"


# def get_existing_value(record: dict | None, field: str, default=None):
#     if not record:
#         return default
#     return record.get(field, default)


# def build_attribute_form(
#     record: dict | None = None,
#     read_only: bool = False,
#     mode: str = "CREATE",
#     generated_prj_id: str | None = None,
#     submit_disabled_key: str | None = None,
# ) -> dict:
#     is_create_mode = mode == "CREATE"
#     disabled_prj = read_only or mode in {"CREATE", "EDIT"}
#     disabled = read_only
#     key_prefix = f"attribute_{mode.lower()}_{'readonly' if read_only else 'editable'}"
#     prj_id_value = (
#         generated_prj_id
#         if is_create_mode and generated_prj_id
#         else str(get_existing_value(record, "prj_id", "") or "")
#     )

#     with st.form(f"{mode.lower()}_attribute_form_{'readonly' if read_only else 'editable'}"):
#         if is_create_mode:
#             # PRJ ID is generated server-side and intentionally hidden on Create New Attribute screens.
#             prj_id = str(prj_id_value or "")
#             c2, c3 = st.columns(2)
#         else:
#             c1, c2, c3 = st.columns(3)
#             with c1:
#                 prj_id = st.text_input("PRJ ID *", value=str(prj_id_value or ""), disabled=disabled_prj, key=f"{key_prefix}_prj_id")
#         with c2:
#             prj_attribute_name = st.text_input(
#                 "Attribute Name *",
#                 value=str(get_existing_value(record, "prj_attribute_name", "") or ""),
#                 disabled=disabled,
#                 key=f"{key_prefix}_attribute_name",
#             )
#         with c3:
#             current_section = get_existing_value(record, "where_in_financial_statement", SECTION_OPTIONS[0]) or SECTION_OPTIONS[0]
#             if current_section not in SECTION_OPTIONS:
#                 current_section = SECTION_OPTIONS[0]
#             where_in_financial_statement = st.selectbox(
#                 "Section / Where in financial statement *",
#                 SECTION_OPTIONS,
#                 index=SECTION_OPTIONS.index(current_section),
#                 disabled=disabled,
#                 key=f"{key_prefix}_section",
#             )

#         prj_attribute_description = st.text_area(
#             "PRJ Attribute Description",
#             value=str(get_existing_value(record, "prj_attribute_description", "") or ""),
#             disabled=disabled,
#             key=f"{key_prefix}_description",
#         )
#         c4, c5, c6 = st.columns(3)
#         with c4:
#             prj_physical_attribute_name = st.text_input(
#                 "PRJ Physical Attribute Name",
#                 value=str(get_existing_value(record, "prj_physical_attribute_name", "") or ""),
#                 disabled=disabled,
#                 key=f"{key_prefix}_physical_name",
#             )
#             percentage_ratio = st.text_input(
#                 "Percentage(%) / Ratio(X)",
#                 value=str(get_existing_value(record, "percentage_ratio", "") or ""),
#                 disabled=disabled,
#                 key=f"{key_prefix}_percentage_ratio",
#             )
#             version_update = st.text_input(
#                 "Version Update",
#                 value=str(get_existing_value(record, "version_update", "") or ""),
#                 disabled=disabled,
#                 key=f"{key_prefix}_version_update",
#             )
#         with c5:
#             editable = st.checkbox("Editable?", value=bool(get_existing_value(record, "editable", False)), disabled=disabled, key=f"{key_prefix}_editable")
#             required_by_corporates = st.checkbox(
#                 "Required by Corporates?",
#                 value=bool(get_existing_value(record, "required_by_corporates", False)),
#                 disabled=disabled,
#                 key=f"{key_prefix}_required_by_corporates",
#             )
#             required_by_banks = st.checkbox(
#                 "Required by FI Banks?",
#                 value=bool(get_existing_value(record, "required_by_banks", False)),
#                 disabled=disabled,
#                 key=f"{key_prefix}_required_by_banks",
#             )
#         with c6:
#             required_by_insurance = st.checkbox(
#                 "Required by FI Insurance?",
#                 value=bool(get_existing_value(record, "required_by_insurance", False)),
#                 disabled=disabled,
#                 key=f"{key_prefix}_required_by_insurance",
#             )
#             required_by_downstream = st.checkbox(
#                 "Required by Zeus Downstream?",
#                 value=bool(get_existing_value(record, "required_by_downstream", False)),
#                 disabled=disabled,
#                 key=f"{key_prefix}_required_by_downstream",
#             )
#             editable_in_historicals = st.checkbox(
#                 "Editable in Historicals",
#                 value=bool(get_existing_value(record, "editable_in_historicals", False)),
#                 disabled=disabled,
#                 key=f"{key_prefix}_editable_in_historicals",
#             )

#         with st.expander("Additional Master / Business Logic Fields", expanded=False):
#             a1, a2, a3 = st.columns(3)
#             with a1:
#                 release_scope = st.text_input("Release Scope", value=str(get_existing_value(record, "release_scope", "") or ""), disabled=disabled, key=f"{key_prefix}_release_scope")
#                 mapping_type = st.text_input("Mapping Type", value=str(get_existing_value(record, "mapping_type", "") or ""), disabled=disabled, key=f"{key_prefix}_mapping_type")
#                 calculation_in_prj = st.text_input("Calculation in PRJ", value=str(get_existing_value(record, "calculation_in_prj", "") or ""), disabled=disabled, key=f"{key_prefix}_calculation_in_prj")
#                 sign_flipping = st.checkbox("Sign Flipping", value=bool(get_existing_value(record, "sign_flipping", False)), disabled=disabled, key=f"{key_prefix}_sign_flipping")
#             with a2:
#                 gc_template_attribute_name = st.text_input("GC Template attribute name", value=str(get_existing_value(record, "gc_template_attribute_name", "") or ""), disabled=disabled, key=f"{key_prefix}_gc_template_attribute_name")
#                 sp_standardisation_attribute_name = st.text_input("S&P Standardisation attribute name", value=str(get_existing_value(record, "sp_standardisation_attribute_name", "") or ""), disabled=disabled, key=f"{key_prefix}_sp_standardisation_attribute_name")
#                 sp_standardisation_dataitem_id = st.text_input("S&P Standardisation dataitem id", value=str(get_existing_value(record, "sp_standardisation_dataitem_id", "") or ""), disabled=disabled, key=f"{key_prefix}_sp_standardisation_dataitem_id")
#                 sp_as_reported_dataitem_id = st.text_input("S&P As-Reported dataitem ID", value=str(get_existing_value(record, "sp_as_reported_dataitem_id", "") or ""), disabled=disabled, key=f"{key_prefix}_sp_as_reported_dataitem_id")
#             with a3:
#                 zeus_attribute = st.text_input("Zeus attribute", value=str(get_existing_value(record, "zeus_attribute", "") or ""), disabled=disabled, key=f"{key_prefix}_zeus_attribute")
#                 zeus_table_name = st.text_input("Zeus table name", value=str(get_existing_value(record, "zeus_table_name", "") or ""), disabled=disabled, key=f"{key_prefix}_zeus_table_name")
#                 snl_dataitemid = st.text_input("SNL dataitemid", value=str(get_existing_value(record, "snl_dataitemid", "") or ""), disabled=disabled, key=f"{key_prefix}_snl_dataitemid")
#                 scanned_calculated = st.text_input("Scanned/Calculated", value=str(get_existing_value(record, "scanned_calculated", "") or ""), disabled=disabled, key=f"{key_prefix}_scanned_calculated")
#             calculation_logic = st.text_area("Calculation Logic", value=str(get_existing_value(record, "calculation_logic", "") or ""), disabled=disabled, key=f"{key_prefix}_calculation_logic")
#             updates = st.text_area("Updates", value=str(get_existing_value(record, "updates", "") or ""), disabled=disabled, key=f"{key_prefix}_updates")
#             zeus_description = st.text_area("Zeus Description", value=str(get_existing_value(record, "zeus_description", "") or ""), disabled=disabled, key=f"{key_prefix}_zeus_description")
#             comments = st.text_area("Comments", value=str(get_existing_value(record, "comments", "") or ""), disabled=disabled, key=f"{key_prefix}_comments")

#         submit_disabled = read_only or bool(submit_disabled_key and st.session_state.get(submit_disabled_key, False))
#         submitted = st.form_submit_button(
#             "Create Attribute" if mode == "CREATE" else "Upload",
#             disabled=submit_disabled,
#             on_click=disable_submit_button if submit_disabled_key else None,
#             args=(submit_disabled_key,) if submit_disabled_key else None,
#         )

#     return {
#         "submitted": submitted,
#         "record": {
#             "prj_id": prj_id.strip(),
#             "prj_attribute_name": prj_attribute_name.strip(),
#             "prj_attribute_description": prj_attribute_description,
#             "prj_physical_attribute_name": prj_physical_attribute_name,
#             "editable": editable,
#             "percentage_ratio": percentage_ratio,
#             "calculation_logic": calculation_logic,
#             "where_in_financial_statement": where_in_financial_statement,
#             "required_by_corporates": required_by_corporates,
#             "required_by_banks": required_by_banks,
#             "required_by_insurance": required_by_insurance,
#             "required_by_downstream": required_by_downstream,
#             "version_update": version_update,
#             "release_scope": release_scope,
#             "mapping_type": mapping_type,
#             "calculation_in_prj": calculation_in_prj,
#             "editable_in_historicals": editable_in_historicals,
#             "sign_flipping": sign_flipping,
#             "gc_template_attribute_name": gc_template_attribute_name,
#             "sp_standardisation_attribute_name": sp_standardisation_attribute_name,
#             "sp_standardisation_dataitem_id": sp_standardisation_dataitem_id,
#             "sp_as_reported_dataitem_id": sp_as_reported_dataitem_id,
#             "updates": updates,
#             "updated_on": None,
#             "zeus_attribute": zeus_attribute,
#             "zeus_table_name": zeus_table_name,
#             "zeus_description": zeus_description,
#             "comments": comments,
#             "snl_dataitemid": snl_dataitemid,
#             "scanned_calculated": scanned_calculated,
#         },
#     }


# def validate_attribute_payload(payload: dict) -> list[str]:
#     errors: list[str] = []
#     if not payload.get("prj_id"):
#         errors.append("PRJ ID is mandatory.")
#     if not payload.get("prj_attribute_name"):
#         errors.append("Attribute Name is mandatory.")
#     if not payload.get("where_in_financial_statement"):
#         errors.append("Section / Where in financial statement is mandatory.")
#     return errors


# def init_state():
#     defaults = {
#         "dictionary_records": [],
#         "selected_portfolio": "ALL",
#         "create_mode": False,
#         "selected_record": None,
#         "selected_active_prj_id": "",
#         "edit_mode": False,
#         "open_create_modal": False,
#         "open_edit_modal": False,
#         "last_result": None,
#         "last_s3_result": None,
#         "show_soft_deleted": False,
#         "selected_user_role": "Admin",
#         "dictionary_records_cache_key": "",
#         "dictionary_records_cache": [],
#         "force_refresh_records": False,
#         "create_attribute_modal_submit_disabled": False,
#         "create_attribute_page_submit_disabled": False,
#     }
#     for key, value in defaults.items():
#         st.session_state.setdefault(key, value)


# def get_query_param(name: str, default: str = "") -> str:
#     """Read a Streamlit query parameter safely across Streamlit versions."""
#     try:
#         value = st.query_params.get(name, default)
#     except Exception:
#         value = default
#     if isinstance(value, list):
#         return str(value[0]) if value else default
#     return str(value or default)


# def clear_popup_state() -> None:
#     """Reset modal state so closed popups do not reopen during Streamlit reruns."""
#     st.session_state.create_mode = False
#     st.session_state.edit_mode = False
#     st.session_state.open_create_modal = False
#     st.session_state.open_edit_modal = False
#     reset_create_submit_state("modal")
#     reset_create_submit_state("page")
#     clear_generated_create_prj_id("modal")


# def new_window_link(label: str, href: str) -> None:
#     """Render a browser-tab link because Streamlit modals are not native resizable windows."""
#     html = (
#         f'<a href="{href}" target="_blank" rel="noopener noreferrer">'
#         f'<button style="border:1px solid #ccc;border-radius:6px;padding:0.45rem 0.75rem;'
#         f'background:#fff;cursor:pointer;">{label}</button></a>'
#     )
#     st.markdown(html, unsafe_allow_html=True)


# def render_create_attribute_page(dictionary_service: DictionaryService, finalization_service: FinalizationService, user_id: str, admin: bool) -> None:
#     st.title("Create New Attribute")
#     st.caption("This page is opened in a separate browser tab. Resize the browser window as needed.")
#     st.markdown("[Back to Data Dictionary](./)", unsafe_allow_html=True)
#     if not admin:
#         st.error("Only Admin users can create attributes.")
#         return
#     generated_prj_id = get_or_generate_create_prj_id(dictionary_service, "page")
#     form_result = build_attribute_form(
#         record=None,
#         read_only=False,
#         mode="CREATE",
#         generated_prj_id=generated_prj_id,
#         submit_disabled_key="create_attribute_page_submit_disabled",
#     )
#     if form_result["submitted"]:
#         payload = form_result["record"]
#         payload["prj_id"] = generated_prj_id
#         errors = validate_attribute_payload(payload)
#         if errors:
#             reset_create_submit_state("page")
#             for error in errors:
#                 st.error(error)
#         else:
#             try:
#                 result = finalization_service.create_attribute(payload, user_id=user_id)
#                 result = {**result, "created_prj_id": generated_prj_id}
#                 clear_generated_create_prj_id("page")
#                 st.success(f"Attribute created successfully. PRJ ID created: {generated_prj_id}. Batch ID: {result['batch_id']}")
#                 st.json(result)
#             except Exception as exc:
#                 reset_create_submit_state("page")
#                 st.error(f"Create failed: {exc}")


# def render_edit_attribute_page(
#     dictionary_service: DictionaryService,
#     finalization_service: FinalizationService,
#     user_id: str,
#     admin: bool,
#     prj_id: str,
# ) -> None:
#     st.title("Edit Attribute")
#     st.caption("This page is opened in a separate browser tab. Resize the browser window as needed.")
#     st.markdown("[Back to Data Dictionary](./)", unsafe_allow_html=True)
#     if not prj_id:
#         st.error("PRJ ID is required to open the edit page.")
#         return
#     records = safe_search_records(dictionary_service, term=prj_id, portfolio="ALL")
#     selected_record = next((r for r in records if str(r.get("prj_id")) == str(prj_id)), None)
#     if not selected_record:
#         st.error(f"No record found for PRJ ID: {prj_id}")
#         return
#     if not admin:
#         st.warning("You are in VIEWER mode. The record is displayed in read-only mode.")
#         build_attribute_form(record=selected_record, read_only=True, mode="EDIT")
#         return

#     st.session_state.setdefault("full_page_edit_enabled", False)
#     c1, c2 = st.columns([1, 5])
#     with c1:
#         if st.button("Edit", key="full_page_enable_edit"):
#             st.session_state.full_page_edit_enabled = True
#             st.rerun()
#     read_only = not st.session_state.full_page_edit_enabled
#     form_result = build_attribute_form(record=selected_record, read_only=read_only, mode="EDIT")
#     if form_result["submitted"]:
#         payload = form_result["record"]
#         payload["prj_id"] = prj_id
#         errors = validate_attribute_payload(payload)
#         if errors:
#             for error in errors:
#                 st.error(error)
#         else:
#             try:
#                 result = finalization_service.update_attribute(payload, user_id=user_id)
#                 st.session_state.full_page_edit_enabled = False
#                 st.success(f"Attribute updated. Batch ID: {result['batch_id']}")
#                 st.json(result)
#             except Exception as exc:
#                 st.error(f"Update failed: {exc}")


# # Environment selector must run before services are created.
# base_settings = get_settings()
# with st.sidebar:
#     st.subheader("Configuration")
#     env_names = base_settings.environment_names or ["LOCAL"]
#     selected_env = st.selectbox(
#         "Environment",
#         env_names,
#         index=env_names.index(base_settings.selected_environment) if base_settings.selected_environment in env_names else 0,
#         key="sidebar_environment_selector",
#     )
#     apply_selected_environment(selected_env)

# settings = get_settings()
# init_state()
# user_id = current_user()
# admin = is_admin_user(user_id)

# dictionary_service = DictionaryService()
# excel_service = ExcelService()
# finalization_service = FinalizationService()
# audit_service = AuditService()
# s3_export_service = S3ExportService()

# page_mode = get_query_param("page")
# if page_mode == "create_attribute":
#     render_create_attribute_page(dictionary_service, finalization_service, user_id=user_id, admin=admin)
#     st.stop()
# elif page_mode == "edit_attribute":
#     render_edit_attribute_page(
#         dictionary_service=dictionary_service,
#         finalization_service=finalization_service,
#         user_id=user_id,
#         admin=admin,
#         prj_id=get_query_param("prj_id"),
#     )
#     st.stop()

# create_attribute_modal = Modal("Create New Attribute", key="create_attribute_modal", max_width=1400)
# edit_attribute_modal = Modal("Edit Attribute", key="edit_attribute_modal", max_width=1400)

# with st.sidebar:
#     role_options = ["Admin", "User"]
#     default_role = st.session_state.get("selected_user_role") or ("Admin" if admin else "User")
#     if default_role not in role_options:
#         default_role = "Admin" if admin else "User"

#     selected_user_role = st.selectbox(
#         "Role",
#         role_options,
#         index=role_options.index(default_role),
#         key="sidebar_role_dropdown",
#         help="Upload Document section is visible only when Role is Admin and the current user has admin permission.",
#     )
#     st.session_state.selected_user_role = selected_user_role
#     upload_document_visible = admin and selected_user_role == "Admin"

#     st.markdown("**Server Details**")
#     st.caption(f"Server: `{settings.sqlserver_server}`")
#     st.caption(f"Database: `{settings.sqlserver_database}`")

#     if st.button("Refresh Data", key="sidebar_refresh_data_button", use_container_width=True):
#         invalidate_dictionary_cache()
#         st.session_state.force_refresh_records = True
#         st.success("Data refresh requested")

# st.title("Data Dictionary Management Admin")
# st.caption("Enhanced Python-only Streamlit version with role-based upload, environment selection, audit search, create/edit, and S3 export.")
# st.info("Popup forms can be closed safely. For a resizable browser window, use the Open in New Window buttons.")

# if not admin:
#     st.warning("You are in VIEWER mode. Create/Edit/Upload Document/S3 export actions are available only for configured Admin users.")
# elif st.session_state.get("selected_user_role") != "Admin":
#     st.info("Role is set to User. Upload Document section is hidden. Switch Role to Admin to view Upload Document.")

# tab_dictionary, tab_ui_display, tab_business_rules, tab_prompts, tab_audit = st.tabs(["Data Dictionary", "UI Display Configuration", "Business Rules", "Prompt Management", "Audit History"])

# with tab_dictionary:
#     st.header("Data Dictionary")
#     st.caption("Filters call the Swagger API endpoint `/api/v1/dictionary/filter`. If the API process is not running, the app falls back to local service logic.")

#     f1, f2, f3 = st.columns(3)
#     with f1:
#         selected_portfolios = st.multiselect(
#             "Portfolio",
#             PORTFOLIO_OPTIONS,
#             default=[st.session_state.selected_portfolio] if st.session_state.selected_portfolio in PORTFOLIO_OPTIONS else ["ALL"],
#             key="dictionary_filter_portfolio",
#         )
#         if not selected_portfolios:
#             selected_portfolios = ["ALL"]
#         if "ALL" in selected_portfolios and len(selected_portfolios) > 1:
#             selected_portfolios = [p for p in selected_portfolios if p != "ALL"]
#         overlapped_attribute = st.checkbox(
#             "Overlapped Attribute",
#             value=False,
#             help="Shows attributes required by more than one portfolio/sector.",
#             key="dictionary_filter_overlapped_attribute",
#         )
#     with f2:
#         filter_prj_id = st.text_input("PRJ_ID", value="", key="dictionary_filter_prj_id")
#         filter_attribute_name = st.text_input("Attribute Name", value="", key="dictionary_filter_attribute_name")
#     with f3:
#         filter_attribute_description = st.text_input("Attribute Description", value="", key="dictionary_filter_attribute_description")
#         filter_section = st.selectbox("Section / Where in financial statement", [""] + SECTION_OPTIONS, key="dictionary_filter_section")

#     portfolio = selected_portfolios[0] if len(selected_portfolios) == 1 else "ALL"
#     st.session_state.selected_portfolio = portfolio

#     dictionary_filters = {
#         "portfolios": selected_portfolios,
#         "portfolio_sector": selected_portfolios,
#         "prj_id": filter_prj_id,
#         "attribute_name": filter_attribute_name,
#         "attribute_description": filter_attribute_description,
#         "section": filter_section,
#         "overlapped_attribute": overlapped_attribute,
#         "active_only": True,
#         "limit": 2000,
#     }
#     force_refresh_records = bool(st.session_state.pop("force_refresh_records", False))
#     records = get_cached_filter_records(
#         dictionary_service,
#         dictionary_filters,
#         force_refresh=force_refresh_records,
#     )
#     search_text = filter_prj_id or filter_attribute_name or filter_attribute_description
#     st.session_state.dictionary_records = records
#     df = records_to_df(records, limited=True)

#     st.subheader("Latest Master Dictionary Records")
#     st.caption("Select one row from the grid, then use View/Edit or Soft Delete. No separate PRJ ID dropdown is required.")
#     active_selection = st.dataframe(
#         df,
#         use_container_width=True,
#         height=430,
#         key="active_dictionary_records_grid",
#         on_select="rerun",
#         selection_mode="single-row",
#     )
#     selected_active_prj_id = get_selected_prj_id_from_grid(active_selection, records)
#     if not selected_active_prj_id:
#         previous_selected_prj_id = str(st.session_state.get("selected_active_prj_id") or "").strip()
#         if previous_selected_prj_id and any(str(r.get("prj_id")) == previous_selected_prj_id for r in records):
#             selected_active_prj_id = previous_selected_prj_id

#     selected_active_record = next((r for r in records if str(r.get("prj_id")) == str(selected_active_prj_id)), None) if selected_active_prj_id else None
#     st.session_state.selected_active_prj_id = selected_active_prj_id
#     st.session_state.selected_record = selected_active_record

#     if selected_active_prj_id:
#         st.success(f"Selected PRJ ID: {selected_active_prj_id}")
#     elif not df.empty:
#         st.info("Select a row from the grid to enable View/Edit and Soft Delete.")

#     if df.empty:
#         st.info("No records found for the selected portfolio/search. Try Portfolio/Sector = ALL or Refresh Data.")

#     action_cols = st.columns([1.2, 1.6, 1.2, 1.2, 3])
#     with action_cols[0]:
#         if st.button("Add New Attribute"):
#             if not admin:
#                 st.error("Only Admin users can create attributes.")
#                 st.stop()
#             st.session_state.create_mode = True
#             st.session_state.selected_record = None
#             st.session_state.edit_mode = False
#             reset_create_submit_state("modal")
#             clear_generated_create_prj_id("modal")
#             st.session_state.open_create_modal = True
#             create_attribute_modal.open()
#     with action_cols[1]:
#         new_window_link("Open Create in New Window", "?page=create_attribute")
#     with action_cols[2]:
#         stream = excel_service.generate_template(records, settings.excel_template_version)
#         st.download_button(
#             "Download Excel",
#             data=stream.getvalue(),
#             file_name=f"data_dictionary_{portfolio.replace(' ', '_')}.xlsx",
#             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         )
#     with action_cols[3]:
#         if st.button("Save Extracts to S3"):
#             if not admin:
#                 st.error("Only Admin users can export extracts to S3.")
#                 st.stop()
#             try:
#                 st.session_state.last_s3_result = s3_export_service.export_four_files(user_id)
#                 st.success("S3 export completed or simulated.")
#             except Exception as exc:
#                 st.error(f"S3 export failed: {exc}")

#     if upload_document_visible:
#         with st.expander("Upload Document", expanded=False):
#             uploaded_file = st.file_uploader("Upload predefined Data Dictionary Excel file", type=["xlsx"])
#             if uploaded_file is not None:
#                 try:
#                     uploaded_records = excel_service.parse_uploaded_file(uploaded_file.getvalue())
#                     st.success(f"Uploaded file parsed successfully. Rows parsed: {len(uploaded_records)}")
#                     uploaded_df = records_to_df(uploaded_records)
#                     preview_limit = 500
#                     if len(uploaded_df) > preview_limit:
#                         st.info(f"Fast-load mode: previewing the first {preview_limit:,} rows of {len(uploaded_df):,}. The full parsed workbook will be uploaded.")
#                         edited_upload_df = st.data_editor(uploaded_df.head(preview_limit), use_container_width=True, height=350, num_rows="dynamic")
#                     else:
#                         edited_upload_df = st.data_editor(uploaded_df, use_container_width=True, height=350, num_rows="dynamic")
#                     if st.button("Upload Parsed Document to DB", type="primary"):
#                         upload_records = [
#                             {**row, "delta_type": "UPDATED"}
#                             for row in (uploaded_records if len(uploaded_df) > preview_limit else df_to_records(edited_upload_df))
#                             if row.get("prj_id")
#                         ]
#                         result = finalization_service.finalize(upload_records, user_id=user_id, source_module="UPLOAD_DOCUMENT")
#                         st.session_state.last_result = result
#                         st.success(f"Upload completed. Batch ID: {result['batch_id']}")
#                 except Exception as exc:
#                     st.error(f"Upload validation failed: {exc}")

#     if st.session_state.last_s3_result:
#         with st.expander("Last S3 Export Result", expanded=False):
#             st.json(st.session_state.last_s3_result)

#     if create_attribute_modal.is_open():
#         with create_attribute_modal.container():
#             st.subheader("Create New Attribute")
#             st.caption("Enter master attribute details. Mandatory fields are marked with *. Use Close to dismiss; it will not reopen until you click Add New Attribute again.")
#             close_cols = st.columns([1, 5])
#             with close_cols[0]:
#                 if st.button("Close", key="close_create_modal"):
#                     clear_popup_state()
#                     create_attribute_modal.close()
#                     st.stop()

#             generated_prj_id = get_or_generate_create_prj_id(dictionary_service, "modal")
#             form_result = build_attribute_form(
#                 record=None,
#                 read_only=False,
#                 mode="CREATE",
#                 generated_prj_id=generated_prj_id,
#                 submit_disabled_key="create_attribute_modal_submit_disabled",
#             )
#             if form_result["submitted"]:
#                 payload = form_result["record"]
#                 payload["prj_id"] = generated_prj_id
#                 errors = validate_attribute_payload(payload)
#                 if errors:
#                     reset_create_submit_state("modal")
#                     for error in errors:
#                         st.error(error)
#                 else:
#                     try:
#                         result = finalization_service.create_attribute(payload, user_id=user_id)
#                         st.session_state.last_result = {**result, "created_prj_id": generated_prj_id}
#                         invalidate_dictionary_cache()
#                         st.session_state.force_refresh_records = True
#                         clear_popup_state()
#                         create_attribute_modal.close()
#                         st.rerun()
#                     except Exception as exc:
#                         reset_create_submit_state("modal")
#                         st.error(f"Create failed: {exc}")

#     st.divider()
#     st.subheader("Selected Attribute Actions")
#     st.caption("Actions below use the row selected in the Latest Master Dictionary Records grid above.")
#     b1, b2, b3, b4 = st.columns([1, 1.6, 1, 4.4])
#     with b1:
#         if st.button("View / Edit", disabled=not bool(selected_active_prj_id)):
#             if not admin:
#                 st.error("Only Admin users can edit attributes.")
#                 st.stop()
#             st.session_state.edit_mode = False
#             st.session_state.open_edit_modal = True
#             edit_attribute_modal.open()
#     with b2:
#         if selected_active_prj_id:
#             new_window_link("Open Edit in New Window", f"?page=edit_attribute&prj_id={quote(str(selected_active_prj_id))}")
#         else:
#             st.button("Open Edit in New Window", disabled=True)
#     with b3:
#         if st.button("Soft Delete", disabled=not bool(selected_active_prj_id)):
#             if not admin:
#                 st.error("Only Admin users can soft delete attributes.")
#                 st.stop()
#             try:
#                 result = finalization_service.soft_delete_attribute(selected_active_prj_id, user_id=user_id)
#                 st.session_state.last_result = result
#                 invalidate_dictionary_cache()
#                 st.session_state.force_refresh_records = True
#                 st.session_state.dictionary_records = []
#                 st.session_state.selected_record = None
#                 st.session_state.selected_active_prj_id = ""
#                 st.success(f"Attribute soft deleted. Batch ID: {result['batch_id']}")
#                 st.rerun()
#             except Exception as exc:
#                 st.error(f"Soft delete failed: {exc}")

#     if edit_attribute_modal.is_open() and st.session_state.selected_record:
#         selected_record = st.session_state.selected_record
#         selected_prj_id = str(selected_record.get("prj_id"))
#         with edit_attribute_modal.container():
#             st.subheader("Edit Attribute")
#             st.caption("Record opens in read-only mode. Click Edit to make fields editable except PRJ ID. Use Close to dismiss; it will not reopen until you click View/Edit again.")
#             top_cols = st.columns([1, 1, 1, 5])
#             with top_cols[0]:
#                 if st.button("Edit", key="modal_edit_enable"):
#                     st.session_state.edit_mode = True
#                     st.rerun()
#             with top_cols[1]:
#                 if st.button("Close", key="close_edit_modal"):
#                     clear_popup_state()
#                     edit_attribute_modal.close()
#                     st.stop()
#             with top_cols[2]:
#                 if st.button("Soft Delete", key="modal_soft_delete"):
#                     try:
#                         result = finalization_service.soft_delete_attribute(selected_prj_id, user_id=user_id)
#                         st.session_state.last_result = result
#                         invalidate_dictionary_cache()
#                         st.session_state.force_refresh_records = True
#                         clear_popup_state()
#                         edit_attribute_modal.close()
#                         st.success(f"Attribute soft deleted. Batch ID: {result['batch_id']}")
#                         st.rerun()
#                     except Exception as exc:
#                         st.error(f"Soft delete failed: {exc}")

#             form_result = build_attribute_form(
#                 record=selected_record,
#                 read_only=not st.session_state.edit_mode,
#                 mode="EDIT",
#             )
#             if form_result["submitted"]:
#                 payload = form_result["record"]
#                 payload["prj_id"] = selected_prj_id
#                 errors = validate_attribute_payload(payload)
#                 if errors:
#                     for error in errors:
#                         st.error(error)
#                 else:
#                     try:
#                         result = finalization_service.update_attribute(payload, user_id=user_id)
#                         st.session_state.last_result = result
#                         invalidate_dictionary_cache()
#                         st.session_state.force_refresh_records = True
#                         clear_popup_state()
#                         edit_attribute_modal.close()
#                         st.success(f"Attribute updated. Batch ID: {result['batch_id']}")
#                         st.rerun()
#                     except Exception as exc:
#                         st.error(f"Update failed: {exc}")

#     st.divider()
#     st.subheader("Soft Deleted Records")
#     sd_cols = st.columns([1.4, 1.4, 5.2])
#     with sd_cols[0]:
#         if st.button("View Soft Deleted Records"):
#             st.session_state.show_soft_deleted = True
#     with sd_cols[1]:
#         if st.button("Hide Soft Deleted Records"):
#             st.session_state.show_soft_deleted = False

#     if st.session_state.show_soft_deleted:
#         if not admin:
#             st.warning("Only Admin users can reactivate soft deleted records.")

#         soft_deleted_records = safe_soft_deleted_records(dictionary_service)
#         if soft_deleted_records:
#             soft_deleted_df = records_to_df(soft_deleted_records, limited=True)
#             st.caption("Select one row from the soft-deleted grid, then click Activate Record. No separate PRJ ID dropdown is required.")
#             soft_deleted_selection = st.dataframe(
#                 soft_deleted_df,
#                 use_container_width=True,
#                 height=300,
#                 key="soft_deleted_records_grid",
#                 on_select="rerun",
#                 selection_mode="single-row",
#             )

#             selected_deleted_prj_id = get_selected_prj_id_from_grid(
#                 soft_deleted_selection,
#                 soft_deleted_records,
#             )

#             if selected_deleted_prj_id:
#                 st.success(f"Selected soft-deleted PRJ ID: {selected_deleted_prj_id}")
#             else:
#                 st.info("Select a row from the grid to enable activation.")

#             if st.button(
#                 "Activate Record",
#                 type="primary",
#                 disabled=not bool(selected_deleted_prj_id),
#             ):
#                 if not admin:
#                     st.error("Only Admin users can make a soft deleted attribute active.")
#                     st.stop()
#                 try:
#                     result = finalization_service.reactivate_attribute(selected_deleted_prj_id, user_id=user_id)
#                     st.session_state.last_result = result
#                     invalidate_dictionary_cache()
#                     st.session_state.force_refresh_records = True
#                     st.session_state.dictionary_records = []
#                     st.session_state.show_soft_deleted = False
#                     st.success(f"Attribute reactivated and moved back to active records. Batch ID: {result['batch_id']}")
#                     st.rerun()
#                 except Exception as exc:
#                     st.error(f"Reactivate failed: {exc}")
#         else:
#             st.info("No soft deleted records found. With ENABLE_DB=false this list remains empty because no DB state exists.")

#     if st.session_state.last_result:
#         created_prj_id = st.session_state.last_result.get("created_prj_id") if isinstance(st.session_state.last_result, dict) else None
#         if created_prj_id:
#             st.success(f"Attribute created successfully. PRJ ID created: {created_prj_id}. Batch ID: {st.session_state.last_result.get('batch_id', '')}")
#         with st.expander("Last DB Operation Result", expanded=False):
#             st.json(st.session_state.last_result)

# with tab_ui_display:
#     st.header("UI Display Configuration")
#     st.caption("Manage active and soft-deleted UI display records. Saving an existing record reactivates it.")
#     config_service = ConfigurationService()
#     show_deleted_display = st.checkbox("Show soft-deleted UI display records", key="show_deleted_display")
#     try:
#         display_rows = config_service.list_displays(active_only=not show_deleted_display)
#         if display_rows:
#             display_df = pd.DataFrame(display_rows)
#             st.dataframe(display_df, use_container_width=True, height=320)
#             display_ids = display_df["display_id"].astype(str).tolist()
#             selected_display_id = st.selectbox("Select Display ID for edit/delete/reactivate", [""] + display_ids, key="selected_display_id")
#             selected_display = next((r for r in display_rows if str(r.get("display_id")) == selected_display_id), None)
#         else:
#             selected_display = None
#             st.info("No UI display configuration records found.")
#     except Exception as exc:
#         display_rows, selected_display = [], None
#         st.error(f"Could not load display configuration: {exc}")

#     with st.form("ui_display_config_form"):
#         c1, c2, c3 = st.columns(3)
#         prj_id = c1.text_input("PRJ ID", value="", key="cfg_display_prj_id")
#         sector = c2.selectbox("Sector", ["Corporates", "Banks", "Insurance", "SnP"], key="cfg_display_sector")
#         display_order = c3.number_input("Display Order", min_value=0, step=1, value=int(selected_display.get("display_order") or 0) if selected_display else 0, key="cfg_display_order")
#         display_name = st.text_input("Display Name", value=(selected_display.get("display_name") or "") if selected_display else "", key="cfg_display_name")
#         section = st.text_input("Section", value=(selected_display.get("section") or "") if selected_display else "", key="cfg_display_section")
#         subsection = st.text_input("Subsection", value=(selected_display.get("subsection") or "") if selected_display else "", key="cfg_display_subsection")
#         view_name = st.text_input("View Name", value=(selected_display.get("view_name") or "") if selected_display else "", key="cfg_display_view_name")
#         description = st.text_area("Description", value=(selected_display.get("description") or "") if selected_display else "", key="cfg_display_description")
#         if st.form_submit_button("Save / Update UI Display Configuration"):
#             try:
#                 result = config_service.save_display({"display_id": int(selected_display_id) if selected_display_id else None, "prj_id": prj_id, "sector": sector, "display_order": display_order, "display_name": display_name, "section": section, "subsection": subsection, "view_name": view_name, "description": description}, user_id)
#                 st.success(f"Saved display configuration {result.get('display_id', '')}")
#                 st.rerun()
#             except Exception as exc:
#                 st.error(str(exc))
#     if selected_display:
#         d1, d2 = st.columns(2)
#         if not bool(selected_display.get("is_deleted")):
#             if d1.button("Soft Delete Selected Display", key="delete_selected_display"):
#                 try:
#                     config_service.soft_delete_display(int(selected_display_id), user_id)
#                     st.success("UI display configuration soft deleted.")
#                     st.rerun()
#                 except Exception as exc: st.error(str(exc))
#         else:
#             if d2.button("Reactivate Selected Display", key="reactivate_selected_display"):
#                 try:
#                     config_service.reactivate_display(int(selected_display_id), user_id)
#                     st.success("UI display configuration reactivated.")
#                     st.rerun()
#                 except Exception as exc: st.error(str(exc))

# with tab_business_rules:
#     st.header("Business Rules")
#     st.caption("Business rules support update, soft delete and reactivation per scope.")
#     config_service = ConfigurationService()
#     show_deleted_rules = st.checkbox("Show soft-deleted business rules", key="show_deleted_rules")
#     try:
#         rule_rows = config_service.list_rules(active_only=not show_deleted_rules)
#         if rule_rows:
#             rule_df = pd.DataFrame(rule_rows)
#             st.dataframe(rule_df, use_container_width=True, height=260)
#             selected_rule_id = st.selectbox("Select Rule ID for delete/reactivate", [""] + rule_df["id"].astype(str).tolist(), key="selected_rule_id")
#             selected_rule = next((r for r in rule_rows if str(r.get("id")) == selected_rule_id), None)
#         else:
#             selected_rule_id, selected_rule = "", None
#             st.info("No business rules found.")
#     except Exception as exc:
#         selected_rule_id, selected_rule = "", None
#         st.error(f"Could not load business rules: {exc}")
#     with st.form("business_rule_form"):
#         c1,c2,c3=st.columns(3)
#         prj_id=c1.text_input("PRJ ID", key="rule_prj_id")
#         sector=c2.selectbox("Sector", ["Corporates", "Banks", "Insurance", "SnP"], key="rule_sector")
#         source=c3.text_input("Source", value="SNPAR", key="rule_source")
#         editable=st.checkbox("Editable?", key="rule_editable")
#         symbol=st.text_input("Percentage / Ratio", key="rule_symbol")
#         mapping_type=st.text_input("Mapping Type", key="rule_mapping_type")
#         mapping_logic=st.text_area("Calculation in PRJ", key="rule_mapping_logic")
#         calculation_logic=st.text_area("Calculation Logic Details", key="rule_calculation_logic")
#         business_logic=st.text_area("Business Logic", key="rule_business_logic")
#         if st.form_submit_button("Save Business Rule"):
#             try:
#                 config_service.save_rule({"prj_id":prj_id,"sector":sector,"source_abbr_name":source,"editable":editable,"symbol":symbol,"mapping_type":mapping_type,"mapping_logic":mapping_logic,"calculation_logic":calculation_logic,"business_logic":business_logic}, user_id)
#                 st.success("Business rule saved.")
#                 st.rerun()
#             except Exception as exc: st.error(str(exc))
#     if selected_rule:
#         if not bool(selected_rule.get("is_deleted")):
#             if st.button("Soft Delete Selected Business Rule", key="delete_selected_rule"):
#                 try:
#                     config_service.soft_delete_rule(int(selected_rule_id), user_id); st.success("Business rule soft deleted."); st.rerun()
#                 except Exception as exc: st.error(str(exc))
#         else:
#             if st.button("Reactivate Selected Business Rule", key="reactivate_selected_rule"):
#                 try:
#                     config_service.reactivate_rule(int(selected_rule_id), user_id); st.success("Business rule reactivated."); st.rerun()
#                 except Exception as exc: st.error(str(exc))

# with tab_audit:
#     st.header("Audit History")
#     st.caption("Search audit records using the same Swagger API filter structure as the Data Dictionary page.")
#     a1, a2, a3 = st.columns(3)
#     with a1:
#         audit_portfolios = st.multiselect("Portfolio", PORTFOLIO_OPTIONS, default=["ALL"], key="audit_portfolio_multiselect")
#         if not audit_portfolios:
#             audit_portfolios = ["ALL"]
#         if "ALL" in audit_portfolios and len(audit_portfolios) > 1:
#             audit_portfolios = [p for p in audit_portfolios if p != "ALL"]
#         audit_overlapped = st.checkbox("Overlapped Attribute", value=False, key="audit_overlapped")
#     with a2:
#         audit_prj_id = st.text_input("PRJ_ID", key="audit_filter_prj_id")
#         audit_attribute_name = st.text_input("Attribute Name", key="audit_filter_attribute_name")
#     with a3:
#         audit_attribute_description = st.text_input("Attribute Description", key="audit_filter_attribute_description")
#         audit_section = st.selectbox("Section", [""] + SECTION_OPTIONS, key="audit_filter_section")

#     include_full = st.checkbox("View full history", value=False, key="audit_filter_include_full_history")

#     audit_filters = {
#         "portfolios": audit_portfolios,
#         "portfolio_sector": audit_portfolios,
#         "prj_id": audit_prj_id,
#         "attribute_name": audit_attribute_name,
#         "attribute_description": audit_attribute_description,
#         "section": audit_section,
#         "overlapped_attribute": audit_overlapped,
#         "include_full_history": include_full,
#         "active_only": False,
#         "limit": 2000 if include_full else 500,
#     }

#     if st.button("Search Audit History", type="primary") or include_full:
#         try:
#             audit_rows = safe_filter_audit(audit_service, audit_filters)
#             if audit_rows:
#                 st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, height=520)
#             else:
#                 st.info("No audit records found. If ENABLE_DB=false, audit search returns no DB data.")
#         except Exception as exc:
#             st.error(f"Audit search failed: {exc}")

# with tab_prompts:
#     st.header("Prompt Management")
#     st.caption("Manage PRJ scanning prompts, bulk-load workbooks, generate reviewable SQL, and apply validated database updates.")
#     config_service = ConfigurationService()
#     prompt_form_tab, sql_generator_tab = st.tabs(["Prompt Form & Library", "SQL Query Generator"])

#     with prompt_form_tab:
#         uploaded_prompt_file = st.file_uploader("Upload Excel 2 prompt workbook", type=["xlsx"], key="prompt_upload")
#         if uploaded_prompt_file and st.button("Load Prompt Workbook", key="prompt_upload_button"):
#             try:
#                 result = config_service.upload_prompts(uploaded_prompt_file.getvalue(), None, user_id)
#                 st.success(f"Loaded or updated {result['processed']} prompt records.")
#                 if result.get("skipped_not_in_master"):
#                     st.warning(f"{len(result['skipped_not_in_master'])} PRJ IDs were not loaded because they are absent from Master Dictionary.")
#                     st.dataframe(pd.DataFrame(result["skipped_not_in_master"]), use_container_width=True)
#                 if result["errors"]:
#                     st.dataframe(pd.DataFrame(result["errors"]), use_container_width=True)
#             except Exception as exc:
#                 st.error(str(exc))

#         show_deleted_prompts = st.checkbox("Show soft-deleted prompts", key="show_deleted_prompts")
#         try:
#             prompt_rows = config_service.list_prompts(active_only=not show_deleted_prompts)
#             if prompt_rows:
#                 prompt_df = pd.DataFrame(prompt_rows)
#                 st.dataframe(prompt_df, use_container_width=True, height=300)
#                 selected_prompt_id = st.selectbox("Select Prompt ID for delete/reactivate", [""] + prompt_df["prompt_id"].astype(str).tolist(), key="selected_prompt_id")
#                 selected_prompt = next((r for r in prompt_rows if str(r.get("prompt_id")) == selected_prompt_id), None)
#             else:
#                 selected_prompt_id, selected_prompt = "", None
#                 st.info("No prompt records found.")
#         except Exception as exc:
#             selected_prompt_id, selected_prompt = "", None
#             st.error(f"Could not load prompt records: {exc}")

#         with st.form("prompt_form"):
#             c1, c2, c3 = st.columns(3)
#             prompt_prj_id = c1.text_input("PRJ ID (must exist in Master Dictionary; readonly after selection)", value=(selected_prompt.get("prj_id") or "") if selected_prompt else "", disabled=bool(selected_prompt), key="prompt_prj_id")
#             prompt_sector = c2.selectbox("Sector", ["Corporates", "Banks", "Insurance", "Downstream", "SnP"], key="prompt_sector")
#             c3.text_input("CFV ID", key="prompt_cfv")
#             prompt_description = st.text_area("Description (Proposed one-shot prompting)", value=(selected_prompt.get("attribute_description") or "") if selected_prompt else "", key="prompt_description")
#             prompt_examples = st.text_area("Examples", value=(selected_prompt.get("examples") or "") if selected_prompt else "", key="prompt_examples")
#             prompt_segment = st.text_input("Segment", value=(selected_prompt.get("segment") or "") if selected_prompt else "", key="prompt_segment")
#             if st.form_submit_button("Save / Update Prompt"):
#                 try:
#                     config_service.save_prompt({"prj_id": prompt_prj_id, "sector": prompt_sector, "attribute_description": prompt_description, "examples": prompt_examples, "segment": prompt_segment}, user_id)
#                     st.success("Prompt saved.")
#                     st.rerun()
#                 except Exception as exc:
#                     st.error(str(exc))
#         if selected_prompt:
#             if not bool(selected_prompt.get("is_deleted")):
#                 if st.button("Soft Delete Selected Prompt", key="delete_selected_prompt"):
#                     try:
#                         config_service.soft_delete_prompt(int(selected_prompt_id), user_id)
#                         st.success("Prompt soft deleted.")
#                         st.rerun()
#                     except Exception as exc:
#                         st.error(str(exc))
#             elif st.button("Reactivate Selected Prompt", key="reactivate_selected_prompt"):
#                 try:
#                     config_service.reactivate_prompt(int(selected_prompt_id), user_id)
#                     st.success("Prompt reactivated.")
#                     st.rerun()
#                 except Exception as exc:
#                     st.error(str(exc))

#     with sql_generator_tab:
#         st.subheader("PRJ Scanning Prompt Reference: SQL Insert / Update Generator")
#         st.caption("The generated SQL is downloadable for review. Use Update Database to run the same rows through the application service, scope validation, and audit logging.")
#         generator_file = st.file_uploader("Upload Excel file for SQL generation", type=["xlsx", "xls"], key="sql_generator_upload")
#         if generator_file is not None:
#             st.session_state["sql_generator_file_bytes"] = generator_file.getvalue()
#             st.session_state["sql_generator_file_name"] = generator_file.name

#         file_bytes = st.session_state.get("sql_generator_file_bytes")
#         if not file_bytes:
#             st.info("Upload an Excel workbook to select a sheet, map the columns, generate SQL, or update the database.")
#         else:
#             try:
#                 excel_file = pd.ExcelFile(BytesIO(file_bytes))
#                 sheet_names = excel_file.sheet_names
#                 selected_sheet = st.selectbox("Select sheet to process", sheet_names, key="sql_generator_sheet")
#                 generator_df = pd.read_excel(BytesIO(file_bytes), sheet_name=selected_sheet)
#                 st.session_state["sql_generator_df"] = generator_df
#                 m1, m2, m3 = st.columns(3)
#                 m1.metric("Total rows", len(generator_df))
#                 m2.metric("Total columns", len(generator_df.columns))
#                 m3.metric("Rows with PRJ ID", int(generator_df.notna().any(axis=1).sum()))
#                 with st.expander("Preview uploaded data", expanded=True):
#                     st.dataframe(generator_df.head(50), use_container_width=True)
#                 with st.expander("Available Excel columns"):
#                     st.write(list(generator_df.columns))

#                 columns = [""] + [str(c) for c in generator_df.columns]
#                 lookup = {str(c).strip().lower(): str(c) for c in generator_df.columns}
#                 def suggested(*names: str) -> int:
#                     for name in names:
#                         value = lookup.get(name.lower())
#                         if value in columns:
#                             return columns.index(value)
#                     return 0

#                 st.markdown("#### Excel to database mapping")
#                 mc1, mc2, mc3 = st.columns(3)
#                 column_mapping = {
#                     "prj_id": mc1.selectbox("PRJ ID column *", columns, index=suggested("PRJID", "PRJ ID"), key="sql_map_prj_id"),
#                     "attribute_name": mc2.selectbox("Attribute Name", columns, index=suggested("PRJ Attribute", "Attribute Name"), key="sql_map_attribute_name"),
#                     "segment": mc3.selectbox("Segment", columns, index=suggested("Location in Financial Reports", "Segment"), key="sql_map_segment"),
#                     "attribute_description": mc1.selectbox("Description", columns, index=suggested("Description (Proposed one-shot prompt)", "Description (Proposed one-shot prompting)", "Description"), key="sql_map_description"),
#                     "section": mc2.selectbox("Section", columns, index=suggested("Section"), key="sql_map_section"),
#                     "sub_section": mc3.selectbox("Sub-section", columns, index=suggested("Sub-Section", "Sub Section"), key="sql_map_subsection"),
#                     "data_type": mc1.selectbox("Data Type", columns, index=suggested("DATA TYPE(Amount%/Ratio/actual)", "Data Type"), key="sql_map_data_type"),
#                     "calculated_or_reported": mc2.selectbox("Calculated or Reported", columns, index=suggested("Calculated or Reported"), key="sql_map_calc_reported"),
#                     "calculation_logic": mc3.selectbox("Calculation Logic", columns, index=suggested("Calculation Logic"), key="sql_map_calc_logic"),
#                     "subcomponent_total": mc1.selectbox("Subcomponent / Total", columns, index=suggested("Subcomponent/Total", "Subcomponent / Total"), key="sql_map_subcomponent"),
#                     "examples": mc2.selectbox("Examples", columns, index=suggested("Examples"), key="sql_map_examples"),
#                 }
#                 sector = mc3.selectbox("Target portfolio / sector *", ["Banks", "Insurance", "Corporates", "Downstream", "SnP"], key="sql_generator_sector")
#                 if not column_mapping["prj_id"]:
#                     st.error("Select the mandatory PRJ ID column before generating SQL or updating the database.")
#                 else:
#                     rows, normalize_errors = config_service.normalize_prompt_generator_rows(generator_df, column_mapping, sector, selected_sheet)
#                     st.info(f"Prepared {len(rows)} rows from sheet '{selected_sheet}'. Blank optional Excel fields will not overwrite existing database values.")
#                     if normalize_errors:
#                         st.dataframe(pd.DataFrame(normalize_errors), use_container_width=True)
#                     action_col1, action_col2 = st.columns(2)
#                     with action_col1:
#                         if st.button("Generate SQL Script", type="primary", use_container_width=True, key="generate_prompt_sql"):
#                             st.session_state["generated_prompt_sql"] = config_service.generate_prompt_upsert_sql(rows, user_id)
#                     with action_col2:
#                         confirm_db_update = st.checkbox("I confirm this will insert/update prompt records", key="confirm_prompt_db_update")
#                         if st.button("Update Database", type="primary", use_container_width=True, disabled=not (admin and confirm_db_update), key="update_prompt_db"):
#                             result = config_service.upsert_prompt_generator_rows(rows, user_id)
#                             st.success(f"Database update completed. {result['processed']} prompt records inserted or updated.")
#                             if result["skipped_not_in_master"]:
#                                 st.warning(f"{len(result['skipped_not_in_master'])} row(s) skipped because PRJ ID is not present in Master Dictionary.")
#                                 st.dataframe(pd.DataFrame(result["skipped_not_in_master"]), use_container_width=True)
#                             if result["errors"]:
#                                 st.error(f"{len(result['errors'])} row(s) could not be processed.")
#                                 st.dataframe(pd.DataFrame(result["errors"]), use_container_width=True)
#                     if not admin:
#                         st.warning("Only Admin users can update the database. SQL generation remains available for review.")
#                     generated_sql = st.session_state.get("generated_prompt_sql")
#                     if generated_sql:
#                         st.markdown("#### Generated SQL Server upsert script")
#                         st.code(generated_sql, language="sql", line_numbers=True)
#                         st.download_button("Download SQL Script", generated_sql, file_name=f"prompt_upsert_{selected_sheet}.sql", mime="text/sql", use_container_width=True)
#             except Exception as exc:
#                 st.error(f"Could not read the SQL generator workbook: {exc}")



"""API-only Streamlit UI for the Data Dictionary Admin App."""
from __future__ import annotations

import os
from pathlib import Path
from io import BytesIO

import pandas as pd
import requests
import streamlit as st
from streamlit_modal import Modal


def load_local_env() -> None:
    """Allow Streamlit to read .env without requiring a duplicate config module."""
    for candidate in (Path.cwd() / '.env', Path(__file__).resolve().parents[3] / '.env'):
        if candidate.exists():
            for raw in candidate.read_text(encoding='utf-8').splitlines():
                line = raw.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
            return


load_local_env()
def normalize_api_base_url(value: str) -> str:
    """Normalise user configuration to the FastAPI v1 route root."""
    base = (value or 'http://localhost:8502/api/v1').strip().rstrip('/')
    if base.endswith('/docs') or base.endswith('/redoc'):
        base = base.rsplit('/', 1)[0]
    if not base.endswith('/api/v1'):
        base = f"{base}/api/v1"
    return base


API = normalize_api_base_url(os.getenv('API_BASE_URL', os.getenv('STREAMLIT_API_BASE_URL', 'http://localhost:8502/api/v1')))
ENVIRONMENTS = [x.strip().upper() for x in os.getenv('APP_ENVIRONMENTS', 'LOCAL,DEV,UAT,PROD').split(',') if x.strip()]
DEFAULT_ENV = os.getenv('SELECTED_ENVIRONMENT', os.getenv('APP_ENV', 'LOCAL')).upper()
SECTIONS = ['Income Statement', 'Balance Sheet', 'Cash Flow', 'Ratios', 'Derivatives', 'Miscellaneous', 'Other']
PORTFOLIOS = ['FI Banks', 'Corporates', 'FI Insurance', 'Zeus Downstream', 'ALL']

st.set_page_config(page_title='Data Dictionary Admin App', layout='wide')
st.title(os.getenv('APP_NAME', 'Data Dictionary Streamlit Admin'))


def api(method: str, path: str, *, quiet: bool = False, **kwargs):
    headers = kwargs.pop('headers', {})
    headers['X-App-Environment'] = st.session_state.get('selected_environment', DEFAULT_ENV)
    try:
        response = requests.request(method, f'{API}{path}', timeout=60, headers=headers, **kwargs)
    except requests.RequestException as exc:
        if not quiet:
            st.error(f'API connection failed: {exc}')
        return None
    if not response.ok:
        try:
            detail = response.json().get('detail', response.text)
        except Exception:
            detail = response.text
        if not quiet:
            st.error(f'API error ({response.status_code}): {detail}')
        return None
    return response


def lookup(path: str, fallback):
    response = api('GET', path, quiet=True)
    return response.json() if response else fallback


with st.sidebar:
    st.subheader('Connection')
    selected = st.selectbox('Environment', ENVIRONMENTS, index=ENVIRONMENTS.index(DEFAULT_ENV) if DEFAULT_ENV in ENVIRONMENTS else 0, key='selected_environment')
    info = api('GET', '/system/environment', quiet=True)
    details = info.json() if info else {
        'server': os.getenv(f'ENV_{selected}_SQLSERVER_SERVER', os.getenv('SQLSERVER_SERVER', 'Not configured')),
        'database': os.getenv(f'ENV_{selected}_SQLSERVER_DATABASE', os.getenv('SQLSERVER_DATABASE', 'PRJ_DB')),
        'database_enabled': os.getenv(f'ENV_{selected}_ENABLE_DB', os.getenv('ENABLE_DB', 'false')),
    }
    st.caption(f"Server: {details.get('server') or 'Not configured'}")
    st.caption(f"Database: {details.get('database') or 'Not configured'}")
    st.caption(f"Database enabled: {details.get('database_enabled')}")
    if not info:
        st.warning('API environment endpoint is unavailable. Server details are shown from .env. Verify that FastAPI is started from this same project folder.')
    st.caption(f"API: {API}")
    user = st.text_input('Current User', value=os.getenv('USERNAME', os.getenv('DEFAULT_USER', 'sysuser')))
    if st.button('Refresh'):
        st.cache_data.clear()
        st.rerun()

sections = lookup('/lookups/sections', SECTIONS)
sources = lookup('/lookups/sources', [{'source_name': 'S&P CAPIQ AS REPORTED DATA', 'source_code': 'SNPAR'}])
source_names = [x['source_name'] for x in sources]


def attribute_payload(prefix: str) -> dict:
    return {
        'prj_id': st.session_state.get(f'{prefix}_prj_id', '').strip(),
        'prj_attribute_name': st.session_state.get(f'{prefix}_name', '').strip(),
        'prj_attribute_description': st.session_state.get(f'{prefix}_description', ''),
        'prj_physical_attribute_name': st.session_state.get(f'{prefix}_physical', ''),
        'where_in_financial_statement': st.session_state.get(f'{prefix}_section'),
        'version_update': st.session_state.get(f'{prefix}_version', ''),
        'calculated_or_reported': st.session_state.get(f'{prefix}_calculated_reported'),
        'calculation_logic': st.session_state.get(f'{prefix}_calculation_logic', ''),
        'calculation_logic_details': st.session_state.get(f'{prefix}_calculation_details', ''),
        'sign_flipping_value': st.session_state.get(f'{prefix}_sign_flipping', ''),
        'mapping_type': st.session_state.get(f'{prefix}_mapping_type', ''),
        'sp_standardisation_dataitem_id': st.session_state.get(f'{prefix}_sp_standardisation', ''),
        'sp_as_reported_dataitem_logic': st.session_state.get(f'{prefix}_sp_as_reported', ''),
        'calculated_in_cfv': st.session_state.get(f'{prefix}_cfv'),
        'editable_in_historicals': st.session_state.get(f'{prefix}_historicals'),
        'required_portfolios': st.session_state.get(f'{prefix}_portfolios', []),
        'source_name': st.session_state.get(f'{prefix}_source'),
        'editable': st.session_state.get(f'{prefix}_editable'),
        'symbol': st.session_state.get(f'{prefix}_symbol', ''),
        'business_logic': st.session_state.get(f'{prefix}_business_logic', ''),
    }


def render_attribute_form(mode: str, initial: dict | None = None):
    prefix = 'new_attribute' if mode == 'create' else 'edit_attribute'
    initial = initial or {}
    disabled = mode == 'edit-readonly'
    with st.form(f'{prefix}_form'):
        row1 = st.columns(3)
        row1[0].text_input('PRJ ID *', value=initial.get('prj_id', ''), key=f'{prefix}_prj_id', disabled=mode != 'create')
        row1[1].text_input('PRJ Attribute Name *', value=initial.get('prj_attribute_name', ''), key=f'{prefix}_name', disabled=disabled)
        row1[2].text_input('PRJ Physical Attribute Name', value=initial.get('prj_physical_attribute_name', ''), key=f'{prefix}_physical', disabled=disabled)
        st.text_area('PRJ Attribute Description', value=initial.get('prj_attribute_description', ''), key=f'{prefix}_description', disabled=disabled)
        row2 = st.columns(3)
        row2[0].selectbox('Where in financial statement', sections, index=sections.index(initial.get('where_in_financial_statement')) if initial.get('where_in_financial_statement') in sections else 0, key=f'{prefix}_section', disabled=disabled)
        row2[1].text_input('Version Update', value=initial.get('version_update', ''), key=f'{prefix}_version', disabled=disabled)
        row2[2].selectbox('Calculated or Reported?', ['', 'Calculated', 'Reported'], index=['', 'Calculated', 'Reported'].index(initial.get('calculated_or_reported')) if initial.get('calculated_or_reported') in ['', 'Calculated', 'Reported'] else 0, key=f'{prefix}_calculated_reported', disabled=disabled)
        row3 = st.columns(3)
        row3[0].selectbox('Editable?', ['', 'Y', 'N'], index=['', 'Y', 'N'].index(initial.get('editable')) if initial.get('editable') in ['', 'Y', 'N'] else 0, key=f'{prefix}_editable', disabled=disabled)
        row3[1].text_input('Percentage (%) / Ratio (X)', value=initial.get('symbol', ''), key=f'{prefix}_symbol', disabled=disabled)
        row3[2].selectbox('Source Name', source_names, index=source_names.index(initial.get('source_name')) if initial.get('source_name') in source_names else 0, key=f'{prefix}_source', disabled=disabled)
        st.multiselect('Required By', PORTFOLIOS[:-1], default=initial.get('required_portfolios', []), key=f'{prefix}_portfolios', disabled=disabled)
        row4 = st.columns(2)
        row4[0].text_area('Calculation Logic', value=initial.get('calculation_logic', ''), key=f'{prefix}_calculation_logic', disabled=disabled)
        row4[1].text_area('Calculation Logic Details', value=initial.get('calculation_logic_details', ''), key=f'{prefix}_calculation_details', disabled=disabled)
        row5 = st.columns(2)
        row5[0].text_input('Mapping Type', value=initial.get('mapping_type', ''), key=f'{prefix}_mapping_type', disabled=disabled)
        row5[1].text_input('S&P Standardisation Dataitem ID', value=initial.get('sp_standardisation_dataitem_id', ''), key=f'{prefix}_sp_standardisation', disabled=disabled)
        row6 = st.columns(2)
        row6[0].text_area('S&P As-Reported Dataitem ID / Logic', value=initial.get('sp_as_reported_dataitem_logic', ''), key=f'{prefix}_sp_as_reported', disabled=disabled)
        row6[1].text_area('Business Logic', value=initial.get('business_logic', ''), key=f'{prefix}_business_logic', disabled=disabled)
        row7 = st.columns(3)
        row7[0].selectbox('Calculated in CFV?', ['', 'Y', 'N'], key=f'{prefix}_cfv', disabled=disabled)
        row7[1].selectbox('Editable in Historicals?', ['', 'Y', 'N'], key=f'{prefix}_historicals', disabled=disabled)
        row7[2].text_input('Sign Flipping (multiply by)', value=initial.get('sign_flipping_value', ''), key=f'{prefix}_sign_flipping', disabled=disabled)
        submitted = st.form_submit_button('Create Attribute' if mode == 'create' else 'Upload Changes', disabled=disabled)
    if submitted:
        payload = attribute_payload(prefix)
        if not payload['prj_id'] or not payload['prj_attribute_name']:
            st.error('PRJ ID and PRJ Attribute Name are mandatory.')
        elif api('POST' if mode == 'create' else 'PUT', '/data-dictionary/attributes' if mode == 'create' else f"/data-dictionary/attributes/{payload['prj_id']}?user={user}", json=payload if mode == 'create' else payload):
            st.success('Attribute saved successfully.')
            st.rerun()


tab1, tab2, tab3 = st.tabs(['Data Dictionary', 'Prompt Management', 'Audit History'])
with tab1:
    st.subheader('View Latest Data Dictionary')
    f1, f2, f3, f4 = st.columns(4)
    selected_portfolios = f1.multiselect('Portfolio/Sector', PORTFOLIOS)
    filter_prj = f2.text_input('PRJ ID filter')
    filter_name = f3.text_input('Attribute Name filter')
    filter_section = f4.selectbox('Section filter', [''] + sections)
    f5, f6 = st.columns(2)
    filter_desc = f5.text_input('Attribute Description filter')
    include_deleted = f6.checkbox('View soft deleted records')
    overlapped = f6.checkbox('Overlapped Attribute only')
    filters = {'portfolios': [] if 'ALL' in selected_portfolios else selected_portfolios, 'prj_id': filter_prj or None, 'attribute_name': filter_name or None, 'attribute_description': filter_desc or None, 'section': filter_section or None, 'overlapped_only': overlapped, 'include_deleted': include_deleted}
    result = api('POST', '/data-dictionary/filter', json=filters)
    rows = result.json() if result else []
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    b1, b2 = st.columns(2)
    if b1.button('Add New Attribute'):
        st.session_state['attribute_modal'] = 'create'
    latest = api('GET', '/data-dictionary/download-latest') if b2.button('Generate Latest Excel') else None
    if latest:
        st.download_button('Download Latest Data', latest.content, 'data_dictionary_latest.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    modal = Modal('Create New Attribute', key='create-attribute-modal')
    if st.session_state.get('attribute_modal') == 'create':
        modal.open()
    if modal.is_open():
        with modal.container():
            render_attribute_form('create')
            if st.button('Close Create Form'):
                modal.close(); st.session_state.pop('attribute_modal', None); st.rerun()

with tab2:
    bulk, manual = st.tabs(['Bulk Upload', 'Edit/Insert Prompts'])
    with bulk:
        uploaded = st.file_uploader('Upload Prompt Excel', type=['xlsx'])
        if uploaded:
            r = api('POST', '/prompt-upload/sheets', quiet=False, files={'file': (uploaded.name, uploaded.getvalue(), uploaded.type)})
            if r:
                st.selectbox('Workbook sheet', r.json().get('sheets', []))
                st.info('Sheet discovery is available. The final bulk preview, validation, delta and commit endpoints must be executed after the Excel mapping is finalized.')
    with manual:
        with st.form('prompt-form'):
            p1,p2,p3 = st.columns(3)
            prj_id = p1.text_input('PRJ ID *')
            prompt_id = p2.number_input('Prompt ID (leave 0 for new)', min_value=0, step=1)
            scope_id = p3.number_input('Scope ID', min_value=0, step=1)
            p4,p5,p6 = st.columns(3)
            attr = p4.text_input('Attribute Name')
            section = p5.selectbox('Section', [''] + sections)
            sub_section = p6.text_input('Sub-Section')
            p7,p8,p9 = st.columns(3)
            data_type = p7.selectbox('DATA TYPE', ['', 'Amount', '%', 'Ratio', 'Actual'])
            calc_report = p8.selectbox('Calculated or Reported', ['', 'Calculated', 'Reported'])
            display = p9.number_input('Display Order', min_value=0, step=1)
            calculation_logic = st.text_area('Calculation Logic')
            segment = st.text_input('Segment')
            description = st.text_area('Description')
            examples = st.text_area('Examples')
            required_scope = st.text_input('Required By Scope')
            submitted = st.form_submit_button('Save Prompt')
        if submitted:
            payload = {'scope_id': scope_id or None, 'prj_id': prj_id, 'required_by_scope': required_scope, 'attribute_name': attr, 'section': section, 'sub_section': sub_section, 'data_type': data_type, 'calculated_or_reported': calc_report, 'calculation_logic': calculation_logic, 'segment': segment, 'attribute_description': description, 'examples': examples, 'display_order': display}
            endpoint = '/prompts' if prompt_id == 0 else f'/prompts/{prompt_id}?user={user}'
            method = 'POST' if prompt_id == 0 else 'PUT'
            if api(method, endpoint, json=payload): st.success('Prompt saved successfully.')

with tab3:
    st.subheader('Audit History')
    a1,a2,a3,a4 = st.columns(4)
    table_name = a1.text_input('Table name')
    record_key = a2.text_input('PRJ ID / Record Key')
    action = a3.selectbox('Action', ['', 'INSERT', 'UPDATE', 'SOFT_DELETE', 'REACTIVATE', 'S3_EXPORT'])
    performed_by = a4.text_input('Performed by')
    audit = api('GET', '/audit', params={'table_name': table_name or None, 'record_key': record_key or None, 'action': action or None, 'performed_by': performed_by or None})
    if audit:
        st.dataframe(pd.DataFrame(audit.json()), use_container_width=True, hide_index=True)
