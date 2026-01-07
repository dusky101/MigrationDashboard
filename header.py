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
    col_search, col_filter = st.columns([3, 1])

    # 1. Render Filter Checkbox FIRST so we can use its value
    with col_filter:
        st.write("") # Alignment spacer
        show_only_pending = st.checkbox("Hide Completed", value=False)
    
    # 2. Prepare list for the dropdown
    user_options = []
    
    # Sort users alphabetically
    sorted_users = sorted(google_users.index.tolist())

    # Mapping to look up email from display name
    display_map = {}
    
    for email in sorted_users:
        # Check Status
        s_text = "Not Started"
        if email in status_df.index:
            s_text = status_df.loc[email, "Status"]

        # FILTER LOGIC: Skip if user is complete and checkbox is ticked
        if show_only_pending and s_text == 'Complete':
            continue

        # Get Name
        row = google_users.loc[email]
        name = row.get('Admin-defined name', '')
        if pd.isna(name) or str(name).strip() == "":
            name = email.split('@')[0].title()
        
        # --- NEW STATUS EMOJI MAPPING ---
        if s_text == 'Complete': 
            status_emoji = "✅"
        elif s_text in ["Migration Run", "Migration setup completed"]: 
            status_emoji = "🚀"
        elif s_text == "Machine Audit Run":
            status_emoji = "💻"
        elif s_text == "Issues":
            status_emoji = "🚩"
        elif s_text == "In Progress": # Legacy support
            status_emoji = "🚧"
        else: 
            status_emoji = "⚪"
        
        display_label = f"{status_emoji} {name} | {email}"
        user_options.append(display_label)
        display_map[display_label] = email

    # 3. Render the Selectbox
    with col_search:
        selected_label = st.selectbox(
            "🔍 Find User", 
            options=user_options,
            index=None,
            placeholder="Type name or email to search...",
            label_visibility="collapsed"
        )

    # 4. Return the actual email address
    if selected_label:
        return display_map[selected_label]
    
    return None