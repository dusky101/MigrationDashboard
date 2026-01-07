import pandas as pd
import io
import os
from migrationaud import find_audit_file, parse_audit_csv

# --- OPT-IN: Future Pandas Behavior ---
# This silences the "Downcasting" warning by disabling silent type inference.
# We explicitly handle types later with .astype(), so this is safe and correct.
pd.set_option('future.no_silent_downcasting', True)

# --- 1. SANITIZATION LOGIC ---
def sanitize_for_excel(val):
    """
    Prevents Excel from interpreting text as formulas.
    """
    if pd.isna(val):
        return ""
    
    s_val = str(val)
    if not s_val: 
        return ""
    
    # Excel Formula Injection triggers
    if s_val.startswith(('=', '+', '-', '@')):
        return f"'{s_val}"
    
    return s_val

# --- 2. DEEP DATA EXTRACTION ---
def get_comprehensive_machine_data(audit_path):
    data = {
        "Machine Model": "Pending Audit", "Serial Number": "-", "Processor": "-",
        "Memory": "-", "OS Version": "-", "Free Space": "-", "Printers": "-",
        "Peripherals": "-", "Network Interfaces": "-", "Installed Apps": "-"
    }
    
    if not audit_path: return data
    df = parse_audit_csv(audit_path)
    if df is None or df.empty: return data
        
    def get_val(type_filter, name_key):
        subset = df[df['TYPE'] == type_filter]
        row = subset[subset['NAME'].astype(str).str.contains(name_key, case=False, na=False)]
        return row.iloc[0]['DETAILS'] if not row.empty else None

    def get_list(type_filters):
        if isinstance(type_filters, str): type_filters = [type_filters]
        subset = df[df['TYPE'].isin(type_filters)]
        if subset.empty: return "-"
        items = sorted(list(set(subset['NAME'].astype(str).str.strip())))
        items = [i for i in items if len(i) > 2]
        return "\n".join(items) if items else "-"

    val = get_val('System Specifications', 'Model Identifier'); 
    if val: data['Machine Model'] = val
    val = get_val('System Specifications', 'Serial Number'); 
    if val: data['Serial Number'] = val
    val = get_val('System Specifications', 'Processor'); 
    if val: data['Processor'] = val
    val = get_val('System Specifications', 'Memory'); 
    if val: data['Memory'] = val
    val = get_val('System Specifications', 'macOS Version'); 
    if val: data['OS Version'] = val
    val = get_val('System Specifications', 'Available Space'); 
    if val: data['Free Space'] = val

    data['Printers'] = get_list(['Printers'])
    data['Peripherals'] = get_list(['External Peripherals', 'DEVICE', 'USB'])
    data['Network Interfaces'] = get_list(['Network & Storage'])
    data['Installed Apps'] = get_list(['Applications Folder', 'Detected Applications'])

    return data

# --- 3. REPORT GENERATION ---
def generate_excel_report(google_df, status_df, audit_folder, filtered_indices=None):
    output = io.BytesIO()

    # A. Prepare Data
    master_df = google_df.join(status_df, how='left')
    
    if filtered_indices is not None:
        master_df = master_df.loc[filtered_indices]

    master_df['Status'] = master_df['Status'].fillna('Not Started')
    master_df['Notes'] = master_df['Notes'].fillna('')
    
    # With the future option set, fillna(False) keeps the column as 'object' (safe),
    # and .astype(bool) then forcibly converts it to boolean. Warning Gone.
    master_df['EntraCreated'] = master_df['EntraCreated'].fillna(False).astype(bool)

    # B. Enrich with Hardware Data
    hardware_data = []
    for user_email in master_df.index:
        audit_path = find_audit_file(audit_folder, user_email)
        user_data = get_comprehensive_machine_data(audit_path)
        user_data['User'] = user_email
        hardware_data.append(user_data)
        
    hardware_df = pd.DataFrame(hardware_data).set_index('User')
    full_report = master_df.join(hardware_df, how='left')
    
    # Apply Sanitization
    full_report = full_report.map(sanitize_for_excel)

    # C. Column Ordering
    priority_cols = [
        'Admin-defined name', 'Status', 'Notes', 
        'Machine Model', 'Serial Number', 'OS Version', 'Memory', 'Free Space',
        'Printers', 'Peripherals', 'Installed Apps',
        'Org Unit Path', 'Total storage used (MB)', 'Recent Email Activity (30d)'
    ]
    
    existing_cols = full_report.columns.tolist()
    final_cols = [c for c in priority_cols if c in existing_cols]
    remaining = [c for c in existing_cols if c not in final_cols]
    full_report = full_report[final_cols + remaining]

    # --- 4. WRITE EXCEL ---
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book

        # Formats
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#2C3E50', 'font_color': 'white', 'border': 1})
        centered = workbook.add_format({'align': 'center', 'valign': 'top'})
        text_wrap = workbook.add_format({'text_wrap': True, 'valign': 'top'})
        
        # Format for Status Colors
        fmt_green = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
        fmt_red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
        fmt_yellow = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500'})

        # --- MAIN SHEET: ASSET REGISTER ---
        sheet_name = 'Asset Register'
        full_report.to_excel(writer, sheet_name=sheet_name, index=True, index_label="Email")
        ws_data = writer.sheets[sheet_name]
        
        # 1. Create the Table (This enables the Filter/Search Arrows)
        (max_row, max_col) = full_report.shape
        column_settings = [{'header': 'Email'}] + [{'header': str(col)} for col in full_report.columns]
        
        ws_data.add_table(0, 0, max_row, max_col, {
            'columns': column_settings,
            'style': 'TableStyleMedium9',
            'name': 'MigrationData'
        })
        
        # 2. Freeze Panes (Keeps Header & Email visible while scrolling)
        ws_data.freeze_panes(1, 1)

        # 3. Conditional Formatting (Traffic Lights for Status)
        # Find the 'Status' column index (It's usually column 2, index 2)
        status_col_idx = 2 
        
        # Range: C2:C1000
        rng = f"{chr(65+status_col_idx)}2:{chr(65+status_col_idx)}{max_row+1}"
        
        ws_data.conditional_format(rng, {'type': 'text', 'criteria': 'containing', 'value': 'Complete', 'format': fmt_green})
        ws_data.conditional_format(rng, {'type': 'text', 'criteria': 'containing', 'value': 'Migration Run', 'format': fmt_yellow})
        ws_data.conditional_format(rng, {'type': 'text', 'criteria': 'containing', 'value': 'Issues', 'format': fmt_red})

        # 4. Column Widths
        ws_data.set_column(0, 0, 30, text_wrap) # Email
        ws_data.set_column(1, 1, 25, text_wrap) # Name
        ws_data.set_column(2, 2, 18, centered)  # Status (Widened)
        ws_data.set_column(3, 3, 30, text_wrap) # Notes
        ws_data.set_column(4, 7, 15, text_wrap) # Hardware Specs
        
        for i, col_name in enumerate(full_report.columns):
            idx = i + 1
            if col_name in ['Printers', 'Peripherals', 'Network Interfaces']:
                ws_data.set_column(idx, idx, 35, text_wrap)
            elif col_name == 'Installed Apps':
                ws_data.set_column(idx, idx, 50, text_wrap)

    output.seek(0)
    return output