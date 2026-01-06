import pandas as pd
import os
import glob
import streamlit as st

def load_google_data(folder_path):
    """Merges all Google CSVs into one master dataframe based on Email."""
    logs_df = pd.DataFrame()
    groups_df = pd.DataFrame()
    
    if not os.path.isdir(folder_path):
        return pd.DataFrame()

    files = glob.glob(os.path.join(folder_path, "*.csv"))
    if not files:
        return pd.DataFrame() 

    for file in files:
        # --- NEW SAFETY CHECK ---
        # If an 'Audit Report' was accidentally saved in the Google Data folder,
        # skip it immediately so we don't try to read it and crash.
        filename = os.path.basename(file)
        if filename.startswith("Audit_Report_"):
            continue

        try:
            df = pd.read_csv(file)
            
            # 1. Clean Column Names
            # Remove [Date] brackets: "Drive Usage [2025-01-01]" -> "Drive Usage"
            df.columns = [c.split(" [")[0].strip() for c in df.columns]
            
            # Normalize 'Member Email' to 'User' (found in some Group exports)
            if 'Member Email' in df.columns:
                df = df.rename(columns={'Member Email': 'User'})
            
            # Skip files that don't have a User identifier
            if 'User' not in df.columns:
                continue

            # 2. Identify & Process File Type
            
            # Case A: Group Data (One user belongs to multiple groups)
            if 'Group Name' in df.columns:
                # IMPROVEMENT: strips whitespace and handles non-string data safely
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
            # This is where your error was coming from. 
            # Now that we skip Audit files above, this shouldn't trigger for them.
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