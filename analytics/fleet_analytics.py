"""
Fleet Analytics Module

Aggregates and analyzes audit data across the entire Mac fleet.
Provides metrics and data structures for dashboard visualizations.

This module efficiently processes all audit files and caches results
for fast dashboard performance.
"""

import os
import re
import pandas as pd
import streamlit as st
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from datetime import datetime

from core.audit_parser import parse_audit_csv
from models.mac_models import (
    get_model_chip,
    get_model_chip_variant,
    get_model_product_name,
    get_model_year,
    is_apple_silicon
)
from models.macos_versions import (
    get_macos_friendly_name,
    get_macos_generation,
    supports_apple_intelligence
)


# ============================================================================
# CORE DATA AGGREGATION
# ============================================================================

@st.cache_data(ttl=300, show_spinner="Loading fleet data...")
def load_all_audits(audit_folder: str) -> pd.DataFrame:
    """
    Parse all audit CSVs and return aggregated fleet dataset.
    
    Returns DataFrame with one row per device containing:
    - User info (name, email, login)
    - Hardware specs (model, chip, RAM, storage)
    - Software (OS version, Homebrew, app count)
    - Compliance (AI support, storage health)
    
    Args:
        audit_folder: Path to folder containing audit CSV files
        
    Returns:
        DataFrame indexed by user key with comprehensive device data
    """
    if not os.path.isdir(audit_folder):
        return pd.DataFrame()
    
    audit_files = [f for f in os.listdir(audit_folder) if f.lower().endswith('.csv')]
    
    if not audit_files:
        return pd.DataFrame()
    
    fleet_data = []
    
    for filename in audit_files:
        file_path = os.path.join(audit_folder, filename)
        
        try:
            # Parse audit
            audit_df = parse_audit_csv(file_path)
            if audit_df is None or audit_df.empty:
                continue
            
            # Extract device data
            device_data = _extract_device_data(audit_df, filename)
            if device_data:
                fleet_data.append(device_data)
                
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    if not fleet_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(fleet_data)
    
    # Set user key as index
    if 'user_key' in df.columns:
        df = df.set_index('user_key')
    
    return df


