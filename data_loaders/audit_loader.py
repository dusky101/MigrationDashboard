"""
Audit Data Loader

Primary data source for the Migration Intelligence Platform.
Loads and enriches user data from audit CSV files.
"""

import os
import re
import pandas as pd
from pathlib import Path
from typing import Optional, Dict
from core.audit_parser import parse_audit_csv, find_audit_file


def extract_user_info_from_audit(audit_df: pd.DataFrame) -> Dict[str, str]:
    """
    Extract comprehensive user information from audit data.
    
    Extracts:
    - Logged-in User (full name)
    - Login Name (username)
    - Email address
    
    Args:
        audit_df: Parsed audit DataFrame
        
    Returns:
        Dictionary with user info fields
    """
    info = {
        "logged_in_user": "",
        "login_name": "",
        "email": ""
    }
    
    if audit_df is None or audit_df.empty:
        return info
    
    specs = audit_df[audit_df["TYPE"] == "System Specifications"].copy()
    
    if specs.empty:
        return info
    
    # Extract Logged-in User
    logged_user_row = specs[specs["NAME"].str.contains("Logged-in User", case=False, na=False)]
    if not logged_user_row.empty:
        info["logged_in_user"] = str(logged_user_row.iloc[0].get("DETAILS", "")).strip()
    
    # Extract Login Name
    login_row = specs[specs["NAME"].str.contains("Login Name", case=False, na=False)]
    if not login_row.empty:
        info["login_name"] = str(login_row.iloc[0].get("DETAILS", "")).strip()
    
    # Extract Email from Email Accounts section
    email_accounts = audit_df[audit_df["TYPE"] == "Email Accounts"].copy()
    if not email_accounts.empty:
        email_pattern = re.compile(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})')
        for detail in email_accounts["DETAILS"].astype(str).tolist():
            match = email_pattern.search(detail)
            if match:
                info["email"] = match.group(1)
                break
    
    return info


def derive_users_from_audit_folder(audit_folder: str) -> pd.DataFrame:
    """
    Create comprehensive user index from audit CSV files.
    
    Now enriched with actual user data from audit files:
    - Parses each audit to extract user name and email
    - Falls back to filename-based derivation if parsing fails
    - Provides complete user profiles without external dependencies
    
    Args:
        audit_folder: Path to folder containing audit CSV files
        
    Returns:
        DataFrame indexed by User key with columns:
        - Admin-defined name (friendly display name)
        - Email (extracted from audit)
        - Login Name (username)
        
    Examples:
        Audit contains "Logged-in User: John Smith", "Login Name: jsmith"
        -> User: "jsmith", Name: "John Smith", Email: "john.smith@company.com"
    """
    if not os.path.isdir(audit_folder):
        return pd.DataFrame(columns=["Admin-defined name", "Email", "Login Name"])

    def extract_key_from_filename(filename: str) -> str:
        """Extract user key from audit filename (fallback method)."""
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
        
        file_path = os.path.join(audit_folder, f)
        
        # Parse audit to extract user info
        audit_df = parse_audit_csv(file_path)
        user_info = extract_user_info_from_audit(audit_df)
        
        # Determine user key (prefer login name, then email, then filename)
        if user_info["login_name"]:
            user_key = user_info["login_name"].lower()
        elif user_info["email"]:
            user_key = user_info["email"].lower()
        else:
            user_key = extract_key_from_filename(f)
        
        # Determine display name (prefer logged-in user, then derive from key)
        if user_info["logged_in_user"]:
            display_name = user_info["logged_in_user"]
        elif user_info["email"]:
            display_name = user_info["email"].split("@")[0].replace(".", " ").title()
        else:
            display_name = user_key.replace(".", " ").title()
        
        rows.append({
            "User": user_key,
            "Admin-defined name": display_name,
            "Email": user_info["email"] or "",
            "Login Name": user_info["login_name"] or ""
        })

    if not rows:
        return pd.DataFrame(columns=["Admin-defined name", "Email", "Login Name"])

    df = pd.DataFrame(rows).drop_duplicates(subset=["User"]).set_index("User")
    return df.sort_index()


def load_audit_data(audit_folder: str) -> pd.DataFrame:
    """
    Load all audit data from a folder (primary data source).
    
    This is now the main entry point for loading user data.
    Replaces the previous Google Workspace CSV dependency.
    
    Args:
        audit_folder: Path to folder containing audit CSV files
        
    Returns:
        DataFrame of users with comprehensive metadata from audits
    """
    return derive_users_from_audit_folder(audit_folder)


def enrich_user_with_audit_data(user_key: str, audit_folder: str) -> Dict[str, str]:
    """
    Enrich a user key with full audit-derived information.
    
    Useful for getting detailed user info on-demand.
    
    Args:
        user_key: User identifier
        audit_folder: Path to audit folder
        
    Returns:
        Dictionary with all available user information
    """
    audit_path = find_audit_file(audit_folder, user_key)
    
    if not audit_path:
        return {
            "user_key": user_key,
            "display_name": user_key.replace(".", " ").title(),
            "email": "",
            "login_name": ""
        }
    
    audit_df = parse_audit_csv(audit_path)
    user_info = extract_user_info_from_audit(audit_df)
    
    # Determine display name
    if user_info["logged_in_user"]:
        display_name = user_info["logged_in_user"]
    elif user_info["email"]:
        display_name = user_info["email"].split("@")[0].replace(".", " ").title()
    else:
        display_name = user_key.replace(".", " ").title()
    
    return {
        "user_key": user_key,
        "display_name": display_name,
        "email": user_info["email"],
        "login_name": user_info["login_name"]
    }
