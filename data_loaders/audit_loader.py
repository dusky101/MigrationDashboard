"""
Audit Data Loader

Orchestrates loading and user derivation from audit CSV files.
Complements Google data with device-specific information.
"""

import os
import re
import pandas as pd
from pathlib import Path
from typing import Optional


def derive_users_from_audit_folder(audit_folder: str) -> pd.DataFrame:
    """
    Create a user index from audit CSV filenames.
    
    Useful when Google data is not available - creates a basic user list
    from the audit files themselves.
    
    Strategy:
    1. Extract email addresses from filenames if present
    2. Otherwise, extract name-like patterns
    3. Generate friendly display names
    
    Args:
        audit_folder: Path to folder containing audit CSV files
        
    Returns:
        DataFrame with columns User (index) and Admin-defined name
        
    Examples:
        Filename: "Audit_Report_john.smith@company.com.csv"
        → User: "john.smith@company.com", Name: "John Smith"
        
        Filename: "Audit_Report_Jane_Doe.csv"
        → User: "jane doe", Name: "Jane Doe"
    """
    if not os.path.isdir(audit_folder):
        return pd.DataFrame()

    def extract_key(filename: str) -> str:
        """Extract user key from audit filename."""
        stem = Path(filename).stem
        
        # Try to find email address first
        m = re.search(r"([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})", stem)
        if m:
            return m.group(1).lower()

        # Otherwise, extract name-like pattern
        cleaned = re.sub(r"(?i)^audit[_\-\s]*report[_\-\s]*", "", stem)
        cleaned = re.sub(r"[_\-]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
        return cleaned if cleaned else stem.lower()

    rows = []
    for f in os.listdir(audit_folder):
        if not f.lower().endswith(".csv"):
            continue
        
        key = extract_key(f)
        
        # Generate friendly name
        if "@" in key:
            friendly = key.split("@")[0].replace(".", " ").title()
        else:
            friendly = key.replace(".", " ").title()
        
        rows.append({"User": key, "Admin-defined name": friendly})

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).drop_duplicates(subset=["User"]).set_index("User")


def merge_google_and_audit_users(
    google_users: pd.DataFrame, 
    audit_users: pd.DataFrame
) -> pd.DataFrame:
    """
    Merge Google user data with audit-derived users.
    
    This ensures users who don't appear in Google exports (e.g., new hires,
    contractors) are still visible if they have audit files.
    
    Args:
        google_users: DataFrame from Google Workspace exports
        audit_users: DataFrame derived from audit filenames
        
    Returns:
        Merged DataFrame with all users from both sources
    """
    if google_users is None or google_users.empty:
        return audit_users

    combined = google_users.copy()
    
    # Add audit-only users (those not in Google data)
    for user_key in audit_users.index:
        if user_key not in combined.index:
            combined.loc[user_key, "Admin-defined name"] = audit_users.loc[user_key].get(
                "Admin-defined name", ""
            )
    
    return combined.sort_index()


def load_audit_data(audit_folder: str) -> pd.DataFrame:
    """
    Load all audit data from a folder.
    
    This is a convenience function that derives the user list from audit files.
    For individual audit parsing, use core.audit_parser.parse_audit_csv()
    
    Args:
        audit_folder: Path to folder containing audit CSV files
        
    Returns:
        DataFrame of users derived from audit filenames
    """
    return derive_users_from_audit_folder(audit_folder)