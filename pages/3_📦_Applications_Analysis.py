"""
Applications Analysis - Deep Dive into App Usage (Streamlit 1.54)

Fixes:
- User selector now shows proper Logged-in User + Login Name (+ Email if found),
  not the CSV filename.
- Exports now use the correct identity fields derived from the audit content.
- Canonical user key aligns with audit_loader.py (Login Name first).
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st

from core.audit_parser import parse_audit_csv
from core.status_tracker import load_status
from data_loaders.audit_loader import extract_user_info_from_audit
from data_loaders.audit_loader import load_audit_data
from ui.sidebar import render_sidebar
from ui.styles import get_custom_css


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Applications Analysis",
    page_icon="📦",
    layout="wide",
)

st.markdown(get_custom_css(), unsafe_allow_html=True)

# Hide app.py from sidebar
st.markdown(
    """
<style>
    [data-testid="stSidebarNav"] ul li:first-child { display: none; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("📦 Applications Analysis")
st.caption("Deep dive into application usage across your device fleet")


# ============================================================================
# SESSION STATE & DATA LOADING
# ============================================================================

if "audit_folder" not in st.session_state:
    st.session_state["audit_folder"] = os.path.join(os.getcwd(), "audit_processed_csvs")

AUDIT_FOLDER = st.session_state["audit_folder"]

if "users_df" not in st.session_state or st.session_state.get("users_df") is None:
    users_df = pd.DataFrame()
    if os.path.isdir(AUDIT_FOLDER):
        try:
            users_df = load_audit_data(AUDIT_FOLDER)
        except Exception as e:
            st.error(f"Error loading audit data: {e}")
    st.session_state["users_df"] = users_df

if "status_df" not in st.session_state:
    st.session_state["status_df"] = load_status()

users_df: pd.DataFrame = st.session_state.get("users_df", pd.DataFrame())
status_df: pd.DataFrame = st.session_state.get("status_df", pd.DataFrame())

# Render sidebar (your existing uploader/controls live here)
uploaded_audit_files = render_sidebar(users_df, status_df, AUDIT_FOLDER)

# If your sidebar uploader adds files and your other pages rely on rerun,
# keep behaviour consistent: reload after uploads if needed.
if uploaded_audit_files:
    # render_sidebar in your app typically handles processing; this is a safe refresh.
    try:
        st.session_state["users_df"] = load_audit_data(AUDIT_FOLDER)
        st.session_state["status_df"] = load_status()
        st.rerun()
    except Exception:
        pass


# ============================================================================
# IDENTITY HELPERS (aligned to audit_loader.py)
# ============================================================================

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalise(v: object) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip()


def _looks_like_email(s: str) -> bool:
    return bool(_EMAIL_RE.match((s or "").strip().lower()))


def _user_index_map(users_index_df: pd.DataFrame) -> Dict[str, Dict[str, str]]:
    """
    Build map from canonical user_key -> display fields, using your audit_loader output.
    users_df columns are:
      - Admin-defined name
      - Email
      - Login Name
    and index is the user key.
    """
    m: Dict[str, Dict[str, str]] = {}
    if users_index_df is None or users_index_df.empty:
        return m

    for user_key in users_index_df.index.astype(str).tolist():
        row = users_index_df.loc[user_key]
        display_name = _normalise(row.get("Admin-defined name", "")) or user_key.replace(".", " ").title()
        email = _normalise(row.get("Email", "")).lower()
        login_name = _normalise(row.get("Login Name", "")).lower()

        m[str(user_key).lower()] = {
            "user_key": str(user_key).lower(),
            "display_name": display_name,
            "email": email if _looks_like_email(email) else "",
            "login_name": login_name or str(user_key).lower(),
        }

    return m


def _resolve_identity_from_audit(
    audit_df: pd.DataFrame,
    user_map: Dict[str, Dict[str, str]],
    fallback_key: str,
) -> Tuple[str, str, str, str]:
    """
    Resolve identity using the same extraction logic as audit_loader.py.

    Returns: (user_key, display_name, email, login_name)

    Canonical user_key preference (to match derive_users_from_audit_folder):
      1) Login Name (lowercased)
      2) Email (lowercased)
      3) fallback_key (usually derived from filename stem)
    """
    info = extract_user_info_from_audit(audit_df)

    logged_in_user = _normalise(info.get("logged_in_user", ""))
    login_name = _normalise(info.get("login_name", "")).lower()
    email = _normalise(info.get("email", "")).lower()

    if not _looks_like_email(email):
        email = ""

    # Canonical key first
    candidate_key = ""
    if login_name:
        candidate_key = login_name
    elif email:
        candidate_key = email
    else:
        candidate_key = fallback_key.lower()

    # If candidate exists in our users index, prefer that record for display
    if candidate_key in user_map:
        rec = user_map[candidate_key]
        return (
            rec["user_key"],
            rec["display_name"] or logged_in_user or candidate_key.replace(".", " ").title(),
            rec["email"] or email,
            rec["login_name"] or login_name or candidate_key,
        )

    # Otherwise, use audit-derived display data
    display_name = logged_in_user
    if not display_name:
        if email:
            display_name = email.split("@")[0].replace(".", " ").title()
        else:
            display_name = candidate_key.replace(".", " ").title()

    return (candidate_key, display_name, email, login_name or candidate_key)


# ============================================================================
# APPLICATION DATA LOADER
# ============================================================================

@st.cache_data(ttl=300, show_spinner="Loading application inventory...")
def load_application_inventory(audit_folder: str, users_index_snapshot: pd.DataFrame) -> pd.DataFrame:
    """
    Parse all audit CSVs and produce an application inventory with correct user identity.
    """
    if not os.path.isdir(audit_folder):
        return pd.DataFrame()

    user_map = _user_index_map(users_index_snapshot)

    files = [f for f in os.listdir(audit_folder) if f.lower().endswith(".csv")]
    files.sort()

    rows: List[Dict[str, str]] = []

    for filename in files:
        path = os.path.join(audit_folder, filename)

        try:
            audit_df = parse_audit_csv(path)
        except Exception:
            continue

        if audit_df is None or audit_df.empty:
            continue

        # Fallback key from filename stem (ONLY used if audit content lacks identity)
        fallback_key = os.path.splitext(filename)[0]

        user_key, display_name, email, login_name = _resolve_identity_from_audit(
            audit_df=audit_df,
            user_map=user_map,
            fallback_key=fallback_key,
        )

        # Applications section in your audits
        if "TYPE" not in audit_df.columns or "NAME" not in audit_df.columns:
            continue

        apps = audit_df[audit_df["TYPE"].astype(str).str.contains("Applications Folder", case=False, na=False)].copy()
        if apps.empty:
            continue

        details_col = "DETAILS" if "DETAILS" in apps.columns else None
        developer_col = "DEVELOPER" if "DEVELOPER" in apps.columns else None

        for _, r in apps.iterrows():
            app_name = _normalise(r.get("NAME", ""))
            if not app_name:
                continue

            app_version = _normalise(r.get(details_col, "")) if details_col else ""
            app_developer = _normalise(r.get(developer_col, "")) if developer_col else ""

            rows.append(
                {
                    "user_key": user_key,
                    "display_name": display_name,
                    "email": email,
                    "login_name": login_name,
                    "app_name": app_name,
                    "app_version": app_version or "Unknown",
                    "app_developer": app_developer or "Unknown",
                    "source_file": filename,
                }
            )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Normalise key fields
    df["user_key"] = df["user_key"].astype(str).str.strip().str.lower()
    df["email"] = df["email"].astype(str).str.strip().str.lower()
    df["login_name"] = df["login_name"].astype(str).str.strip().str.lower()
    df["app_name"] = df["app_name"].astype(str).str.strip()
    df["app_version"] = df["app_version"].astype(str).str.strip()
    df["app_developer"] = df["app_developer"].astype(str).str.strip()

    # De-dupe
    df = df.drop_duplicates(subset=["user_key", "app_name", "app_version", "app_developer", "source_file"])
    return df


apps_df = load_application_inventory(AUDIT_FOLDER, users_df.copy(deep=False))

if apps_df.empty:
    st.warning("No application data found yet. Upload audit reports to begin.")
    st.stop()


# ============================================================================
# OVERVIEW METRICS
# ============================================================================

users_with_apps = int(apps_df["user_key"].nunique())
total_installations = int(len(apps_df))
unique_apps = int(apps_df["app_name"].nunique())
avg_apps = (total_installations / users_with_apps) if users_with_apps else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Unique Applications", unique_apps)
c2.metric("Total Installations", total_installations)
c3.metric("Users / Devices", users_with_apps)
c4.metric("Avg Apps per Device", f"{avg_apps:.0f}")

st.divider()


# ============================================================================
# USER LABEL + SELECTOR (this is what fixes the “CSV filename shown” issue)
# ============================================================================

def _format_user_label(user_key: str) -> str:
    sub = apps_df[apps_df["user_key"] == user_key].head(1)
    if sub.empty:
        return user_key

    name = _normalise(sub["display_name"].iloc[0]) or user_key
    email = _normalise(sub["email"].iloc[0]).lower()
    login = _normalise(sub["login_name"].iloc[0]).lower()

    bits = [name]
    if email:
        bits.append(email)
    if login and (not email or login != email):
        bits.append(login)

    return " | ".join(bits)


# ============================================================================
# TABS
# ============================================================================

tab_apps, tab_users, tab_devs, tab_export = st.tabs(
    ["📱 By Application", "👥 By User", "🏢 By Developer", "📥 Power BI Exports"]
)

# ---------------------------------------------------------------------------
# TAB: BY APPLICATION
# ---------------------------------------------------------------------------
with tab_apps:
    st.subheader("📱 Application Adoption")

    app_adoption = (
        apps_df.groupby(["app_name", "app_developer"], as_index=False)
        .agg(user_count=("user_key", "nunique"))
        .sort_values("user_count", ascending=False)
    )
    app_adoption["adoption_percent"] = (app_adoption["user_count"] / users_with_apps * 100).round(1)

    col_a, col_b = st.columns([3, 1])
    with col_a:
        q = st.text_input("Search applications", placeholder="e.g. Adobe, Microsoft, Chrome...")
    with col_b:
        min_users = st.number_input(
            "Min users",
            min_value=1,
            max_value=int(app_adoption["user_count"].max()) if not app_adoption.empty else 1,
            value=1,
        )

    filtered = app_adoption.copy()
    if q:
        mask = (
            filtered["app_name"].str.contains(q, case=False, na=False)
            | filtered["app_developer"].str.contains(q, case=False, na=False)
        )
        filtered = filtered[mask]
    filtered = filtered[filtered["user_count"] >= min_users]

    st.dataframe(
        filtered.rename(
            columns={
                "app_name": "Application",
                "app_developer": "Developer",
                "user_count": "Users",
                "adoption_percent": "Adoption %",
            }
        ),
        width="stretch",
        hide_index=True,
    )

    if not filtered.empty:
        top = filtered.head(20)
        fig = px.bar(top, y="app_name", x="user_count", orientation="h", text="user_count")
        fig.update_traces(textposition="outside")
        fig.update_layout(height=600, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, width="stretch")


# ---------------------------------------------------------------------------
# TAB: BY USER
# ---------------------------------------------------------------------------
with tab_users:
    st.subheader("👥 Applications by User")

    user_keys = sorted(apps_df["user_key"].unique().tolist())

    selected_user = st.selectbox(
        "Select user to view their applications",
        options=user_keys,
        format_func=_format_user_label,
    )

    user_apps = apps_df[apps_df["user_key"] == selected_user].copy()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Apps", int(len(user_apps)))
    c2.metric("Unique Apps", int(user_apps["app_name"].nunique()))
    c3.metric("Developers", int(user_apps["app_developer"].nunique()))

    with st.expander("User identity details"):
        st.dataframe(
            user_apps.head(1)[["display_name", "email", "login_name", "source_file"]].rename(
                columns={
                    "display_name": "Logged-in User",
                    "email": "Email",
                    "login_name": "Login Name",
                    "source_file": "Source CSV",
                }
            ),
            width="stretch",
            hide_index=True,
        )

    st.markdown("#### Installed Applications")
    show = (
        user_apps[["app_name", "app_version", "app_developer"]]
        .drop_duplicates()
        .sort_values(["app_developer", "app_name"])
        .rename(columns={"app_name": "Application", "app_version": "Version", "app_developer": "Developer"})
    )
    st.dataframe(show, width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# TAB: BY DEVELOPER
# ---------------------------------------------------------------------------
with tab_devs:
    st.subheader("🏢 Developer / Vendor Summary")

    dev_stats = (
        apps_df.groupby("app_developer", as_index=False)
        .agg(
            unique_apps=("app_name", "nunique"),
            devices=("user_key", "nunique"),
            total_installations=("app_name", "size"),
        )
        .sort_values("devices", ascending=False)
        .rename(
            columns={
                "app_developer": "Developer",
                "unique_apps": "Unique Apps",
                "devices": "Devices",
                "total_installations": "Total Installations",
            }
        )
    )

    st.dataframe(dev_stats, width="stretch", hide_index=True)

    if not dev_stats.empty:
        top = dev_stats.head(20)
        fig = px.bar(top, y="Developer", x="Devices", orientation="h", text="Devices")
        fig.update_traces(textposition="outside")
        fig.update_layout(height=600, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, width="stretch")


# ---------------------------------------------------------------------------
# TAB: EXPORTS
# ---------------------------------------------------------------------------
with tab_export:
    st.subheader("📥 Power BI Exports")
    st.caption("These exports use audit-derived identity (Logged-in User / Login Name / Email) and will not drift to filenames.")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Export 1: Full matrix
    user_app_matrix = apps_df[
        ["user_key", "display_name", "email", "login_name", "app_name", "app_version", "app_developer", "source_file"]
    ].copy()

    st.download_button(
        "Download User–App Matrix (CSV)",
        data=user_app_matrix.to_csv(index=False),
        file_name=f"user_app_matrix_{ts}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # Export 2: App summary
    app_summary = (
        apps_df.groupby(["app_name", "app_developer"], as_index=False)
        .agg(user_count=("user_key", "nunique"))
        .sort_values("user_count", ascending=False)
    )
    app_summary["adoption_percent"] = (app_summary["user_count"] / users_with_apps * 100).round(2)

    st.download_button(
        "Download App Summary (CSV)",
        data=app_summary.to_csv(index=False),
        file_name=f"app_summary_{ts}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # Export 3: Developer summary
    st.download_button(
        "Download Developer Summary (CSV)",
        data=dev_stats.to_csv(index=False),
        file_name=f"developer_summary_{ts}.csv",
        mime="text/csv",
        use_container_width=True,
    )
