"""
Sidebar Component

Renders the sidebar with audit data configuration, file uploads, and reports.
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
        "zips_path": st.session_state.get("zips_path", ""),
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
        show_info: Whether to show info icon
        info_text: Info popup text
    """
    if show_info and info_text:
        col_title, col_info = st.sidebar.columns([4, 1])
        with col_title:
            st.sidebar.markdown(f"### {icon} {title}")
        with col_info:
            st.sidebar.markdown("")
            with st.popover("ℹ️"):
                st.info(info_text)
    else:
        st.sidebar.markdown(f"### {icon} {title}")
    
    current_os = platform.system()
    tkinter_available = _check_tkinter_available()

    if tkinter_available:
        col1, col2 = st.sidebar.columns([1, 2])
        
        with col1:
            if st.button("Browse", key=f"btn_{session_key}"):
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

    path = st.session_state.get(session_key, "")
    if path:
        if os.path.isdir(path):
            st.sidebar.success("✅ Linked")
        else:
            st.sidebar.warning("⚠️ Path not found")

    st.sidebar.divider()


def render_sidebar(users_df: pd.DataFrame, status_df: pd.DataFrame, audit_folder: str):
    """
    Render complete sidebar with audit data configuration and reports.
    
    Args:
        users_df: DataFrame of users (from audit data)
        status_df: DataFrame of migration statuses
        audit_folder: Path to audit CSV folder (for exports)
        
    Returns:
        uploaded_audit_files
    """
    
    st.sidebar.title("⚙️ Data Sources")

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

    st.sidebar.markdown("### ⬆️ Upload Audit Reports")
    st.sidebar.caption("Drag and drop CSV or ZIP files here")

    uploaded_audit_files = st.sidebar.file_uploader(
        "Audit Reports (CSV/ZIP)",
        type=["csv", "zip"],
        accept_multiple_files=True,
        key="audit_uploader",
        help="Drag and drop files here or click Browse files",
        label_visibility="collapsed"
    )

    st.sidebar.divider()

    st.sidebar.markdown("### 📥 Reports")

    if st.sidebar.button(
        "Prepare Asset Register", 
        help="Generates Excel for Power BI", 
        width='stretch'
    ):
        with st.spinner("Generating..."):
            try:
                excel_full = generate_excel_report(users_df, status_df, audit_folder)
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

    if st.sidebar.button("Quit Application", type="primary", width='stretch'):
        st.sidebar.warning("Shutting down...")
        os._exit(0)

    return uploaded_audit_files
