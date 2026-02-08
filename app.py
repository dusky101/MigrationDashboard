"""
Migration Mission Control

MacBook Migration Intelligence Platform
Streamlit-based dashboard for managing device migrations with audit data analysis.
"""

import streamlit as st
import os
import json
import pandas as pd
import zipfile
import shutil
import tempfile

# ============================================================================
# NEW IMPORTS - Reorganized Structure
# ============================================================================
from core.status_tracker import load_status
from core.zip_processor import process_incoming_zips

from data_loaders.google_loader import load_google_data
from data_loaders.audit_loader import (
    derive_users_from_audit_folder,
    merge_google_and_audit_users,
)

from ui.header import render_header
from ui.main_section import render_main_section
from ui.data_section import render_data_section
from ui.styles import get_custom_css
from ui.sidebar import render_sidebar

from export.excel_exporter import generate_excel_report

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="Migration Mission Control",
    layout="wide",
    page_icon="🚀"
)

# ============================================================================
# APPLY CUSTOM CSS STYLING
# ============================================================================
st.markdown(get_custom_css(), unsafe_allow_html=True)

# ============================================================================
# CONFIGURATION
# ============================================================================
CONFIG_FILE = "config.json"

# Local internal folder where app stores extracted audit CSVs
INTERNAL_CSV_STORE = os.path.join(os.getcwd(), "audit_processed_csvs")
os.makedirs(INTERNAL_CSV_STORE, exist_ok=True)

# A separate temp folder for uploaded audit files
if "UPLOAD_WORK_DIR" not in st.session_state:
    st.session_state["UPLOAD_WORK_DIR"] = tempfile.mkdtemp(prefix="mig_audit_uploads_")

UPLOAD_WORK_DIR = st.session_state["UPLOAD_WORK_DIR"]


def load_config():
    """Load configuration from JSON file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    
    return {
        "google_path": os.path.join(os.getcwd(), "google_data"),
        "zips_path": os.path.join(os.getcwd(), "audit_zips"),
        "use_google": False,
    }


def save_config(google_path, zips_path, use_google: bool):
    """Save configuration to JSON file."""
    data = {
        "google_path": google_path,
        "zips_path": zips_path,
        "use_google": bool(use_google)
    }
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving config: {e}")


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
# INITIALIZE SESSION STATE
# ============================================================================
if "config_loaded" not in st.session_state:
    saved_config = load_config()
    st.session_state["google_path"] = saved_config.get("google_path", "")
    st.session_state["zips_path"] = saved_config.get("zips_path", "")
    st.session_state["use_google"] = bool(saved_config.get("use_google", False))
    st.session_state["config_loaded"] = True

# ============================================================================
# INGEST AUDIT DATA
# ============================================================================
google_folder = st.session_state.get("google_path", "")
zips_folder = st.session_state.get("zips_path", "")

audit_data_available = False

# Process zip files from folder
if os.path.isdir(zips_folder):
    with st.spinner("Processing Incoming Zips..."):
        new_count = process_incoming_zips(zips_folder, INTERNAL_CSV_STORE)
        if new_count > 0:
            st.toast(f"📦 Extracted {new_count} new audit reports!", icon="✅")

# Check if audit data exists
if os.path.isdir(INTERNAL_CSV_STORE):
    audit_csvs = [f for f in os.listdir(INTERNAL_CSV_STORE) if f.lower().endswith(".csv")]
    audit_data_available = len(audit_csvs) > 0

# ============================================================================
# LOAD GOOGLE USERS (OPTIONAL)
# ============================================================================
google_users = pd.DataFrame()
google_loaded = False

if st.session_state.get("use_google", False):
    if os.path.isdir(google_folder):
        with st.spinner("Loading Google data (folder)..."):
            try:
                google_users = load_google_data(google_folder)
                google_loaded = google_users is not None and not google_users.empty
            except Exception as e:
                st.sidebar.warning(f"Google folder load failed: {e}")
                google_users = pd.DataFrame()
                google_loaded = False

# Load status tracker
status_df = load_status()

# Derive users from audit files and merge with Google data
audit_users_df = derive_users_from_audit_folder(INTERNAL_CSV_STORE) if audit_data_available else pd.DataFrame()
google_users = merge_google_and_audit_users(google_users, audit_users_df)

# ============================================================================
# RENDER SIDEBAR (with actual data for reports)
# ============================================================================
uploaded_audit_files, uploaded_google_csv = render_sidebar(google_users, status_df, INTERNAL_CSV_STORE)

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
            st.toast(f"📦 Added {extracted_count} audit report(s) from upload.", icon="✅")
            st.rerun()  # Refresh to show new data

if uploaded_google_csv is not None:
    try:
        google_users_uploaded = pd.read_csv(uploaded_google_csv)
        if "User" in google_users_uploaded.columns:
            google_users_uploaded["User"] = google_users_uploaded["User"].astype(str).str.strip().str.lower()
            google_users_uploaded = google_users_uploaded.set_index("User")
            
            # Merge with existing google users
            if not google_users_uploaded.empty:
                google_users = merge_google_and_audit_users(google_users_uploaded, audit_users_df)
                google_loaded = True
                st.toast("✅ Google data uploaded successfully!", icon="📊")
        else:
            st.warning("⚠️ The uploaded Google CSV is missing a 'User' column. It will be ignored.")
    except Exception as e:
        st.warning(f"⚠️ Unable to read uploaded Google CSV: {e}")

# ============================================================================
# CHECK IF DATA IS AVAILABLE
# ============================================================================
if not audit_data_available and google_users.empty:
    st.warning("Waiting for data... Upload audit files or point to folders in the sidebar.")
    st.stop()

# ============================================================================
# MAIN DASHBOARD RENDER
# ============================================================================
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
        st.caption("Exports exactly what you've selected.")
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

# ============================================================================
# RENDER USER SECTIONS
# ============================================================================
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
        # SINGLE USER MODE: direct display
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