"""
Header Component

Renders the top navigation bar with search, metrics, and filters.
"""

import streamlit as st
import pandas as pd


def render_header(users_df: pd.DataFrame, status_df: pd.DataFrame) -> list:
    """
    Renders the top navigation bar with Title, Metrics, and User Search.
    
    Now works with audit-derived user data only (no Google dependency).

    Args:
        users_df: DataFrame of users from audit data (indexed by user key)
        status_df: DataFrame of migration statuses
        
    Returns:
        List of selected user keys (emails/usernames)
    """

    c1, c2, c3 = st.columns([2, 1, 1])

    with c1:
        st.title("🚀 Migration Mission Control")

    with c2:
        total = len(users_df) if users_df is not None else 0

        done = 0
        if status_df is not None and not status_df.empty:
            if "Status" in status_df.columns:
                done = int((status_df["Status"] == "Complete").sum())
            else:
                done = len(status_df[status_df == "Complete"])

        percent = int((done / total) * 100) if total > 0 else 0
        st.metric("Migration Progress", f"{percent}%", f"{done}/{total} Users")

    with c3:
        st.write("")
        if st.button("🔄 Refresh Data", width='stretch'):
            st.rerun()

    st.divider()

    col_search, col_filter = st.columns([3, 1])

    with col_filter:
        st.write("")
        show_only_pending = st.checkbox("Hide Completed", value=False)
        st.caption("Tip: select multiple users for side-by-side review.")

    user_options = []
    display_map = {}

    if users_df is None or users_df.empty:
        with col_search:
            st.warning("No user index available yet. Upload audit data to begin.")
        return []

    sorted_users = sorted(users_df.index.tolist())

    for user_key in sorted_users:
        s_text = "Not Started"
        if status_df is not None and not status_df.empty and user_key in status_df.index:
            try:
                s_text = str(status_df.loc[user_key, "Status"])
            except Exception:
                pass

        if show_only_pending and s_text == "Complete":
            continue

        row = users_df.loc[user_key]
        name = row.get("Admin-defined name", "")
        if pd.isna(name) or str(name).strip() == "":
            name = str(user_key).replace(".", " ").title()

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

    with col_search:
        selected_labels = st.multiselect(
            "🔍 Find User(s)",
            options=user_options,
            default=[],
            placeholder="Type name or user key to search... (you can pick multiple)",
            label_visibility="collapsed",
        )

    selected_users = [display_map[lbl] for lbl in selected_labels if lbl in display_map]
    return selected_users
