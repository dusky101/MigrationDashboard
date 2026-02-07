import os
import streamlit as st
import pandas as pd

from migrationaud import find_audit_file, parse_audit_csv

# --- CONSTANTS ---
STATUS_FILE = "status_tracker.csv"
STATUS_OPTIONS = [
    "Not Started",
    "Machine Audit Run",
    "Migration setup completed",
    "Migration Run",
    "Complete",
]


# -----------------------------------------------------------------------------
# STATUS FUNCTIONS
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------
def _google_data_available(google_users: pd.DataFrame) -> bool:
    """
    Determines whether we should show Google-dependent UI.
    Treat Google as 'available' only if:
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


def _audit_summary_for_user(audit_folder: str | None, user_key: str) -> dict:
    """
    Extracts a concise audit summary (System Specifications + Homebrew presence).
    Returns dict of display fields.
    """
    summary = {
        "Model Identifier": "—",
        "Serial Number": "—",
        "Processor / Chip": "—",
        "Memory (RAM)": "—",
        "Hard Drive Capacity": "—",
        "Available Space": "—",
        "macOS Version": "—",
        "Homebrew Installed": "Unknown",
    }

    if not audit_folder or not os.path.isdir(audit_folder):
        return summary

    audit_path = find_audit_file(audit_folder, user_key)
    if not audit_path:
        return summary

    df = parse_audit_csv(audit_path)
    if df is None or df.empty:
        return summary

    specs = df[df["TYPE"].astype(str).str.lower() == "system specifications"].copy()

    def get_spec(name_key: str) -> str:
        if specs.empty:
            return "—"
        row = specs[specs["NAME"].astype(str).str.contains(name_key, case=False, na=False)]
        if row.empty:
            return "—"
        return str(row.iloc[0].get("DETAILS", "—")).strip() or "—"

    # Pull exact items (best-effort)
    summary["Hard Drive Capacity"] = get_spec("Hard Drive Capacity")
    summary["Available Space"] = get_spec("Available Space")
    summary["Memory (RAM)"] = get_spec("Memory")
    summary["Processor / Chip"] = get_spec("Processor")
    summary["Serial Number"] = get_spec("Serial Number")
    summary["Model Identifier"] = get_spec("Model Identifier")
    summary["macOS Version"] = get_spec("macOS Version")

    # Homebrew detection (robust across versions)
    type_has_homebrew = df["TYPE"].astype(str).str.contains("homebrew", case=False, na=False).any()
    name_has_homebrew = df["NAME"].astype(str).str.contains("homebrew|brew", case=False, na=False).any()

    # If you have a dedicated row like "Homebrew Installed, Yes/No", this will catch it too:
    homebrew_detail_row = df[
        df["NAME"].astype(str).str.contains("homebrew", case=False, na=False)
        | df["DETAILS"].astype(str).str.contains("homebrew", case=False, na=False)
    ]
    detail_says_yes = False
    if not homebrew_detail_row.empty:
        joined = " ".join(homebrew_detail_row["DETAILS"].astype(str).tolist()).lower()
        if any(tok in joined for tok in ["installed", "present", "true", "yes", "found"]):
            detail_says_yes = True
        if any(tok in joined for tok in ["not installed", "absent", "false", "no"]):
            detail_says_yes = False

    if type_has_homebrew or name_has_homebrew:
        summary["Homebrew Installed"] = "Yes" if detail_says_yes or type_has_homebrew else "Yes"
    else:
        summary["Homebrew Installed"] = "No"

    return summary


def _status_badge(curr_status: str) -> None:
    if curr_status == "Complete":
        st.success(f"✅ {curr_status}")
    elif curr_status in ["Migration Run", "Migration setup completed"]:
        st.warning(f"🚀 {curr_status}")
    elif curr_status == "Machine Audit Run":
        st.info(f"💻 {curr_status}")
    else:
        st.write(f"⚪ {curr_status}")


# -----------------------------------------------------------------------------
# RENDER FUNCTION
# -----------------------------------------------------------------------------
def render_main_section(
    selected_user: str,
    google_users: pd.DataFrame,
    status_df: pd.DataFrame,
    audit_folder: str | None = None,
) -> None:
    """
    Main user dashboard.

    Update:
    - Workflow is narrower.
    - Adds an Audit Summary column (key machine details + Homebrew installed).
    - Google enrichment is shown below and only if Google data is actually available.
    """

    key_prefix = f"ms::{selected_user}::"
    google_enabled = _google_data_available(google_users)

    # Pull google row only if it exists
    user_data = pd.Series(dtype="object")
    if google_enabled and selected_user in google_users.index:
        user_data = google_users.loc[selected_user]

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

    # Status (from tracker)
    curr_status = "Not Started"
    if status_df is not None and not status_df.empty and selected_user in status_df.index:
        try:
            curr_status = str(status_df.loc[selected_user, "Status"])
        except Exception:
            curr_status = "Not Started"

    # --- HEADER ROW ---
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"# 👤 {full_name}")
        if "@" in selected_user:
            st.markdown(f"**Email:** [{selected_user}](mailto:{selected_user})")
        else:
            st.markdown(f"**User Key:** `{selected_user}`")

    with col_h2:
        _status_badge(curr_status)

    st.divider()

    # --- TWO-COLUMN ROW: Workflow (narrow) + Audit Summary (wide) ---
    col_workflow, col_audit = st.columns([1.1, 1.6])

    # ==========================================================================
    # WORKFLOW (NARROW)
    # ==========================================================================
    with col_workflow:
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
                height=120,
                key=f"{key_prefix}notes_text",
            )

            if st.form_submit_button("💾 Save", width='stretch'):
                save_status(selected_user, new_status, new_notes, new_entra)
                st.toast("Saved", icon="✅")
                st.rerun()

    # ==========================================================================
    # AUDIT SUMMARY (WIDE)
    # ==========================================================================
    with col_audit:
        st.subheader("🖥 Audit Summary")

        audit_summary = _audit_summary_for_user(audit_folder, selected_user)

        # Top line: key identity metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Model Identifier", audit_summary.get("Model Identifier", "—"))
        m2.metric("Memory (RAM)", audit_summary.get("Memory (RAM)", "—"))
        m3.metric("Serial Number", audit_summary.get("Serial Number", "—"))

        st.write("")

        # Secondary: storage + OS + processor + Homebrew badge
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Disk Capacity", audit_summary.get("Hard Drive Capacity", "—"))
        c2.metric("Available Space", audit_summary.get("Available Space", "—"))
        c3.metric("macOS Version", audit_summary.get("macOS Version", "—"))

        hb = str(audit_summary.get("Homebrew Installed", "Unknown"))
        if hb.lower() == "yes":
            c4.success("🍺 Homebrew: Installed")
        elif hb.lower() == "no":
            c4.info("🍺 Homebrew: Not detected")
        else:
            c4.warning("🍺 Homebrew: Unknown")

        # Processor can be long; show as a neat line
        proc = audit_summary.get("Processor / Chip", "—")
        if proc and proc != "—":
            st.caption(f"**Processor / Chip:** {proc}")

    st.divider()

    # ==========================================================================
    # GOOGLE ENRICHMENT (HIDDEN WHEN NOT AVAILABLE)
    # ==========================================================================
    if not google_enabled:
        # Nothing Google-related should appear
        return

    with st.expander("📊 Google enrichment", expanded=False):
        g1, g2 = st.columns([1.1, 1.1])

        # --- Storage & Groups ---
        with g1:
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
                cols = st.columns(2)
                for i, group_name in enumerate(groups):
                    with cols[i % 2]:
                        with st.popover(group_name, width='stretch'):
                            st.markdown(f"**Members of `{group_name}`**")

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
                                st.dataframe(display_df, hide_index=True, width='stretch')
                                st.caption(f"Total: {len(members)}")
                            else:
                                st.info("No other members found.")
            else:
                st.info("No groups found")

        # --- Security & Role ---
        with g2:
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
