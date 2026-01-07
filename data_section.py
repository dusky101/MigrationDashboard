import streamlit as st
import pandas as pd
import os
from migrationaud import find_audit_file, parse_audit_csv

def render_data_section(audit_folder, selected_user, google_users):
    
    user_data = google_users.loc[selected_user]
    
    tab_audit, tab_explore = st.tabs(["💻 Local Audit Report", "📊 Google Data Explorer"])

    # --- TAB 1: LOCAL AUDIT ---
    with tab_audit:
        if not os.path.isdir(audit_folder):
            st.warning("Audit Folder invalid.")
        else:
            audit_path = find_audit_file(audit_folder, selected_user)
            if audit_path:
                st.success(f"**Linked:** `{os.path.basename(audit_path)}`")
                audit_df = parse_audit_csv(audit_path)
                
                if audit_df is not None:
                    # Tabs: Specs, Apps, Network, Printers, Devices
                    t_specs, t_apps, t_net, t_print, t_dev = st.tabs(["🖥️ Specs", "📂 Apps", "☁️ Network", "🖨 Printers", "🔌 Devices"])
                    
                    # --- 1. SYSTEM SPECS (Updated for Tahoe & RAM) ---
                    with t_specs:
                        st.caption("Hardware & System Details")
                        specs = audit_df[audit_df['TYPE'] == 'System Specifications']
                        
                        if not specs.empty:
                            # --- HERO METRICS EXTRACTION ---
                            # Helper to safely grab values from the dataframe
                            def get_spec(name_key):
                                row = specs[specs['NAME'].astype(str).str.contains(name_key, case=False, na=False)]
                                return row.iloc[0]['DETAILS'] if not row.empty else "N/A"

                            # Extract key data points
                            model = get_spec("Model Identifier")
                            ram = get_spec("Memory") # Matches "Memory (RAM)" or "Physical Memory"
                            serial = get_spec("Serial Number")
                            tahoe = get_spec("Tahoe Support")

                            # Display Top Row Metrics
                            c1, c2, c3 = st.columns(3)
                            c1.metric("Machine Model", model)
                            c2.metric("Memory (RAM)", ram)
                            c3.metric("Serial Number", serial)
                            
                            st.divider()

                            # Display Tahoe Compliance Status visually
                            # The CSV returns icons like "❌ Unsupported" or "✅ Supported"
                            if "Unsupported" in tahoe:
                                st.error(f"**AI Readiness:** {tahoe} (Hardware upgrade required)")
                            elif "OS Only" in tahoe:
                                st.warning(f"**AI Readiness:** {tahoe} (OS Update required for full features)")
                            elif "Supported" in tahoe:
                                st.success(f"**AI Readiness:** {tahoe}")
                            else:
                                # Fallback if field is missing or format is different
                                st.info(f"**AI Readiness:** {tahoe}")

                            st.divider()
                            
                            # Show full list (excluding the ones we just highlighted to save space? 
                            # No, let's show all for completeness in case parsing misses something)
                            st.dataframe(specs[['NAME', 'DETAILS']], width="stretch", hide_index=True)
                        else:
                            st.info("No system specs found.")

                    # --- 2. APPS ---
                    with t_apps:
                        col_app1, col_app2 = st.columns(2)
                        
                        # LEFT: Installed Apps (User Folder)
                        with col_app1:
                            st.markdown("**User Apps (Folder)**")
                            main = audit_df[audit_df['TYPE'] == 'Applications Folder']
                            if not main.empty: 
                                st.dataframe(main[['NAME', 'DETAILS']], width="stretch", hide_index=True)
                            else: 
                                st.caption("Empty")
                        
                        # RIGHT: Detected Apps (Grouping & Filter Enabled)
                        with col_app2:
                            st.markdown("**Installed / Detected Apps**")
                            other = audit_df[audit_df['TYPE'].isin(['Detected Applications', 'System Internals'])]
                            
                            if not other.empty:
                                # 1. Get unique developers for filter
                                devs = sorted(other['DEVELOPER'].astype(str).unique().tolist())
                                
                                # 2. Filter Widget
                                sel_devs = st.multiselect("Filter by Developer", devs, placeholder="e.g. Adobe")
                                
                                # 3. Grouping Toggle
                                group_view = st.toggle("Group by Developer", value=True)
                                
                                # LOGIC: Filter -> Then Group or Show
                                df_show = other if not sel_devs else other[other['DEVELOPER'].isin(sel_devs)]
                                
                                if not df_show.empty:
                                    if group_view:
                                        # Render as Expanders (Minimised Sections)
                                        current_devs = sorted(df_show['DEVELOPER'].unique())
                                        for d in current_devs:
                                            subset = df_show[df_show['DEVELOPER'] == d]
                                            with st.expander(f"{d} ({len(subset)})"):
                                                st.dataframe(subset[['NAME', 'DETAILS']], width="stretch", hide_index=True)
                                    else:
                                        # Render as Big Table
                                        st.dataframe(df_show[['DEVELOPER', 'NAME', 'DETAILS']], width="stretch", hide_index=True)
                                else:
                                    st.info("No apps match filter.")
                            else:
                                st.caption("Empty")
                    
                    # --- 3. OTHER TABS ---
                    with t_net:
                        net = audit_df[audit_df['TYPE'] == 'Network & Storage']
                        if not net.empty: st.dataframe(net[['NAME', 'DETAILS']], width="stretch", hide_index=True)
                        else: st.info("None")
                    
                    with t_print:
                        printr = audit_df[audit_df['TYPE'] == 'Printers']
                        if not printr.empty: st.dataframe(printr[['NAME', 'DETAILS']], width="stretch", hide_index=True)
                        else: st.info("None")
                    
                    with t_dev:
                        dev = audit_df[audit_df['TYPE'].isin(['External Peripherals', 'DEVICE', 'Built-in / System'])]
                        if not dev.empty: st.dataframe(dev[['NAME', 'DETAILS']], width="stretch", hide_index=True)
                        else: st.info("None")
            else:
                st.warning(f"⚠️ No Audit File for **{selected_user}**")

    # --- TAB 2: EXPLORER ---
    with tab_explore:
        st.markdown("### 🔍 Migration Record")
        st.caption("Key user data points extracted from Google Workspace logs.")
        
        df_for_display = google_users.reset_index()
        all_cols = df_for_display.columns.tolist()
        
        preferred_cols = ['User', 'Admin-defined name', 'Role', 'User account status', 'Total storage used (MB)', 
                          'Gmail (Web) - last used time', 'Org Unit Path', 'Groups', 'External apps']
        default_cols = [c for c in preferred_cols if c in all_cols]
        
        selected_cols = st.multiselect("Select Data Points:", all_cols, default=default_cols)
        
        if selected_cols:
            storage_cols_found = [c for c in selected_cols if 'storage used (mb)' in c.lower() or 'quota' in c.lower()]
            
            use_gb = False
            if storage_cols_found:
                smart_default = False
                for c in storage_cols_found:
                    try:
                        if float(user_data.get(c, 0)) > 1024:
                            smart_default = True
                            break
                    except:
                        pass
                use_gb = st.toggle("Show Storage in GB", value=smart_default)
            
            data_to_show = df_for_display[selected_cols].copy()
            
            if use_gb:
                for col in storage_cols_found:
                    try:
                        val_mb = data_to_show[col].astype(float)
                        val_gb = val_mb / 1024
                        data_to_show[col] = val_gb.map('{:.2f}'.format)
                        new_header = col.replace("(MB)", "(GB)").replace("(mb)", "(GB)").replace("_in_mb", "_in_gb")
                        data_to_show = data_to_show.rename(columns={col: new_header})
                    except:
                        pass

            st.dataframe(data_to_show.astype(str), width="stretch")
        else:
            st.info("Select columns above to view data.")