def _extract_device_data(audit_df: pd.DataFrame, filename: str) -> Optional[Dict]:
    """
    Extract comprehensive device data from a single audit DataFrame.
    
    Returns dictionary with all device metrics.
    """
    specs = audit_df[audit_df["TYPE"] == "System Specifications"].copy()
    
    if specs.empty:
        return None
    
    def get_spec(name_key: str) -> str:
        row = specs[specs["NAME"].str.contains(name_key, case=False, na=False)]
        if row.empty:
            return ""
        return str(row.iloc[0].get("DETAILS", "")).strip()
    
    # ========================================================================
    # USER IDENTIFICATION
    # ========================================================================
    logged_user = get_spec("Logged-in User")
    login_name = get_spec("Login Name")
    
    # Extract email
    email = ""
    email_accounts = audit_df[audit_df["TYPE"] == "Email Accounts"].copy()
    if not email_accounts.empty:
        email_pattern = re.compile(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})')
        for detail in email_accounts["DETAILS"].astype(str).tolist():
            match = email_pattern.search(detail)
            if match:
                email = match.group(1)
                break
    
    # Determine user key
    user_key = login_name or email or Path(filename).stem.lower()
    
    # ========================================================================
    # HARDWARE SPECS
    # ========================================================================
    raw_model = get_spec("Model Identifier")
    serial = get_spec("Serial Number")
    processor = get_spec("Processor")
    ram = get_spec("Memory")
    
    # Model transformations
    model_name = get_model_product_name(raw_model) if raw_model else "Unknown"
    model_chip = get_model_chip(raw_model) if raw_model else "Unknown"
    chip_variant = get_model_chip_variant(raw_model) if raw_model else "Unknown"
    model_year = get_model_year(raw_model) if raw_model else None
    apple_silicon = is_apple_silicon(raw_model) if raw_model else False
    
    # ========================================================================
    # STORAGE
    # ========================================================================
    disk_capacity = get_spec("Hard Drive Capacity")
    available_space = get_spec("Available Space")
    
    # Parse storage values
    capacity_gb = _parse_storage_to_gb(disk_capacity)
    available_gb = _parse_storage_to_gb(available_space)
    used_gb = capacity_gb - available_gb if capacity_gb and available_gb else 0
    storage_pct = (used_gb / capacity_gb * 100) if capacity_gb > 0 else 0
    
    # ========================================================================
    # macOS VERSION
    # ========================================================================
    raw_version = get_spec("macOS Version")
    os_version = get_macos_friendly_name(raw_version) if raw_version else "Unknown"
    os_generation = get_macos_generation(raw_version) if raw_version else "Unknown"
    ai_supported = supports_apple_intelligence(raw_version) if raw_version else False
    
    # ========================================================================
    # SOFTWARE
    # ========================================================================
    # Homebrew detection
    homebrew_installed = False
    homebrew_package_count = 0
    
    brew_data = audit_df[audit_df["TYPE"] == "Homebrew Packages"].copy()
    if not brew_data.empty:
        homebrew_installed = True
        formulae = brew_data[brew_data["DETAILS"].str.contains("Homebrew Formula", case=False, na=False)]
        homebrew_package_count = len(formulae)
    
    # Application count
    apps = audit_df[audit_df["TYPE"] == "Applications Folder"].copy()
    app_count = len(apps)
    
    # ========================================================================
    # COMPLIANCE FLAGS
    # ========================================================================
    # Low storage warning (< 50GB free)
    low_storage = available_gb < 50 if available_gb else False
    
    # Low RAM warning (< 16GB)
    low_ram = False
    if ram:
        ram_match = re.search(r'(\d+)\s*GB', ram)
        if ram_match:
            ram_gb = int(ram_match.group(1))
            low_ram = ram_gb < 16
    
    # AI readiness (hardware + OS support)
    ai_ready = apple_silicon and ai_supported
    
    # ========================================================================
    # RETURN DEVICE DATA
    # ========================================================================
    return {
        # User identification
        'user_key': user_key,
        'display_name': logged_user or login_name or user_key,
        'email': email,
        'login_name': login_name,
        
        # Hardware
        'model_name': model_name,
        'model_identifier': raw_model,
        'model_chip': model_chip,
        'chip_variant': chip_variant,
        'model_year': model_year,
        'apple_silicon': apple_silicon,
        'serial_number': serial,
        'processor': processor,
        'ram': ram,
        
        # Storage
        'disk_capacity_gb': capacity_gb,
        'available_space_gb': available_gb,
        'used_space_gb': used_gb,
        'storage_used_pct': storage_pct,
        
        # Software
        'os_version': os_version,
        'os_version_raw': raw_version,
        'os_generation': os_generation,
        'homebrew_installed': homebrew_installed,
        'homebrew_package_count': homebrew_package_count,
        'app_count': app_count,
        
        # Compliance
        'ai_supported': ai_supported,
        'ai_ready': ai_ready,
        'low_storage': low_storage,
        'low_ram': low_ram,
    }


def _parse_storage_to_gb(storage_str: str) -> Optional[float]:
    """
    Parse storage strings like "512 GB", "1.2 TB" to GB as float.
    
    Returns None if unparseable.
    """
    if not storage_str or storage_str == "—":
        return None
    
    try:
        # Match patterns like "512 GB", "1.2 TB", "94.5 MB"
        match = re.search(r'([\d.]+)\s*(GB|TB|MB)', storage_str, re.IGNORECASE)
        if not match:
            return None
        
        value = float(match.group(1))
        unit = match.group(2).upper()
        
        if unit == "GB":
            return value
        elif unit == "TB":
            return value * 1024
        elif unit == "MB":
            return value / 1024
        
        return None
    except Exception:
        return None


# ============================================================================
# FLEET METRICS
# ============================================================================

@st.cache_data(ttl=300)
def get_fleet_metrics(audit_folder: str) -> Dict:
    """
    Calculate key fleet-wide metrics.
    
    Returns dictionary with summary statistics.
    """
    df = load_all_audits(audit_folder)
    
    if df.empty:
        return {
            'total_devices': 0,
            'apple_silicon_count': 0,
            'apple_silicon_pct': 0,
            'avg_storage_free_gb': 0,
            'ai_ready_count': 0,
            'ai_ready_pct': 0,
            'homebrew_adoption_pct': 0,
            'low_storage_count': 0,
            'low_ram_count': 0,
        }
    
    total = len(df)
    
    return {
        'total_devices': total,
        'apple_silicon_count': int(df['apple_silicon'].sum()),
        'apple_silicon_pct': round(df['apple_silicon'].sum() / total * 100, 1),
        'avg_storage_free_gb': round(df['available_space_gb'].mean(), 1),
        'ai_ready_count': int(df['ai_ready'].sum()),
        'ai_ready_pct': round(df['ai_ready'].sum() / total * 100, 1),
        'homebrew_adoption_pct': round(df['homebrew_installed'].sum() / total * 100, 1),
        'low_storage_count': int(df['low_storage'].sum()),
        'low_ram_count': int(df['low_ram'].sum()),
    }


