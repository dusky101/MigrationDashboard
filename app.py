import streamlit as st
import os
import platform
import json
import pandas as pd
import zipfile
import shutil
import re
import tempfile
from pathlib import Path

# Optional Google loader (keep behaviour, but tolerate missing module)
try:
    from googleimports import load_google_data
except Exception:
    load_google_data = None

# --- IMPORT MODULES ---
from header import render_header
from main_section import render_main_section, load_status
from data_section import render_data_section
from exporter import generate_excel_report
from zip_processor import process_incoming_zips

# --- PAGE CONFIG ---
st.set_page_config(page_title="Migration Mission Control", layout="wide", page_icon="🚀")

# ==============================================================================
# GLOBAL UI / LAYOUT FIXES
# - Ensure the main content truly expands when the sidebar is collapsed
# - Keep a compact sidebar when expanded
# - Make the collapse/expand control stay in a sensible spot
# ==============================================================================
st.markdown(
    """
    <style>
      /* Let the main area use the full viewport width */
      section.main > div.block-container{
        max-width: 100% !important;
        padding-left: 2.0rem !important;
        padding-right: 2.0rem !important;
      }

      /* Compact sidebar width when expanded */
      [data-testid="stSidebar"]{
        min-width: 320px !important;
        max-width: 320px !important;
      }

      /* When sidebar is collapsed, do not reserve space */
      [data-testid="stSidebar"][aria-expanded="false"]{
        min-width: 0px !important;
        max-width: 0px !important;
        width: 0px !important;
      }

      /* Keep the collapse/expand chevron accessible */
      [data-testid="collapsedControl"]{
        position: fixed !important;
        top: 0.75rem !important;
        left: 0.75rem !important;
        z-index: 9999 !important;
      }

      /* A little more breathing room for wide layouts */
      @media (min-width: 1400px){
        section.main > div.block-container{
          padding-left: 2.5rem !important;
          padding-right: 2.5rem !important;
        }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# CONFIGURATION
# ==============================================================================
CONFIG_FILE = "config.json"

# Local internal folder where app stores extracted audit CSVs
INTERNAL_CSV_STORE = os.path.join(os.getcwd(), "audit_processed_csvs")
os.makedirs(INTERNAL_CSV_STORE, exist_ok=True)

# A separate temp folder for uploaded audit files (so we can still process zips cleanly)
if "UPLOAD_WORK_DIR" not in st.session_state:
    st.session_state["UPLOAD_WORK_DIR"] = tempfile.mkdtemp(prefix="mig_audit_uploads_")

UPLOAD_WORK_DIR = st.session_state["UPLOAD_WORK_DIR"]


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Remember whether Google is enabled
    return {
        "google_path": os.path.join(os.getcwd(), "google_data"),
        "zips_path": os.path.join(os.getcwd(), "audit_zips"),
        "use_google": False,
    }


def save_config(google_path, zips_path, use_google: bool):
    data = {"google_path": google_path, "zips_path": zips_path, "use_google": bool(use_google)}
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving config: {e}")


# ==============================================================================
# HELPERS
# ==============================================================================
def select_folder_windows():
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder_path = filedialog.askdirectory()
        root.destroy()
        return folder_path
    except Exception:
        return None


def render_smart_path_input(title, icon, session_key, help_text, enabled: bool = True):
    st.sidebar.markdown(f"### {icon} {title}")
    current_os = platform.system()

    if not enabled:
        st.sidebar.caption("Disabled")
        st.sidebar.divider()
        return

    # WINDOWS: Browse
    if current_os == "Windows":
        col1, col2 = st.sidebar.columns([1, 2])
        with col1:
            if st.button("Browse", key=f"btn_{session_key}"):
                new_path = select_folder_windows()
                if new_path:
                    st.session_state[session_key] = new_path
                    save_config(
                        st.session_state["google_path"],
                        st.session_state["zips_path"],
                        st.session_state["use_google"],
                    )
                    st.rerun()
        with col2:
            current_val = st.session_state[session_key]
            if current_val:
                st.sidebar.caption(f"...\\{os.path.basename(current_val)}")
            else:
                st.sidebar.caption("Not Set")

    # macOS/Linux: Paste
    else:
        new_val = st.sidebar.text_input(
            "Paste Folder Path",
            value=st.session_state[session_key],
            key=f"input_{session_key}",
            help=help_text,
        )
        if new_val != st.session_state[session_key]:
            st.session_state[session_key] = new_val.strip('"').strip("'")
            save_config(
                st.session_state["google_path"],
                st.session_state["zips_path"],
                st.session_state["use_google"],
            )
            st.rerun()

    # Validation
    path = st.session_state[session_key]
    if os.path.isdir(path):
        st.sidebar.success("✅ Linked")
    else:
        st.sidebar.warning("⚠️ Path not found")

    st.sidebar.divider()


def _save_uploaded_file(uploaded_file, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, uploaded_file.name)
    with open(dest, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return dest


def _extract_csvs_from_zip(zip_path: str, dest_dir: str) -> int:
    extracted = 0
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for member in z.namelist():
                if not member.lower().endswith(".csv"):
                    continue
                base = os.path.basename(member)
                if not base:
                    continue
                out_path = os.path.join(dest_dir, base)
                with z.open(member) as src, open(out_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                extracted += 1
    except zipfile.BadZipFile:
        st.error(f"❌ Invalid ZIP uploaded: {os.path.basename(zip_path)}")
    return extracted


def _derive_users_from_audit_folder(audit_folder: str) -> pd.DataFrame:
    if not os.path.isdir(audit_folder):
        return pd.DataFrame()

    def extract_key(filename: str) -> str:
        stem = Path(filename).stem
        m = re.search(r"([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})", stem)
        if m:
            return m.group(1).lower()

        cleaned = re.sub(r"(?i)^audit[_\-\s]*report[_\-\s]*", "", stem)
        cleaned = re.sub(r"[_\-]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
        return cleaned if cleaned else stem.lower()

    rows = []
    for f in os.listdir(audit_folder):
        if not f.lower().endswith(".csv"):
            continue
        key = extract_key(f)
        friendly = key.split("@")[0].replace(".", " ").title() if "@" in key else key.replace(".", " ").title()
        rows.append({"User": key, "Admin-defined name": friendly})

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).drop_duplicates(subset=["User"]).set_index("User")


def _merge_google_users_with_audit_users(google_users: pd.DataFrame, audit_users: pd.DataFrame) -> pd.DataFrame:
    if google_users is None or google_users.empty:
        return audit_users

    combined = google_users.copy()
    for user_key in audit_users.index:
        if user_key not in combined.index:
            combined.loc[user_key, "Admin-defined name"] = audit_users.loc[user_key].get("Admin-defined name", "")
    return combined.sort_index()


# ==============================================================================
# SIDEBAR UI
# ==============================================================================
st.sidebar.title("⚙️ Data Sources")

if "config_loaded" not in st.session_state:
    saved_config = load_config()
    st.session_state["google_path"] = saved_config.get("google_path", "")
    st.session_state["zips_path"] = saved_config.get("zips_path", "")
    st.session_state["use_google"] = bool(saved_config.get("use_google", False))
    st.session_state["config_loaded"] = True

google_loader_available = load_google_data is not None
if not google_loader_available:
    st.session_state["use_google"] = False

st.sidebar.markdown("### 📊 Google (Optional)")
use_google = st.sidebar.toggle(
    "Enable Google data",
    value=bool(st.session_state.get("use_google", False)),
    disabled=not google_loader_available,
    help="If disabled (or if no Google CSV is provided), all Google sections are hidden.",
)
if use_google != st.session_state.get("use_google"):
    st.session_state["use_google"] = use_google
    save_config(st.session_state["google_path"], st.session_state["zips_path"], st.session_state["use_google"])
    st.rerun()

# Folder paths
if st.session_state["use_google"]:
    render_smart_path_input("Google CSVs", "📊", "google_path", "Folder with UserStats.csv (optional)")
else:
    render_smart_path_input("Google CSVs", "📊", "google_path", "Optional", enabled=False)

render_smart_path_input("Audit Zips", "📦", "zips_path", "OneDrive folder with Zip files (optional)")

# Uploaders
st.sidebar.markdown("### ⬆️ Upload (Optional)")
st.sidebar.caption("Upload Audit CSV/ZIP here instead of using folder paths. Google remains optional.")

uploaded_audit_files = st.sidebar.file_uploader(
    "Audit Reports (CSV/ZIP)",
    type=["csv", "zip"],
    accept_multiple_files=True,
)

uploaded_google_csv = None
if st.session_state["use_google"]:
    uploaded_google_csv = st.sidebar.file_uploader(
        "Google Users CSV (optional)",
        type=["csv"],
        accept_multiple_files=False,
    )

st.sidebar.divider()

google_folder = st.session_state["google_path"]
zips_folder = st.session_state["zips_path"]

# ==============================================================================
# INGEST AUDIT DATA
# ==============================================================================
audit_data_available = False

if uploaded_audit_files:
    with st.spinner("Processing uploaded audit files..."):
        extracted_count = 0
        for uf in uploaded_audit_files:
            saved_path = _save_uploaded_file(uf, UPLOAD_WORK_DIR)
            if saved_path.lower().endswith(".zip"):
                extracted_count += _extract_csvs_from_zip(saved_path, INTERNAL_CSV_STORE)
            elif saved_path.lower().endswith(".csv"):
                shutil.copy(saved_path, os.path.join(INTERNAL_CSV_STORE, os.path.basename(saved_path)))
                extracted_count += 1

        if extracted_count > 0:
            st.toast(f"📦 Added {extracted_count} audit report(s) from upload.", icon="✅")

if os.path.isdir(zips_folder):
    with st.spinner("Processing Incoming Zips..."):
        new_count = process_incoming_zips(zips_folder, INTERNAL_CSV_STORE)
        if new_count > 0:
            st.toast(f"📦 Extracted {new_count} new audit reports!", icon="✅")

if os.path.isdir(INTERNAL_CSV_STORE):
    audit_csvs = [f for f in os.listdir(INTERNAL_CSV_STORE) if f.lower().endswith(".csv")]
    audit_data_available = len(audit_csvs) > 0

# ==============================================================================
# LOAD GOOGLE USERS (OPTIONAL)
# ==============================================================================
google_users = pd.DataFrame()
google_loaded = False

if st.session_state["use_google"]:
    if uploaded_google_csv is not None:
        try:
            google_users = pd.read_csv(uploaded_google_csv)
            if "User" in google_users.columns:
                google_users["User"] = google_users["User"].astype(str).str.strip().str.lower()
                google_users = google_users.set_index("User")
                google_loaded = not google_users.empty
            else:
                st.warning("⚠️ The uploaded Google CSV is missing a 'User' column. It will be ignored.")
                google_users = pd.DataFrame()
        except Exception:
            st.warning("⚠️ Unable to read uploaded Google CSV. It will be ignored.")
            google_users = pd.DataFrame()

    if google_users.empty and os.path.isdir(google_folder) and load_google_data is not None:
        with st.spinner("Loading Google data (folder)..."):
            try:
                google_users = load_google_data(google_folder)
                google_loaded = google_users is not None and not google_users.empty
            except Exception as e:
                st.sidebar.warning(f"Google folder load failed: {e}")
                google_users = pd.DataFrame()
                google_loaded = False

status_df = load_status()

audit_users_df = _derive_users_from_audit_folder(INTERNAL_CSV_STORE) if audit_data_available else pd.DataFrame()
google_users = _merge_google_users_with_audit_users(google_users, audit_users_df)

if not audit_data_available and google_users.empty:
    st.warning("Waiting for data... Upload audit files or point to folders in the sidebar.")
    st.stop()

# ==============================================================================
# SIDEBAR: REPORTS
# ==============================================================================
st.sidebar.markdown("### 📥 Reports")

if st.sidebar.button("Prepare Asset Register", help="Generates Excel for Power BI"):
    with st.spinner("Generating..."):
        excel_full = generate_excel_report(google_users, status_df, INTERNAL_CSV_STORE)
        st.session_state["full_excel"] = excel_full

if "full_excel" in st.session_state:
    st.sidebar.download_button(
        label="📄 Download Excel (Full)",
        data=st.session_state["full_excel"],
        file_name="Migration_Asset_Register.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width='stretch',
    )

st.sidebar.caption("Tip: You can export only selected users from the main page after filtering.")
st.sidebar.divider()

if st.sidebar.button("Quit Application", type="primary", width='stretch'):
    st.sidebar.warning("Shutting down...")
    os._exit(0)

# ==============================================================================
# MAIN DASHBOARD RENDER
# ==============================================================================
selected = render_header(google_users, status_df)

if selected is None:
    selected_users = []
elif isinstance(selected, list):
    selected_users = selected
else:
    selected_users = [selected]

# Export selected users (XLSX)
if selected_users:
    c1, c2, c3 = st.columns([2, 3, 7])
    with c1:
        st.subheader("📦 Export")
    with c2:
        st.caption("Exports exactly what you’ve selected.")
    with c3:
        try:
            excel_filtered = generate_excel_report(
                google_users,
                status_df,
                INTERNAL_CSV_STORE,
                filtered_indices=selected_users,
            )
            st.download_button(
                label="💾 Download XLSX (Selected Users)",
                data=excel_filtered,
                file_name="Migration_Selected_Users.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width='content',
            )
        except Exception as e:
            st.error(f"❌ Export failed: {e}")

st.divider()

if selected_users:
    # MULTI-USER MODE: collapsible sections
    if len(selected_users) > 1:
        for user_key in selected_users:
            display_name = ""
            try:
                if user_key in google_users.index:
                    display_name = str(google_users.loc[user_key].get("Admin-defined name", "")).strip()
            except Exception:
                pass

            title = f"👤 {display_name} — {user_key}" if display_name else f"👤 {user_key}"
            with st.expander(title, expanded=False):
                render_main_section(user_key, google_users, status_df, audit_folder=INTERNAL_CSV_STORE)
                render_data_section(
                    INTERNAL_CSV_STORE,
                    user_key,
                    google_users,
                    google_enabled=bool(st.session_state.get("use_google", False) and google_loaded),
                )
    else:
        user_key = selected_users[0]
        render_main_section(user_key, google_users, status_df, audit_folder=INTERNAL_CSV_STORE)
        render_data_section(
            INTERNAL_CSV_STORE,
            user_key,
            google_users,
            google_enabled=bool(st.session_state.get("use_google", False) and google_loaded),
        )
else:
    st.info("👋 Welcome to Mission Control! Please search for a user above to begin.")
