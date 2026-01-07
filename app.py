import streamlit as st
import os
import platform
import json
from googleimports import load_google_data

# --- IMPORT NEW MODULES ---
from header import render_header
from main_section import render_main_section, load_status
from data_section import render_data_section

# --- PAGE CONFIG ---
st.set_page_config(page_title="Migration Mission Control", layout="wide", page_icon="🚀")

# --- UI TWEAK: COMPACT SIDEBAR ---
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        min-width: 300px;
        max-width: 300px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- CONFIGURATION MANAGER ---
CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {
        "google_path": os.path.join(os.getcwd(), "google_data"),
        "audit_path": os.path.join(os.getcwd(), "audit_reports")
    }

def save_config(google_path, audit_path):
    data = {"google_path": google_path, "audit_path": audit_path}
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
st.sidebar.title("⚙️ Settings")

if 'config_loaded' not in st.session_state:
    saved_config = load_config()
    st.session_state['google_path'] = saved_config.get("google_path", "")
    st.session_state['audit_path'] = saved_config.get("audit_path", "")
    st.session_state['config_loaded'] = True

def render_smart_path_input(title, icon, session_key, help_text):
    st.sidebar.markdown(f"### {icon} {title}")
    current_os = platform.system()
    
    if current_os == "Windows":
        col1, col2 = st.sidebar.columns([1, 2])
        with col1:
            if st.button("Browse", key=f"btn_{session_key}"):
                new_path = select_folder_windows()
                if new_path:
                    st.session_state[session_key] = new_path
                    save_config(st.session_state['google_path'], st.session_state['audit_path'])
                    st.rerun()
        with col2:
            st.sidebar.caption(f"Current: `{os.path.basename(st.session_state[session_key])}`")
    else:
        new_val = st.sidebar.text_input(
            "Paste Folder Path", 
            value=st.session_state[session_key], 
            key=f"input_{session_key}", 
            help=help_text
        )
        if new_val != st.session_state[session_key]:
             st.session_state[session_key] = new_val.strip('"').strip("'")
             save_config(st.session_state['google_path'], st.session_state['audit_path'])

    path = st.session_state[session_key]
    if os.path.isdir(path):
        st.sidebar.success(f"✅ Linked")
    else:
        st.sidebar.error("❌ Not found")
    st.sidebar.divider()

render_smart_path_input("Google Data", "📊", "google_path", "Folder with Google CSVs")
render_smart_path_input("Audit Reports", "💻", "audit_path", "Folder with Swift App CSVs")

# --- SIDEBAR: SHUTDOWN CONTROL (NEW) ---
# Since we run with --windowed, users have no console to close. 
# We MUST provide a way to kill the process.
# st.sidebar.divider()
st.sidebar.markdown("### 🛑 App Control")
st.sidebar.caption("When finished, click below to close the application safely.")

if st.sidebar.button("Quit Application", type="primary", use_container_width=True):
    st.sidebar.warning("Shutting down... You can close this tab.")
    # os._exit(0) forces an immediate, hard exit of the python process.
    os._exit(0)

# --- MAIN APP ORCHESTRATOR ---

google_folder = st.session_state['google_path']
audit_folder = st.session_state['audit_path']

save_config(google_folder, audit_folder)

if not os.path.isdir(google_folder):
    st.warning("Waiting for Google Data folder...")
    st.stop()

with st.spinner("Loading Data..."):
    google_users = load_google_data(google_folder)
    # Note: load_status is now imported from main_section.py
    status_df = load_status()

if google_users.empty:
    st.warning(f"No CSV data found in: `{google_folder}`")
    st.stop()

# 1. RENDER HEADER (Search & Progress)
selected_user = render_header(google_users, status_df)

if selected_user:
    # 2. RENDER MAIN SECTION (Dashboard)
    render_main_section(selected_user, google_users, status_df)
    
    # 3. RENDER DATA SECTION (Audit Tabs & Explorer)
    render_data_section(audit_folder, selected_user, google_users)
else:
    st.info("👋 Welcome to Mission Control! Please search for a user above to begin.")