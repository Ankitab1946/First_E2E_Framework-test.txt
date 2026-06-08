import os
from typing import Any
from urllib.parse import quote

import requests
import pandas as pd
import streamlit as st
from streamlit_modal import Modal

from app.core.config import get_settings
from app.services.audit_service import AuditService
from app.services.dictionary_service import DictionaryService
from app.services.excel_service import ExcelService
from app.services.finalization_service import FinalizationService
from app.services.s3_export_service import S3ExportService
from app.utils.constants import LIMITED_DICTIONARY_FIELDS, PORTFOLIO_OPTIONS, SECTION_OPTIONS
from app.utils.excel_mapping import BOOLEAN_FIELDS, MASTER_FIELDS
from app.utils.sample_data import get_sample_records


st.set_page_config(page_title="Data Dictionary Admin", layout="wide")


def apply_modal_css() -> None:
    """Make streamlit-modal dialogs centered and scrollable across laptop/monitor sizes."""
    st.markdown(
        """
        <style>
        /* streamlit-modal / common modal wrappers */
        div[data-testid="stModal"],
        div[data-modal-container="true"],
        div[class*="modal"],
        div[class*="Modal"] {
            box-sizing: border-box;
        }

        /* Main dialog body: keep it centered and within viewport */
        div[data-testid="stModal"] > div,
        div[data-modal-container="true"] > div,
        div[class*="modal-content"],
        div[class*="ModalContent"],
        div[class*="streamlit-modal"] {
            position: fixed !important;
            top: 50% !important;
            left: 50% !important;
            transform: translate(-50%, -50%) !important;
            width: min(92vw, 1400px) !important;
            max-width: 92vw !important;
            max-height: 86vh !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            border-radius: 12px !important;
            padding: 1rem 1.25rem !important;
            z-index: 100000 !important;
        }

        /* Streamlit forms and blocks inside popup should not exceed modal height */
        div[data-testid="stModal"] section,
        div[data-testid="stModal"] div[data-testid="stVerticalBlock"],
        div[data-modal-container="true"] section,
        div[data-modal-container="true"] div[data-testid="stVerticalBlock"],
        div[class*="modal-content"] section,
        div[class*="modal-content"] div[data-testid="stVerticalBlock"] {
            max-height: none !important;
            overflow: visible !important;
        }

        /* Ensure long select boxes/text areas behave inside modal */
        div[data-testid="stModal"] textarea,
        div[data-testid="stModal"] input,
        div[class*="modal-content"] textarea,
        div[class*="modal-content"] input {
            max-width: 100% !important;
        }

        @media (max-width: 900px) {
            div[data-testid="stModal"] > div,
            div[data-modal-container="true"] > div,
            div[class*="modal-content"],
            div[class*="ModalContent"],
            div[class*="streamlit-modal"] {
                width: 96vw !important;
                max-width: 96vw !important;
                max-height: 90vh !important;
                padding: 0.75rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

apply_modal_css()


def current_user() -> str:
    settings = get_settings()
    return os.getenv("USERNAME") or os.getenv("USER") or settings.default_user


def apply_selected_environment(environment_name: str) -> None:
    """Apply selected environment details from .env into standard SQLSERVER_* variables."""
    env_key = environment_name.upper().replace(" ", "_")
    mapping = {
        "SQLSERVER_SERVER": f"ENV_{env_key}_SQLSERVER_SERVER",
        "SQLSERVER_DATABASE": f"ENV_{env_key}_SQLSERVER_DATABASE",
        "SQLSERVER_WINDOWS_AUTH": f"ENV_{env_key}_SQLSERVER_WINDOWS_AUTH",
        "SQLSERVER_USER": f"ENV_{env_key}_SQLSERVER_USER",
        "SQLSERVER_PASSWORD": f"ENV_{env_key}_SQLSERVER_PASSWORD",
        "ENABLE_DB": f"ENV_{env_key}_ENABLE_DB",
    }
    for target_name, source_name in mapping.items():
        value = os.getenv(source_name)
        if value not in (None, ""):
            os.environ[target_name] = value
    os.environ["SELECTED_ENVIRONMENT"] = environment_name.upper()
    os.environ["APP_ENV"] = environment_name.upper()
    get_settings.cache_clear()


def apply_selected_db_auth_mode(auth_label: str) -> None:
    """Apply the DB authentication mode selected in the sidebar.

    Default remains Windows logged-in user. Keytab mode reads krb5/keytab
    settings from the UI/.env and prepares the runtime configuration used by
    local Streamlit DB operations. API calls also receive the selected mode
    through request headers.
    """
    mode_map = {
        "Windows Logged-in User": "windows",
        "Kerberos Keytab": "keytab",
        "SQL Username/Password": "sql",
    }
    auth_mode = mode_map.get(auth_label, "windows")
    os.environ["SQLSERVER_AUTH_MODE"] = auth_mode
    os.environ["SQLSERVER_WINDOWS_AUTH"] = "true" if auth_mode in {"windows", "keytab"} else "false"
    get_settings.cache_clear()


def apply_keytab_runtime_values(
    krb5_config_path: str,
    krb5_keytab_path: str,
    krb5_principal: str,
    krb5_cache_path: str,
    krb5_kinit_enabled: bool,
) -> None:
    """Apply sidebar Kerberos values to runtime environment variables."""
    if krb5_config_path:
        os.environ["KRB5_CONFIG_PATH"] = krb5_config_path
    if krb5_keytab_path:
        os.environ["KRB5_KEYTAB_PATH"] = krb5_keytab_path
    if krb5_principal:
        os.environ["KRB5_PRINCIPAL"] = krb5_principal
    if krb5_cache_path:
        os.environ["KRB5_CACHE_PATH"] = krb5_cache_path
    os.environ["KRB5_KINIT_ENABLED"] = "true" if krb5_kinit_enabled else "false"
    get_settings.cache_clear()


def is_admin_user(user_id: str) -> bool:
    """Return True when the current user has admin rights.

    Local/dev mode can auto-enable admin actions through LOCAL_AUTO_ADMIN=true.
    For controlled environments, set LOCAL_AUTO_ADMIN=false and maintain ADMIN_USERS.
    Matching supports plain usernames, DOMAIN\\user values, and wildcard '*'.
    """
    settings = get_settings()
    if settings.local_auto_admin and settings.selected_environment.upper() in {"LOCAL", "DEV"}:
        return True

    admin_users = settings.admin_user_list
    normalized_user = (user_id or settings.default_user or "sysuser").strip().lower()
    short_user = normalized_user.split("\\")[-1]

    return (
        "*" in admin_users
        or normalized_user in admin_users
        or short_user in admin_users
    )


def normalize_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def records_to_df(records: list[dict], limited: bool = False) -> pd.DataFrame:
    fields = LIMITED_DICTIONARY_FIELDS if limited else MASTER_FIELDS
    if not records:
        return pd.DataFrame(columns=fields)
    df = pd.DataFrame(records)
    for field in fields:
        if field not in df.columns:
            df[field] = None
    extra_cols = [c for c in ["delta_type", "changed_fields", "is_active", "version_no", "created_at", "updated_at"] if c in df.columns]
    return df[fields + extra_cols]


def df_to_records(df: pd.DataFrame) -> list[dict]:
    return df.where(pd.notnull(df), None).to_dict(orient="records")



def call_api_post(endpoint: str, payload: dict, timeout: int = 30) -> dict:
    settings = get_settings()
    base_url = (settings.api_base_url or "").rstrip("/")
    # Streamlit normally runs on 8501; the FastAPI/Swagger service runs on 8502.
    # If a copied .env accidentally points API_BASE_URL to 8501, correct it here
    # to avoid calling Streamlit's internal endpoints and receiving 403 Forbidden.
    if base_url.startswith("http://localhost:8501") or base_url.startswith("http://127.0.0.1:8501"):
        base_url = base_url.replace(":8501", ":8502", 1)
    if not base_url:
        raise RuntimeError("API_BASE_URL is not configured.")
    runtime_settings = get_settings()
    headers = {
        "X-User-Id": current_user(),
        "X-Db-Auth-Mode": runtime_settings.effective_sql_auth_mode,
        "X-Krb5-Config-Path": runtime_settings.krb5_config_path or "",
        "X-Krb5-Keytab-Path": runtime_settings.krb5_keytab_path or "",
        "X-Krb5-Principal": runtime_settings.krb5_principal or "",
        "X-Krb5-Cache-Path": runtime_settings.krb5_cache_path or "",
        "X-Krb5-Kinit-Enabled": "true" if runtime_settings.krb5_kinit_enabled else "false",
    }
    response = requests.post(
        f"{base_url}{endpoint}",
        json=payload,
        headers=headers,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def safe_filter_records(dictionary_service: DictionaryService, filters: dict) -> list[dict]:
    """Fetch Data Dictionary records through Swagger API filters when available.

    If the FastAPI process is not running, the app falls back to the existing
    in-process service so current edit/add/delete/S3 workflows remain usable.
    """
    settings = get_settings()
    if settings.use_api_for_filters:
        try:
            api_result = call_api_post("/dictionary/filter", filters)
            return api_result.get("records", [])
        except Exception as exc:
            st.warning(f"Filter API is not available. Falling back to local service. Details: {exc}")
    try:
        return dictionary_service.filter_records(filters)
    except Exception as exc:
        st.warning(f"Could not fetch filtered records from configured database. Showing sample data. Details: {exc}")
        fallback = DictionaryService()
        fallback.settings.enable_db = False
        return fallback.filter_records(filters)


def safe_filter_audit(audit_service: AuditService, filters: dict) -> list[dict]:
    settings = get_settings()
    if settings.use_api_for_filters:
        try:
            api_result = call_api_post("/audit/filter", filters)
            return api_result.get("records", [])
        except Exception as exc:
            st.warning(f"Audit Filter API is not available. Falling back to local service. Details: {exc}")
    return audit_service.filter_audit(filters)

def safe_search_records(dictionary_service: DictionaryService, term: str = "", portfolio: str = "ALL", section: str = "") -> list[dict]:
    """Load records without leaving the main grid blank because of connection/config issues.

    In DB-enabled mode the DB remains the primary source. If the DB call fails, the UI
    shows sample records plus a warning so users can still verify screens/buttons.
    """
    try:
        return dictionary_service.search_records(term=term, portfolio=portfolio, section=section)
    except Exception as exc:
        st.warning(f"Could not fetch records from configured database. Showing sample data. Details: {exc}")
        records = get_sample_records()
        portfolio_field_map = {
            "FI Banks": "required_by_banks",
            "Corporates": "required_by_corporates",
            "FI Insurance": "required_by_insurance",
            "Zeus Downstream": "required_by_downstream",
        }
        field_name = portfolio_field_map.get(portfolio)
        if field_name:
            records = [record for record in records if bool(record.get(field_name))]
        if section:
            records = [record for record in records if record.get("where_in_financial_statement") == section]
        if term:
            term_lower = term.lower()
            records = [
                record for record in records
                if term_lower in str(record.get("prj_id", "")).lower()
                or term_lower in str(record.get("prj_attribute_name", "")).lower()
                or term_lower in str(record.get("prj_attribute_description", "")).lower()
            ]
        return records




def safe_soft_deleted_records(dictionary_service: DictionaryService) -> list[dict]:
    """Load inactive master records for reactivate workflow without breaking the UI."""
    try:
        return dictionary_service.get_soft_deleted_records()
    except Exception as exc:
        st.warning(f"Could not fetch soft deleted records from configured database. Details: {exc}")
        return []


def get_selected_prj_id_from_grid(selection_event, grid_records: list[dict]) -> str:
    """Return PRJ ID selected from a Streamlit dataframe selection event.

    Streamlit reruns the script after row selection. This helper keeps the UI
    independent of a separate dropdown and uses the selected row from the grid.
    """
    try:
        selected_rows = selection_event.selection.rows
    except Exception:
        try:
            selected_rows = selection_event.get("selection", {}).get("rows", [])
        except Exception:
            selected_rows = []

    if not selected_rows:
        return ""

    selected_index = selected_rows[0]
    if selected_index is None or selected_index >= len(grid_records):
        return ""

    return str(grid_records[selected_index].get("prj_id") or "").strip()


def boolean_label(value: bool | None) -> str:
    if value is None:
        return ""
    return "Yes" if bool(value) else "No"


def get_existing_value(record: dict | None, field: str, default=None):
    if not record:
        return default
    return record.get(field, default)


def build_attribute_form(record: dict | None = None, read_only: bool = False, mode: str = "CREATE") -> dict:
    disabled_prj = read_only or mode == "EDIT"
    disabled = read_only
    key_prefix = f"attribute_{mode.lower()}_{'readonly' if read_only else 'editable'}"

    with st.form(f"{mode.lower()}_attribute_form_{'readonly' if read_only else 'editable'}"):
        c1, c2, c3 = st.columns(3)
        with c1:
            prj_id = st.text_input("PRJ ID *", value=str(get_existing_value(record, "prj_id", "") or ""), disabled=disabled_prj, key=f"{key_prefix}_prj_id")
        with c2:
            prj_attribute_name = st.text_input(
                "Attribute Name *",
                value=str(get_existing_value(record, "prj_attribute_name", "") or ""),
                disabled=disabled,
                key=f"{key_prefix}_attribute_name",
            )
        with c3:
            current_section = get_existing_value(record, "where_in_financial_statement", SECTION_OPTIONS[0]) or SECTION_OPTIONS[0]
            if current_section not in SECTION_OPTIONS:
                current_section = SECTION_OPTIONS[0]
            where_in_financial_statement = st.selectbox(
                "Section / Where in financial statement *",
                SECTION_OPTIONS,
                index=SECTION_OPTIONS.index(current_section),
                disabled=disabled,
                key=f"{key_prefix}_section",
            )

        prj_attribute_description = st.text_area(
            "PRJ Attribute Description",
            value=str(get_existing_value(record, "prj_attribute_description", "") or ""),
            disabled=disabled,
            key=f"{key_prefix}_description",
        )
        c4, c5, c6 = st.columns(3)
        with c4:
            prj_physical_attribute_name = st.text_input(
                "PRJ Physical Attribute Name",
                value=str(get_existing_value(record, "prj_physical_attribute_name", "") or ""),
                disabled=disabled,
                key=f"{key_prefix}_physical_name",
            )
            percentage_ratio = st.text_input(
                "Percentage(%) / Ratio(X)",
                value=str(get_existing_value(record, "percentage_ratio", "") or ""),
                disabled=disabled,
                key=f"{key_prefix}_percentage_ratio",
            )
            version_update = st.text_input(
                "Version Update",
                value=str(get_existing_value(record, "version_update", "") or ""),
                disabled=disabled,
                key=f"{key_prefix}_version_update",
            )
        with c5:
            editable = st.checkbox("Editable?", value=bool(get_existing_value(record, "editable", False)), disabled=disabled, key=f"{key_prefix}_editable")
            required_by_corporates = st.checkbox(
                "Required by Corporates?",
                value=bool(get_existing_value(record, "required_by_corporates", False)),
                disabled=disabled,
                key=f"{key_prefix}_required_by_corporates",
            )
            required_by_banks = st.checkbox(
                "Required by FI Banks?",
                value=bool(get_existing_value(record, "required_by_banks", False)),
                disabled=disabled,
                key=f"{key_prefix}_required_by_banks",
            )
        with c6:
            required_by_insurance = st.checkbox(
                "Required by FI Insurance?",
                value=bool(get_existing_value(record, "required_by_insurance", False)),
                disabled=disabled,
                key=f"{key_prefix}_required_by_insurance",
            )
            required_by_downstream = st.checkbox(
                "Required by Zeus Downstream?",
                value=bool(get_existing_value(record, "required_by_downstream", False)),
                disabled=disabled,
                key=f"{key_prefix}_required_by_downstream",
            )
            editable_in_historicals = st.checkbox(
                "Editable in Historicals",
                value=bool(get_existing_value(record, "editable_in_historicals", False)),
                disabled=disabled,
                key=f"{key_prefix}_editable_in_historicals",
            )

        with st.expander("Additional Master / Business Logic Fields", expanded=False):
            a1, a2, a3 = st.columns(3)
            with a1:
                release_scope = st.text_input("Release Scope", value=str(get_existing_value(record, "release_scope", "") or ""), disabled=disabled, key=f"{key_prefix}_release_scope")
                mapping_type = st.text_input("Mapping Type", value=str(get_existing_value(record, "mapping_type", "") or ""), disabled=disabled, key=f"{key_prefix}_mapping_type")
                calculation_in_prj = st.text_input("Calculation in PRJ", value=str(get_existing_value(record, "calculation_in_prj", "") or ""), disabled=disabled, key=f"{key_prefix}_calculation_in_prj")
                sign_flipping = st.checkbox("Sign Flipping", value=bool(get_existing_value(record, "sign_flipping", False)), disabled=disabled, key=f"{key_prefix}_sign_flipping")
            with a2:
                gc_template_attribute_name = st.text_input("GC Template attribute name", value=str(get_existing_value(record, "gc_template_attribute_name", "") or ""), disabled=disabled, key=f"{key_prefix}_gc_template_attribute_name")
                sp_standardisation_attribute_name = st.text_input("S&P Standardisation attribute name", value=str(get_existing_value(record, "sp_standardisation_attribute_name", "") or ""), disabled=disabled, key=f"{key_prefix}_sp_standardisation_attribute_name")
                sp_standardisation_dataitem_id = st.text_input("S&P Standardisation dataitem id", value=str(get_existing_value(record, "sp_standardisation_dataitem_id", "") or ""), disabled=disabled, key=f"{key_prefix}_sp_standardisation_dataitem_id")
                sp_as_reported_dataitem_id = st.text_input("S&P As-Reported dataitem ID", value=str(get_existing_value(record, "sp_as_reported_dataitem_id", "") or ""), disabled=disabled, key=f"{key_prefix}_sp_as_reported_dataitem_id")
            with a3:
                zeus_attribute = st.text_input("Zeus attribute", value=str(get_existing_value(record, "zeus_attribute", "") or ""), disabled=disabled, key=f"{key_prefix}_zeus_attribute")
                zeus_table_name = st.text_input("Zeus table name", value=str(get_existing_value(record, "zeus_table_name", "") or ""), disabled=disabled, key=f"{key_prefix}_zeus_table_name")
                snl_dataitemid = st.text_input("SNL dataitemid", value=str(get_existing_value(record, "snl_dataitemid", "") or ""), disabled=disabled, key=f"{key_prefix}_snl_dataitemid")
                scanned_calculated = st.text_input("Scanned/Calculated", value=str(get_existing_value(record, "scanned_calculated", "") or ""), disabled=disabled, key=f"{key_prefix}_scanned_calculated")
            calculation_logic = st.text_area("Calculation Logic", value=str(get_existing_value(record, "calculation_logic", "") or ""), disabled=disabled, key=f"{key_prefix}_calculation_logic")
            updates = st.text_area("Updates", value=str(get_existing_value(record, "updates", "") or ""), disabled=disabled, key=f"{key_prefix}_updates")
            zeus_description = st.text_area("Zeus Description", value=str(get_existing_value(record, "zeus_description", "") or ""), disabled=disabled, key=f"{key_prefix}_zeus_description")
            comments = st.text_area("Comments", value=str(get_existing_value(record, "comments", "") or ""), disabled=disabled, key=f"{key_prefix}_comments")

        submitted = st.form_submit_button("Create Attribute" if mode == "CREATE" else "Upload", disabled=read_only)

    return {
        "submitted": submitted,
        "record": {
            "prj_id": prj_id.strip(),
            "prj_attribute_name": prj_attribute_name.strip(),
            "prj_attribute_description": prj_attribute_description,
            "prj_physical_attribute_name": prj_physical_attribute_name,
            "editable": editable,
            "percentage_ratio": percentage_ratio,
            "calculation_logic": calculation_logic,
            "where_in_financial_statement": where_in_financial_statement,
            "required_by_corporates": required_by_corporates,
            "required_by_banks": required_by_banks,
            "required_by_insurance": required_by_insurance,
            "required_by_downstream": required_by_downstream,
            "version_update": version_update,
            "release_scope": release_scope,
            "mapping_type": mapping_type,
            "calculation_in_prj": calculation_in_prj,
            "editable_in_historicals": editable_in_historicals,
            "sign_flipping": sign_flipping,
            "gc_template_attribute_name": gc_template_attribute_name,
            "sp_standardisation_attribute_name": sp_standardisation_attribute_name,
            "sp_standardisation_dataitem_id": sp_standardisation_dataitem_id,
            "sp_as_reported_dataitem_id": sp_as_reported_dataitem_id,
            "updates": updates,
            "updated_on": None,
            "zeus_attribute": zeus_attribute,
            "zeus_table_name": zeus_table_name,
            "zeus_description": zeus_description,
            "comments": comments,
            "snl_dataitemid": snl_dataitemid,
            "scanned_calculated": scanned_calculated,
        },
    }


def validate_attribute_payload(payload: dict) -> list[str]:
    errors: list[str] = []
    if not payload.get("prj_id"):
        errors.append("PRJ ID is mandatory.")
    if not payload.get("prj_attribute_name"):
        errors.append("Attribute Name is mandatory.")
    if not payload.get("where_in_financial_statement"):
        errors.append("Section / Where in financial statement is mandatory.")
    return errors


def init_state():
    defaults = {
        "dictionary_records": [],
        "selected_portfolio": "ALL",
        "create_mode": False,
        "selected_record": None,
        "selected_active_prj_id": "",
        "edit_mode": False,
        "open_create_modal": False,
        "open_edit_modal": False,
        "last_result": None,
        "last_s3_result": None,
        "show_soft_deleted": False,
        "selected_user_role": "Admin",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def get_query_param(name: str, default: str = "") -> str:
    """Read a Streamlit query parameter safely across Streamlit versions."""
    try:
        value = st.query_params.get(name, default)
    except Exception:
        value = default
    if isinstance(value, list):
        return str(value[0]) if value else default
    return str(value or default)


def clear_popup_state() -> None:
    """Reset modal state so closed popups do not reopen during Streamlit reruns."""
    st.session_state.create_mode = False
    st.session_state.edit_mode = False
    st.session_state.open_create_modal = False
    st.session_state.open_edit_modal = False


def new_window_link(label: str, href: str) -> None:
    """Render a browser-tab link because Streamlit modals are not native resizable windows."""
    html = (
        f'<a href="{href}" target="_blank" rel="noopener noreferrer">'
        f'<button style="border:1px solid #ccc;border-radius:6px;padding:0.45rem 0.75rem;'
        f'background:#fff;cursor:pointer;">{label}</button></a>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_create_attribute_page(finalization_service: FinalizationService, user_id: str, admin: bool) -> None:
    st.title("Create New Attribute")
    st.caption("This page is opened in a separate browser tab. Resize the browser window as needed.")
    st.markdown("[Back to Data Dictionary](./)", unsafe_allow_html=True)
    if not admin:
        st.error("Only Admin users can create attributes.")
        return
    form_result = build_attribute_form(record=None, read_only=False, mode="CREATE")
    if form_result["submitted"]:
        payload = form_result["record"]
        errors = validate_attribute_payload(payload)
        if errors:
            for error in errors:
                st.error(error)
        else:
            try:
                result = finalization_service.create_attribute(payload, user_id=user_id)
                st.success(f"Attribute created. Batch ID: {result['batch_id']}")
                st.json(result)
            except Exception as exc:
                st.error(f"Create failed: {exc}")


def render_edit_attribute_page(
    dictionary_service: DictionaryService,
    finalization_service: FinalizationService,
    user_id: str,
    admin: bool,
    prj_id: str,
) -> None:
    st.title("Edit Attribute")
    st.caption("This page is opened in a separate browser tab. Resize the browser window as needed.")
    st.markdown("[Back to Data Dictionary](./)", unsafe_allow_html=True)
    if not prj_id:
        st.error("PRJ ID is required to open the edit page.")
        return
    records = safe_search_records(dictionary_service, term=prj_id, portfolio="ALL")
    selected_record = next((r for r in records if str(r.get("prj_id")) == str(prj_id)), None)
    if not selected_record:
        st.error(f"No record found for PRJ ID: {prj_id}")
        return
    if not admin:
        st.warning("You are in VIEWER mode. The record is displayed in read-only mode.")
        build_attribute_form(record=selected_record, read_only=True, mode="EDIT")
        return

    st.session_state.setdefault("full_page_edit_enabled", False)
    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("Edit", key="full_page_enable_edit"):
            st.session_state.full_page_edit_enabled = True
            st.rerun()
    read_only = not st.session_state.full_page_edit_enabled
    form_result = build_attribute_form(record=selected_record, read_only=read_only, mode="EDIT")
    if form_result["submitted"]:
        payload = form_result["record"]
        payload["prj_id"] = prj_id
        errors = validate_attribute_payload(payload)
        if errors:
            for error in errors:
                st.error(error)
        else:
            try:
                result = finalization_service.update_attribute(payload, user_id=user_id)
                st.session_state.full_page_edit_enabled = False
                st.success(f"Attribute updated. Batch ID: {result['batch_id']}")
                st.json(result)
            except Exception as exc:
                st.error(f"Update failed: {exc}")


# Environment selector must run before services are created.
base_settings = get_settings()
with st.sidebar:
    st.subheader("Runtime")
    env_names = base_settings.environment_names or ["LOCAL"]
    selected_env = st.selectbox(
        "Environment",
        env_names,
        index=env_names.index(base_settings.selected_environment) if base_settings.selected_environment in env_names else 0,
        key="sidebar_environment_selector",
    )
    apply_selected_environment(selected_env)

    auth_labels = ["Windows Logged-in User", "Kerberos Keytab", "SQL Username/Password"]
    auth_mode_to_label = {
        "windows": "Windows Logged-in User",
        "keytab": "Kerberos Keytab",
        "sql": "SQL Username/Password",
    }
    current_auth_label = auth_mode_to_label.get(get_settings().effective_sql_auth_mode, "Windows Logged-in User")
    selected_auth_label = st.selectbox(
        "DB Authentication",
        auth_labels,
        index=auth_labels.index(current_auth_label),
        key="sidebar_db_auth_selector",
        help="Default is Windows logged-in user. Select Kerberos Keytab only when krb5.conf and krb5.keytab are available on this machine/server.",
    )
    apply_selected_db_auth_mode(selected_auth_label)

    if selected_auth_label == "Kerberos Keytab":
        keytab_settings = get_settings()
        st.caption("Kerberos keytab settings")
        krb5_config_path = st.text_input(
            "krb5.conf path",
            value=keytab_settings.krb5_config_path or "security/krb5.conf",
            key="sidebar_krb5_config_path",
        )
        krb5_keytab_path = st.text_input(
            "krb5.keytab path",
            value=keytab_settings.krb5_keytab_path or "security/krb5.keytab",
            key="sidebar_krb5_keytab_path",
        )
        krb5_principal = st.text_input(
            "Kerberos principal",
            value=keytab_settings.krb5_principal or "",
            key="sidebar_krb5_principal",
        )
        krb5_cache_path = st.text_input(
            "Kerberos cache path",
            value=keytab_settings.krb5_cache_path or "krb5cc_prj_app",
            key="sidebar_krb5_cache_path",
        )
        krb5_kinit_enabled = st.checkbox(
            "Run kinit using keytab",
            value=keytab_settings.krb5_kinit_enabled,
            key="sidebar_krb5_kinit_enabled",
        )
        apply_keytab_runtime_values(
            krb5_config_path=krb5_config_path,
            krb5_keytab_path=krb5_keytab_path,
            krb5_principal=krb5_principal,
            krb5_cache_path=krb5_cache_path,
            krb5_kinit_enabled=krb5_kinit_enabled,
        )

settings = get_settings()
init_state()
user_id = current_user()
admin = is_admin_user(user_id)

dictionary_service = DictionaryService()
excel_service = ExcelService()
finalization_service = FinalizationService()
audit_service = AuditService()
s3_export_service = S3ExportService()

page_mode = get_query_param("page")
if page_mode == "create_attribute":
    render_create_attribute_page(finalization_service, user_id=user_id, admin=admin)
    st.stop()
elif page_mode == "edit_attribute":
    render_edit_attribute_page(
        dictionary_service=dictionary_service,
        finalization_service=finalization_service,
        user_id=user_id,
        admin=admin,
        prj_id=get_query_param("prj_id"),
    )
    st.stop()

create_attribute_modal = Modal("Create New Attribute", key="create_attribute_modal", max_width=1400)
edit_attribute_modal = Modal("Edit Attribute", key="edit_attribute_modal", max_width=1400)

with st.sidebar:
    st.write(f"Selected Environment: `{settings.selected_environment}`")
    st.write(f"Server: `{settings.sqlserver_server}`")
    st.write(f"Database: `{settings.sqlserver_database}`")
    st.write(f"DB Auth Mode: `{settings.effective_sql_auth_mode}`")
    st.write(f"Windows Auth: `{settings.sqlserver_windows_auth}`")
    st.write(f"Database writes: `{'ON' if settings.enable_db else 'OFF / simulated'}`")
    st.write(f"Current User: `{user_id}`")

    role_options = ["Admin", "User"]
    default_role = st.session_state.get("selected_user_role") or ("Admin" if admin else "User")
    if default_role not in role_options:
        default_role = "Admin" if admin else "User"

    selected_user_role = st.selectbox(
        "Role",
        role_options,
        index=role_options.index(default_role),
        key="sidebar_role_dropdown",
        help="Upload Document section is visible only when Role is Admin and the current user has admin permission.",
    )
    st.session_state.selected_user_role = selected_user_role
    upload_document_visible = admin and selected_user_role == "Admin"

    st.write(f"Configured Permission: `{'ADMIN' if admin else 'VIEWER'}`")
    st.write(f"Effective Role: `{selected_user_role}`")
    st.write(f"Upload Document: `{'VISIBLE' if upload_document_visible else 'HIDDEN'}`")
    st.write(f"Filter API: `{'ON' if settings.use_api_for_filters else 'OFF'}`")
    st.write(f"API Base URL: `{settings.api_base_url}`")
    if st.button("Refresh Data"):
        st.session_state.dictionary_records = safe_filter_records(dictionary_service, {"portfolios": [st.session_state.selected_portfolio], "active_only": True, "limit": 2000})
        st.success("Data refreshed")

st.title("Data Dictionary Management Admin")
st.caption("Enhanced Python-only Streamlit version with role-based upload, environment selection, audit search, create/edit, and S3 export.")
st.info("Popup forms can be closed safely. For a resizable browser window, use the Open in New Window buttons.")

if not admin:
    st.warning("You are in VIEWER mode. Create/Edit/Upload Document/S3 export actions are available only for configured Admin users.")
elif st.session_state.get("selected_user_role") != "Admin":
    st.info("Role is set to User. Upload Document section is hidden. Switch Role to Admin to view Upload Document.")

tab_dictionary, tab_audit, tab_prompts = st.tabs(["Data Dictionary", "Audit History", "Prompts Library"])

with tab_dictionary:
    st.header("Data Dictionary")
    st.caption("Filters call the Swagger API endpoint `/api/v1/dictionary/filter`. If the API process is not running, the app falls back to local service logic.")

    f1, f2, f3 = st.columns(3)
    with f1:
        selected_portfolios = st.multiselect(
            "Portfolio",
            PORTFOLIO_OPTIONS,
            default=[st.session_state.selected_portfolio] if st.session_state.selected_portfolio in PORTFOLIO_OPTIONS else ["ALL"],
            key="dictionary_filter_portfolio",
        )
        if not selected_portfolios:
            selected_portfolios = ["ALL"]
        if "ALL" in selected_portfolios and len(selected_portfolios) > 1:
            selected_portfolios = [p for p in selected_portfolios if p != "ALL"]
        overlapped_attribute = st.checkbox(
            "Overlapped Attribute",
            value=False,
            help="Shows attributes required by more than one portfolio/sector.",
            key="dictionary_filter_overlapped_attribute",
        )
    with f2:
        filter_prj_id = st.text_input("PRJ_ID", value="", key="dictionary_filter_prj_id")
        filter_attribute_name = st.text_input("Attribute Name", value="", key="dictionary_filter_attribute_name")
    with f3:
        filter_attribute_description = st.text_input("Attribute Description", value="", key="dictionary_filter_attribute_description")
        filter_section = st.selectbox("Section / Where in financial statement", [""] + SECTION_OPTIONS, key="dictionary_filter_section")

    portfolio = selected_portfolios[0] if len(selected_portfolios) == 1 else "ALL"
    st.session_state.selected_portfolio = portfolio

    dictionary_filters = {
        "portfolios": selected_portfolios,
        "portfolio_sector": selected_portfolios,
        "prj_id": filter_prj_id,
        "attribute_name": filter_attribute_name,
        "attribute_description": filter_attribute_description,
        "section": filter_section,
        "overlapped_attribute": overlapped_attribute,
        "active_only": True,
        "limit": 2000,
    }
    records = safe_filter_records(dictionary_service, dictionary_filters)
    search_text = filter_prj_id or filter_attribute_name or filter_attribute_description
    st.session_state.dictionary_records = records
    df = records_to_df(records, limited=True)

    st.subheader("Latest Master Dictionary Records")
    st.caption("Select one row from the grid, then use View/Edit or Soft Delete. No separate PRJ ID dropdown is required.")
    active_selection = st.dataframe(
        df,
        use_container_width=True,
        height=430,
        key="active_dictionary_records_grid",
        on_select="rerun",
        selection_mode="single-row",
    )
    selected_active_prj_id = get_selected_prj_id_from_grid(active_selection, records)
    if not selected_active_prj_id:
        previous_selected_prj_id = str(st.session_state.get("selected_active_prj_id") or "").strip()
        if previous_selected_prj_id and any(str(r.get("prj_id")) == previous_selected_prj_id for r in records):
            selected_active_prj_id = previous_selected_prj_id

    selected_active_record = next((r for r in records if str(r.get("prj_id")) == str(selected_active_prj_id)), None) if selected_active_prj_id else None
    st.session_state.selected_active_prj_id = selected_active_prj_id
    st.session_state.selected_record = selected_active_record

    if selected_active_prj_id:
        st.success(f"Selected PRJ ID: {selected_active_prj_id}")
    elif not df.empty:
        st.info("Select a row from the grid to enable View/Edit and Soft Delete.")

    if df.empty:
        st.info("No records found for the selected portfolio/search. Try Portfolio/Sector = ALL or Refresh Data.")

    action_cols = st.columns([1.2, 1.6, 1.2, 1.2, 3])
    with action_cols[0]:
        if st.button("Add New Attribute"):
            if not admin:
                st.error("Only Admin users can create attributes.")
                st.stop()
            st.session_state.create_mode = True
            st.session_state.selected_record = None
            st.session_state.edit_mode = False
            st.session_state.open_create_modal = True
            create_attribute_modal.open()
    with action_cols[1]:
        new_window_link("Open Create in New Window", "?page=create_attribute")
    with action_cols[2]:
        stream = excel_service.generate_template(records, settings.excel_template_version)
        st.download_button(
            "Download Excel",
            data=stream.getvalue(),
            file_name=f"data_dictionary_{portfolio.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with action_cols[3]:
        if st.button("Save Extracts to S3"):
            if not admin:
                st.error("Only Admin users can export extracts to S3.")
                st.stop()
            try:
                st.session_state.last_s3_result = s3_export_service.export_four_files(user_id)
                st.success("S3 export completed or simulated.")
            except Exception as exc:
                st.error(f"S3 export failed: {exc}")

    if upload_document_visible:
        with st.expander("Upload Document", expanded=False):
            uploaded_file = st.file_uploader("Upload predefined Data Dictionary Excel file", type=["xlsx"])
            if uploaded_file is not None:
                try:
                    uploaded_records = excel_service.parse_uploaded_file(uploaded_file.getvalue())
                    st.success(f"Uploaded file parsed successfully. Rows parsed: {len(uploaded_records)}")
                    uploaded_df = records_to_df(uploaded_records)
                    edited_upload_df = st.data_editor(uploaded_df, use_container_width=True, height=350, num_rows="dynamic")
                    if st.button("Upload Parsed Document to DB", type="primary"):
                        upload_records = [
                            {**row, "delta_type": "UPDATED"}
                            for row in df_to_records(edited_upload_df)
                            if row.get("prj_id")
                        ]
                        result = finalization_service.finalize(upload_records, user_id=user_id, source_module="UPLOAD_DOCUMENT")
                        st.session_state.last_result = result
                        st.success(f"Upload completed. Batch ID: {result['batch_id']}")
                except Exception as exc:
                    st.error(f"Upload validation failed: {exc}")

    if st.session_state.last_s3_result:
        with st.expander("Last S3 Export Result", expanded=False):
            st.json(st.session_state.last_s3_result)

    if create_attribute_modal.is_open():
        with create_attribute_modal.container():
            st.subheader("Create New Attribute")
            st.caption("Enter master attribute details. Mandatory fields are marked with *. Use Close to dismiss; it will not reopen until you click Add New Attribute again.")
            form_result = build_attribute_form(record=None, read_only=False, mode="CREATE")
            close_cols = st.columns([1, 5])
            with close_cols[0]:
                if st.button("Close", key="close_create_modal"):
                    clear_popup_state()
                    create_attribute_modal.close()
                    st.rerun()
            if form_result["submitted"]:
                payload = form_result["record"]
                errors = validate_attribute_payload(payload)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    try:
                        result = finalization_service.create_attribute(payload, user_id=user_id)
                        st.session_state.last_result = result
                        clear_popup_state()
                        create_attribute_modal.close()
                        st.success(f"Attribute created. Batch ID: {result['batch_id']}")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Create failed: {exc}")

    st.divider()
    st.subheader("Selected Attribute Actions")
    st.caption("Actions below use the row selected in the Latest Master Dictionary Records grid above.")
    b1, b2, b3, b4 = st.columns([1, 1.6, 1, 4.4])
    with b1:
        if st.button("View / Edit", disabled=not bool(selected_active_prj_id)):
            if not admin:
                st.error("Only Admin users can edit attributes.")
                st.stop()
            st.session_state.edit_mode = False
            st.session_state.open_edit_modal = True
            edit_attribute_modal.open()
    with b2:
        if selected_active_prj_id:
            new_window_link("Open Edit in New Window", f"?page=edit_attribute&prj_id={quote(str(selected_active_prj_id))}")
        else:
            st.button("Open Edit in New Window", disabled=True)
    with b3:
        if st.button("Soft Delete", disabled=not bool(selected_active_prj_id)):
            if not admin:
                st.error("Only Admin users can soft delete attributes.")
                st.stop()
            try:
                result = finalization_service.soft_delete_attribute(selected_active_prj_id, user_id=user_id)
                st.session_state.last_result = result
                st.session_state.dictionary_records = safe_search_records(
                    dictionary_service,
                    term=search_text,
                    portfolio=portfolio,
                )
                st.session_state.selected_record = None
                st.session_state.selected_active_prj_id = ""
                st.success(f"Attribute soft deleted. Batch ID: {result['batch_id']}")
                st.rerun()
            except Exception as exc:
                st.error(f"Soft delete failed: {exc}")

    if edit_attribute_modal.is_open() and st.session_state.selected_record:
        selected_record = st.session_state.selected_record
        selected_prj_id = str(selected_record.get("prj_id"))
        with edit_attribute_modal.container():
            st.subheader("Edit Attribute")
            st.caption("Record opens in read-only mode. Click Edit to make fields editable except PRJ ID. Use Close to dismiss; it will not reopen until you click View/Edit again.")
            top_cols = st.columns([1, 1, 1, 5])
            with top_cols[0]:
                if st.button("Edit", key="modal_edit_enable"):
                    st.session_state.edit_mode = True
                    st.rerun()
            with top_cols[1]:
                if st.button("Close", key="close_edit_modal"):
                    clear_popup_state()
                    edit_attribute_modal.close()
                    st.rerun()
            with top_cols[2]:
                if st.button("Soft Delete", key="modal_soft_delete"):
                    try:
                        result = finalization_service.soft_delete_attribute(selected_prj_id, user_id=user_id)
                        st.session_state.last_result = result
                        clear_popup_state()
                        edit_attribute_modal.close()
                        st.success(f"Attribute soft deleted. Batch ID: {result['batch_id']}")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Soft delete failed: {exc}")

            form_result = build_attribute_form(
                record=selected_record,
                read_only=not st.session_state.edit_mode,
                mode="EDIT",
            )
            if form_result["submitted"]:
                payload = form_result["record"]
                payload["prj_id"] = selected_prj_id
                errors = validate_attribute_payload(payload)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    try:
                        result = finalization_service.update_attribute(payload, user_id=user_id)
                        st.session_state.last_result = result
                        clear_popup_state()
                        edit_attribute_modal.close()
                        st.success(f"Attribute updated. Batch ID: {result['batch_id']}")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Update failed: {exc}")

    st.divider()
    st.subheader("Soft Deleted Records")
    sd_cols = st.columns([1.4, 1.4, 5.2])
    with sd_cols[0]:
        if st.button("View Soft Deleted Records"):
            st.session_state.show_soft_deleted = True
    with sd_cols[1]:
        if st.button("Hide Soft Deleted Records"):
            st.session_state.show_soft_deleted = False

    if st.session_state.show_soft_deleted:
        if not admin:
            st.warning("Only Admin users can reactivate soft deleted records.")

        soft_deleted_records = safe_soft_deleted_records(dictionary_service)
        if soft_deleted_records:
            soft_deleted_df = records_to_df(soft_deleted_records, limited=True)
            st.caption("Select one row from the soft-deleted grid, then click Activate Record. No separate PRJ ID dropdown is required.")
            soft_deleted_selection = st.dataframe(
                soft_deleted_df,
                use_container_width=True,
                height=300,
                key="soft_deleted_records_grid",
                on_select="rerun",
                selection_mode="single-row",
            )

            selected_deleted_prj_id = get_selected_prj_id_from_grid(
                soft_deleted_selection,
                soft_deleted_records,
            )

            if selected_deleted_prj_id:
                st.success(f"Selected soft-deleted PRJ ID: {selected_deleted_prj_id}")
            else:
                st.info("Select a row from the grid to enable activation.")

            if st.button(
                "Activate Record",
                type="primary",
                disabled=not bool(selected_deleted_prj_id),
            ):
                if not admin:
                    st.error("Only Admin users can make a soft deleted attribute active.")
                    st.stop()
                try:
                    result = finalization_service.reactivate_attribute(selected_deleted_prj_id, user_id=user_id)
                    st.session_state.last_result = result
                    st.session_state.dictionary_records = safe_search_records(
                        dictionary_service,
                        term=search_text,
                        portfolio=portfolio,
                    )
                    st.session_state.show_soft_deleted = False
                    st.success(f"Attribute reactivated and moved back to active records. Batch ID: {result['batch_id']}")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Reactivate failed: {exc}")
        else:
            st.info("No soft deleted records found. With ENABLE_DB=false this list remains empty because no DB state exists.")

    if st.session_state.last_result:
        with st.expander("Last DB Operation Result", expanded=False):
            st.json(st.session_state.last_result)

with tab_audit:
    st.header("Audit History")
    st.caption("Search audit records using the same Swagger API filter structure as the Data Dictionary page.")
    a1, a2, a3 = st.columns(3)
    with a1:
        audit_portfolios = st.multiselect("Portfolio", PORTFOLIO_OPTIONS, default=["ALL"], key="audit_portfolio_multiselect")
        if not audit_portfolios:
            audit_portfolios = ["ALL"]
        if "ALL" in audit_portfolios and len(audit_portfolios) > 1:
            audit_portfolios = [p for p in audit_portfolios if p != "ALL"]
        audit_overlapped = st.checkbox("Overlapped Attribute", value=False, key="audit_overlapped")
    with a2:
        audit_prj_id = st.text_input("PRJ_ID", key="audit_filter_prj_id")
        audit_attribute_name = st.text_input("Attribute Name", key="audit_filter_attribute_name")
    with a3:
        audit_attribute_description = st.text_input("Attribute Description", key="audit_filter_attribute_description")
        audit_section = st.selectbox("Section", [""] + SECTION_OPTIONS, key="audit_filter_section")

    include_full = st.checkbox("View full history", value=False, key="audit_filter_include_full_history")

    audit_filters = {
        "portfolios": audit_portfolios,
        "portfolio_sector": audit_portfolios,
        "prj_id": audit_prj_id,
        "attribute_name": audit_attribute_name,
        "attribute_description": audit_attribute_description,
        "section": audit_section,
        "overlapped_attribute": audit_overlapped,
        "include_full_history": include_full,
        "active_only": False,
        "limit": 2000 if include_full else 500,
    }

    if st.button("Search Audit History", type="primary") or include_full:
        try:
            audit_rows = safe_filter_audit(audit_service, audit_filters)
            if audit_rows:
                st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, height=520)
            else:
                st.info("No audit records found. If ENABLE_DB=false, audit search returns no DB data.")
        except Exception as exc:
            st.error(f"Audit search failed: {exc}")

with tab_prompts:
    st.header("Prompts Library")
    st.caption("Future-ready tab. With ENABLE_DB=true, this reads active prompts from dbo.prompt_library in read-only mode.")
    try:
        prompts = audit_service.get_prompts()
        st.dataframe(pd.DataFrame(prompts), use_container_width=True, height=520)
    except Exception as exc:
        st.error(f"Could not load prompt library: {exc}")
