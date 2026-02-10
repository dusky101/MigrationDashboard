"""
Data Section Component

Renders detailed audit data explorer with MODEL and macOS VERSION transformations.
Provides tabs for different audit categories.
"""

import os
import streamlit as st
import pandas as pd

from core.audit_parser import find_audit_file, parse_audit_csv
from models.mac_models import (
    get_friendly_model_name, 
    get_model_chip_variant,
    get_model_product_name,
    get_model_screen_size,
    get_model_year
)
from models.macos_versions import get_macos_friendly_name, supports_apple_intelligence


@st.cache_data(show_spinner=False)
def _load_audit_df_cached(audit_path: str, mtime: float) -> pd.DataFrame | None:
    """
    Cached wrapper around parse_audit_csv().
    We include mtime in the cache key so updates to the file invalidate the cache.
    """
    _ = mtime  # included only to invalidate cache when file changes
    return parse_audit_csv(audit_path)


def _safe_df(df: pd.DataFrame | None) -> pd.DataFrame:
    return df if df is not None else pd.DataFrame()


def _bytes_to_gb(val: str) -> str:
    """
    Best-effort conversion for values like:
      - "13.44 GB"
      - "94.9 MB"
      - "6.3 MB"
    Returns a friendly string, not a number.
    """
    try:
        s = str(val).strip()
        if not s:
            return ""
        parts = s.split()
        if len(parts) < 2:
            return s
        num = float(parts[0])
        unit = parts[1].upper()

        if unit == "GB":
            return f"{num:.2f} GB"
        if unit == "MB":
            return f"{(num / 1024):.2f} GB"
        if unit == "KB":
            return f"{(num / 1024 / 1024):.2f} GB"
        return s
    except Exception:
        return str(val)


