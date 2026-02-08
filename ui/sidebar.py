"""
Sidebar Component

Renders the sidebar with data source configuration, file uploads, and reports.
"""

import os
import platform
import streamlit as st
import pandas as pd

from export.excel_exporter import generate_excel_report


def select_folder_browser():
    """
    Open native folder browser dialog.
    
    Works cross-platform IF tkinter is installed.
    Returns None if tkinter is not available or user cancels.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)
        folder_path = filedialog.askdirectory(parent=root)
        root.destroy()
        return folder_path if folder_path else None
    except ImportError:
        st.sidebar.error("❌ Folder browser unavailable: tkinter not installed. Please use manual paste option below.")
        return None
    except Exception as e:
        st.sidebar.error(f"Could not open folder browser: {e}")
        return None


def _save_sidebar_config():
    """Save sidebar configuration to session state and config file."""
    import json
    
    CONFIG_FILE = "config.json"
    
    data = {
        "google_path": st.session_state.get("google_path", ""),
        "zips_path": st.session_state.get("zips_path", ""),
        "use_google": bool(st.session_state.get("use_google", False))
    }
    
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving config: {e}")


def _check_tkinter_available() -> bool:
    """Check if tkinter is available."""
    try:
        import tkinter
        return True
    except ImportError:
        return False


def render_folder_input(
    title: str, 
    icon: str, 
    session_key: str, 
    help_text: str, 
    enabled: bool = True,
    show_info: bool = False,
    info_text: str = ""
):
    """
    Render folder path input with Browse button (if tkinter available) and manual paste option.
    
    Args:
        title: Display title
        icon: Emoji icon
        session_key: Session state key for this path
        help_text: Help text for manual input
        enabled: Whether this input is enabled
        show_info: Whether to show info icon
        info_text: Info popup text
    """
    # Header with optional info icon
    if show_info and info_text:
        col_title, col_info = st.sidebar.columns([4, 1])
        with col_title:
            st.sidebar.markdown(f"### {icon} {title}")
        with col_info:
            st.sidebar.markdown("")  # Spacer for alignment
            with st.popover("ℹ️"):
                st.info(info_text)
    else:
        st.sidebar.markdown(f"### {icon} {title}")
    
    if not enabled:
        st.sidebar.caption("Disabled")
        st.sidebar.divider()
        return

    current_os = platform.system()
    tkinter_available = _check_tkinter_available()

    # Show Browse button only if tkinter is available
    if tkinter_available:
        col1, col2 = st.sidebar.columns([1, 2])
        
        with col1:
            if st.button("Browse", key=f"btn_{session_key}", width='stretch'):
                new_path = select_folder_browser()
                
                if new_path:
                    st.session_state[session_key] = new_path
                    _save_sidebar_config()
                    st.rerun()
        
        with col2:
            current_val = st.session_state.get(session_key, "")
            if current_val and os.path.isdir(current_val):
                display_name = os.path.basename(current_val)
                if current_os == "Windows":
                    st.sidebar.caption(f"...\\{display_name}")
                else:
                    st.sidebar.caption(f".../{display_name}")
            else:
                st.sidebar.caption("Not Set")

        # Collapsible manual paste
        with st.sidebar.expander("📝 Or paste path manually", expanded=False):
            new_val = st.text_input(
                "Folder Path",
                value=st.session_state.get(session_key, ""),
                key=f"input_{session_key}",
                help=help_text,
                label_visibility="collapsed"
            )
            if new_val and new_val != st.session_state.get(session_key):
                cleaned_path = new_val.strip('"').strip("'").strip()
                st.session_state[session_key] = cleaned_path
                _save_sidebar_config()
                st.rerun()
    else:
        # Fallback: No Browse button, just text input (like old macOS behavior)
        st.sidebar.caption("💡 Paste folder path below (tkinter not available for Browse button)")
        
        new_val = st.sidebar.text_input(
            "Folder Path",
            value=st.session_state.get(session_key, ""),
            key=f"input_{session_key}",
            help=help_text,
            label_visibility="collapsed",
            placeholder="Paste full folder path here..."
        )
        if new_val and new_val != st.session_state.get(session_key):
            cleaned_path = new_val.strip('"').strip("'").strip()
            st.session_state[session_key] = cleaned_path
            _save_sidebar_config()
            st.rerun()

    # Validation
    path = st.session_state.get(session_key, "")
    if path:
        if os.path.isdir(path):
            st.sidebar.success("✅ Linked")
        else:
            st.sidebar.warning("⚠️ Path not found")

    st.sidebar.divider()


def render_sidebar(google_users: pd.DataFrame, status_df: pd.DataFrame, audit_folder: str):
    """
    Render complete sidebar with all configuration options.
    
    Args:
        google_users: DataFrame of Google user data
        status_df: DataFrame of migration statuses
        audit_folder: Path to audit CSV folder (for exports)
        
    Returns:
        Tuple of (uploaded_audit_files, uploaded_google_csv)
    """
    
    st.sidebar.title("⚙️ Data Sources")

    # =========================================================================
    # GOOGLE DATA TOGGLE
    # =========================================================================
    st.sidebar.markdown("### 📊 Google (Optional)")
    
    use_google = st.sidebar.toggle(
        "Enable Google data",
        value=bool(st.session_state.get("use_google", False)),
        help="If disabled (or if no Google CSV is provided), all Google sections are hidden.",
    )
    
    if use_google != st.session_state.get("use_google"):
        st.session_state["use_google"] = use_google
        _save_sidebar_config()
        st.rerun()

    # =========================================================================
    # FOLDER PATH INPUTS
    # =========================================================================
    if st.session_state.get("use_google", False):
        render_folder_input(
            "Google CSVs",
            "📊",
            "google_path",
            "Folder with UserStats.csv (optional)"
        )
    else:
        render_folder_input(
            "Google CSVs",
            "📊",
            "google_path",
            "Optional",
            enabled=False
        )

    # Audit Zips with info icon
    render_folder_input(
        "Audit Zips Folder",
        "📦",
        "zips_path",
        "OneDrive folder with Zip files (optional)",
        show_info=True,
        info_text="""
        **Audit Zips Folder Setup:**
        
        Point this to a folder where audit report ZIP files are automatically saved (e.g., from OneDrive sync or network drive).
        
        The app will:
        - Monitor this folder for new ZIP files
        - Automatically extract audit CSVs
        - Add them to the dashboard
        
        **Tip:** Leave empty if you prefer to upload files manually using the upload section below.
        """
    )

    # =========================================================================
    # FILE UPLOADERS (Automatic processing on upload)
    # =========================================================================
    st.sidebar.markdown("### ⬆️ Upload (Optional)")
    st.sidebar.caption("Upload Audit CSV/ZIP here instead of using folder paths. Google remains optional.")

    # Audit file uploader (always visible)
    uploaded_audit_files = st.sidebar.file_uploader(
        "Audit Reports (CSV/ZIP)",
        type=["csv", "zip"],
        accept_multiple_files=True,
        key="audit_uploader",
        help="Drag and drop files here or click Browse files"
    )

    # Google CSV uploader (only when Google is enabled)
    uploaded_google_csv = None
    if st.session_state.get("use_google", False):
        uploaded_google_csv = st.sidebar.file_uploader(
            "Google Users CSV (optional)",
            type=["csv"],
            accept_multiple_files=False,
            key="google_uploader",
            help="Drag and drop your Google Workspace export CSV"
        )

    st.sidebar.divider()

    # =========================================================================
    # REPORTS SECTION
    # =========================================================================
    st.sidebar.markdown("### 📥 Reports")

    if st.sidebar.button(
        "Prepare Asset Register", 
        help="Generates Excel for Power BI", 
        width='stretch'
    ):
        with st.spinner("Generating..."):
            try:
                excel_full = generate_excel_report(google_users, status_df, audit_folder)
                st.session_state["full_excel"] = excel_full
                st.toast("✅ Excel report ready for download!", icon="📄")
            except Exception as e:
                st.error(f"Failed to generate report: {e}")

    if "full_excel" in st.session_state:
        st.sidebar.download_button(
            label="📄 Download Excel (Full)",
            data=st.session_state["full_excel"],
            file_name="Migration_Asset_Register.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width='stretch',
        )

    st.sidebar.caption("Tip: You can export only selected users from the main page after filtering.")
    st.sidebar.divider()

    # =========================================================================
    # QUIT BUTTON
    # =========================================================================
    if st.sidebar.button("Quit Application", type="primary", width='stretch'):
        st.sidebar.warning("Shutting down...")
        os._exit(0)

    # Return uploaded files for processing in app.py
    return uploaded_audit_files, uploaded_google_csv