import streamlit as st
import pandas as pd
import os
import platform
import json
from googleimports import load_google_data
from migrationaud import find_audit_file, parse_audit_csv
from header import render_header  # <--- NEW IMPORT

# --- PAGE CONFIG ---
st.set_page_config(page_title="Migration Mission Control", layout="wide", page_icon="🚀")

# --- UI TWEAK: COMPACT SIDEBAR ---
# Since search is gone, we can shrink the sidebar back to normal
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

# --- STATUS TRACKER FUNCTIONS ---
STATUS_FILE = "status_tracker.csv"
def load_status():
    if os.path.exists(STATUS_FILE):
        return pd.read_csv(STATUS_FILE).set_index("User")
    return pd.DataFrame(columns=["Status", "Notes"])

def save_status(email, status, notes):
    df = load_status()
    df.loc[email] = [status, notes]
    df.to_csv(STATUS_FILE, index_label="User")

# --- MAIN APP LOGIC ---

google_folder = st.session_state['google_path']
audit_folder = st.session_state['audit_path']

save_config(google_folder, audit_folder)

if not os.path.isdir(google_folder):
    st.warning("Waiting for Google Data folder...")
    st.stop()

with st.spinner("Loading Data..."):
    google_users = load_google_data(google_folder)
    status_df = load_status()

if google_users.empty:
    st.warning(f"No CSV data found in: `{google_folder}`")
    st.stop()

# --- NEW HEADER SECTION (MOVED SEARCH HERE) ---
# This replaces the sidebar search
selected_user = render_header(google_users, status_df)

