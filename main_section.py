import streamlit as st
import pandas as pd
import os

# --- CONSTANTS ---
STATUS_FILE = "status_tracker.csv"
STATUS_OPTIONS = [
    "Not Started",
    "Machine Audit Run",
    "Migration setup completed",
    "Migration Run",
    "Complete"
]

# --- STATUS FUNCTIONS ---
def load_status():
    """
    Loads the status tracker CSV.
    Handles backward compatibility if the 'EntraCreated' column is missing.
    """
    if os.path.exists(STATUS_FILE):
        df = pd.read_csv(STATUS_FILE).set_index("User")
        
        # Ensure 'Status' column exists
        if "Status" not in df.columns:
            df["Status"] = "Not Started"
            
        # Ensure 'Notes' column exists
        if "Notes" not in df.columns:
            df["Notes"] = ""

        # NEW: Ensure 'EntraCreated' column exists (for backward compatibility)
        if "EntraCreated" not in df.columns:
            df["EntraCreated"] = False
            
        return df
    
    # Create empty dataframe with new schema
    return pd.DataFrame(columns=["Status", "Notes", "EntraCreated"])

def save_status(email, status, notes, entra_created):
    """Saves Status, Notes, and Entra Checkbox to CSV."""
    df = load_status()
    # Save all three values
    df.loc[email] = [status, notes, entra_created]
    df.to_csv(STATUS_FILE, index_label="User")

# --- RENDER FUNCTION ---
def render_main_section(selected_user, google_users, status_df):
    
    user_data = google_users.loc[selected_user]
    
    full_name = user_data.get('Admin-defined name', '')
    if pd.isna(full_name) or str(full_name).strip() == "":
        full_name = selected_user.split('@')[0].replace('.', ' ').title()

    # --- HEADER: Name & Clickable Email ---
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"# 👤 {full_name}")
        st.markdown(f"**Email:** [{selected_user}](mailto:{selected_user})")

    # --- TOP RIGHT: Status Badge ---
    with col_h2:
        curr_status = "Not Started"
        if selected_user in status_df.index:
            curr_status = status_df.loc[selected_user, "Status"]
        
        # Logic for new status colors
        if curr_status == "Complete": 
            st.success(f"✅ {curr_status}")
        elif curr_status in ["Migration Run", "Migration setup completed"]: 
            st.warning(f"🚀 {curr_status}")
        elif curr_status == "Machine Audit Run":
            st.info(f"💻 {curr_status}")
        else: 
            st.write(f"⚪ {curr_status}")
    
    st.divider()

    c1, c2, c3 = st.columns([1.4, 1, 1])
    
    # --- COLUMN 1: Workflow & Details ---
    with c1:
        st.subheader("📋 Workflow")
        
        # Get current values from tracker
        current_notes = ""
        current_entra = False
        
        if selected_user in status_df.index:
            current_notes = status_df.loc[selected_user, "Notes"]
            # Handle potential NaN/Missing boolean values safely
            val = status_df.loc[selected_user, "EntraCreated"]
            current_entra = bool(val) if pd.notna(val) else False

        # Determine index for dropdown (handle case where old status isn't in new list)
        try:
            status_index = STATUS_OPTIONS.index(curr_status)
        except ValueError:
            status_index = 0

        with st.form("status_form"):
            # 1. Status Dropdown
            new_status = st.selectbox("Status", STATUS_OPTIONS, index=status_index)
            
            # 2. MS Entra Checkbox
            new_entra = st.checkbox("User created in MS Entra", value=current_entra)
            
            # 3. Notes
            new_notes = st.text_area("Engineer Notes", value=str(current_notes) if pd.notna(current_notes) else "", height=100)
            
            # 4. Save Button
            if st.form_submit_button("💾 Save", use_container_width=True):
                save_status(selected_user, new_status, new_notes, new_entra)
                st.rerun()
        
        st.divider()
        
        # Org Unit
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
        try: drive = float(user_data.get('Drive storage used (MB)', 0))
        except: drive = 0.0
        try: mail = float(user_data.get('Gmail storage used (MB)', 0))
        except: mail = 0.0
        try: photos = float(user_data.get('Photos storage used (MB)', 0))
        except: photos = 0.0
        
        total_gb = (drive + mail + photos) / 1024 
        
        if total_gb > 30:
            st.metric("Total Usage", f"{total_gb:.2f} GB", delta="Heavy", delta_color="inverse")
        else:
            st.metric("Total Usage", f"{total_gb:.2f} GB")
        
        st.caption(f"Drive: {drive/1024:.2f} GB | Mail: {mail/1024:.2f} GB")
        
        st.divider()

        # Groups Popovers
        groups_raw = user_data.get('Groups', [])
        if isinstance(groups_raw, str): groups = [g.strip() for g in groups_raw.split(',')]
        elif isinstance(groups_raw, list): groups = groups_raw
        else: groups = []
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
                                st.dataframe(display_df, hide_index=True, width="stretch", column_config={
                                    "Name": st.column_config.TextColumn("Name", width="medium"),
                                    "Email": st.column_config.TextColumn("Email", width="large")
                                })
                                st.caption(f"Total: {len(members)}")
                            else:
                                st.info("No other members found.")
                        except Exception as e:
                            st.error(f"Could not load members: {e}")
        else:
            st.info("No groups found")
        
    # --- COLUMN 3: Security & Role ---
    with c3:
        st.subheader("🛡 Security")
        
        # Role Badge
        role = user_data.get('Role', 'User')
        if role == 'Super Admin': st.error(f"👑 Role: **{role}**")
        elif role == 'Delegated Admin': st.warning(f"🔧 Role: **{role}**")
        else: st.success(f"👤 Role: **{role}**")
            
        st.divider()
        
        # Account Status
        status = user_data.get('User account status', 'Unknown')
        if status == 'Active': st.success(f"Account Status: **{status}**")
        else: st.error(f"Account Status: **{status}**")
            
        last_login = str(user_data.get('Last Login Time', 'Never')).split('T')[0]
        st.metric("Last Login", last_login)

    st.divider()