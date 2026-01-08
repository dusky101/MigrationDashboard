import streamlit as st
import os
import platform
import json
import pandas as pd
from googleimports import load_google_data

# --- IMPORT MODULES ---
from header import render_header
from main_section import render_main_section, load_status
from data_section import render_data_section
from exporter import generate_excel_report
from migrationaud import find_audit_file
from zip_processor import process_incoming_zips # <--- NEW IMPORT

# --- PAGE CONFIG ---
st.set_page_config(page_title="Migration Mission Control", layout="wide", page_icon="🚀")

# --- UI TWEAK: COMPACT SIDEBAR ---
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { min-width: 320px; max-width: 320px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- CONFIGURATION MANAGER ---
CONFIG_FILE = "config.json"
# This is the hidden folder where the app will store the raw CSVs after unzipping
INTERNAL_CSV_STORE = os.path.join(os.getcwd(), "audit_processed_csvs")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {
        "google_path": os.path.join(os.getcwd(), "google_data"),
        "zips_path": os.path.join(os.getcwd(), "audit_zips") # Default backup
    }

def save_config(google_path, zips_path):
    data = {"google_path": google_path, "zips_path": zips_path}
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving config: {e}")

# --- HELPER: WINDOWS FOLDER PICKER ---
def select_folder_windows():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder_path = filedialog.askdirectory()
        root.destroy()
        return folder_path
    except Exception as e:
        return None

# --- SIDEBAR: SETTINGS UI ---
st.sidebar.title("⚙️ Data Sources")

if 'config_loaded' not in st.session_state:
    saved_config = load_config()
    st.session_state['google_path'] = saved_config.get("google_path", "")
    st.session_state['zips_path'] = saved_config.get("zips_path", "") # Renamed from audit_path
    st.session_state['config_loaded'] = True

def render_smart_path_input(title, icon, session_key, help_text):
    st.sidebar.markdown(f"### {icon} {title}")
    current_os = platform.system()
    
    # 1. WINDOWS: Show Browse Button + Current Path
    if current_os == "Windows":
        col1, col2 = st.sidebar.columns([1, 2])
        with col1:
            if st.button("Browse", key=f"btn_{session_key}"):
                new_path = select_folder_windows()
                if new_path:
                    st.session_state[session_key] = new_path
                    save_config(st.session_state['google_path'], st.session_state['zips_path'])
                    st.rerun()
        with col2:
            current_val = st.session_state[session_key]
            if current_val:
                st.sidebar.caption(f"...\\{os.path.basename(current_val)}")
            else:
                st.sidebar.caption("Not Set")
                
    # 2. MAC/OTHER: Show Paste Box
    else:
        new_val = st.sidebar.text_input(
            "Paste Folder Path", 
            value=st.session_state[session_key], 
            key=f"input_{session_key}", 
            help=help_text
        )
        if new_val != st.session_state[session_key]:
             st.session_state[session_key] = new_val.strip('"').strip("'")
             save_config(st.session_state['google_path'], st.session_state['zips_path'])
             st.rerun()

    # Validation
    path = st.session_state[session_key]
    if os.path.isdir(path):
        st.sidebar.success(f"✅ Linked")
    else:
        st.sidebar.warning("⚠️ Path not found")
    st.sidebar.divider()

# RENDER INPUTS
render_smart_path_input("Google CSVs", "📊", "google_path", "Folder with UserStats.csv")
render_smart_path_input("Audit Zips", "📦", "zips_path", "OneDrive folder with Zip files")

# --- MAIN APP ORCHESTRATOR ---
google_folder = st.session_state['google_path']
zips_folder = st.session_state['zips_path']

# --- AUTOMATIC ETL PROCESS ---
# If the Zips folder exists, we run the processor to extract CSVs to INTERNAL_CSV_STORE
if os.path.isdir(zips_folder):
    with st.spinner("Processing Incoming Zips..."):
        new_count = process_incoming_zips(zips_folder, INTERNAL_CSV_STORE)
        if new_count > 0:
            st.toast(f"📦 Extracted {new_count} new audit reports!", icon="✅")

# --- LOAD DATA ---
if not os.path.isdir(google_folder):
    st.warning("Waiting for Google Data folder...")
    st.stop()

with st.spinner("Loading Dashboard..."):
    google_users = load_google_data(google_folder)
    status_df = load_status()

if google_users.empty:
    st.warning(f"No CSV data found in: `{google_folder}`")
    st.stop()

# --- SIDEBAR: REPORTS ---
st.sidebar.markdown("### 📥 Reports")
if st.sidebar.button("Prepare Asset Register", help="Generates Excel for Power BI"):
    with st.spinner("Generating..."):
        # CRITICAL: We pass the internal CSV store (the unzipped files) to the exporter
        # If we passed 'zips_folder' here, the exporter would fail to find CSVs.
        excel_full = generate_excel_report(google_users, status_df, INTERNAL_CSV_STORE)
        st.session_state['full_excel'] = excel_full

if 'full_excel' in st.session_state:
    st.sidebar.download_button(
        label="📄 Download Excel",
        data=st.session_state['full_excel'],
        file_name="Migration_Asset_Register.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

st.sidebar.divider()
if st.sidebar.button("Quit Application", type="primary", use_container_width=True):
    st.sidebar.warning("Shutting down...")
    os._exit(0)

# ==============================================================================
#  MAIN DASHBOARD RENDER
# ==============================================================================

# 1. RENDER HEADER (Search & Progress)
selected_user = render_header(google_users, status_df)

if selected_user:
    # 2. RENDER MAIN SECTION (Dashboard)
    render_main_section(selected_user, google_users, status_df)
    
    # 3. RENDER DATA SECTION (Audit Tabs & Explorer)
    # CRITICAL: We pass the internal CSV store so it reads the clean CSVs
    render_data_section(INTERNAL_CSV_STORE, selected_user, google_users)
else:
    st.info("👋 Welcome to Mission Control! Please search for a user above to begin.")