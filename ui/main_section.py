"""
Main Section Component

Renders the primary user dashboard with workflow and audit summary.
Integrates model identifier and macOS version transformations.
"""

import os
import streamlit as st
import pandas as pd

from core.audit_parser import find_audit_file, parse_audit_csv
from core.status_tracker import save_status, STATUS_OPTIONS
from models.mac_models import (
    get_friendly_model_name, 
    get_model_chip_variant,
    get_model_product_name,
    get_model_screen_size,
    get_model_year
)
from models.macos_versions import get_macos_friendly_name, supports_apple_intelligence


def _audit_summary_for_user(audit_folder: str | None, user_key: str) -> dict:
    """
    Extracts a concise audit summary with MODEL and macOS VERSION TRANSFORMATIONS.
    
    Returns dict with both friendly names and original identifiers.
    """
    summary = {
        "Model Identifier": "—",
        "Model Identifier (Raw)": "—",
        "Model Product Name": "—",
        "Model Screen Size": None,
        "Model Year": None,
        "Model Chip": "—",
        "Serial Number": "—",
        "Processor / Chip": "—",
        "Memory (RAM)": "—",
        "Hard Drive Capacity": "—",
        "Available Space": "—",
        "macOS Version": "—",
        "macOS Version (Raw)": "—",
        "Supports Apple Intelligence": False,
        "Homebrew Installed": "Unknown",
        "Logged-in User": "—",
        "Login Name": "—",
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

    # Pull specs
    summary["Hard Drive Capacity"] = get_spec("Hard Drive Capacity")
    summary["Available Space"] = get_spec("Available Space")
    summary["Memory (RAM)"] = get_spec("Memory")
    summary["Processor / Chip"] = get_spec("Processor")
    summary["Serial Number"] = get_spec("Serial Number")
    summary["Logged-in User"] = get_spec("Logged-in User")
    summary["Login Name"] = get_spec("Login Name")
    
    # MODEL IDENTIFIER TRANSFORMATION
    raw_model = get_spec("Model Identifier")
    summary["Model Identifier (Raw)"] = raw_model
    
    if raw_model and raw_model != "—":
        friendly_model = get_friendly_model_name(raw_model)
        summary["Model Identifier"] = friendly_model
        summary["Model Product Name"] = get_model_product_name(raw_model)
        summary["Model Screen Size"] = get_model_screen_size(raw_model)
        summary["Model Year"] = get_model_year(raw_model)
        summary["Model Chip"] = get_model_chip_variant(raw_model)
    else:
        summary["Model Identifier"] = "—"
        summary["Model Product Name"] = "—"
        summary["Model Chip"] = "—"
    
    # macOS VERSION TRANSFORMATION
    raw_version = get_spec("macOS Version")
    summary["macOS Version (Raw)"] = raw_version
    
    if raw_version and raw_version != "—":
        friendly_version = get_macos_friendly_name(raw_version)
        summary["macOS Version"] = friendly_version
        summary["Supports Apple Intelligence"] = supports_apple_intelligence(raw_version)
    else:
        summary["macOS Version"] = "—"
        summary["Supports Apple Intelligence"] = False

    # Homebrew detection
    type_has_homebrew = df["TYPE"].astype(str).str.contains("homebrew", case=False, na=False).any()
    name_has_homebrew = df["NAME"].astype(str).str.contains("homebrew|brew", case=False, na=False).any()

    homebrew_detail_row = df[
        df["NAME"].astype(str).str.contains("homebrew", case=False, na=False)
        | df["DETAILS"].astype(str).str.contains("homebrew", case=False, na=False)
    ]
    detail_says_yes = False
    if not homebrew_detail_row.empty:
        joined = " ".join(homebrew_detail_row["DETAILS"].astype(str).tolist()).lower()
        if any(tok in joined for tok in ["installed", "present", "true", "yes", "found"]):
            detail_says_yes = True

    if type_has_homebrew or name_has_homebrew:
        summary["Homebrew Installed"] = "Yes" if detail_says_yes or type_has_homebrew else "Yes"
    else:
        summary["Homebrew Installed"] = "No"

    return summary


def _status_badge(curr_status: str) -> None:
    """Display status badge with appropriate styling."""
    if curr_status == "Complete":
        st.success(f"✅ {curr_status}")
    elif curr_status in ["Migration Run", "Migration setup completed"]:
        st.warning(f"🚀 {curr_status}")
    elif curr_status == "Machine Audit Run":
        st.info(f"💻 {curr_status}")
    else:
        st.write(f"⚪ {curr_status}")


def render_main_section(
    selected_user: str,
    users_df: pd.DataFrame,
    status_df: pd.DataFrame,
    audit_folder: str | None = None,
) -> None:
    """
    Main user dashboard with MODEL and macOS VERSION transformations.

    Shows:
    - User header with status
    - Workflow form (narrow column)
    - Audit Summary with CLEAN model display (wide column)
    
    Args:
        selected_user: User key (email/username)
        users_df: DataFrame of users from audit data
        status_df: DataFrame of migration statuses
        audit_folder: Path to audit CSV folder
    """

    key_prefix = f"ms::{selected_user}::"

    # Pull user row
    user_data = pd.Series(dtype="object")
    if users_df is not None and selected_user in users_df.index:
        user_data = users_df.loc[selected_user]

    # Friendly name
    full_name = str(user_data.get("Admin-defined name", "")).strip()
    if not full_name:
        full_name = selected_user.replace(".", " ").title()

    # Email
    email = str(user_data.get("Email", "")).strip()
    if not email and "@" in selected_user:
        email = selected_user

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
        if email:
            st.markdown(f"**Email:** [{email}](mailto:{email})")
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
    # AUDIT SUMMARY (WIDE) WITH CLEAN MODEL DISPLAY
    # ==========================================================================
    with col_audit:
        st.subheader("🖥 Audit Summary")

        audit_summary = _audit_summary_for_user(audit_folder, selected_user)

        # MODEL DISPLAY - CLEAN BREAKDOWN
        m1, m2, m3 = st.columns(3)
        
        product_name = audit_summary.get("Model Product Name", "—")
        screen_size = audit_summary.get("Model Screen Size")
        model_year = audit_summary.get("Model Year")
        chip_variant = audit_summary.get("Model Chip", "—")
        
        with m1:
            # If unknown model
            if "⚠️" in product_name:
                st.metric("Machine Model", product_name)
            else:
                st.metric("Machine Model", product_name)
                
                # Build details line
                details = []
                if screen_size:
                    details.append(screen_size)
                if chip_variant and chip_variant != "—":
                    details.append(chip_variant)
                if model_year:
                    details.append(str(model_year))
                
                if details:
                    st.caption(" • ".join(details))
        
        m2.metric("Memory (RAM)", audit_summary.get("Memory (RAM)", "—"))
        m3.metric("Serial Number", audit_summary.get("Serial Number", "—"))

        st.write("")

        # Show raw identifier below in small text
        raw_model = audit_summary.get("Model Identifier (Raw)", "—")
        if raw_model != "—" and "⚠️" not in product_name:
            st.caption(f"*Model Identifier:* `{raw_model}`")

        st.divider()

        # LOGGED-IN USER INFO
        logged_user = audit_summary.get("Logged-in User", "—")
        login_name = audit_summary.get("Login Name", "—")
        
        if logged_user != "—" or login_name != "—":
            u1, u2 = st.columns(2)
            if logged_user != "—":
                u1.metric("Logged-in User", logged_user)
            if login_name != "—":
                u2.metric("Login Name", f"`{login_name}`")
            st.divider()

        # STORAGE + OS + HOMEBREW
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Disk Capacity", audit_summary.get("Hard Drive Capacity", "—"))
        c2.metric("Available Space", audit_summary.get("Available Space", "—"))
        
        # macOS Version (friendly) with Apple Intelligence badge
        macos_display = audit_summary.get("macOS Version", "—")
        supports_ai = audit_summary.get("Supports Apple Intelligence", False)
        
        if supports_ai and macos_display != "—":
            c3.success(f"**macOS:** {macos_display}\n🤖 Apple Intelligence")
        else:
            c3.metric("macOS Version", macos_display)
        
        # Show raw version below
        raw_version = audit_summary.get("macOS Version (Raw)", "—")
        if raw_version != "—" and macos_display != "—":
            c3.caption(f"`{raw_version}`")

        # Homebrew badge
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
