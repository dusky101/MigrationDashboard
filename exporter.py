import io
import os
import pandas as pd

from migrationaud import find_audit_file, parse_audit_csv

# --- OPT-IN: Future Pandas Behaviour ---
pd.set_option("future.no_silent_downcasting", True)


# -----------------------------------------------------------------------------
# 1) Sanitisation
# -----------------------------------------------------------------------------
def sanitize_for_excel(val):
    """
    Prevents Excel from interpreting text as formulas.
    """
    if pd.isna(val):
        return ""
    s_val = str(val)
    if not s_val:
        return ""
    if s_val.startswith(("=", "+", "-", "@")):
        return f"'{s_val}"
    return s_val


# -----------------------------------------------------------------------------
# 2) Cached audit loader (simple in-module cache; avoids re-parsing during export)
# -----------------------------------------------------------------------------
_AUDIT_CACHE: dict[str, tuple[float, pd.DataFrame | None]] = {}


def _load_audit_df(audit_path: str) -> pd.DataFrame | None:
    """
    Load and parse audit csv with an in-module cache keyed by path + mtime.
    This keeps export snappy for multi-user exports.
    """
    if not audit_path or not os.path.exists(audit_path):
        return None

    try:
        mtime = os.path.getmtime(audit_path)
    except Exception:
        mtime = 0.0

    cached = _AUDIT_CACHE.get(audit_path)
    if cached and cached[0] == mtime:
        return cached[1]

    df = parse_audit_csv(audit_path)
    _AUDIT_CACHE[audit_path] = (mtime, df)
    return df


# -----------------------------------------------------------------------------
# 3) Deep data extraction from audit
# -----------------------------------------------------------------------------
def get_comprehensive_machine_data(audit_path: str) -> dict:
    """
    Extract key values from the audit csv and also produce normalised lists.
    """
    data = {
        "Machine Model": "Pending Audit",
        "Serial Number": "-",
        "Processor": "-",
        "Memory": "-",
        "OS Version": "-",
        "Free Space": "-",
        "Tahoe Support": "-",
        "Printers": "-",
        "Peripherals": "-",
        "Network Interfaces": "-",
        "Installed Apps": "-",
    }

    if not audit_path:
        return data

    df = _load_audit_df(audit_path)
    if df is None or df.empty:
        return data

    def get_val(type_filter: str, name_key: str):
        subset = df[df["TYPE"] == type_filter]
        row = subset[subset["NAME"].astype(str).str.contains(name_key, case=False, na=False)]
        return row.iloc[0]["DETAILS"] if not row.empty else None

    def get_list(type_filters):
        if isinstance(type_filters, str):
            type_filters = [type_filters]
        subset = df[df["TYPE"].isin(type_filters)]
        if subset.empty:
            return "-"
        items = sorted(list(set(subset["NAME"].astype(str).str.strip())))
        items = [i for i in items if len(i) > 2]  # Filter short noise
        return "\n".join(items) if items else "-"

    val = get_val("System Specifications", "Model Identifier")
    if val:
        data["Machine Model"] = val

    val = get_val("System Specifications", "Serial Number")
    if val:
        data["Serial Number"] = val

    val = get_val("System Specifications", "Processor")
    if val:
        data["Processor"] = val

    val = get_val("System Specifications", "Memory")
    if val:
        data["Memory"] = val

    # Your audit exporter previously used 'macOS Version'
    # The audit CSV sometimes uses slightly different labelling; keep best effort.
    val = get_val("System Specifications", "macOS Version") or get_val("System Specifications", "OS Version")
    if val:
        data["OS Version"] = val

    val = get_val("System Specifications", "Available Space") or get_val("System Specifications", "Free Space")
    if val:
        data["Free Space"] = val

    val = get_val("System Specifications", "Tahoe Support")
    if val:
        data["Tahoe Support"] = val

    data["Printers"] = get_list(["Printers"])
    data["Peripherals"] = get_list(["External Peripherals", "DEVICE", "USB", "Built-in / System"])
    data["Network Interfaces"] = get_list(["Network & Storage"])

    # Restrict to 'Applications Folder' to reduce noise (as per your original choice)
    data["Installed Apps"] = get_list(["Applications Folder"])

    return data


