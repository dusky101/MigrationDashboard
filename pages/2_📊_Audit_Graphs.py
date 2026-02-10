"""
Audit Graphs - Device Analytics Dashboard

Comprehensive device analytics with interactive filtering and data export.
Filter what you see, export what you need.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import zipfile
import shutil
import tempfile

from analytics.fleet_analytics import (
    load_all_audits,
    get_fleet_metrics,
    get_hardware_distribution,
    get_storage_analytics,
    get_software_distribution,
    get_top_applications,
    get_compliance_summary,
    get_devices_needing_attention,
)
from components.audit_graphs_components import (
    render_column_selector,
    render_data_filters,
    apply_filters,
    render_filtered_data_table,
)
from ui.sidebar import render_sidebar
from ui.styles import get_custom_css
from core.zip_processor import process_incoming_zips
from data_loaders.audit_loader import load_audit_data
from core.status_tracker import load_status


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Audit Graphs",
    page_icon="📊",
    layout="wide"
)

# Apply custom CSS
st.markdown(get_custom_css(), unsafe_allow_html=True)

# Hide app.py from sidebar
st.markdown("""
<style>
    [data-testid="stSidebarNav"] ul li:first-child {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Audit Graphs")
st.caption("Device analytics with interactive filtering and data export")

# ============================================================================
# ENSURE SESSION STATE IS INITIALIZED
# ============================================================================
if "audit_folder" not in st.session_state:
    st.session_state["audit_folder"] = os.path.join(os.getcwd(), "audit_processed_csvs")

if "UPLOAD_WORK_DIR" not in st.session_state:
    st.session_state["UPLOAD_WORK_DIR"] = tempfile.mkdtemp(prefix="mig_audit_uploads_")

INTERNAL_CSV_STORE = st.session_state["audit_folder"]
UPLOAD_WORK_DIR = st.session_state["UPLOAD_WORK_DIR"]

# ============================================================================
# FILE HANDLING HELPERS
# ============================================================================
def _save_uploaded_file(uploaded_file, dest_dir: str) -> str:
    """Save uploaded file to destination directory."""
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, uploaded_file.name)
    with open(dest, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return dest


def _extract_csvs_from_zip(zip_path: str, dest_dir: str) -> int:
    """Extract CSV files from ZIP archive."""
    extracted = 0
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for member in z.namelist():
                if not member.lower().endswith(".csv"):
                    continue
                base = os.path.basename(member)
                if not base:
                    continue
                out_path = os.path.join(dest_dir, base)
                with z.open(member) as src, open(out_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                extracted += 1
    except zipfile.BadZipFile:
        st.error(f"❌ Invalid ZIP uploaded: {os.path.basename(zip_path)}")
    return extracted


# ============================================================================
# RELOAD DATA IF NEEDED
# ============================================================================
if "users_df" not in st.session_state or st.session_state.get("users_df") is None:
    users_df = pd.DataFrame()
    if os.path.isdir(INTERNAL_CSV_STORE):
        try:
            users_df = load_audit_data(INTERNAL_CSV_STORE)
        except Exception as e:
            st.error(f"Error loading audit data: {e}")
    st.session_state["users_df"] = users_df

if "status_df" not in st.session_state:
    st.session_state["status_df"] = load_status()

# Get data from session state
users_df = st.session_state.get("users_df", pd.DataFrame())
status_df = st.session_state.get("status_df", pd.DataFrame())
AUDIT_FOLDER = st.session_state["audit_folder"]

# ============================================================================
# RENDER SIDEBAR (with upload capability)
# ============================================================================
uploaded_audit_files = render_sidebar(users_df, status_df, INTERNAL_CSV_STORE)

# ============================================================================
# PROCESS UPLOADED FILES
# ============================================================================
if uploaded_audit_files:
    with st.spinner("Processing uploaded audit files..."):
        extracted_count = 0
        for uf in uploaded_audit_files:
            saved_path = _save_uploaded_file(uf, UPLOAD_WORK_DIR)
            if saved_path.lower().endswith(".zip"):
                extracted_count += _extract_csvs_from_zip(saved_path, INTERNAL_CSV_STORE)
            elif saved_path.lower().endswith(".csv"):
                shutil.copy(saved_path, os.path.join(INTERNAL_CSV_STORE, os.path.basename(saved_path)))
                extracted_count += 1

        if extracted_count > 0:
            # Reload data
            users_df = load_audit_data(INTERNAL_CSV_STORE)
            status_df = load_status()
            st.session_state["users_df"] = users_df
            st.session_state["status_df"] = status_df
            
            st.toast(f"📦 Added {extracted_count} audit report(s) from upload.", icon="✅")
            st.rerun()


# ============================================================================
# LOAD DATA
# ============================================================================

# Load fleet data (cached)
fleet_df = load_all_audits(AUDIT_FOLDER)

if fleet_df.empty:
    st.warning("⏳ No data available yet. Upload audit files to see analytics.")
    st.stop()

# Get metrics (cached)
metrics = get_fleet_metrics(AUDIT_FOLDER)
compliance = get_compliance_summary(AUDIT_FOLDER)


# ============================================================================
# KEY METRICS ROW
# ============================================================================

st.markdown("### 🎯 Overview")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        label="Total Devices",
        value=metrics['total_devices'],
        help="Total Mac devices"
    )

with col2:
    st.metric(
        label="Apple Silicon",
        value=f"{metrics['apple_silicon_pct']}%",
        delta=f"{metrics['apple_silicon_count']} devices",
        help="Percentage running Apple Silicon (M1/M2/M3/M4/M5)"
    )

with col3:
    # Show delta based on AI readiness threshold
    ai_delta = f"{metrics['ai_ready_count']} devices"
    if metrics['ai_ready_pct'] < 50:
        ai_delta = f"{metrics['ai_ready_count']} devices (⚠️ Below 50%)"
    
    st.metric(
        label="AI Ready",
        value=f"{metrics['ai_ready_pct']}%",
        delta=ai_delta,
        help="Devices ready for Apple Intelligence (Apple Silicon + macOS 15.1+)"
    )

with col4:
    st.metric(
        label="Avg Free Storage",
        value=f"{metrics['avg_storage_free_gb']:.0f} GB",
        help="Average available storage"
    )

with col5:
    st.metric(
        label="Homebrew Adoption",
        value=f"{metrics['homebrew_adoption_pct']:.0f}%",
        help="Percentage with Homebrew installed"
    )

st.divider()


# ============================================================================
# DATA FILTERING SECTION
# ============================================================================

st.markdown("### 🔍 Filter Data")

with st.expander("📋 Column Selection & Filters", expanded=True):
    st.caption("Choose which columns to display and apply filters to narrow down the data")
    
    # Initialize session state for selected columns if not exists
    if "selected_columns" not in st.session_state:
        essential_cols = ["display_name", "email", "model_name", "chip_variant", "ram", 
                         "available_space_gb", "os_version", "ai_ready", "applications"]
        st.session_state["selected_columns"] = [c for c in essential_cols if c in fleet_df.columns]
    
    # Render column selector (from components)
    render_column_selector(fleet_df)
    
    st.divider()
    
    # Render data filters (from components)
    filters = render_data_filters(fleet_df)


# Apply filters (from components)
filtered_df = apply_filters(fleet_df, filters)

# Render filtered data table (from components)
render_filtered_data_table(filtered_df, st.session_state["selected_columns"])


# ============================================================================
# TABS FOR VISUALIZATIONS
# ============================================================================

st.divider()

tab_hw, tab_sw, tab_compliance, tab_storage, tab_apps = st.tabs([
    "🖥️ Hardware",
    "💻 Software",
    "✅ Compliance",
    "💾 Storage",
    "📦 Applications"
])


# ============================================================================
# HARDWARE TAB
# ============================================================================

with tab_hw:
    st.markdown("### Hardware Distribution")
    
    hw_dist = get_hardware_distribution(AUDIT_FOLDER)
    
    if not hw_dist.empty:
        col_model, col_chip = st.columns(2)
        
        with col_model:
            st.markdown("#### Mac Models")
            
            model_data = hw_dist[hw_dist['category'] == 'Model'].sort_values('count', ascending=False)
            
            if not model_data.empty:
                fig_model = px.bar(
                    model_data,
                    x='count',
                    y='label',
                    orientation='h',
                    text='count',
                    color='count',
                    color_continuous_scale='Blues',
                    labels={'count': 'Devices', 'label': 'Model'}
                )
                
                fig_model.update_traces(textposition='outside')
                fig_model.update_layout(
                    showlegend=False,
                    height=400,
                    yaxis={'categoryorder': 'total ascending'}
                )
                
                st.plotly_chart(fig_model, width='stretch')
        
        with col_chip:
            st.markdown("#### Chip Distribution")
            
            chip_data = hw_dist[hw_dist['category'] == 'Chip'].sort_values('count', ascending=False)
            
            if not chip_data.empty:
                fig_chip = px.pie(
                    chip_data,
                    values='count',
                    names='label',
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                
                fig_chip.update_traces(textposition='inside', textinfo='label+percent')
                fig_chip.update_layout(height=400)
                
                st.plotly_chart(fig_chip, width='stretch')
        
        st.divider()
        
        # RAM distribution
        st.markdown("#### RAM Distribution")
        
        ram_data = hw_dist[hw_dist['category'] == 'RAM'].sort_values('count', ascending=False)
        
        if not ram_data.empty:
            fig_ram = px.bar(
                ram_data,
                x='label',
                y='count',
                text='count',
                color='count',
                color_continuous_scale='Greens',
                labels={'count': 'Devices', 'label': 'RAM Configuration'}
            )
            
            fig_ram.update_traces(textposition='outside')
            fig_ram.update_layout(showlegend=False, height=300)
            
            st.plotly_chart(fig_ram, width='stretch')
    
    else:
        st.info("No hardware data available.")


# ============================================================================
# SOFTWARE TAB
# ============================================================================

with tab_sw:
    st.markdown("### Software Distribution")
    
    sw_dist = get_software_distribution(AUDIT_FOLDER)
    
    if not sw_dist.empty:
        col_os, col_brew = st.columns(2)
        
        with col_os:
            st.markdown("#### macOS Versions")
            
            os_data = sw_dist[sw_dist['category'] == 'macOS Version'].sort_values('count', ascending=False)
            
            if not os_data.empty:
                fig_os = px.bar(
                    os_data,
                    x='count',
                    y='label',
                    orientation='h',
                    text='count',
                    color='count',
                    color_continuous_scale='Purples',
                    labels={'count': 'Devices', 'label': 'macOS Version'}
                )
                
                fig_os.update_traces(textposition='outside')
                fig_os.update_layout(
                    showlegend=False,
                    height=300,
                    yaxis={'categoryorder': 'total ascending'}
                )
                
                st.plotly_chart(fig_os, width='stretch')
        
        with col_brew:
            st.markdown("#### Homebrew Adoption")
            
            brew_data = sw_dist[sw_dist['category'] == 'Homebrew']
            
            if not brew_data.empty:
                fig_brew = go.Figure(data=[go.Pie(
                    labels=brew_data['label'],
                    values=brew_data['count'],
                    hole=.4,
                    marker_colors=['#2ecc71', '#95a5a6']
                )])
                
                fig_brew.update_traces(textposition='inside', textinfo='label+percent')
                fig_brew.update_layout(height=300)
                
                st.plotly_chart(fig_brew, width='stretch')
    
    else:
        st.info("No software data available.")


# ============================================================================
# COMPLIANCE TAB
# ============================================================================

with tab_compliance:
    st.markdown("### 🛡️ Compliance & Readiness")
    
    # Key compliance metrics
    col_ai1, col_ai2, col_ai3 = st.columns(3)
    
    with col_ai1:
        st.metric(
            label="AI Ready",
            value=compliance['ai_ready'],
            delta=f"{compliance['ai_ready_pct']}%"
        )
    
    with col_ai2:
        st.metric(
            label="Need OS Update",
            value=compliance['os_update_needed'],
            delta="Apple Silicon only",
            delta_color="inverse"
        )
    
    with col_ai3:
        st.metric(
            label="Need Hardware Upgrade",
            value=compliance['hw_upgrade_needed'],
            delta="Intel Macs",
            delta_color="inverse"
        )
    
    st.divider()
    
    # Latest OS adoption
    col_os1, col_os2 = st.columns([1, 2])
    
    with col_os1:
        st.metric(
            label="macOS Sequoia (15.x)",
            value=compliance['latest_os_count'],
            delta=f"{compliance['latest_os_pct']}% adoption"
        )
    
    with col_os2:
        # Progress bar visualization
        progress_value = compliance['latest_os_pct'] / 100
        st.progress(progress_value, text=f"Latest macOS adoption: {compliance['latest_os_pct']}%")
    
    st.divider()
    
    # Devices needing attention
    st.markdown("### ⚠️ Devices Needing Attention")
    
    attention_df = get_devices_needing_attention(AUDIT_FOLDER)
    
    if not attention_df.empty:
        st.caption(f"Found {len(attention_df)} device(s) with potential issues")
        
        st.dataframe(
            attention_df,
            width='stretch',
            hide_index=True,
            column_config={
                'display_name': st.column_config.TextColumn('User', width='medium'),
                'model_name': st.column_config.TextColumn('Model', width='medium'),
                'os_generation': st.column_config.TextColumn('macOS', width='small'),
                'issues': st.column_config.TextColumn('Issues', width='large'),
            }
        )
    else:
        st.success("✅ All devices look healthy!")


# ============================================================================
# STORAGE TAB
# ============================================================================

with tab_storage:
    st.markdown("### 💾 Storage Analytics")
    
    storage_df = get_storage_analytics(AUDIT_FOLDER)
    
    if not storage_df.empty:
        # Storage overview metrics
        col_s1, col_s2, col_s3 = st.columns(3)
        
        with col_s1:
            st.metric(
                label="Devices Low on Storage",
                value=int(storage_df['low_storage'].sum()),
                delta=f"{int(storage_df['low_storage'].sum() / len(storage_df) * 100)}%",
                delta_color="inverse"
            )
        
        with col_s2:
            avg_used = storage_df['storage_used_pct'].mean()
            st.metric(
                label="Avg Storage Used",
                value=f"{avg_used:.0f}%"
            )
        
        with col_s3:
            total_free = storage_df['available_space_gb'].sum()
            st.metric(
                label="Total Free Space",
                value=f"{total_free:.0f} GB"
            )
        
        st.divider()
        
        # Storage usage chart
        st.markdown("#### Storage Usage by Device")
        
        # Sort by storage used percentage
        chart_df = storage_df.sort_values('storage_used_pct', ascending=False).head(20)
        
        fig_storage = go.Figure()
        
        # Used space
        fig_storage.add_trace(go.Bar(
            name='Used',
            y=chart_df['display_name'],
            x=chart_df['used_space_gb'],
            orientation='h',
            marker=dict(color='#e74c3c')
        ))
        
        # Free space
        fig_storage.add_trace(go.Bar(
            name='Free',
            y=chart_df['display_name'],
            x=chart_df['available_space_gb'],
            orientation='h',
            marker=dict(color='#2ecc71')
        ))
        
        fig_storage.update_layout(
            barmode='stack',
            height=600,
            xaxis_title='Storage (GB)',
            yaxis={'categoryorder': 'total ascending'},
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        
        st.plotly_chart(fig_storage, width='stretch')
        
        # Low storage devices table
        low_storage = storage_df[storage_df['low_storage'] == True].copy()
        
        if not low_storage.empty:
            st.warning(f"⚠️ {len(low_storage)} device(s) with low storage (<50GB free)")
            
            st.dataframe(
                low_storage[['display_name', 'disk_capacity_gb', 'available_space_gb', 'storage_used_pct']],
                width='stretch',
                hide_index=True,
                column_config={
                    'display_name': 'User',
                    'disk_capacity_gb': st.column_config.NumberColumn('Capacity (GB)', format="%.0f"),
                    'available_space_gb': st.column_config.NumberColumn('Free (GB)', format="%.0f"),
                    'storage_used_pct': st.column_config.ProgressColumn('Used', format="%.0f%%", min_value=0, max_value=100),
                }
            )
    
    else:
        st.info("No storage data available.")


# ============================================================================
# APPLICATIONS TAB
# ============================================================================

with tab_apps:
    st.markdown("### 📦 Application Distribution")
    
    # Top apps slider
    top_n = st.slider("Show top N applications", min_value=5, max_value=50, value=15, step=5, key="top_apps_slider")
    
    with st.spinner("Analyzing application data..."):
        apps_df = get_top_applications(AUDIT_FOLDER, top_n=top_n)
    
    if not apps_df.empty:
        col_chart, col_table = st.columns([2, 1])
        
        with col_chart:
            fig_apps = px.bar(
                apps_df,
                y='app_name',
                x='device_count',
                orientation='h',
                text='device_count',
                color='percentage',
                color_continuous_scale='Viridis',
                labels={'device_count': 'Devices', 'app_name': 'Application', 'percentage': 'Adoption %'}
            )
            
            fig_apps.update_traces(textposition='outside')
            fig_apps.update_layout(
                height=600,
                yaxis={'categoryorder': 'total ascending'},
                showlegend=False
            )
            
            st.plotly_chart(fig_apps, width='stretch')
        
        with col_table:
            st.dataframe(
                apps_df,
                width='stretch',
                hide_index=True,
                height=600,
                column_config={
                    'app_name': 'Application',
                    'device_count': st.column_config.NumberColumn('Devices', format="%d"),
                    'percentage': st.column_config.ProgressColumn('Adoption', format="%.0f%%", min_value=0, max_value=100),
                }
            )
    
    else:
        st.info("No application data available.")


# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Total devices analyzed: {metrics['total_devices']} | Filtered: {len(filtered_df)}")
