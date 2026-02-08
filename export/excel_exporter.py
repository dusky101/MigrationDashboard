"""
Excel Report Generator

Generates comprehensive Excel reports with:
- Model identifier transformations (Mac16,7 → MacBook Pro 16-inch M4 Max)
- macOS version transformations (Version 24.2 → macOS 15 Sequoia 15.2)
- Email address extraction from audit data
- Logged-in user information from audit
- Conditional formatting for warnings
- Reference sheets for decode tables
"""

import io
import os
import re
import pandas as pd

from core.audit_parser import find_audit_file, parse_audit_csv
from models.mac_models import get_friendly_model_name, get_model_chip_variant
from models.macos_versions import get_macos_friendly_name

# --- OPT-IN: Future Pandas Behaviour ---
pd.set_option("future.no_silent_downcasting", True)

# -----------------------------------------------------------------------------
# 1) Sanitisation
# -----------------------------------------------------------------------------
def sanitize_for_excel(val):
    """
    Prevent Excel interpreting text as formulas.
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
# 3) Helpers: parse sizes like "13.44 GB" / "94.9 MB"
# -----------------------------------------------------------------------------
_SIZE_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([KMG]B)\s*$", re.IGNORECASE)


def _size_to_gb(val: str) -> float:
    """
    Converts strings like "13.44 GB", "94.9 MB", "120 KB" to GB (float).
    Returns 0.0 if unknown/unparseable.
    """
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return 0.0
    s = str(val).strip()
    if not s:
        return 0.0

    m = _SIZE_RE.match(s)
    if not m:
        return 0.0

    num = float(m.group(1))
    unit = m.group(2).upper()

    if unit == "GB":
        return num
    if unit == "MB":
        return num / 1024
    if unit == "KB":
        return num / (1024 * 1024)
    return 0.0


def _sum_type_sizes_gb(df: pd.DataFrame, type_name: str) -> float:
    """
    Sums DETAILS size values for a given TYPE.
    """
    if df is None or df.empty:
        return 0.0
    subset = df[df["TYPE"].astype(str) == type_name]
    if subset.empty:
        return 0.0
    return float(sum(_size_to_gb(x) for x in subset["DETAILS"].astype(str).tolist()))


def _get_first_details(df: pd.DataFrame, type_filter: str, name_contains: str) -> str | None:
    """
    Best-effort lookup: within TYPE, find first row where NAME contains substring.
    Returns DETAILS or None.
    """
    if df is None or df.empty:
        return None
    subset = df[df["TYPE"].astype(str) == type_filter]
    if subset.empty:
        return None
    mask = subset["NAME"].astype(str).str.contains(name_contains, case=False, na=False)
    row = subset[mask]
    if row.empty:
        return None
    return str(row.iloc[0].get("DETAILS", "")).strip() or None


def _yes_no(flag: bool) -> str:
    return "Yes" if bool(flag) else "No"


def _extract_email_from_audit(df: pd.DataFrame) -> str:
    """
    Extract actual email address from Email Accounts section of audit.
    Returns first valid email found, or "-" if none found.
    """
    if df is None or df.empty:
        return "-"
    
    email_accounts = df[df["TYPE"] == "Email Accounts"].copy()
    if email_accounts.empty:
        return "-"
    
    # Look for email pattern in DETAILS column
    email_pattern = re.compile(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})')
    
    for detail in email_accounts["DETAILS"].astype(str).tolist():
        match = email_pattern.search(detail)
        if match:
            return match.group(1)
    
    return "-"


# -----------------------------------------------------------------------------
# 4) Deep data extraction from audit ⭐ WITH MODEL, EMAIL & USER TRANSFORMATIONS
# -----------------------------------------------------------------------------
def get_comprehensive_machine_data(audit_path: str) -> dict:
    """
    Extracts key values from the audit CSV with transformations:
    - Model identifiers → Friendly names
    - macOS versions → Marketing names
    - Email accounts → Actual email addresses
    - Logged-in user → User name and login name
    
    Returns both friendly names and original codes for IT reference.
    """
    data = {
        # Core - Friendly Names
        "Machine Model": "Pending Audit",
        "Model Code": "-",
        "Model Chip": "-",
        "Serial Number": "-",
        "Processor": "-",
        "Memory": "-",
        "OS Version": "-",
        "OS Version Code": "-",
        "Disk Capacity": "-",
        "Available Space": "-",
        "Email Address": "-",  # ⭐ Actual email from audit
        "Logged-in User": "-",  # ⭐ NEW: User's full name
        "Login Name": "-",      # ⭐ NEW: User's login name
        # Media
        "Music Library Size (GB)": "",
        "Photos Library Size (GB)": "",
        # Homebrew
        "Homebrew Installed": "No",
        "Homebrew Package Count": "",
        # Legacy fields
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

    # =========================================================================
    # EMAIL ADDRESS EXTRACTION ⭐
    # =========================================================================
    data["Email Address"] = _extract_email_from_audit(df)

    # =========================================================================
    # LOGGED-IN USER EXTRACTION ⭐ NEW
    # =========================================================================
    logged_user = _get_first_details(df, "System Specifications", "Logged-in User")
    if logged_user:
        data["Logged-in User"] = logged_user

    login_name = _get_first_details(df, "System Specifications", "Login Name")
    if login_name:
        data["Login Name"] = login_name

    # =========================================================================
    # MODEL IDENTIFIER TRANSFORMATION ⭐
    # =========================================================================
    raw_model = _get_first_details(df, "System Specifications", "Model Identifier")
    if raw_model:
        data["Model Code"] = raw_model
        friendly_model = get_friendly_model_name(raw_model)
        data["Machine Model"] = friendly_model
        
        chip_variant = get_model_chip_variant(raw_model)
        data["Model Chip"] = chip_variant if chip_variant != "Unknown" else "-"

    # =========================================================================
    # macOS VERSION TRANSFORMATION ⭐
    # =========================================================================
    raw_version = _get_first_details(df, "System Specifications", "macOS Version") or _get_first_details(df, "System Specifications", "OS Version")
    if raw_version:
        data["OS Version Code"] = raw_version
        friendly_version = get_macos_friendly_name(raw_version)
        data["OS Version"] = friendly_version

    # =========================================================================
    # OTHER SYSTEM SPECIFICATIONS
    # =========================================================================
    val = _get_first_details(df, "System Specifications", "Serial Number")
    if val:
        data["Serial Number"] = val

    val = _get_first_details(df, "System Specifications", "Processor")
    if val:
        data["Processor"] = val

    val = _get_first_details(df, "System Specifications", "Memory")
    if val:
        data["Memory"] = val

    disk = _get_first_details(df, "System Specifications", "Hard Drive Capacity")
    if disk:
        data["Disk Capacity"] = disk

    avail = _get_first_details(df, "System Specifications", "Available Space") or _get_first_details(df, "System Specifications", "Free Space")
    if avail:
        data["Available Space"] = avail
        data["Free Space"] = avail

    tahoe = _get_first_details(df, "System Specifications", "Tahoe Support")
    if tahoe:
        data["Tahoe Support"] = tahoe

    # =========================================================================
    # MEDIA LIBRARY SIZES
    # =========================================================================
    music_gb = _sum_type_sizes_gb(df, "Music Library")
    photos_gb = _sum_type_sizes_gb(df, "Photos Library")
    data["Music Library Size (GB)"] = f"{music_gb:.2f}" if music_gb > 0 else ""
    data["Photos Library Size (GB)"] = f"{photos_gb:.2f}" if photos_gb > 0 else ""

    # =========================================================================
    # HOMEBREW DETECTION
    # =========================================================================
    brew = df[df["TYPE"].astype(str) == "Homebrew Packages"].copy()
    if not brew.empty:
        hb_marker = brew[brew["NAME"].astype(str).str.contains("Homebrew Installed", case=False, na=False)]
        brew_installed = not hb_marker.empty
        data["Homebrew Installed"] = _yes_no(brew_installed)

        formulae = brew[brew["DETAILS"].astype(str).str.contains("Homebrew Formula", case=False, na=False)]
        if not formulae.empty:
            data["Homebrew Package Count"] = str(len(formulae))
        else:
            summary = brew[brew["NAME"].astype(str).str.contains("Brew Packages", case=False, na=False)]
            if not summary.empty:
                s = str(summary.iloc[0].get("DETAILS", ""))
                m = re.search(r"(\d+)", s)
                if m:
                    data["Homebrew Package Count"] = m.group(1)

    # =========================================================================
    # LISTS (legacy behaviour for backwards compatibility)
    # =========================================================================
    def get_list(type_filters):
        if isinstance(type_filters, str):
            type_filters = [type_filters]
        subset = df[df["TYPE"].isin(type_filters)]
        if subset.empty:
            return "-"
        items = sorted(list(set(subset["NAME"].astype(str).str.strip())))
        items = [i for i in items if len(i) > 2]
        return "\n".join(items) if items else "-"

    data["Printers"] = get_list(["Printers"])
    data["Peripherals"] = get_list(["External Peripherals", "DEVICE", "USB", "Built-in / System"])
    data["Network Interfaces"] = get_list(["Network & Storage"])
    data["Installed Apps"] = get_list(["Applications Folder"])

    return data


def extract_fonts_rows(audit_path: str, user_key: str) -> list[dict]:
    """
    Returns rows suitable for the Fonts sheet.
    """
    df = _load_audit_df(audit_path)
    if df is None or df.empty:
        return []
    
    fonts = df[df["TYPE"].astype(str) == "Fonts"].copy()
    if fonts.empty:
        return []

    out = []
    for _, r in fonts.iterrows():
        out.append(
            {
                "Email": user_key,
                "Font": str(r.get("NAME", "")).strip(),
                "Scope": str(r.get("DEVELOPER", "")).strip(),
                "Path": str(r.get("DETAILS", "")).strip(),
            }
        )
    return out


def extract_homebrew_rows(audit_path: str, user_key: str) -> list[dict]:
    """
    Returns rows suitable for the Homebrew Apps sheet (formulae only).
    """
    df = _load_audit_df(audit_path)
    if df is None or df.empty:
        return []
    
    brew = df[df["TYPE"].astype(str) == "Homebrew Packages"].copy()
    if brew.empty:
        return []

    formulae = brew[brew["DETAILS"].astype(str).str.contains("Homebrew Formula", case=False, na=False)].copy()
    if formulae.empty:
        return []

    out = []
    for _, r in formulae.iterrows():
        out.append(
            {
                "Email": user_key,
                "Package": str(r.get("NAME", "")).strip(),
                "Source": str(r.get("DEVELOPER", "")).strip(),
                "Type": str(r.get("DETAILS", "")).strip(),
            }
        )
    return out


# -----------------------------------------------------------------------------
# 5) Report generation
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

    if out.index.name is None or out.index.name == "":
        if "Email" in out.columns:
            out["Email"] = out["Email"].astype(str).str.strip().str.lower()
            out = out.set_index("Email")
        elif "User" in out.columns:
            out["User"] = out["User"].astype(str).str.strip().str.lower()
            out = out.set_index("User")

    if "Status" not in out.columns:
        out["Status"] = "Not Started"
    if "Notes" not in out.columns:
        out["Notes"] = ""
    if "EntraCreated" not in out.columns:
        out["EntraCreated"] = False

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
    try:
        g.index = g.index.astype(str).str.strip().str.lower()
    except Exception:
        pass

    master = g.join(status_df, how="left")
    master["Status"] = master["Status"].fillna("Not Started").astype(str)
    master["Notes"] = master["Notes"].fillna("").astype(str)
    master["EntraCreated"] = master["EntraCreated"].fillna(False).astype(bool)
    return master


def _friendly_name_from_key(user_key: str) -> str:
    """
    Derive friendly name from user key.
    If email: extract name before @
    Otherwise: capitalize words
    """
    if not user_key:
        return ""
    s = str(user_key).strip()
    if "@" in s:
        return s.split("@")[0].replace(".", " ").title()
    return s.replace(".", " ").title()


def _build_name_lookup(master_df: pd.DataFrame) -> dict[str, str]:
    """
    Returns { user_key: display_name }
    Prefers 'Admin-defined name' if present; otherwise derives from user_key.
    """
    lookup: dict[str, str] = {}
    if master_df is None or master_df.empty:
        return lookup

    has_name = "Admin-defined name" in master_df.columns
    for user_key in master_df.index:
        nm = ""
        if has_name:
            try:
                nm = str(master_df.loc[user_key, "Admin-defined name"] or "").strip()
            except Exception:
                nm = ""
        lookup[str(user_key)] = nm if nm else _friendly_name_from_key(str(user_key))
    return lookup


def generate_excel_report(google_df, status_df, audit_folder, filtered_indices=None):
    """
    Generates an Excel report with MODEL, macOS VERSION, EMAIL, and USER transformations:
      - Asset Register (front sheet with friendly names + actual emails + logged-in users)
      - App Inventory (normalised)
      - Fonts (audit-derived)
      - Homebrew Apps (audit-derived)
      - Reference: Model Codes (decode table)
      - Reference: macOS Versions (decode table)
      
    Returns XLSX bytes suitable for Streamlit download_button.
    """
    output = io.BytesIO()
    master_df = _build_master_df(google_df, status_df)

    # Apply filtering if provided
    if filtered_indices is not None:
        keep = [i for i in filtered_indices if i in master_df.index]
        master_df = master_df.loc[keep] if keep else master_df.iloc[0:0]

    # Build Name lookup for all sheets
    name_lookup = _build_name_lookup(master_df)

    # Enrich with audit-derived data
    hardware_rows = []
    app_inventory_rows = []
    fonts_rows = []
    brew_rows = []

    for user_key in master_df.index:
        audit_path = find_audit_file(audit_folder, user_key)

        machine = get_comprehensive_machine_data(audit_path)
        machine["User"] = user_key
        hardware_rows.append(machine)

        # Get actual email (prefer from audit, fallback to user_key if it looks like an email)
        actual_email = machine.get("Email Address", "-")
        if actual_email == "-" and "@" in str(user_key):
            actual_email = str(user_key)

        # App inventory
        apps_str = machine.get("Installed Apps", "-")
        if apps_str and apps_str != "-":
            for app in apps_str.split("\n"):
                app = app.strip()
                if app:
                    app_inventory_rows.append(
                        {
                            "Name": name_lookup.get(str(user_key), _friendly_name_from_key(str(user_key))),
                            "Email": actual_email,
                            "Application": app,
                        }
                    )

        # Fonts + Homebrew sheets (use actual email)
        if audit_path:
            extracted_fonts = extract_fonts_rows(audit_path, actual_email)
            for r in extracted_fonts:
                r["Name"] = name_lookup.get(str(user_key), _friendly_name_from_key(str(user_key)))
            fonts_rows.extend(extracted_fonts)

            extracted_brew = extract_homebrew_rows(audit_path, actual_email)
            for r in extracted_brew:
                r["Name"] = name_lookup.get(str(user_key), _friendly_name_from_key(str(user_key)))
            brew_rows.extend(extracted_brew)

    hardware_df = pd.DataFrame(hardware_rows).set_index("User") if hardware_rows else pd.DataFrame()
    full_report = master_df.join(hardware_df, how="left")

    # Sanitise all cells
    full_report = full_report.map(sanitize_for_excel)

    # Remove "Admin-defined name" to avoid duplication (we use "Name" column instead)
    if "Admin-defined name" in full_report.columns:
        full_report = full_report.drop(columns=["Admin-defined name"])

    # Column ordering (front sheet) - prioritise friendly names, keep codes for reference
    priority_cols = [
        "Status",
        "Notes",
        "Email Address",          # ⭐ Actual email from audit
        "Logged-in User",         # ⭐ NEW: User's full name
        "Login Name",             # ⭐ NEW: User's login name
        "Machine Model",
        "Model Chip",
        "Model Code",
        "Serial Number",
        "Processor",
        "Memory",
        "OS Version",
        "OS Version Code",
        "Disk Capacity",
        "Available Space",
        "Music Library Size (GB)",
        "Photos Library Size (GB)",
        "Homebrew Installed",
        "Homebrew Package Count",
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

    # =========================================================================
    # Write Excel
    # =========================================================================
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book

        # Formats
        header_fmt = workbook.add_format({"bold": True, "bg_color": "#2C3E50", "font_color": "white", "border": 1})
        centered = workbook.add_format({"align": "center", "valign": "top"})
        text_wrap = workbook.add_format({"text_wrap": True, "valign": "top"})
        fmt_green = workbook.add_format({"bg_color": "#C6EFCE", "font_color": "#006100"})
        fmt_red = workbook.add_format({"bg_color": "#FFC7CE", "font_color": "#9C0006"})
        fmt_yellow = workbook.add_format({"bg_color": "#FFEB9C", "font_color": "#9C6500"})
        fmt_orange = workbook.add_format({"bg_color": "#FFD8B1", "font_color": "#974706"})

        # =====================================================================
        # SHEET 1: ASSET REGISTER
        # =====================================================================
        sheet_name = "Asset Register"

        export_df = full_report.copy()
        
        # Insert Name and User Key columns at front
        export_df.insert(
            0,
            "Name",
            [name_lookup.get(str(idx), _friendly_name_from_key(str(idx))) for idx in export_df.index],
        )
        export_df.insert(1, "User Key", [str(idx) for idx in export_df.index])

        export_df.to_excel(writer, sheet_name=sheet_name, index=False)
        ws_data = writer.sheets[sheet_name]

        max_row, max_col = export_df.shape

        column_settings = [{"header": str(col)} for col in export_df.columns]

        if max_row > 0:
            ws_data.add_table(
                0, 0, max_row, max_col - 1,
                {"columns": column_settings, "style": "TableStyleMedium9", "name": "MigrationData"},
            )

        ws_data.freeze_panes(1, 2)

        # =====================================================================
        # CONDITIONAL FORMATTING
        # =====================================================================
        try:
            # Status column - green/yellow/red badges
            if "Status" in export_df.columns:
                status_col_pos = list(export_df.columns).index("Status")
                col_ltr = chr(65 + status_col_pos) if status_col_pos < 26 else f"A{chr(65 + status_col_pos - 26)}"
                rng = f"{col_ltr}2:{col_ltr}{max_row+1}"
                ws_data.conditional_format(rng, {"type": "text", "criteria": "containing", "value": "Complete", "format": fmt_green})
                ws_data.conditional_format(rng, {"type": "text", "criteria": "containing", "value": "Migration Run", "format": fmt_yellow})
                ws_data.conditional_format(rng, {"type": "text", "criteria": "containing", "value": "Issues", "format": fmt_red})

            # Memory column - warn if < 16GB
            if "Memory" in export_df.columns:
                mem_col_pos = list(export_df.columns).index("Memory")
                col_ltr = chr(65 + mem_col_pos) if mem_col_pos < 26 else f"A{chr(65 + mem_col_pos - 26)}"
                rng = f"{col_ltr}2:{col_ltr}{max_row+1}"
                ws_data.conditional_format(rng, {"type": "text", "criteria": "containing", "value": "8 GB", "format": fmt_orange})
                ws_data.conditional_format(rng, {"type": "text", "criteria": "containing", "value": "4 GB", "format": fmt_red})

            # Homebrew Installed - green badge for Yes
            if "Homebrew Installed" in export_df.columns:
                brew_col_pos = list(export_df.columns).index("Homebrew Installed")
                col_ltr = chr(65 + brew_col_pos) if brew_col_pos < 26 else f"A{chr(65 + brew_col_pos - 26)}"
                rng = f"{col_ltr}2:{col_ltr}{max_row+1}"
                ws_data.conditional_format(rng, {"type": "text", "criteria": "containing", "value": "Yes", "format": fmt_green})

        except Exception:
            pass

        # =====================================================================
        # COLUMN SIZING
        # =====================================================================
        ws_data.set_column(0, 0, 24, text_wrap)  # Name
        ws_data.set_column(1, 1, 20, text_wrap)  # User Key

        for i, col_name in enumerate(export_df.columns):
            if i in (0, 1):
                continue
            if col_name == "Email Address":
                ws_data.set_column(i, i, 32, text_wrap)  # Email Address
            elif col_name == "Logged-in User":
                ws_data.set_column(i, i, 24, text_wrap)  # ⭐ NEW
            elif col_name == "Login Name":
                ws_data.set_column(i, i, 18, centered)   # ⭐ NEW
            elif col_name == "Machine Model":
                ws_data.set_column(i, i, 40, text_wrap)
            elif col_name in ["Model Code", "OS Version Code"]:
                ws_data.set_column(i, i, 18, centered)
            elif col_name == "OS Version":
                ws_data.set_column(i, i, 35, text_wrap)
            elif col_name in ["Printers", "Peripherals", "Network Interfaces", "Groups", "Notes"]:
                ws_data.set_column(i, i, 35, text_wrap)
            elif col_name in ["Status", "Homebrew Installed", "Model Chip"]:
                ws_data.set_column(i, i, 18, centered)
            elif col_name in ["Processor"]:
                ws_data.set_column(i, i, 28, text_wrap)
            else:
                ws_data.set_column(i, i, 20, text_wrap)

        # Ensure header format
        for col_idx in range(0, max_col):
            ws_data.write(0, col_idx, column_settings[col_idx]["header"], header_fmt)

        # =====================================================================
        # SHEET 2: APP INVENTORY
        # =====================================================================
        if app_inventory_rows:
            app_df = pd.DataFrame(app_inventory_rows).map(sanitize_for_excel)
            desired = ["Name", "Email", "Application"]
            cols = [c for c in desired if c in app_df.columns] + [c for c in app_df.columns if c not in desired]
            app_df = app_df[cols]

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
            ws_apps.freeze_panes(1, 1)
            ws_apps.set_column(0, 0, 24)
            ws_apps.set_column(1, 1, 32)  # Email
            ws_apps.set_column(2, 2, 50)

        # =====================================================================
        # SHEET 3: FONTS
        # =====================================================================
        if fonts_rows:
            fonts_df = pd.DataFrame(fonts_rows).map(sanitize_for_excel)
            desired = ["Name", "Email", "Font", "Scope", "Path"]
            cols = [c for c in desired if c in fonts_df.columns] + [c for c in fonts_df.columns if c not in desired]
            fonts_df = fonts_df[cols]

            sheet_fonts = "Fonts"
            fonts_df.to_excel(writer, sheet_name=sheet_fonts, index=False)
            ws_fonts = writer.sheets[sheet_fonts]
            ws_fonts.freeze_panes(1, 1)
            ws_fonts.set_column(0, 0, 24)
            ws_fonts.set_column(1, 1, 32)  # Email
            ws_fonts.set_column(2, 2, 36)
            ws_fonts.set_column(3, 3, 18)
            ws_fonts.set_column(4, 4, 80)

        # =====================================================================
        # SHEET 4: HOMEBREW APPS
        # =====================================================================
        if brew_rows:
            brew_df = pd.DataFrame(brew_rows).map(sanitize_for_excel)
            desired = ["Name", "Email", "Package", "Source", "Type"]
            cols = [c for c in desired if c in brew_df.columns] + [c for c in brew_df.columns if c not in desired]
            brew_df = brew_df[cols]

            sheet_brew = "Homebrew Apps"
            brew_df.to_excel(writer, sheet_name=sheet_brew, index=False)
            ws_brew = writer.sheets[sheet_brew]
            ws_brew.freeze_panes(1, 1)
            ws_brew.set_column(0, 0, 24)
            ws_brew.set_column(1, 1, 32)  # Email
            ws_brew.set_column(2, 2, 30)
            ws_brew.set_column(3, 3, 20)
            ws_brew.set_column(4, 4, 22)

        # =====================================================================
        # SHEET 5: REFERENCE - MODEL CODES
        # =====================================================================
        model_codes_seen = set()
        if "Model Code" in full_report.columns:
            model_codes_seen = set(full_report["Model Code"].dropna().unique())
            model_codes_seen.discard("-")
            model_codes_seen.discard("Pending Audit")

        if model_codes_seen:
            ref_rows = []
            for code in sorted(model_codes_seen):
                friendly = get_friendly_model_name(code)
                chip = get_model_chip_variant(code)
                ref_rows.append({
                    "Model Code": code,
                    "Friendly Name": friendly,
                    "Chip": chip
                })

            ref_df = pd.DataFrame(ref_rows)
            sheet_ref_models = "Reference - Model Codes"
            ref_df.to_excel(writer, sheet_name=sheet_ref_models, index=False)
            ws_ref_models = writer.sheets[sheet_ref_models]
            ws_ref_models.freeze_panes(1, 0)
            ws_ref_models.set_column(0, 0, 20)
            ws_ref_models.set_column(1, 1, 50)
            ws_ref_models.set_column(2, 2, 20)

        # =====================================================================
        # SHEET 6: REFERENCE - macOS VERSIONS
        # =====================================================================
        version_codes_seen = set()
        if "OS Version Code" in full_report.columns:
            version_codes_seen = set(full_report["OS Version Code"].dropna().unique())
            version_codes_seen.discard("-")

        if version_codes_seen:
            ref_rows = []
            for code in sorted(version_codes_seen, reverse=True):  # Newest first
                friendly = get_macos_friendly_name(code)
                ref_rows.append({
                    "Version Code": code,
                    "Marketing Name": friendly
                })

            ref_df = pd.DataFrame(ref_rows)
            sheet_ref_os = "Reference - macOS Versions"
            ref_df.to_excel(writer, sheet_name=sheet_ref_os, index=False)
            ws_ref_os = writer.sheets[sheet_ref_os]
            ws_ref_os.freeze_panes(1, 0)
            ws_ref_os.set_column(0, 0, 20)
            ws_ref_os.set_column(1, 1, 40)

    output.seek(0)
    return output.getvalue()