"""
Google Workspace Data Loader

Merges multiple Google Workspace CSV exports into a unified dataset.
Handles user activity logs, storage usage, and group memberships.
"""

import pandas as pd
import os
import glob
import streamlit as st
from typing import Optional


def load_google_data(folder_path: str) -> pd.DataFrame:
    """
    Merges all Google CSVs into one master dataframe based on Email.
    
    Handles:
    - User activity logs (one row per user)
    - Group membership data (multiple groups per user)
    - Storage usage statistics
    - Various column naming conventions
    
    Args:
        folder_path: Path to folder containing Google CSV exports
        
    Returns:
        Unified DataFrame indexed by User (email), or empty DataFrame if no data
    """
    logs_df = pd.DataFrame()
    groups_df = pd.DataFrame()
    
    if not os.path.isdir(folder_path):
        return pd.DataFrame()

    files = glob.glob(os.path.join(folder_path, "*.csv"))
    if not files:
        return pd.DataFrame() 

    for file in files:
        # Skip Audit Reports that were accidentally saved in Google Data folder
        filename = os.path.basename(file)
        if filename.startswith("Audit_Report_"):
            continue

        try:
            df = pd.read_csv(file)
            
            # 1. Clean Column Names
            # Remove [Date] brackets: "Drive Usage [2025-01-01]" -> "Drive Usage"
            df.columns = [c.split(" [")[0].strip() for c in df.columns]
            
            # Normalise 'Member Email' to 'User' (found in some Group exports)
            if 'Member Email' in df.columns:
                df = df.rename(columns={'Member Email': 'User'})
            
            # Skip files that don't have a User identifier
            if 'User' not in df.columns:
                continue

            # 2. Identify & Process File Type
            
            # Case A: Group Data (One user belongs to multiple groups)
            if 'Group Name' in df.columns:
                # Aggregate groups per user with proper handling of non-string data
                grp_agg = df.groupby('User')['Group Name'].apply(
                    lambda x: ', '.join(sorted(set(str(s).strip() for s in x if pd.notna(s))))
                ).to_frame(name='Groups')
                
                if groups_df.empty:
                    groups_df = grp_agg
                else:
                    groups_df = groups_df.combine_first(grp_agg)
            
            # Case B: User Log Data (One row per user)
            else:
                # Set User as the ID
                df = df.set_index('User')
                
                # Merge into logs dataframe
                if logs_df.empty:
                    logs_df = df
                else:
                    logs_df = df.combine_first(logs_df)

        except Exception as e:
            # Inform about problematic files
            st.sidebar.warning(f"Could not read {os.path.basename(file)}: {e}")
            
    # 3. Final Merge of Logs + Groups
    if logs_df.empty and groups_df.empty:
        return pd.DataFrame()
    elif logs_df.empty:
        return groups_df
    elif groups_df.empty:
        return logs_df
    else:
        # Join the groups column onto the main user logs
        master_df = logs_df.join(groups_df, how='left')
        return master_df