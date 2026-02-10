"""
Audit Graphs Components

Reusable UI components for the Audit Graphs page.
Handles column selection, filtering, and data display.
"""

import streamlit as st
import pandas as pd
from datetime import datetime


def render_column_selector(fleet_df: pd.DataFrame) -> None:
    """
    Render the column selection UI with proper state management.
    
    Args:
        fleet_df: Full fleet DataFrame with all columns
    """
    st.markdown("#### Select Columns to Display")
    
    all_columns = list(fleet_df.columns)
    
    # Initialize widget version counter (forces widget recreation)
    if "checkbox_version" not in st.session_state:
        st.session_state["checkbox_version"] = 0
    
    # Predefined column groups
    col_groups = {
        "🆔 Identity": ["display_name", "email", "login_name"],
        "🖥️ Hardware": ["model_name", "chip_variant", "ram", "disk_capacity_gb", "apple_silicon"],
        "💾 Storage": ["available_space_gb", "used_space_gb", "storage_used_pct", "low_storage"],
        "💻 Software": ["os_version", "os_generation", "homebrew_installed", "homebrew_package_count", "app_count"],
        "📦 Applications": ["applications"],
        "✅ Compliance": ["ai_ready", "ai_supported", "low_ram"],
        "📊 Technical": ["model_identifier", "model_chip", "model_year", "serial_number", "processor", "os_version_raw"]
    }
    
    # Quick select buttons
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button("✅ Select All Columns", width='stretch', key="btn_select_all"):
            st.session_state["selected_columns"] = all_columns.copy()
            st.session_state["checkbox_version"] += 1  # Increment version to force widget recreation
            st.rerun()
    
    with col_btn2:
        if st.button("📊 Essential Columns", width='stretch', key="btn_essential"):
            essential = ["display_name", "email", "model_name", "chip_variant", "ram", 
                        "available_space_gb", "os_version", "ai_ready", "homebrew_installed", "applications"]
            st.session_state["selected_columns"] = [c for c in essential if c in all_columns]
            st.session_state["checkbox_version"] += 1  # Increment version to force widget recreation
            st.rerun()
    
    with col_btn3:
        if st.button("❌ Clear Selection", width='stretch', key="btn_clear"):
            st.session_state["selected_columns"] = []
            st.session_state["checkbox_version"] += 1  # Increment version to force widget recreation
            st.rerun()
    
    st.divider()
    
    # Get current version for checkbox keys
    version = st.session_state["checkbox_version"]
    
    # Column checkboxes by group
    for group_name, group_cols in col_groups.items():
        available_in_group = [c for c in group_cols if c in all_columns]
        if available_in_group:
            st.markdown(f"**{group_name}**")
            cols_in_row = st.columns(min(len(available_in_group), 4))
            
            for idx, col_name in enumerate(available_in_group):
                with cols_in_row[idx % len(cols_in_row)]:
                    # Check current state
                    is_checked = col_name in st.session_state["selected_columns"]
                    
                    # Create checkbox with version-based key (forces recreation when version changes)
                    new_state = st.checkbox(
                        col_name, 
                        value=is_checked, 
                        key=f"col_checkbox_{col_name}_v{version}"
                    )
                    
                    # Update session state based on checkbox
                    if new_state and col_name not in st.session_state["selected_columns"]:
                        st.session_state["selected_columns"].append(col_name)
                    elif not new_state and col_name in st.session_state["selected_columns"]:
                        st.session_state["selected_columns"].remove(col_name)


def render_data_filters(fleet_df: pd.DataFrame) -> dict:
    """
    Render data filter controls and return filter selections.
    
    Args:
        fleet_df: Full fleet DataFrame
        
    Returns:
        Dictionary of filter selections
    """
    st.markdown("#### Apply Data Filters")
    
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    filters = {}
    
    with filter_col1:
        filters['apple_silicon'] = st.checkbox("🍎 Apple Silicon Only", value=False, key="filter_as")
        filters['ai_ready'] = st.checkbox("🤖 AI Ready Only", value=False, key="filter_ai")
    
    with filter_col2:
        filters['low_storage'] = st.checkbox("⚠️ Low Storage Only", value=False, key="filter_storage")
        filters['homebrew'] = st.checkbox("🍺 Homebrew Installed", value=False, key="filter_brew")
    
    with filter_col3:
        # OS filter
        os_versions = sorted(fleet_df['os_generation'].unique().tolist())
        filters['os_versions'] = st.multiselect(
            "💻 Filter by macOS", 
            os_versions, 
            default=[], 
            key="filter_os"
        )
        
        # Chip filter
        chips = sorted(fleet_df['model_chip'].unique().tolist())
        filters['chips'] = st.multiselect(
            "⚙️ Filter by Chip", 
            chips, 
            default=[], 
            key="filter_chip"
        )
    
    return filters


def apply_filters(fleet_df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """
    Apply filters to the fleet DataFrame.
    
    Args:
        fleet_df: Full fleet DataFrame
        filters: Dictionary of filter selections
        
    Returns:
        Filtered DataFrame
    """
    filtered_df = fleet_df.copy()
    
    if filters.get('apple_silicon'):
        filtered_df = filtered_df[filtered_df['apple_silicon'] == True]
    
    if filters.get('ai_ready'):
        filtered_df = filtered_df[filtered_df['ai_ready'] == True]
    
    if filters.get('low_storage'):
        filtered_df = filtered_df[filtered_df['low_storage'] == True]
    
    if filters.get('homebrew'):
        filtered_df = filtered_df[filtered_df['homebrew_installed'] == True]
    
    if filters.get('os_versions'):
        filtered_df = filtered_df[filtered_df['os_generation'].isin(filters['os_versions'])]
    
    if filters.get('chips'):
        filtered_df = filtered_df[filtered_df['model_chip'].isin(filters['chips'])]
    
    return filtered_df


def render_filtered_data_table(filtered_df: pd.DataFrame, selected_columns: list) -> None:
    """
    Render the filtered data table with export button.
    
    Args:
        filtered_df: Filtered DataFrame
        selected_columns: List of selected column names
    """
    st.markdown(f"### 📋 Filtered Data ({len(filtered_df)} devices)")
    
    if not selected_columns:
        st.warning("⚠️ Please select at least one column to display")
        return
    
    # Display filtered data with selected columns
    display_cols = [c for c in selected_columns if c in filtered_df.columns]
    display_df = filtered_df[display_cols]
    
    st.dataframe(
        display_df,
        width='stretch',
        height=400,
        hide_index=False
    )
    
    # Export section
    st.divider()
    
    col_exp1, col_exp2 = st.columns([1, 3])
    
    with col_exp1:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_data = display_df.to_csv(index=True)
        
        st.download_button(
            label="📥 Download Filtered Data (CSV)",
            data=csv_data,
            file_name=f"devices_filtered_{timestamp}.csv",
            mime="text/csv",
            width='stretch',
            help="Download exactly what you see above"
        )
    
    with col_exp2:
        st.caption(f"💡 **Export includes:** {len(filtered_df)} devices × {len(display_cols)} columns = {len(filtered_df) * len(display_cols)} data points")
        if "applications" in display_cols:
            st.caption("📦 **Applications column** contains comma-separated list of all installed apps per device")