if selected_user:
    user_data = google_users.loc[selected_user]
    
    full_name = user_data.get('Admin-defined name', '')
    if pd.isna(full_name) or str(full_name).strip() == "":
        full_name = selected_user.split('@')[0].replace('.', ' ').title()

    # --- HEADER: Name & Clickable Email ---
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"# 👤 {full_name}")
        st.markdown(f"**Email:** [{selected_user}](mailto:{selected_user})")

    with col_h2:
        curr_status = "Not Started"
        if selected_user in status_df.index:
            curr_status = status_df.loc[selected_user, "Status"]
        
        if curr_status == "Complete": st.success("✅ COMPLETE")
        elif curr_status == "In Progress": st.warning("🚧 IN PROGRESS")
        elif curr_status == "Issues": st.error("🚩 ISSUES")
        else: st.info("WAITING")
    
    st.divider()

    c1, c2, c3 = st.columns([1.4, 1, 1])
    
    # --- COLUMN 1: Workflow ---
    with c1:
        st.subheader("📋 Workflow")
        current_notes = status_df.loc[selected_user, "Notes"] if selected_user in status_df.index else ""
        with st.form("status_form"):
            new_status = st.selectbox("Status", ["Not Started", "In Progress", "Issues", "Complete"], index=["Not Started", "In Progress", "Issues", "Complete"].index(curr_status))
            new_notes = st.text_area("Engineer Notes", value=str(current_notes) if pd.notna(current_notes) else "", height=100)
            
            if st.form_submit_button("💾 Save", use_container_width=True):
                save_status(selected_user, new_status, new_notes)
                st.rerun()
        
        st.divider()
        
        # --- ORG UNIT DISPLAY ---
        st.markdown(f"**🏢 Organizational Unit**")
        ou_path = user_data.get('Org Unit Path', '/')
        st.code(ou_path, language="text")

        # Recent Activity
        st.write("") 
        activity = user_data.get('Recent Email Activity (30d)', 0)
        st.metric("📨 Recent Email Activity (30d)", activity)

    # --- COLUMN 2: Storage & Groups ---
    with c2:
        st.subheader("☁️ Storage")
        # Ensure values are floats before math
        try:
            drive = float(user_data.get('Drive storage used (MB)', 0))
        except: drive = 0.0
        
        try:
            mail = float(user_data.get('Gmail storage used (MB)', 0))
        except: mail = 0.0
            
        try:
            photos = float(user_data.get('Photos storage used (MB)', 0))
        except: photos = 0.0
        
        total_gb = (drive + mail + photos) / 1024 
        
        if total_gb > 30:
            st.metric("Total Usage", f"{total_gb:.2f} GB", delta="Heavy", delta_color="inverse")
        else:
            st.metric("Total Usage", f"{total_gb:.2f} GB")
        
        st.caption(f"Drive: {drive/1024:.2f} GB | Mail: {mail/1024:.2f} GB")
        
        st.divider()

        # --- INTERACTIVE GROUP POPOVERS ---
        groups_raw = user_data.get('Groups', [])
        
        if isinstance(groups_raw, str):
             groups = [g.strip() for g in groups_raw.split(',')]
        elif isinstance(groups_raw, list):
             groups = groups_raw
        else:
             groups = []
        groups = [g for g in groups if g] 
        groups.sort()

        st.subheader(f"👥 Groups ({len(groups)})")
        
        if groups:
            st.caption("Click a group to view its members.")
            
            cols = st.columns(2)
            
            for i, group_name in enumerate(groups):
                with cols[i % 2]:
                    with st.popover(group_name, use_container_width=True):
                        st.markdown(f"**Members of `{group_name}`**")
                        
                        try:
                            def is_in_group(user_groups_str):
                                if not isinstance(user_groups_str, str): return False
                                current_user_list = [g.strip() for g in user_groups_str.split(',')]
                                return group_name in current_user_list

                            members_mask = google_users['Groups'].apply(is_in_group)
                            members = google_users[members_mask].reset_index()
                            
                            if not members.empty:
                                display_df = members[['Admin-defined name', 'User']].rename(
                                    columns={'Admin-defined name': 'Name', 'User': 'Email'}
                                )
                                
                                st.dataframe(
                                    display_df, 
                                    hide_index=True,
                                    width="stretch",
                                    column_config={
                                        "Name": st.column_config.TextColumn("Name", width="medium"),
                                        "Email": st.column_config.TextColumn("Email", width="large")
                                    }
                                )
                                st.caption(f"Total: {len(members)}")
                            else:
                                st.info("No other members found.")
                        except Exception as e:
                            st.error(f"Could not load members: {e}")

        else:
            st.info("No groups found")
        
    # --- COLUMN 3: Security ---
    with c3:
        st.subheader("🛡 Security")
        
        # Role Display
        role = user_data.get('Role', 'User')
        
        if role == 'Super Admin':
            st.error(f"👑 Role: **{role}**")
        elif role == 'Delegated Admin':
            st.warning(f"🔧 Role: **{role}**")
        else:
            st.success(f"👤 Role: **{role}**")
            
        st.divider()
        
        # Account Status
        status = user_data.get('User account status', 'Unknown')
        
        if status == 'Active':
            st.success(f"Account Status: **{status}**")
        else:
            st.error(f"Account Status: **{status}**")
            
        last_login = str(user_data.get('Last Login Time', 'Never')).split('T')[0]
        st.metric("Last Login", last_login)

    st.divider()

    tab_audit, tab_explore = st.tabs(["💻 Local Audit Report", "📊 Google Data Explorer"])

    # --- TAB 1: LOCAL AUDIT (UPDATED with System Specs) ---
    with tab_audit:
        if not os.path.isdir(audit_folder):
            st.warning("Audit Folder invalid.")
        else:
            audit_path = find_audit_file(audit_folder, selected_user)
            if audit_path:
                st.success(f"**Linked:** `{os.path.basename(audit_path)}`")
                audit_df = parse_audit_csv(audit_path)
                
                if audit_df is not None:
                    # NEW TABS: Specs, Apps, Network, Printers, Devices
                    t_specs, t_apps, t_net, t_print, t_dev = st.tabs(["🖥️ Specs", "📂 Apps", "☁️ Network", "🖨 Printers", "🔌 Devices"])
                    
                    with t_specs:
                        st.caption("Hardware & System Details")
                        # Filter for 'System Specifications' (e.g. Model Identifier, Serial Number)
                        specs = audit_df[audit_df['TYPE'] == 'System Specifications']
                        if not specs.empty:
                            st.dataframe(specs[['NAME', 'DETAILS']], width="stretch", hide_index=True)
                        else:
                            st.info("No system specs found.")

                    with t_apps:
                        col_app1, col_app2 = st.columns(2)
                        with col_app1:
                            st.markdown("**User Apps (Folder)**")
                            main = audit_df[audit_df['TYPE'] == 'Applications Folder']
                            if not main.empty: st.dataframe(main[['NAME', 'DETAILS']], width="stretch", hide_index=True)
                            else: st.caption("Empty")
                        with col_app2:
                            st.markdown("**Installed / Detected Apps**")
                            # UPDATED: Includes 'Detected Applications' AND 'System Internals' from your CSV
                            other = audit_df[audit_df['TYPE'].isin(['Detected Applications', 'System Internals'])]
                            if not other.empty:
                                st.dataframe(other[['DEVELOPER', 'NAME', 'DETAILS']], width="stretch", hide_index=True)
                            else:
                                st.caption("Empty")
                    
                    with t_net:
                        net = audit_df[audit_df['TYPE'] == 'Network & Storage']
                        if not net.empty: st.dataframe(net[['NAME', 'DETAILS']], width="stretch", hide_index=True)
                        else: st.info("None")
                    
                    with t_print:
                        printr = audit_df[audit_df['TYPE'] == 'Printers']
                        if not printr.empty: st.dataframe(printr[['NAME', 'DETAILS']], width="stretch", hide_index=True)
                        else: st.info("None")
                    
                    with t_dev:
                        # UPDATED: Includes 'Built-in / System' alongside devices
                        dev = audit_df[audit_df['TYPE'].isin(['External Peripherals', 'DEVICE', 'Built-in / System'])]
                        if not dev.empty: st.dataframe(dev[['NAME', 'DETAILS']], width="stretch", hide_index=True)
                        else: st.info("None")
            else:
                st.warning(f"⚠️ No Audit File for **{selected_user}**")

    # --- TAB 2: EXPLORER ---
    with tab_explore:
        st.markdown("### 🔍 Migration Record")
        st.caption("Key user data points extracted from Google Workspace logs.")
        
        df_for_display = google_users.reset_index()
        all_cols = df_for_display.columns.tolist()
        
        preferred_cols = ['User', 'Admin-defined name', 'Role', 'User account status', 'Total storage used (MB)', 
                          'Gmail (Web) - last used time', 'Org Unit Path', 'Groups', 'External apps']
        default_cols = [c for c in preferred_cols if c in all_cols]
        
        selected_cols = st.multiselect("Select Data Points:", all_cols, default=default_cols)
        
        if selected_cols:
            storage_cols_found = [c for c in selected_cols if 'storage used (mb)' in c.lower() or 'quota' in c.lower()]
            
            use_gb = False
            if storage_cols_found:
                smart_default = False
                for c in storage_cols_found:
                    try:
                        if float(user_data.get(c, 0)) > 1024:
                            smart_default = True
                            break
                    except:
                        pass
                
                use_gb = st.toggle("Show Storage in GB", value=smart_default)
            
            data_to_show = df_for_display[selected_cols].copy()
            
            if use_gb:
                for col in storage_cols_found:
                    try:
                        val_mb = data_to_show[col].astype(float)
                        val_gb = val_mb / 1024
                        data_to_show[col] = val_gb.map('{:.2f}'.format)
                        
                        new_header = col.replace("(MB)", "(GB)").replace("(mb)", "(GB)").replace("_in_mb", "_in_gb")
                        data_to_show = data_to_show.rename(columns={col: new_header})
                    except:
                        pass

            st.dataframe(data_to_show.astype(str), width="stretch")
        else:
            st.info("Select columns above to view data.")
else:
    # --- NO USER SELECTED STATE ---
    # Show a friendly welcome message when the app first loads
    st.info("👋 Welcome to Mission Control! Please search for a user above to begin.")