"""
Migration Mission Control - Entrypoint

Pure data loader and session state manager.
This page handles all data loading and immediately redirects to Mission Control.
"""

import streamlit as st
import os
import json
import pandas as pd
import zipfile
import shutil
import tempfile

# ============================================================================
# IMPORTS
# ============================================================================
from core.status_tracker import load_status
from core.zip_processor import process_incoming_zips
from data_loaders.audit_loader import load_audit_data
from ui.styles import get_custom_css

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="Migration Intelligence Platform",
    page_icon="🚀",
    layout="wide"
)

# Hide this page from sidebar navigation
st.markdown("""
<style>
    [data-testid="stSidebarNav"] ul li:first-child {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

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
        "zips_path": os.path.join(os.getcwd(), "audit_zips"),
    }


# ============================================================================
# INITIALIZE SESSION STATE
# ============================================================================
if "config_loaded" not in st.session_state:
    saved_config = load_config()
    st.session_state["zips_path"] = saved_config.get("zips_path", "")
    st.session_state["config_loaded"] = True

# ============================================================================
# INGEST AUDIT DATA
# ============================================================================
zips_folder = st.session_state.get("zips_path", "")

# Process zip files from folder
if os.path.isdir(zips_folder):
    new_count = process_incoming_zips(zips_folder, INTERNAL_CSV_STORE)
    if new_count > 0:
        st.toast(f"📦 Extracted {new_count} new audit reports!", icon="✅")

# Check if audit data exists
audit_data_available = False
if os.path.isdir(INTERNAL_CSV_STORE):
    audit_csvs = [f for f in os.listdir(INTERNAL_CSV_STORE) if f.lower().endswith(".csv")]
    audit_data_available = len(audit_csvs) > 0

# ============================================================================
# LOAD DATA INTO SESSION STATE
# ============================================================================
users_df = pd.DataFrame()

if audit_data_available:
    try:
        users_df = load_audit_data(INTERNAL_CSV_STORE)
    except Exception as e:
        st.error(f"Error loading audit data: {e}")

# Load status tracker
status_df = load_status()

# Store data in session state for pages to access
st.session_state["audit_folder"] = INTERNAL_CSV_STORE
st.session_state["users_df"] = users_df
st.session_state["status_df"] = status_df

# ============================================================================
# AUTO-REDIRECT TO MISSION CONTROL
# ============================================================================
# Automatically switch to Mission Control page
st.switch_page("pages/1_🚀_Mission_Control.py")