# -----------------------------------------------------------------------------
# 4) Report generation
# -----------------------------------------------------------------------------
def _normalise_status_df(status_df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure status_df is indexed by email/user key and has Status/Notes/EntraCreated.
    """
    if status_df is None or status_df.empty:
        out = pd.DataFrame(columns=["Status", "Notes", "EntraCreated"])
        out.index.name = "User"
        return out

    out = status_df.copy()

    # If not indexed, try to index it
    if out.index.name is None or out.index.name == "":
        # Common case: there is an "Email" column
        if "Email" in out.columns:
            out["Email"] = out["Email"].astype(str).str.strip().str.lower()
            out = out.set_index("Email")
        elif "User" in out.columns:
            out["User"] = out["User"].astype(str).str.strip().str.lower()
            out = out.set_index("User")

    # Ensure expected columns exist
    if "Status" not in out.columns:
        out["Status"] = "Not Started"
    if "Notes" not in out.columns:
        out["Notes"] = ""
    if "EntraCreated" not in out.columns:
        out["EntraCreated"] = False

    # Normalise types
    out["Status"] = out["Status"].fillna("Not Started").astype(str)
    out["Notes"] = out["Notes"].fillna("").astype(str)
    out["EntraCreated"] = out["EntraCreated"].fillna(False).astype(bool)

    return out


def _build_master_df(google_df: pd.DataFrame, status_df: pd.DataFrame) -> pd.DataFrame:
    """
    Join Google and status data safely.
    If google_df is empty, master is built from status_df alone.
    """
    status_df = _normalise_status_df(status_df)

    if google_df is None or google_df.empty:
        master = status_df.copy()
        master.index.name = "User"
        return master

    g = google_df.copy()

    # Ensure index is clean
    try:
        g.index = g.index.astype(str).str.strip().str.lower()
    except Exception:
        pass

    master = g.join(status_df, how="left")
    master["Status"] = master["Status"].fillna("Not Started").astype(str)
    master["Notes"] = master["Notes"].fillna("").astype(str)
    master["EntraCreated"] = master["EntraCreated"].fillna(False).astype(bool)
    return master


def generate_excel_report(google_df, status_df, audit_folder, filtered_indices=None):
    """
    Generates an Excel report (Asset Register + App Inventory).
    Returns XLSX bytes suitable for Streamlit download_button.
    """
    output = io.BytesIO()

    master_df = _build_master_df(google_df, status_df)

    # Apply filtering if provided
    if filtered_indices is not None:
        # Be resilient: keep only indices that exist
        keep = [i for i in filtered_indices if i in master_df.index]
        if keep:
            master_df = master_df.loc[keep]
        else:
            # If none match, return an empty-but-valid workbook with headers
            master_df = master_df.iloc[0:0]

    # Enrich with Hardware Data & Build App List
    hardware_rows = []
    app_inventory_rows = []

    for user_key in master_df.index:
        audit_path = find_audit_file(audit_folder, user_key)
        machine = get_comprehensive_machine_data(audit_path)
        machine["User"] = user_key
        hardware_rows.append(machine)

        apps_str = machine.get("Installed Apps", "-")
        if apps_str and apps_str != "-":
            for app in apps_str.split("\n"):
                app = app.strip()
                if app:
                    app_inventory_rows.append({"Email": user_key, "Application": app})

    hardware_df = pd.DataFrame(hardware_rows).set_index("User") if hardware_rows else pd.DataFrame()

    full_report = master_df.join(hardware_df, how="left")

    # Sanitise all cells
    full_report = full_report.map(sanitize_for_excel)

    # Column Ordering (keeps your intended report shape)
    priority_cols = [
        "Admin-defined name",
        "Status",
        "Notes",
        "Machine Model",
        "Serial Number",
        "OS Version",
        "Memory",
        "Tahoe Support",
        "Free Space",
        "Printers",
        "Peripherals",
        "Org Unit Path",
        "Total storage used (MB)",
        "Recent Email Activity (30d)",
    ]

    existing_cols = full_report.columns.tolist()
    final_cols = [c for c in priority_cols if c in existing_cols]
    remaining = [c for c in existing_cols if c not in final_cols and c != "Installed Apps"]
    full_report = full_report[final_cols + remaining]

    # -------------------------------------------------------------------------
    # Write Excel
    # -------------------------------------------------------------------------
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book

        # Styles
        header_fmt = workbook.add_format(
            {"bold": True, "bg_color": "#2C3E50", "font_color": "white", "border": 1}
        )
        centered = workbook.add_format({"align": "center", "valign": "top"})
        text_wrap = workbook.add_format({"text_wrap": True, "valign": "top"})
        fmt_green = workbook.add_format({"bg_color": "#C6EFCE", "font_color": "#006100"})
        fmt_red = workbook.add_format({"bg_color": "#FFC7CE", "font_color": "#9C0006"})
        fmt_yellow = workbook.add_format({"bg_color": "#FFEB9C", "font_color": "#9C6500"})

        # --- SHEET 1: ASSET REGISTER ---
        sheet_name = "Asset Register"
        full_report.to_excel(writer, sheet_name=sheet_name, index=True, index_label="Email")
        ws_data = writer.sheets[sheet_name]

        max_row, max_col = full_report.shape

        # Add Excel table (only if there is data; table requires at least header row)
        column_settings = [{"header": "Email"}] + [{"header": str(col)} for col in full_report.columns]

        # Table needs row count including header row (row 0)
        # If max_row == 0, just format headers manually
        if max_row > 0:
            ws_data.add_table(
                0, 0, max_row, max_col,
                {
                    "columns": column_settings,
                    "style": "TableStyleMedium9",
                    "name": "MigrationData",
                },
            )

        ws_data.freeze_panes(1, 1)

        # Conditional formatting on Status column (find it dynamically)
        try:
            status_col_pos = 1 + list(full_report.columns).index("Status")  # +1 for Email index column
            # Convert 0-based col to Excel col letters (supports beyond Z)
            def col_letter(n: int) -> str:
                s = ""
                while n >= 0:
                    s = chr(n % 26 + 65) + s
                    n = n // 26 - 1
                return s

            col_ltr = col_letter(status_col_pos)
            rng = f"{col_ltr}2:{col_ltr}{max_row+1 if max_row > 0 else 2}"
            ws_data.conditional_format(rng, {"type": "text", "criteria": "containing", "value": "Complete", "format": fmt_green})
            ws_data.conditional_format(rng, {"type": "text", "criteria": "containing", "value": "Migration Run", "format": fmt_yellow})
            ws_data.conditional_format(rng, {"type": "text", "criteria": "containing", "value": "Issues", "format": fmt_red})
        except Exception:
            # If Status doesn't exist, do nothing
            pass

        # Column sizing (sensible defaults)
        ws_data.set_column(0, 0, 30, text_wrap)   # Email
        if max_col >= 1:
            ws_data.set_column(1, 1, 25, text_wrap)  # Admin-defined name (usually)
        # Wrap long list columns if present
        for i, col_name in enumerate(full_report.columns):
            idx = i + 1  # shift for index column
            if col_name in ["Printers", "Peripherals", "Network Interfaces", "Installed Apps", "Groups"]:
                ws_data.set_column(idx, idx, 35, text_wrap)
            elif col_name in ["Status"]:
                ws_data.set_column(idx, idx, 18, centered)
            else:
                ws_data.set_column(idx, idx, 20, text_wrap)

        # Apply header format (optional, table style already covers this, but keeps consistency when empty)
        for col_idx in range(0, max_col + 1):
            ws_data.write(0, col_idx, column_settings[col_idx]["header"], header_fmt)

        # --- SHEET 2: APP INVENTORY (NORMALISED) ---
        if app_inventory_rows:
            app_df = pd.DataFrame(app_inventory_rows)

            sheet_apps = "App Inventory"
            app_df.to_excel(writer, sheet_name=sheet_apps, index=False)
            ws_apps = writer.sheets[sheet_apps]

            app_rows, app_cols = app_df.shape
            app_col_settings = [{"header": str(col)} for col in app_df.columns]

            if app_rows > 0:
                ws_apps.add_table(
                    0, 0, app_rows, app_cols - 1,
                    {"columns": app_col_settings, "style": "TableStyleLight9", "name": "AppInventory"},
                )

            ws_apps.freeze_panes(1, 0)
            ws_apps.set_column(0, 0, 30)  # Email
            ws_apps.set_column(1, 1, 50)  # Application Name

    output.seek(0)
    return output.getvalue()
