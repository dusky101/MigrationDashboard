import os
import streamlit as st
import pandas as pd

# --- CONSTANTS ---
STATUS_FILE = "status_tracker.csv"
STATUS_OPTIONS = [
    "Not Started",
    "Machine Audit Run",
    "Migration setup completed",
    "Migration Run",
    "Complete",
]

# --- STATUS FUNCTIONS ---
def load_status() -> pd.DataFrame:
    """
    Loads the status tracker CSV.

    Enhancements:
    - Normalises index values (lowercase + strip) to reduce mismatch issues.
    - Handles backward compatibility if columns are missing.
    - Always returns a DF indexed by "User".
    """
    if os.path.exists(STATUS_FILE):
        df = pd.read_csv(STATUS_FILE)

        # Backward compatibility: if file existed without 'User' header
        if "User" not in df.columns and len(df.columns) > 0:
            df = df.rename(columns={df.columns[0]: "User"})

        if "User" in df.columns:
            df["User"] = df["User"].astype(str).str.strip().str.lower()
            df = df.set_index("User")
        else:
            return pd.DataFrame(columns=["Status", "Notes", "EntraCreated"]).set_index(
                pd.Index([], name="User")
            )

        if "Status" not in df.columns:
            df["Status"] = "Not Started"
        if "Notes" not in df.columns:
            df["Notes"] = ""
        if "EntraCreated" not in df.columns:
            df["EntraCreated"] = False

        df["Status"] = df["Status"].fillna("Not Started").astype(str)
        df["Notes"] = df["Notes"].fillna("").astype(str)
        df["EntraCreated"] = df["EntraCreated"].fillna(False).astype(bool)

        return df

    return pd.DataFrame(columns=["Status", "Notes", "EntraCreated"]).set_index(
        pd.Index([], name="User")
    )


def save_status(user_key: str, status: str, notes: str, entra_created: bool) -> None:
    """
    Saves Status, Notes, and EntraCreated flag to CSV.
    """
    user_key = str(user_key).strip().lower()
    df = load_status()

    df.loc[user_key, "Status"] = status
    df.loc[user_key, "Notes"] = notes
    df.loc[user_key, "EntraCreated"] = bool(entra_created)

    df.to_csv(STATUS_FILE, index_label="User")


def _google_data_available(google_users: pd.DataFrame) -> bool:
    """
    Determines whether we should show Google-dependent UI.
    We treat Google as 'available' only if:
      - dataframe is non-empty, AND
      - it has at least one of the typical Google columns we rely on.
    """
    if google_users is None or google_users.empty:
        return False

    google_signal_cols = {
        "Org Unit Path",
        "Drive storage used (MB)",
        "Gmail storage used (MB)",
        "Photos storage used (MB)",
        "Groups",
        "Role",
        "User account status",
        "Last Login Time",
        "Recent Email Activity (30d)",
    }
    return any(c in google_users.columns for c in google_signal_cols)