def render_data_section(audit_folder: str, selected_user: str) -> None:
    """
    Local Audit Report Explorer.
    
    Features MODEL and macOS VERSION transformations in the Specs tab.
    
    Args:
        audit_folder: Path to audit CSV folder
        selected_user: User key (email/username)
    """

    key_prefix = f"ds::{selected_user}::"

    st.markdown("### 💻 Local Audit Report")

    if not audit_folder or not os.path.isdir(audit_folder):
        st.warning("Audit Folder invalid or not set.")
        st.stop()

    audit_path = find_audit_file(audit_folder, selected_user)
    if not audit_path:
        st.warning(f"⚠️ No Audit File for **{selected_user}**")
        return

    st.success(f"**Linked:** `{os.path.basename(audit_path)}`")

    try:
        mtime = os.path.getmtime(audit_path)
    except Exception:
        mtime = 0.0

    audit_df = _safe_df(_load_audit_df_cached(audit_path, mtime))
    if audit_df.empty:
        st.warning("Audit file loaded but contains no recognised audit data.")
        return

    # Tabs
    t_specs, t_apps, t_brew, t_browsers, t_email, t_cloud, t_media, t_fonts, t_net, t_print, t_dev = st.tabs(
        [
            "🖥️ Specs",
            "📂 Apps",
            "🍺 Homebrew",
            "🌐 Browsers",
            "📧 Email",
            "☁️ Cloud",
            "🖼️ Media",
            "🔤 Fonts",
            "🌐 Network",
            "🖨 Printers",
            "🔌 Devices",
        ]
    )

    # ========================================================================
    # 1) SYSTEM SPECS WITH MODEL & macOS TRANSFORMATIONS
    # ========================================================================
    with t_specs:
        st.caption("Hardware & System Details")
        specs = audit_df[audit_df["TYPE"] == "System Specifications"].copy()

        if specs.empty:
            st.info("No system specs found.")
        else:
            def get_spec(name_key: str) -> str:
                row = specs[specs["NAME"].astype(str).str.contains(name_key, case=False, na=False)]
                if row.empty:
                    return "N/A"
                return str(row.iloc[0].get("DETAILS", "N/A"))

            # Get raw values
            raw_model = get_spec("Model Identifier")
            raw_version = get_spec("macOS Version")
            ram = get_spec("Memory")
            serial = get_spec("Serial Number")
            logged_user = get_spec("Logged-in User")
            login_name = get_spec("Login Name")

            # MODEL TRANSFORMATION
            if raw_model and raw_model != "N/A":
                product_name = get_model_product_name(raw_model)
                screen_size = get_model_screen_size(raw_model)
                model_year = get_model_year(raw_model)
                chip_variant = get_model_chip_variant(raw_model)
            else:
                product_name = "N/A"
                screen_size = None
                model_year = None
                chip_variant = "N/A"

            # macOS VERSION TRANSFORMATION
            if raw_version and raw_version != "N/A":
                friendly_version = get_macos_friendly_name(raw_version)
                supports_ai = supports_apple_intelligence(raw_version)
            else:
                friendly_version = "N/A"
                supports_ai = False

            # DISPLAY - MODEL (CLEAN BREAKDOWN)
            c1, c2, c3 = st.columns(3)
            
            # Model with chip badge
            if "⚠️" in product_name:
                c1.metric("Machine Model", product_name)
            else:
                c1.metric("Machine Model", product_name)
                
                # Build details line
                details = []
                if screen_size:
                    details.append(screen_size)
                if chip_variant != "N/A":
                    details.append(chip_variant)
                if model_year:
                    details.append(str(model_year))
                
                if details:
                    c1.caption(" • ".join(details))
                c1.caption(f"`{raw_model}`")
            
            c2.metric("Memory (RAM)", ram)
            c3.metric("Serial Number", serial)

            st.divider()

            # LOGGED-IN USER INFO
            if logged_user != "N/A" or login_name != "N/A":
                u1, u2 = st.columns(2)
                if logged_user != "N/A":
                    u1.metric("Logged-in User", logged_user)
                if login_name != "N/A":
                    u2.metric("Login Name", f"`{login_name}`")
                st.divider()

            # macOS VERSION with AI badge
            if supports_ai and friendly_version != "N/A":
                st.success(f"**macOS Version:** {friendly_version} 🤖")
                st.caption(f"✅ Supports Apple Intelligence | `{raw_version}`")
            elif friendly_version != "N/A":
                st.info(f"**macOS Version:** {friendly_version}")
                st.caption(f"`{raw_version}`")
            else:
                st.metric("macOS Version", "N/A")

            st.divider()

            # Tahoe Support (legacy field)
            tahoe = get_spec("Tahoe Support")
            if "Unsupported" in tahoe:
                st.error(f"**AI Readiness:** {tahoe} (Hardware upgrade required)")
            elif "OS Only" in tahoe:
                st.warning(f"**AI Readiness:** {tahoe} (OS Update required for full features)")
            elif "Supported" in tahoe:
                st.success(f"**AI Readiness:** {tahoe}")
            elif tahoe != "N/A":
                st.info(f"**AI Readiness:** {tahoe}")

            st.divider()

            with st.expander("Show full system specifications", expanded=False):
                st.dataframe(
                    specs[["NAME", "DETAILS"]],
                    width='stretch',
                    hide_index=True,
                )

    # ------------------------
    # 2) APPS
    # ------------------------
    with t_apps:
        col_app1, col_app2 = st.columns(2)

        with col_app1:
            st.markdown("**User Apps (Folder)**")
            main = audit_df[audit_df["TYPE"] == "Applications Folder"].copy()

            if main.empty:
                st.caption("Empty")
            else:
                st.caption(f"{len(main)} item(s)")
                with st.expander("Show user apps list", expanded=True):
                    st.dataframe(
                        main[["NAME", "DETAILS"]],
                        width='stretch',
                        hide_index=True,
                    )

        with col_app2:
            st.markdown("**Installed / Detected Apps**")
            other = audit_df[audit_df["TYPE"].isin(["Detected Applications", "System Internals"])].copy()

            if other.empty:
                st.caption("Empty")
            else:
                st.caption(f"{len(other)} item(s)")
                devs = sorted(other["DEVELOPER"].astype(str).fillna("Unknown").unique().tolist())

                sel_devs = st.multiselect(
                    "Filter by Developer",
                    devs,
                    default=[],
                    placeholder="e.g. Adobe",
                    key=f"{key_prefix}apps_dev_filter",
                )

                group_view = st.toggle(
                    "Group by Developer",
                    value=True,
                    key=f"{key_prefix}apps_group_toggle",
                )

                df_show = other if not sel_devs else other[other["DEVELOPER"].astype(str).isin(sel_devs)]

                if df_show.empty:
                    st.info("No apps match filter.")
                else:
                    if group_view:
                        current_devs = sorted(df_show["DEVELOPER"].astype(str).fillna("Unknown").unique())
                        for d in current_devs:
                            subset = df_show[df_show["DEVELOPER"].astype(str).fillna("Unknown") == d]
                            with st.expander(f"{d} ({len(subset)})", expanded=False):
                                st.dataframe(
                                    subset[["NAME", "DETAILS"]],
                                    width='stretch',
                                    hide_index=True,
                                )
                    else:
                        st.dataframe(
                            df_show[["DEVELOPER", "NAME", "DETAILS"]],
                            width='stretch',
                            hide_index=True,
                        )

    # ------------------------
    # 3) HOMEBREW PACKAGES
    # ------------------------
    with t_brew:
        st.caption("Homebrew packages detected on the device.")
        brew = audit_df[audit_df["TYPE"] == "Homebrew Packages"].copy()

        if brew.empty:
            st.info("No Homebrew packages detected (or Homebrew not installed).")
        else:
            q = st.text_input(
                "Search packages",
                value="",
                key=f"{key_prefix}brew_search",
                placeholder="e.g. git, python, node",
            )

            show = brew
            if q.strip():
                qq = q.strip().lower()
                show = show[
                    show["NAME"].astype(str).str.lower().str.contains(qq, na=False)
                    | show["DETAILS"].astype(str).str.lower().str.contains(qq, na=False)
                ]

            c1, c2 = st.columns([1, 3])
            c1.metric("Packages", len(brew))
            c2.caption("Tip: use search to find a package quickly.")

            st.dataframe(
                show[["NAME", "DETAILS"]],
                width='stretch',
                hide_index=True,
            )

    # ------------------------
    # 4) WEB BROWSERS
    # ------------------------
    with t_browsers:
        st.caption("Browser artefacts detected (profiles, bookmarks, etc.).")
        browsers = audit_df[audit_df["TYPE"] == "Web Browsers"].copy()

        if browsers.empty:
            st.info("No browser artefacts detected.")
        else:
            for browser_name in sorted(browsers["NAME"].astype(str).fillna("Unknown").unique()):
                subset = browsers[browsers["NAME"].astype(str).fillna("Unknown") == browser_name]
                vendor = subset["DEVELOPER"].astype(str).fillna("Unknown").iloc[0] if not subset.empty else "Unknown"
                with st.expander(f"{browser_name} ({vendor})", expanded=True):
                    details = subset["DETAILS"].astype(str).fillna("").tolist()
                    for d in details:
                        if d.strip():
                            st.write(f"• {d}")

                    st.dataframe(
                        subset[["DEVELOPER", "NAME", "DETAILS"]],
                        width='stretch',
                        hide_index=True,
                    )

    # ------------------------
    # 5) EMAIL ACCOUNTS
    # ------------------------
    with t_email:
        st.caption("Email client profiles and account artefacts detected.")
        email = audit_df[audit_df["TYPE"] == "Email Accounts"].copy()

        if email.empty:
            st.info("No email account artefacts detected.")
        else:
            names = sorted(email["NAME"].astype(str).fillna("Unknown").unique())
            for n in names:
                subset = email[email["NAME"].astype(str).fillna("Unknown") == n]
                vendor = subset["DEVELOPER"].astype(str).fillna("Unknown").iloc[0] if not subset.empty else "Unknown"
                with st.expander(f"{n} ({vendor})", expanded=True):
                    details = subset["DETAILS"].astype(str).fillna("").tolist()
                    for d in details:
                        if d.strip():
                            st.write(f"• {d}")

                    st.dataframe(
                        subset[["DEVELOPER", "NAME", "DETAILS"]],
                        width='stretch',
                        hide_index=True,
                    )

    # ------------------------
    # 6) CLOUD STORAGE
    # ------------------------
    with t_cloud:
        st.caption("Third-party cloud storage detections.")
        cloud = audit_df[audit_df["TYPE"] == "Cloud Storage"].copy()

        if cloud.empty:
            st.info("No cloud storage signals detected.")
        else:
            if len(cloud) == 1:
                row = cloud.iloc[0]
                name = str(row.get("NAME", "Cloud Storage"))
                details = str(row.get("DETAILS", ""))
                if "no cloud" in f"{name} {details}".lower():
                    st.info(f"**{name}** — {details}")
                else:
                    st.success(f"**{name}** — {details}")
            else:
                st.dataframe(
                    cloud[["DEVELOPER", "NAME", "DETAILS"]],
                    width='stretch',
                    hide_index=True,
                )

    # ------------------------
    # 7) MEDIA (MUSIC + PHOTOS)
    # ------------------------
    with t_media:
        st.caption("Local media libraries detected (Music / Photos).")

        music = audit_df[audit_df["TYPE"] == "Music Library"].copy()
        photos = audit_df[audit_df["TYPE"] == "Photos Library"].copy()

        m1, m2 = st.columns(2)

        with m1:
            st.subheader("🎵 Music Library")
            if music.empty:
                st.info("No music library detected.")
            else:
                st.caption(f"{len(music)} item(s)")
                st.dataframe(
                    music[["NAME", "DETAILS"]],
                    width='stretch',
                    hide_index=True,
                )

        with m2:
            st.subheader("🖼 Photos Library")
            if photos.empty:
                st.info("No photos library detected.")
            else:
                st.caption(f"{len(photos)} item(s)")
                try:
                    first = photos.iloc[0]
                    st.metric("Largest Library (reported)", _bytes_to_gb(first.get("DETAILS", "")))
                except Exception:
                    pass
                st.dataframe(
                    photos[["NAME", "DETAILS"]],
                    width='stretch',
                    hide_index=True,
                )

    # ------------------------
    # 8) FONTS
    # ------------------------
    with t_fonts:
        st.caption("Fonts detected on the device. Use search to quickly find a font.")
        fonts = audit_df[audit_df["TYPE"] == "Fonts"].copy()

        if fonts.empty:
            st.info("No font inventory detected.")
        else:
            q = st.text_input(
                "Search fonts",
                value="",
                key=f"{key_prefix}fonts_search",
                placeholder="e.g. Helvetica, Calibri, Gotham",
            )

            show = fonts
            if q.strip():
                qq = q.strip().lower()
                show = fonts[fonts["NAME"].astype(str).str.lower().str.contains(qq, na=False)]

            c1, c2 = st.columns([1, 3])
            c1.metric("Fonts", len(fonts))
            c2.caption("Results update instantly as you type.")

            st.dataframe(
                show[["NAME", "DETAILS"]],
                width='stretch',
                hide_index=True,
            )

    # ------------------------
    # 9) NETWORK
    # ------------------------
    with t_net:
        net = audit_df[audit_df["TYPE"] == "Network & Storage"].copy()
        if net.empty:
            st.info("None")
        else:
            st.caption(f"{len(net)} item(s)")
            with st.expander("Show network & storage details", expanded=True):
                st.dataframe(
                    net[["NAME", "DETAILS"]],
                    width='stretch',
                    hide_index=True,
                )

    # ------------------------
    # 10) PRINTERS
    # ------------------------
    with t_print:
        printr = audit_df[audit_df["TYPE"] == "Printers"].copy()
        if printr.empty:
            st.info("None")
        else:
            st.caption(f"{len(printr)} printer(s)")
            with st.expander("Show printers", expanded=True):
                st.dataframe(
                    printr[["NAME", "DETAILS"]],
                    width='stretch',
                    hide_index=True,
                )

    # ------------------------
    # 11) DEVICES / PERIPHERALS
    # ------------------------
    with t_dev:
        dev = audit_df[audit_df["TYPE"].isin(["External Peripherals", "DEVICE", "Built-in / System", "USB"])].copy()
        if dev.empty:
            st.info("None")
        else:
            st.caption(f"{len(dev)} device/peripheral item(s)")
            with st.expander("Show devices & peripherals", expanded=True):
                st.dataframe(
                    dev[["NAME", "DETAILS"]],
                    width='stretch',
                    hide_index=True,
                )
