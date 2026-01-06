import streamlit as st
import pandas as pd

def render_header(google_users, status_df):
    """
    Renders the top navigation bar with Title, Metrics, and User Search.
    Returns: The selected_user (str) or None
    """
    
    # --- TOP ROW: Title & Global Stats ---
    c1, c2, c3 = st.columns([2, 1, 1])
    
    with c1:
        st.title("🚀 Migration Mission Control")
    
    with c2:
        # Progress Metric
        total = len(google_users)
        done = len(status_df[status_df['Status'] == 'Complete'])
        percent = int((done / total) * 100) if total > 0 else 0
        st.metric("Migration Progress", f"{percent}%", f"{done}/{total} Users")
        
    with c3:
        # Refresh Button (Right Aligned)
        st.write("") # Spacer to align with title
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()

    st.divider()

    # --- SECOND ROW: Smart Search Bar ---
    # We combine search & select into one smart dropdown
    
    # 1. Prepare list for the dropdown (formatted nicely)
    # Format: "Jonathan Mifsud (jonathan@buddy.hr)"
    user_options = []
    
    # Sort users: Incomplete first, then by name
    # We can't easily custom sort the dropdown key, so we just sort the list alphabetically for now
    sorted_users = sorted(google_users.index.tolist())

    # Create a mapping so we can look up the email from the display name
    display_map = {}
    for email in sorted_users:
        row = google_users.loc[email]
        name = row.get('Admin-defined name', '')
        if pd.isna(name) or str(name).strip() == "":
            name = email.split('@')[0].title()
        
        # Add a status emoji to the name
        status = "⚪"
        if email in status_df.index:
            s_text = status_df.loc[email, "Status"]
            if s_text == 'Complete': status = "✅"
            elif s_text == 'In Progress': status = "🚧"
            elif s_text == 'Issues': status = "🚩"
        
        display_label = f"{status} {name} | {email}"
        user_options.append(display_label)
        display_map[display_label] = email

    # 2. Render the Selectbox in the main area (not sidebar)
    col_search, col_filter = st.columns([3, 1])
    
    with col_search:
        selected_label = st.selectbox(
            "🔍 Find User", 
            options=user_options,
            index=None,
            placeholder="Type name or email to search...",
            label_visibility="collapsed" # Hides the label text for a cleaner look
        )

    with col_filter:
        # Filter toggle
        show_only_pending = st.checkbox("Hide Completed", value=False)

    # 3. Return the actual email address of the selected user
    if selected_label:
        return display_map[selected_label]
    
    return None