# ============================================================================
# HARDWARE ANALYTICS
# ============================================================================

@st.cache_data(ttl=300)
def get_hardware_distribution(audit_folder: str) -> pd.DataFrame:
    """
    Get hardware distribution data for charts.
    
    Returns DataFrame with columns: category, label, count, percentage
    """
    df = load_all_audits(audit_folder)
    
    if df.empty:
        return pd.DataFrame(columns=['category', 'label', 'count', 'percentage'])
    
    results = []
    
    # Model distribution
    model_counts = df['model_name'].value_counts()
    for model, count in model_counts.items():
        results.append({
            'category': 'Model',
            'label': model,
            'count': int(count),
            'percentage': round(count / len(df) * 100, 1)
        })
    
    # Chip distribution
    chip_counts = df['model_chip'].value_counts()
    for chip, count in chip_counts.items():
        results.append({
            'category': 'Chip',
            'label': chip,
            'count': int(count),
            'percentage': round(count / len(df) * 100, 1)
        })
    
    # RAM distribution
    ram_counts = df['ram'].value_counts()
    for ram, count in ram_counts.items():
        results.append({
            'category': 'RAM',
            'label': ram if ram else "Unknown",
            'count': int(count),
            'percentage': round(count / len(df) * 100, 1)
        })
    
    return pd.DataFrame(results)


@st.cache_data(ttl=300)
def get_storage_analytics(audit_folder: str) -> pd.DataFrame:
    """
    Get storage usage analytics.
    
    Returns DataFrame with device storage data.
    """
    df = load_all_audits(audit_folder)
    
    if df.empty:
        return pd.DataFrame()
    
    # Filter for valid storage data
    storage_df = df[df['disk_capacity_gb'].notna()].copy()
    
    return storage_df[['display_name', 'disk_capacity_gb', 'available_space_gb', 
                       'used_space_gb', 'storage_used_pct', 'low_storage']]


# ============================================================================
# SOFTWARE ANALYTICS
# ============================================================================

@st.cache_data(ttl=300)
def get_software_distribution(audit_folder: str) -> pd.DataFrame:
    """
    Get software distribution data (OS versions, Homebrew).
    
    Returns DataFrame with columns: category, label, count, percentage
    """
    df = load_all_audits(audit_folder)
    
    if df.empty:
        return pd.DataFrame(columns=['category', 'label', 'count', 'percentage'])
    
    results = []
    
    # OS version distribution
    os_counts = df['os_generation'].value_counts()
    for os_gen, count in os_counts.items():
        results.append({
            'category': 'macOS Version',
            'label': os_gen,
            'count': int(count),
            'percentage': round(count / len(df) * 100, 1)
        })
    
    # Homebrew adoption
    brew_yes = df['homebrew_installed'].sum()
    brew_no = len(df) - brew_yes
    
    results.append({
        'category': 'Homebrew',
        'label': 'Installed',
        'count': int(brew_yes),
        'percentage': round(brew_yes / len(df) * 100, 1)
    })
    
    results.append({
        'category': 'Homebrew',
        'label': 'Not Installed',
        'count': int(brew_no),
        'percentage': round(brew_no / len(df) * 100, 1)
    })
    
    return pd.DataFrame(results)


