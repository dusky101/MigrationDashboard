import os
import streamlit as st
import pandas as pd

from migrationaud import find_audit_file, parse_audit_csv


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


def render_data_section(audit_folder: str, selected_user: str, google_users: pd.DataFrame) -> None:
    """
    Local Audit Report + Google Data Explorer (optional).

    Updated:
    - Adds audit sections for:
      - Homebrew Packages
      - Web Browsers
      - Email Accounts
      - Cloud Storage
      - Music Library
      - Photos Library
      - Fonts
    - Keeps existing tabs (Specs, Apps, Network, Printers, Devices)
    - Uses per-user widget keys to avoid clashes in multi-user expanders
    """

    key_prefix = f"ds::{selected_user}::"

    try:
        user_data = google_users.loc[selected_user]
    except Exception:
        user_data = pd.Series(dtype="object")

    tab_audit, tab_explore = st.tabs(["💻 Local Audit Report", "📊 Google Data Explorer"])

    # ==========================================================================
    # TAB 1: LOCAL AUDIT
    # ==========================================================================
    with tab_audit:
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

        # ----------------------------------------------------------------------
        # Tabs (expanded as requested)
        # ----------------------------------------------------------------------
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
                "☁️ Network",
                "🖨 Printers",
                "🔌 Devices",
            ]
        )

        # ------------------------
        # 1) SYSTEM SPECS
        # ------------------------
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

                model = get_spec("Model Identifier")
                ram = get_spec("Memory")
                serial = get_spec("Serial Number")
                tahoe = get_spec("Tahoe Support")

                c1, c2, c3 = st.columns(3)
                c1.metric("Machine Model", model)
                c2.metric("Memory (RAM)", ram)
                c3.metric("Serial Number", serial)

                st.divider()

                if "Unsupported" in tahoe:
                    st.error(f"**AI Readiness:** {tahoe} (Hardware upgrade required)")
                elif "OS Only" in tahoe:
                    st.warning(f"**AI Readiness:** {tahoe} (OS Update required for full features)")
                elif "Supported" in tahoe:
                    st.success(f"**AI Readiness:** {tahoe}")
                else:
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
                        st.dataframe(main[["NAME", "DETAILS"]], width='stretch', hide_index=True)

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
                                    st.dataframe(subset[["NAME", "DETAILS"]], width='stretch', hide_index=True)
                        else:
                            st.dataframe(df_show[["DEVELOPER", "NAME", "DETAILS"]], width='stretch', hide_index=True)

        # ------------------------
        # 3) HOMEBREW PACKAGES
        # ------------------------
        with t_brew:
            st.caption("Homebrew packages detected on the device.")
            brew = audit_df[audit_df["TYPE"] == "Homebrew Packages"].copy()

            if brew.empty:
                st.info("No Homebrew packages detected (or Homebrew not installed).")
            else:
                # Search/filter
                q = st.text_input("Search packages", value="", key=f"{key_prefix}brew_search", placeholder="e.g. git, python, node")
                show = brew
                if q.strip():
                    qq = q.strip().lower()
                    show = show[
                        brew["NAME"].astype(str).str.lower().str.contains(qq, na=False)
                        | brew["DETAILS"].astype(str).str.lower().str.contains(qq, na=False)
                    ]

                c1, c2 = st.columns([1, 3])
                c1.metric("Packages", len(brew))
                c2.caption("Tip: use search to find a package quickly.")

                st.dataframe(show[["NAME", "DETAILS"]], width='stretch', hide_index=True)

        # ------------------------
        # 4) WEB BROWSERS
        # ------------------------
        with t_browsers:
            st.caption("Browser artefacts detected (profiles, bookmarks, etc.).")
            browsers = audit_df[audit_df["TYPE"] == "Web Browsers"].copy()

            if browsers.empty:
                st.info("No browser artefacts detected.")
            else:
                # Group by browser name (NAME column) for a nicer presentation
                for browser_name in sorted(browsers["NAME"].astype(str).fillna("Unknown").unique()):
                    subset = browsers[browsers["NAME"].astype(str).fillna("Unknown") == browser_name]
                    vendor = subset["DEVELOPER"].astype(str).fillna("Unknown").iloc[0] if not subset.empty else "Unknown"
                    with st.expander(f"{browser_name} ({vendor})", expanded=True):
                        # Show key messages as bullets
                        details = subset["DETAILS"].astype(str).fillna("").tolist()
                        for d in details:
                            if d.strip():
                                st.write(f"• {d}")
                        # And a structured table for completeness
                        st.dataframe(subset[["DEVELOPER", "NAME", "DETAILS"]], width='stretch', hide_index=True)

        # ------------------------
        # 5) EMAIL ACCOUNTS
        # ------------------------
        with t_email:
            st.caption("Email client profiles and account artefacts detected.")
            email = audit_df[audit_df["TYPE"] == "Email Accounts"].copy()

            if email.empty:
                st.info("No email account artefacts detected.")
            else:
                # Group by app/profile name
                names = sorted(email["NAME"].astype(str).fillna("Unknown").unique())
                for n in names:
                    subset = email[email["NAME"].astype(str).fillna("Unknown") == n]
                    vendor = subset["DEVELOPER"].astype(str).fillna("Unknown").iloc[0] if not subset.empty else "Unknown"
                    with st.expander(f"{n} ({vendor})", expanded=True):
                        details = subset["DETAILS"].astype(str).fillna("").tolist()
                        for d in details:
                            if d.strip():
                                st.write(f"• {d}")
                        st.dataframe(subset[["DEVELOPER", "NAME", "DETAILS"]], width='stretch', hide_index=True)

        # ------------------------
        # 6) CLOUD STORAGE
        # ------------------------
        with t_cloud:
            st.caption("Third-party cloud storage detections.")
            cloud = audit_df[audit_df["TYPE"] == "Cloud Storage"].copy()

            if cloud.empty:
                st.info("No cloud storage signals detected.")
            else:
                # Often a single line: "No Cloud Storage"
                # Show a clear status first
                if len(cloud) == 1:
                    row = cloud.iloc[0]
                    st.info(f"**{row.get('NAME', 'Cloud Storage')}** — {row.get('DETAILS', '')}")
                else:
                    st.dataframe(cloud[["DEVELOPER", "NAME", "DETAILS"]], width='stretch', hide_index=True)

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
                    # Metric: total size (best effort)
                    sizes = [_bytes_to_gb(x) for x in music["DETAILS"].astype(str).tolist()]
                    st.caption(f"{len(music)} item(s)")
                    st.dataframe(music[["NAME", "DETAILS"]], width='stretch', hide_index=True)

            with m2:
                st.subheader("🖼 Photos Library")
                if photos.empty:
                    st.info("No photos library detected.")
                else:
                    st.caption(f"{len(photos)} item(s)")
                    # Show biggest library as metric if possible
                    try:
                        first = photos.iloc[0]
                        st.metric("Largest Library (reported)", _bytes_to_gb(first.get("DETAILS", "")))
                    except Exception:
                        pass
                    st.dataframe(photos[["NAME", "DETAILS"]], width='stretch', hide_index=True)

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

                st.dataframe(show[["NAME", "DETAILS"]], width='stretch', hide_index=True)

        # ------------------------
        # 9) NETWORK (legacy / if present)
        # ------------------------
        with t_net:
            net = audit_df[audit_df["TYPE"] == "Network & Storage"].copy()
            if net.empty:
                st.info("None")
            else:
                st.caption(f"{len(net)} item(s)")
                with st.expander("Show network & storage details", expanded=True):
                    st.dataframe(net[["NAME", "DETAILS"]], width='stretch', hide_index=True)

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
                    st.dataframe(printr[["NAME", "DETAILS"]], width='stretch', hide_index=True)

        # ------------------------
        # 11) DEVICES / PERIPHERALS (legacy / if present)
        # ------------------------
        with t_dev:
            dev = audit_df[audit_df["TYPE"].isin(["External Peripherals", "DEVICE", "Built-in / System"])].copy()
            if dev.empty:
                st.info("None")
            else:
                st.caption(f"{len(dev)} device/peripheral item(s)")
                with st.expander("Show devices & peripherals", expanded=True):
                    st.dataframe(dev[["NAME", "DETAILS"]], width='stretch', hide_index=True)

    # ==========================================================================
    # TAB 2: GOOGLE DATA EXPLORER (OPTIONAL)
    # ==========================================================================
    with tab_explore:
        st.markdown("### 🔍 Migration Record")
        st.caption("Optional enrichment from Google Workspace logs (if provided).")

        if google_users is None or google_users.empty:
            st.info("No Google data loaded. This is fine — the audit report is the primary source.")
            return

        if selected_user in google_users.index:
            df_for_display = google_users.loc[[selected_user]].reset_index()
        else:
            st.info("This user/device is not present in the uploaded Google dataset.")
            return

        all_cols = df_for_display.columns.tolist()

        preferred_cols = [
            "User",
            "Admin-defined name",
            "Role",
            "User account status",
            "Total storage used (MB)",
            "Gmail (Web) - last used time",
            "Org Unit Path",
            "Groups",
            "External apps",
        ]
        default_cols = [c for c in preferred_cols if c in all_cols]

        selected_cols = st.multiselect(
            "Select Data Points:",
            all_cols,
            default=default_cols,
            key=f"{key_prefix}g_explorer_cols",
        )

        if not selected_cols:
            st.info("Select columns above to view data.")
            return

        storage_cols_found = [
            c for c in selected_cols
            if ("storage used" in c.lower())
            or ("quota" in c.lower())
            or ("(mb)" in c.lower() and "storage" in c.lower())
        ]

        use_gb = False
        if storage_cols_found:
            smart_default = False
            for c in storage_cols_found:
                try:
                    val = df_for_display.iloc[0].get(c, 0)
                    if pd.notna(val) and float(val) > 1024:
                        smart_default = True
                        break
                except Exception:
                    pass

            use_gb = st.toggle(
                "Show Storage in GB",
                value=smart_default,
                key=f"{key_prefix}g_explorer_gb",
            )

        data_to_show = df_for_display[selected_cols].copy()

        if use_gb and storage_cols_found:
            for col in storage_cols_found:
                try:
                    val_mb = pd.to_numeric(data_to_show[col], errors="coerce")
                    val_gb = val_mb / 1024
                    data_to_show[col] = val_gb.map(lambda x: "" if pd.isna(x) else f"{x:.2f}")
                    new_header = col.replace("(MB)", "(GB)").replace("(mb)", "(GB)").replace("_in_mb", "_in_gb")
                    data_to_show = data_to_show.rename(columns={col: new_header})
                except Exception:
                    continue

        st.dataframe(
            data_to_show.astype(str),
            width='stretch',
            hide_index=True,
        )
