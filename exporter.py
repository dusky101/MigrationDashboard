import io
import os
import re
import pandas as pd

from migrationaud import find_audit_file, parse_audit_csv

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


def _get_first_name(df: pd.DataFrame, type_filter: str, name_contains: str) -> str | None:
    """
    Best-effort lookup: within TYPE, find first row where NAME contains substring.
    Returns NAME or None.
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
    return str(row.iloc[0].get("NAME", "")).strip() or None


def _yes_no(flag: bool) -> str:
    return "Yes" if bool(flag) else "No"


# -----------------------------------------------------------------------------
# 4) Deep data extraction from audit
# -----------------------------------------------------------------------------
def get_comprehensive_machine_data(audit_path: str) -> dict:
    """
    Extracts key values from the audit CSV plus:
      - Disk capacity / available space
      - Music + Photos library total sizes
      - Homebrew installed (Yes/No)
    Also returns legacy list fields used by your existing report.
    """
    data = {
        # Core
        "Machine Model": "Pending Audit",      # Model Identifier
        "Serial Number": "-",
        "Processor": "-",                      # Processor / Chip
        "Memory": "-",                         # Memory (RAM)
        "OS Version": "-",                     # macOS Version
        "Disk Capacity": "-",                  # Hard Drive Capacity
        "Available Space": "-",                # Available Space
        # Media
        "Music Library Size (GB)": "",
        "Photos Library Size (GB)": "",
        # Homebrew
        "Homebrew Installed": "No",
        "Homebrew Package Count": "",
        # Existing fields
        "Free Space": "-",                     # retained for backward compatibility
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

    # --- System Specifications ---
    # Your real audit uses these NAME labels:
    # Hard Drive Capacity / Available Space / Memory (RAM) / Processor / Chip / Serial Number / Model Identifier / macOS Version
    val = _get_first_details(df, "System Specifications", "Model Identifier")
    if val:
        data["Machine Model"] = val

    val = _get_first_details(df, "System Specifications", "Serial Number")
    if val:
        data["Serial Number"] = val

    val = _get_first_details(df, "System Specifications", "Processor")
    if val:
        data["Processor"] = val

    val = _get_first_details(df, "System Specifications", "Memory")
    if val:
        data["Memory"] = val

    val = _get_first_details(df, "System Specifications", "macOS Version") or _get_first_details(df, "System Specifications", "OS Version")
    if val:
        data["OS Version"] = val

    disk = _get_first_details(df, "System Specifications", "Hard Drive Capacity")
    if disk:
        data["Disk Capacity"] = disk

    avail = _get_first_details(df, "System Specifications", "Available Space") or _get_first_details(df, "System Specifications", "Free Space")
    if avail:
        data["Available Space"] = avail
        data["Free Space"] = avail  # keep old column populated too

    tahoe = _get_first_details(df, "System Specifications", "Tahoe Support")
    if tahoe:
        data["Tahoe Support"] = tahoe

    # --- Media sizes ---
    music_gb = _sum_type_sizes_gb(df, "Music Library")
    photos_gb = _sum_type_sizes_gb(df, "Photos Library")
    data["Music Library Size (GB)"] = f"{music_gb:.2f}" if music_gb > 0 else ""
    data["Photos Library Size (GB)"] = f"{photos_gb:.2f}" if photos_gb > 0 else ""

    # --- Homebrew ---
    brew = df[df["TYPE"].astype(str) == "Homebrew Packages"].copy()
    if not brew.empty:
        # Prefer explicit marker row if present
        hb_marker = brew[brew["NAME"].astype(str).str.contains("Homebrew Installed", case=False, na=False)]
        brew_installed = not hb_marker.empty
        data["Homebrew Installed"] = _yes_no(brew_installed)

        # Count formulae rows (your audit uses DETAILS like "Homebrew Formula")
        formulae = brew[brew["DETAILS"].astype(str).str.contains("Homebrew Formula", case=False, na=False)]
        if not formulae.empty:
            data["Homebrew Package Count"] = str(len(formulae))
        else:
            # Fallback: try the "Brew Packages" summary row e.g. "46 formulae installed"
            summary = brew[brew["NAME"].astype(str).str.contains("Brew Packages", case=False, na=False)]
            if not summary.empty:
                s = str(summary.iloc[0].get("DETAILS", ""))
                m = re.search(r"(\d+)", s)
                if m:
                    data["Homebrew Package Count"] = m.group(1)

    # --- Lists (legacy behaviour) ---
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
                "Scope": str(r.get("DEVELOPER", "")).strip(),  # e.g. Admin Installed / User Installed
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

    # Only formula rows
    formulae = brew[brew["DETAILS"].astype(str).str.contains("Homebrew Formula", case=False, na=False)].copy()
    if formulae.empty:
        return []

    out = []
    for _, r in formulae.iterrows():
        out.append(
            {
                "Email": user_key,
                "Package": str(r.get("NAME", "")).strip(),
                "Source": str(r.get("DEVELOPER", "")).strip(),  # often Community
                "Type": str(r.get("DETAILS", "")).strip(),      # "Homebrew Formula"
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
    if not user_key:
        return ""
    s = str(user_key).strip()
    if "@" in s:
        return s.split("@")[0].replace(".", " ").title()
    return s.replace(".", " ").title()


def _build_name_lookup(master_df: pd.DataFrame) -> dict[str, str]:
    """
    Returns { user_key(email): display_name }
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
    Generates an Excel report:
      - Asset Register (front sheet)
      - App Inventory (normalised)
      - Fonts (audit-derived)
      - Homebrew Apps (audit-derived)
    Name is the FIRST column in every sheet.
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

        # App inventory
        apps_str = machine.get("Installed Apps", "-")
        if apps_str and apps_str != "-":
            for app in apps_str.split("\n"):
                app = app.strip()
                if app:
                    app_inventory_rows.append(
                        {
                            "Name": name_lookup.get(str(user_key), _friendly_name_from_key(str(user_key))),
                            "Email": str(user_key),
                            "Application": app,
                        }
                    )

        # Fonts + Homebrew sheets
        if audit_path:
            # Ensure these extract_* functions return dicts with Email at minimum
            extracted_fonts = extract_fonts_rows(audit_path, user_key)
            for r in extracted_fonts:
                r_email = str(r.get("Email", user_key))
                r["Name"] = name_lookup.get(r_email, _friendly_name_from_key(r_email))
                r["Email"] = r_email
            fonts_rows.extend(extracted_fonts)

            extracted_brew = extract_homebrew_rows(audit_path, user_key)
            for r in extracted_brew:
                r_email = str(r.get("Email", user_key))
                r["Name"] = name_lookup.get(r_email, _friendly_name_from_key(r_email))
                r["Email"] = r_email
            brew_rows.extend(extracted_brew)

    hardware_df = pd.DataFrame(hardware_rows).set_index("User") if hardware_rows else pd.DataFrame()
    full_report = master_df.join(hardware_df, how="left")

    # Sanitise all cells
    full_report = full_report.map(sanitize_for_excel)

    # Column ordering (front sheet)
    priority_cols = [
        "Admin-defined name",
        "Status",
        "Notes",
        "Machine Model",
        "Serial Number",
        "Processor",
        "Memory",
        "OS Version",
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

    # -------------------------------------------------------------------------
    # Write Excel
    # -------------------------------------------------------------------------
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book

        header_fmt = workbook.add_format({"bold": True, "bg_color": "#2C3E50", "font_color": "white", "border": 1})
        centered = workbook.add_format({"align": "center", "valign": "top"})
        text_wrap = workbook.add_format({"text_wrap": True, "valign": "top"})
        fmt_green = workbook.add_format({"bg_color": "#C6EFCE", "font_color": "#006100"})
        fmt_red = workbook.add_format({"bg_color": "#FFC7CE", "font_color": "#9C0006"})
        fmt_yellow = workbook.add_format({"bg_color": "#FFEB9C", "font_color": "#9C6500"})

        # --- SHEET 1: ASSET REGISTER ---
        sheet_name = "Asset Register"

        # Insert Name as FIRST column, keep Email as second column
        export_df = full_report.copy()
        export_df.insert(
            0,
            "Name",
            [name_lookup.get(str(idx), _friendly_name_from_key(str(idx))) for idx in export_df.index],
        )
        export_df.insert(1, "Email", [str(idx) for idx in export_df.index])

        export_df.to_excel(writer, sheet_name=sheet_name, index=False)
        ws_data = writer.sheets[sheet_name]

        max_row, max_col = export_df.shape  # rows/cols including Name+Email

        column_settings = [{"header": str(col)} for col in export_df.columns]

        if max_row > 0:
            ws_data.add_table(
                0, 0, max_row, max_col - 1,
                {"columns": column_settings, "style": "TableStyleMedium9", "name": "MigrationData"},
            )

        ws_data.freeze_panes(1, 2)  # freeze Name+Email

        # Conditional formatting on Status (if present)
        try:
            status_col_pos = list(export_df.columns).index("Status")  # 0-based

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
            pass

        # Column sizing
        # Name, Email
        ws_data.set_column(0, 0, 24, text_wrap)  # Name
        ws_data.set_column(1, 1, 30, text_wrap)  # Email

        for i, col_name in enumerate(export_df.columns):
            if i in (0, 1):
                continue
            if col_name in ["Printers", "Peripherals", "Network Interfaces", "Groups", "Notes"]:
                ws_data.set_column(i, i, 35, text_wrap)
            elif col_name in ["Status", "Homebrew Installed"]:
                ws_data.set_column(i, i, 18, centered)
            elif col_name in ["Processor", "OS Version"]:
                ws_data.set_column(i, i, 28, text_wrap)
            else:
                ws_data.set_column(i, i, 20, text_wrap)

        # Ensure header format even when empty
        for col_idx in range(0, max_col):
            ws_data.write(0, col_idx, column_settings[col_idx]["header"], header_fmt)

        # --- SHEET 2: APP INVENTORY ---
        if app_inventory_rows:
            app_df = pd.DataFrame(app_inventory_rows).map(sanitize_for_excel)

            # Ensure Name is first
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
            ws_apps.set_column(0, 0, 24)  # Name
            ws_apps.set_column(1, 1, 30)  # Email
            ws_apps.set_column(2, 2, 50)  # Application

        # --- SHEET 3: FONTS ---
        if fonts_rows:
            fonts_df = pd.DataFrame(fonts_rows).map(sanitize_for_excel)

            # Ensure Name is first
            desired = ["Name", "Email", "Font", "Scope", "Path"]
            cols = [c for c in desired if c in fonts_df.columns] + [c for c in fonts_df.columns if c not in desired]
            fonts_df = fonts_df[cols]

            sheet_fonts = "Fonts"
            fonts_df.to_excel(writer, sheet_name=sheet_fonts, index=False)
            ws_fonts = writer.sheets[sheet_fonts]
            ws_fonts.freeze_panes(1, 1)
            ws_fonts.set_column(0, 0, 24)  # Name
            ws_fonts.set_column(1, 1, 30)  # Email
            ws_fonts.set_column(2, 2, 36)  # Font
            ws_fonts.set_column(3, 3, 18)  # Scope
            ws_fonts.set_column(4, 4, 80)  # Path

        # --- SHEET 4: HOMEBREW APPS ---
        if brew_rows:
            brew_df = pd.DataFrame(brew_rows).map(sanitize_for_excel)

            # Ensure Name is first
            desired = ["Name", "Email", "Package", "Source", "Type"]
            cols = [c for c in desired if c in brew_df.columns] + [c for c in brew_df.columns if c not in desired]
            brew_df = brew_df[cols]

            sheet_brew = "Homebrew Apps"
            brew_df.to_excel(writer, sheet_name=sheet_brew, index=False)
            ws_brew = writer.sheets[sheet_brew]
            ws_brew.freeze_panes(1, 1)
            ws_brew.set_column(0, 0, 24)  # Name
            ws_brew.set_column(1, 1, 30)  # Email
            ws_brew.set_column(2, 2, 30)  # Package
            ws_brew.set_column(3, 3, 20)  # Source
            ws_brew.set_column(4, 4, 22)  # Type

    output.seek(0)
    return output.getvalue()