@st.cache_data(ttl=300)
def get_top_applications(audit_folder: str, top_n: int = 10) -> pd.DataFrame:
    """
    Get most common applications across fleet.
    
    Args:
        audit_folder: Path to audit folder
        top_n: Number of top apps to return
        
    Returns:
        DataFrame with columns: app_name, device_count, percentage
    """
    if not os.path.isdir(audit_folder):
        return pd.DataFrame(columns=['app_name', 'device_count', 'percentage'])
    
    audit_files = [f for f in os.listdir(audit_folder) if f.lower().endswith('.csv')]
    
    # Collect all apps
    app_counts = {}
    total_devices = 0
    
    for filename in audit_files:
        file_path = os.path.join(audit_folder, filename)
        
        try:
            audit_df = parse_audit_csv(file_path)
            if audit_df is None or audit_df.empty:
                continue
            
            total_devices += 1
            
            # Get apps for this device
            apps = audit_df[audit_df["TYPE"] == "Applications Folder"]["NAME"].tolist()
            
            for app in apps:
                app = str(app).strip()
                if app and len(app) > 2:
                    app_counts[app] = app_counts.get(app, 0) + 1
                    
        except Exception:
            continue
    
    if not app_counts:
        return pd.DataFrame(columns=['app_name', 'device_count', 'percentage'])
    
    # Sort and get top N
    sorted_apps = sorted(app_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    
    results = []
    for app_name, count in sorted_apps:
        results.append({
            'app_name': app_name,
            'device_count': count,
            'percentage': round(count / total_devices * 100, 1) if total_devices > 0 else 0
        })
    
    return pd.DataFrame(results)


# ============================================================================
# COMPLIANCE ANALYTICS
# ============================================================================

@st.cache_data(ttl=300)
def get_compliance_summary(audit_folder: str) -> Dict:
    """
    Get compliance and readiness metrics.
    
    Returns dictionary with compliance statistics.
    """
    df = load_all_audits(audit_folder)
    
    if df.empty:
        return {
            'ai_ready': 0,
            'ai_ready_pct': 0,
            'os_update_needed': 0,
            'hw_upgrade_needed': 0,
            'latest_os_count': 0,
            'latest_os_pct': 0,
        }
    
    total = len(df)
    
    # AI readiness breakdown
    ai_ready = df['ai_ready'].sum()
    os_update_needed = df[df['apple_silicon'] & ~df['ai_supported']].shape[0]
    hw_upgrade_needed = df[~df['apple_silicon']].shape[0]
    
    # Latest OS adoption (Sequoia = macOS 15)
    latest_os = df[df['os_generation'] == 'Sequoia'].shape[0]
    
    return {
        'ai_ready': int(ai_ready),
        'ai_ready_pct': round(ai_ready / total * 100, 1),
        'os_update_needed': int(os_update_needed),
        'hw_upgrade_needed': int(hw_upgrade_needed),
        'latest_os_count': int(latest_os),
        'latest_os_pct': round(latest_os / total * 100, 1),
    }


@st.cache_data(ttl=300)
def get_devices_needing_attention(audit_folder: str) -> pd.DataFrame:
    """
    Get list of devices that need attention (low storage, low RAM, old OS).
    
    Returns DataFrame with devices and their issues.
    """
    df = load_all_audits(audit_folder)
    
    if df.empty:
        return pd.DataFrame()
    
    # Filter devices with issues
    issues_df = df[df['low_storage'] | df['low_ram'] | ~df['ai_ready']].copy()
    
    if issues_df.empty:
        return pd.DataFrame()
    
    # Build issue descriptions
    def describe_issues(row):
        issues = []
        if row['low_storage']:
            issues.append(f"Low storage ({row['available_space_gb']:.1f}GB free)")
        if row['low_ram']:
            issues.append(f"Low RAM ({row['ram']})")
        if not row['ai_ready']:
            if not row['apple_silicon']:
                issues.append("Intel Mac (needs hardware upgrade)")
            elif not row['ai_supported']:
                issues.append("Needs OS update for AI features")
        return "; ".join(issues)
    
    issues_df['issues'] = issues_df.apply(describe_issues, axis=1)
    
    return issues_df[['display_name', 'model_name', 'os_generation', 'issues']]


# ============================================================================
# EXPORT HELPERS
# ============================================================================

def export_fleet_summary_csv(audit_folder: str) -> str:
    """
    Export complete fleet data as CSV string.
    
    Returns CSV string suitable for download.
    """
    df = load_all_audits(audit_folder)
    
    if df.empty:
        return ""
    
    # Select key columns for export
    export_cols = [
        'display_name', 'email', 'model_name', 'chip_variant', 
        'ram', 'disk_capacity_gb', 'available_space_gb', 
        'os_version', 'homebrew_installed', 'ai_ready'
    ]
    
    export_df = df[[col for col in export_cols if col in df.columns]]
    
    return export_df.to_csv(index=True)