# --- RENDER FUNCTION ---
def render_main_section(selected_user: str, google_users: pd.DataFrame, status_df: pd.DataFrame) -> None:
    """
    Renders the main dashboard section for a single user.

    Updated:
    - If Google data is not available, hides the entire Google-only columns (Storage/Groups + Security/Role)
      and removes the Google-only fields from column 1.
    """
    key_prefix = f"ms::{selected_user}::"

    google_enabled = _google_data_available(google_users)

    # Pull row (audit-only users may not be in google_users; use empty Series)
    if google_enabled and selected_user in google_users.index:
        user_data = google_users.loc[selected_user]
    else:
        user_data = pd.Series(dtype="object")

    # Friendly name
    full_name = ""
    try:
        full_name = str(user_data.get("Admin-defined name", "")).strip()
    except Exception:
        full_name = ""

    if not full_name:
        if "@" in selected_user:
            full_name = selected_user.split("@")[0].replace(".", " ").title()
        else:
            full_name = selected_user.replace(".", " ").title()

    # --- HEADER: Name & Clickable Email (only if it looks like an email) ---
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"# 👤 {full_name}")
        if "@" in selected_user:
            st.markdown(f"**Email:** [{selected_user}](mailto:{selected_user})")
        else:
            st.markdown(f"**User Key:** `{selected_user}`")

    # --- TOP RIGHT: Status Badge ---
    curr_status = "Not Started"
    if status_df is not None and not status_df.empty and selected_user in status_df.index:
        try:
            curr_status = str(status_df.loc[selected_user, "Status"])
        except Exception:
            curr_status = "Not Started"

    with col_h2:
        if curr_status == "Complete":
            st.success(f"✅ {curr_status}")
        elif curr_status in ["Migration Run", "Migration setup completed"]:
            st.warning(f"🚀 {curr_status}")
        elif curr_status == "Machine Audit Run":
            st.info(f"💻 {curr_status}")
        else:
            st.write(f"⚪ {curr_status}")

    st.divider()

    # Layout: if Google is enabled, keep 3 columns. If not, show only Workflow column full width.
    if google_enabled:
        c1, c2, c3 = st.columns([1.4, 1, 1])
    else:
        c1 = st.container()
        c2 = None
        c3 = None

    # ==========================================================================
    # COLUMN 1: Workflow & Details (always shown)
    # ==========================================================================
    with c1:
        st.subheader("📋 Workflow")

        current_notes = ""
        current_entra = False

        if status_df is not None and not status_df.empty and selected_user in status_df.index:
            try:
                current_notes = status_df.loc[selected_user, "Notes"]
            except Exception:
                current_notes = ""
            try:
                val = status_df.loc[selected_user, "EntraCreated"]
                current_entra = bool(val) if pd.notna(val) else False
            except Exception:
                current_entra = False

        try:
            status_index = STATUS_OPTIONS.index(curr_status)
        except ValueError:
            status_index = 0

        with st.form(key=f"{key_prefix}status_form"):
            new_status = st.selectbox(
                "Status",
                STATUS_OPTIONS,
                index=status_index,
                key=f"{key_prefix}status_select",
            )

            new_entra = st.checkbox(
                "User created in MS Entra",
                value=current_entra,
                key=f"{key_prefix}entra_checkbox",
            )

            new_notes = st.text_area(
                "Engineer Notes",
                value=str(current_notes) if pd.notna(current_notes) else "",
                height=100,
                key=f"{key_prefix}notes_text",
            )

            if st.form_submit_button("💾 Save", use_container_width=True):
                save_status(selected_user, new_status, new_notes, new_entra)
                st.toast("Saved", icon="✅")
                st.rerun()

        st.divider()

        # Google-only extras shown only if Google is available
        if google_enabled:
            st.markdown("**🏢 Organisational Unit**")
            ou_path = user_data.get("Org Unit Path", None)
            if ou_path is None or (isinstance(ou_path, float) and pd.isna(ou_path)) or str(ou_path).strip() == "":
                st.code("/", language="text")
            else:
                st.code(str(ou_path), language="text")

            st.write("")
            activity = user_data.get("Recent Email Activity (30d)", None)
            if activity is None or (isinstance(activity, float) and pd.isna(activity)):
                st.metric("📨 Recent Email Activity (30d)", "N/A")
            else:
                st.metric("📨 Recent Email Activity (30d)", activity)

        else:
            st.caption("Google enrichment is disabled or not loaded. Only workflow/status is shown here.")

    # ==========================================================================
    # COLUMN 2: Storage & Groups (Google-only)
    # ==========================================================================
    if google_enabled and c2 is not None:
        with c2:
            st.subheader("☁️ Storage")

            def _get_mb(col_name: str) -> float:
                try:
                    return float(user_data.get(col_name, 0) or 0)
                except Exception:
                    return 0.0

            drive = _get_mb("Drive storage used (MB)")
            mail = _get_mb("Gmail storage used (MB)")
            photos = _get_mb("Photos storage used (MB)")
            total_gb = (drive + mail + photos) / 1024

            if drive == 0 and mail == 0 and photos == 0:
                st.metric("Total Usage", "N/A")
                st.caption("No Google storage data available.")
            else:
                if total_gb > 30:
                    st.metric("Total Usage", f"{total_gb:.2f} GB", delta="Heavy", delta_color="inverse")
                else:
                    st.metric("Total Usage", f"{total_gb:.2f} GB")
                st.caption(f"Drive: {drive/1024:.2f} GB | Mail: {mail/1024:.2f} GB")

            st.divider()

            groups_col_exists = "Groups" in google_users.columns
            groups_raw = user_data.get("Groups", []) if groups_col_exists else []

            if isinstance(groups_raw, str):
                groups = [g.strip() for g in groups_raw.split(",")]
            elif isinstance(groups_raw, list):
                groups = groups_raw
            else:
                groups = []

            groups = [g for g in groups if g]
            groups.sort()

            st.subheader(f"👥 Groups ({len(groups)})")

            if not groups_col_exists:
                st.info("Group membership not available.")
            elif groups:
                st.caption("Click a group to view its members.")
                cols = st.columns(2)

                for i, group_name in enumerate(groups):
                    with cols[i % 2]:
                        with st.popover(group_name, use_container_width=True):
                            st.markdown(f"**Members of `{group_name}`**")

                            try:
                                def is_in_group(user_groups_str):
                                    if not isinstance(user_groups_str, str):
                                        return False
                                    current_user_list = [g.strip() for g in user_groups_str.split(",")]
                                    return group_name in current_user_list

                                members_mask = google_users["Groups"].apply(is_in_group)
                                members = google_users[members_mask].reset_index()

                                if not members.empty:
                                    name_col = "Admin-defined name" if "Admin-defined name" in members.columns else members.columns[0]
                                    display_df = members[[name_col, "User"]].rename(columns={name_col: "Name", "User": "Email"})

                                    st.dataframe(
                                        display_df,
                                        hide_index=True,
                                        use_container_width=True,
                                        column_config={
                                            "Name": st.column_config.TextColumn("Name", width="medium"),
                                            "Email": st.column_config.TextColumn("Email", width="large"),
                                        },
                                    )
                                    st.caption(f"Total: {len(members)}")
                                else:
                                    st.info("No other members found.")
                            except Exception as e:
                                st.error(f"Could not load members: {e}")
            else:
                st.info("No groups found")

    # ==========================================================================
    # COLUMN 3: Security & Role (Google-only)
    # ==========================================================================
    if google_enabled and c3 is not None:
        with c3:
            st.subheader("🛡 Security")

            role = user_data.get("Role", None)
            if role is None or (isinstance(role, float) and pd.isna(role)) or str(role).strip() == "":
                st.info("Role: N/A")
            else:
                role = str(role)
                if role == "Super Admin":
                    st.error(f"👑 Role: **{role}**")
                elif role == "Delegated Admin":
                    st.warning(f"🔧 Role: **{role}**")
                else:
                    st.success(f"👤 Role: **{role}**")

            st.divider()

            acct_status = user_data.get("User account status", None)
            if acct_status is None or (isinstance(acct_status, float) and pd.isna(acct_status)) or str(acct_status).strip() == "":
                st.info("Account Status: N/A")
            else:
                acct_status = str(acct_status)
                if acct_status == "Active":
                    st.success(f"Account Status: **{acct_status}**")
                else:
                    st.error(f"Account Status: **{acct_status}**")

            last_login = user_data.get("Last Login Time", None)
            if last_login is None or (isinstance(last_login, float) and pd.isna(last_login)) or str(last_login).strip() == "":
                st.metric("Last Login", "N/A")
            else:
                last_login_str = str(last_login).split("T")[0]
                st.metric("Last Login", last_login_str)

    st.divider()
