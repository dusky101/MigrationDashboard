"""
Header Component

Renders the top navigation bar with search, metrics, and filters.
"""

import streamlit as st
import pandas as pd


def render_header(google_users: pd.DataFrame, status_df: pd.DataFrame) -> list:
    """
    Renders the top navigation bar with Title, Metrics, and User Search.

    Updated behaviour:
    - Uses a MULTISELECT so you can choose multiple users/devices at once.
    - Returns: List[str] of selected user keys (may be empty list)
      (For backwards compatibility with older callers, empty selection returns [])
      
    Args:
        google_users: DataFrame of users (indexed by email/user key)
        status_df: DataFrame of migration statuses
        
    Returns:
        List of selected user keys (emails)
    """

    # --- TOP ROW: Title & Global Stats ---
    c1, c2, c3 = st.columns([2, 1, 1])

    with c1:
        st.title("🚀 Migration Mission Control")

    with c2:
        total = len(google_users) if google_users is not None else 0

        # Calculate completion stats
        done = 0
        if status_df is not None and not status_df.empty:
            if "Status" in status_df.columns:
                done = int((status_df["Status"] == "Complete").sum())
            else:
                # Legacy fallback
                done = len(status_df[status_df == "Complete"])

        percent = int((done / total) * 100) if total > 0 else 0
        st.metric("Migration Progress", f"{percent}%", f"{done}/{total} Users")

    with c3:
        st.write("")  # Spacer to align with title
        if st.button("🔄 Refresh Data", width='stretch'):
            st.rerun()

    st.divider()

    # --- SECOND ROW: Smart Search Bar + Filters ---
    col_search, col_filter = st.columns([3, 1])

    with col_filter:
        st.write("")  # Alignment spacer
        show_only_pending = st.checkbox("Hide Completed", value=False)

        # Quick tip
        st.caption("Tip: select multiple users for side-by-side review.")

    # --- Prepare list for the multiselect ---
    user_options = []
    display_map = {}

    if google_users is None or google_users.empty:
        with col_search:
            st.warning("No user index available yet. Upload audit data (and optionally Google data) to begin.")
        return []

    sorted_users = sorted(google_users.index.tolist())

    for user_key in sorted_users:
        # Determine status
        s_text = "Not Started"
        if status_df is not None and not status_df.empty and user_key in status_df.index:
            try:
                s_text = str(status_df.loc[user_key, "Status"])
            except Exception:
                pass

        # Filter completed if requested
        if show_only_pending and s_text == "Complete":
            continue

        # Determine display name
        row = google_users.loc[user_key]
        name = row.get("Admin-defined name", "")
        if pd.isna(name) or str(name).strip() == "":
            if "@" in str(user_key):
                name = str(user_key).split("@")[0].replace(".", " ").title()
            else:
                name = str(user_key).replace(".", " ").title()

        # Status emoji mapping
        if s_text == "Complete":
            status_emoji = "✅"
        elif s_text in ["Migration Run", "Migration setup completed"]:
            status_emoji = "🚀"
        elif s_text == "Machine Audit Run":
            status_emoji = "💻"
        elif s_text == "Issues":
            status_emoji = "🚩"
        elif s_text == "In Progress":
            status_emoji = "🚧"
        else:
            status_emoji = "⚪"

        display_label = f"{status_emoji} {name} | {user_key}"
        user_options.append(display_label)
        display_map[display_label] = user_key

    # --- Render the MULTISELECT ---
    with col_search:
        selected_labels = st.multiselect(
            "🔍 Find User(s)",
            options=user_options,
            default=[],
            placeholder="Type name or user key to search... (you can pick multiple)",
            label_visibility="collapsed",
        )

    # Return selected keys as a list
    selected_users = [display_map[lbl] for lbl in selected_labels if lbl in display_map]
    return selected_users