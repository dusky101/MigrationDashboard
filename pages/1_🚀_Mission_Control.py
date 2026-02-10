"""
Mission Control - Main Dashboard

Individual device management, workflow tracking, and detailed audit exploration.
"""

import streamlit as st
import pandas as pd
import os
import zipfile
import shutil
import tempfile

from ui.header import render_header
from ui.main_section import render_main_section
from ui.data_section import render_data_section
from ui.sidebar import render_sidebar
from ui.styles import get_custom_css
from export.excel_exporter import generate_excel_report
from core.zip_processor import process_incoming_zips
from data_loaders.audit_loader import load_audit_data
from core.status_tracker import load_status

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="Mission Control",
    page_icon="🚀",
    layout="wide"
)

# Apply custom CSS
st.markdown(get_custom_css(), unsafe_allow_html=True)

# Hide app.py from sidebar
st.markdown("""
<style>
    [data-testid="stSidebarNav"] ul li:first-child {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# ENSURE SESSION STATE IS INITIALIZED
# ============================================================================
if "audit_folder" not in st.session_state:
    st.session_state["audit_folder"] = os.path.join(os.getcwd(), "audit_processed_csvs")

if "UPLOAD_WORK_DIR" not in st.session_state:
    st.session_state["UPLOAD_WORK_DIR"] = tempfile.mkdtemp(prefix="mig_audit_uploads_")

INTERNAL_CSV_STORE = st.session_state["audit_folder"]
UPLOAD_WORK_DIR = st.session_state["UPLOAD_WORK_DIR"]

# ============================================================================
# FILE HANDLING HELPERS
# ============================================================================
def _save_uploaded_file(uploaded_file, dest_dir: str) -> str:
    """Save uploaded file to destination directory."""
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, uploaded_file.name)
    with open(dest, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return dest


def _extract_csvs_from_zip(zip_path: str, dest_dir: str) -> int:
    """Extract CSV files from ZIP archive."""
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


# ============================================================================
# RELOAD DATA IF NEEDED
# ============================================================================
# Check if we need to reload data
if "users_df" not in st.session_state or st.session_state.get("users_df") is None:
    users_df = pd.DataFrame()
    if os.path.isdir(INTERNAL_CSV_STORE):
        try:
            users_df = load_audit_data(INTERNAL_CSV_STORE)
        except Exception as e:
            st.error(f"Error loading audit data: {e}")
    st.session_state["users_df"] = users_df

if "status_df" not in st.session_state:
    st.session_state["status_df"] = load_status()

# Get data from session state
users_df = st.session_state.get("users_df", pd.DataFrame())
status_df = st.session_state.get("status_df", pd.DataFrame())

# ============================================================================
# RENDER SIDEBAR (with upload capability)
# ============================================================================
uploaded_audit_files = render_sidebar(users_df, status_df, INTERNAL_CSV_STORE)

# ============================================================================
# PROCESS UPLOADED FILES
# ============================================================================
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
            # Reload data
            users_df = load_audit_data(INTERNAL_CSV_STORE)
            status_df = load_status()
            st.session_state["users_df"] = users_df
            st.session_state["status_df"] = status_df
            
            st.toast(f"📦 Added {extracted_count} audit report(s) from upload.", icon="✅")
            st.rerun()

# ============================================================================
# CHECK IF DATA IS AVAILABLE
# ============================================================================
if users_df.empty:
    st.warning("⏳ No data available. Please upload audit files using the sidebar.")
    st.stop()

# ============================================================================
# MAIN DASHBOARD RENDER
# ============================================================================
selected = render_header(users_df, status_df)

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
        st.caption("Exports exactly what you've selected.")
    with c3:
        try:
            excel_filtered = generate_excel_report(
                users_df,
                status_df,
                INTERNAL_CSV_STORE,
                filtered_indices=selected_users,
            )
            st.download_button(
                label="💾 Download XLSX (Selected Users)",
                data=excel_filtered,
                file_name="Migration_Selected_Users.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as e:
            st.error(f"❌ Export failed: {e}")

st.divider()

# ============================================================================
# RENDER USER SECTIONS
# ============================================================================
if selected_users:
    if len(selected_users) > 1:
        for user_key in selected_users:
            display_name = ""
            try:
                if user_key in users_df.index:
                    display_name = str(users_df.loc[user_key].get("Admin-defined name", "")).strip()
            except Exception:
                pass

            title = f"👤 {display_name} — {user_key}" if display_name else f"👤 {user_key}"
            with st.expander(title, expanded=False):
                render_main_section(user_key, users_df, status_df, audit_folder=INTERNAL_CSV_STORE)
                render_data_section(INTERNAL_CSV_STORE, user_key)
    else:
        user_key = selected_users[0]
        render_main_section(user_key, users_df, status_df, audit_folder=INTERNAL_CSV_STORE)
        render_data_section(INTERNAL_CSV_STORE, user_key)
else:
    st.info("👋 Welcome to Mission Control! Please search for a user above to begin.")
