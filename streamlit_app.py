import os
from datetime import datetime
from typing import Optional, Tuple

import gspread
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials


load_dotenv()  # Load variables from .env if present


# ────────────────────────────────────────────────────────────────
# Configuration helpers
# ────────────────────────────────────────────────────────────────


def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _get_credentials_path() -> str:
    """
    Resolve path to the Google service account JSON key.

    Preference order:
    1. GOOGLE_APPLICATION_CREDENTIALS
    2. ./credentials.json
    """
    path = _get_env("GOOGLE_APPLICATION_CREDENTIALS") or "credentials.json"
    return path


def _get_sheet_id() -> str:
    sheet_id = _get_env("TIKTOK_SHEET_ID")
    if not sheet_id:
        raise RuntimeError(
            "Missing TIKTOK_SHEET_ID environment variable (Google Sheet ID)."
        )
    return sheet_id


def _get_refresh_minutes() -> int:
    raw = _get_env("DASHBOARD_REFRESH_MINUTES", "5")
    try:
        minutes = int(raw)
        return max(1, minutes)
    except ValueError:
        return 5


SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
REFRESH_MINUTES = _get_refresh_minutes()


# ────────────────────────────────────────────────────────────────
# Data access layer
# ────────────────────────────────────────────────────────────────


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [
        str(col).strip().lower().replace(" ", "_").replace("-", "_")
        for col in df.columns
    ]
    return df


def _find_column(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    columns_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        cand_lower = cand.lower()
        if cand_lower in columns_lower:
            return columns_lower[cand_lower]
    # Fallback: substring match
    for c in df.columns:
        cl = c.lower()
        if any(cand.lower() in cl for cand in candidates):
            return c
    return None


@st.cache_data(ttl=REFRESH_MINUTES * 60)
def fetch_tiktok_data() -> Tuple[pd.DataFrame, datetime]:
    """
    Fetch TikTok engagement data from Google Sheets and return as a DataFrame.

    Returns (df, last_updated_utc).
    """
    creds_path = _get_credentials_path()
    sheet_id = _get_sheet_id()

    credentials = Credentials.from_service_account_file(creds_path, scopes=SCOPE)
    client = gspread.authorize(credentials)

    worksheet_name = _get_env("TIKTOK_WORKSHEET_NAME")
    if worksheet_name:
        worksheet = client.open_by_key(sheet_id).worksheet(worksheet_name)
    else:
        worksheet = client.open_by_key(sheet_id).sheet1

    records = worksheet.get_all_records(
        expected_headers=None,
        default_blank="",
        head=1,
    )
    if not records:
        df = pd.DataFrame()
        return df, datetime.utcnow()

    df = pd.DataFrame(records)
    df = _normalize_columns(df)

    # Try to parse a date column if present
    date_col = _find_column(df, ["date", "posted_date", "publish_date"])
    if date_col and not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    # Coerce common numeric metric columns
    metric_candidates = {
        "views": ["views", "view", "plays", "play_count"],
        "likes": ["likes", "like", "hearts"],
        "comments": ["comments", "comment"],
        "shares": ["shares", "share"],
        "watch_time": ["watch_time", "avg_watch_time", "average_watch_time"],
    }
    for cands in metric_candidates.values():
        col = _find_column(df, cands)
        if col:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df, datetime.utcnow()


# ────────────────────────────────────────────────────────────────
# Dashboard UI
# ────────────────────────────────────────────────────────────────


def build_filters(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    date_col = _find_column(df, ["date", "posted_date", "publish_date"])
    account_col = _find_column(df, ["account", "profile", "channel", "page"])
    category_col = _find_column(df, ["category", "niche", "topic", "content_type"])

    st.sidebar.header("Filters")

    # Date range filter
    if date_col and df[date_col].notna().any():
        min_date = df[date_col].min()
        max_date = df[date_col].max()
        if pd.notna(min_date) and pd.notna(max_date):
            start_default = min_date.date()
            end_default = max_date.date()
            start_date, end_date = st.sidebar.date_input(
                "Date range",
                value=(start_default, end_default),
            )
            if isinstance(start_date, datetime):
                start_date = start_date.date()
            if isinstance(end_date, datetime):
                end_date = end_date.date()

            mask = (df[date_col].dt.date >= start_date) & (
                df[date_col].dt.date <= end_date
            )
            df = df[mask]

    # Account filter
    if account_col and df[account_col].notna().any():
        accounts = sorted(df[account_col].dropna().unique().tolist())
        selected_accounts = st.sidebar.multiselect(
            "Account", accounts, default=accounts
        )
        if selected_accounts:
            df = df[df[account_col].isin(selected_accounts)]

    # Category filter
    if category_col and df[category_col].notna().any():
        categories = sorted(df[category_col].dropna().unique().tolist())
        selected_categories = st.sidebar.multiselect(
            "Category", categories, default=categories
        )
        if selected_categories:
            df = df[df[category_col].isin(selected_categories)]

    return df


def build_kpis(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No data available to compute KPIs.")
        return

    views_col = _find_column(df, ["views", "view", "plays", "play_count"])
    likes_col = _find_column(df, ["likes", "like", "hearts"])
    comments_col = _find_column(df, ["comments", "comment"])
    shares_col = _find_column(df, ["shares", "share"])
    watch_time_col = _find_column(
        df, ["watch_time", "avg_watch_time", "average_watch_time"]
    )

    total_views = df[views_col].sum() if views_col else 0
    total_likes = df[likes_col].sum() if likes_col else 0
    total_comments = df[comments_col].sum() if comments_col else 0
    total_shares = df[shares_col].sum() if shares_col else 0

    total_engagements = total_likes + total_comments + total_shares
    engagement_rate = (total_engagements / total_views * 100) if total_views > 0 else None

    avg_watch_time = (
        df[watch_time_col].mean()
        if watch_time_col and df[watch_time_col].notna().any()
        else None
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total views", f"{int(total_views):,}")
    col2.metric("Total engagements", f"{int(total_engagements):,}")
    col3.metric("Engagement rate", f"{engagement_rate:.2f}%" if engagement_rate else "N/A")
    col4.metric(
        "Avg. watch time", f"{avg_watch_time:.1f}" if avg_watch_time is not None else "N/A"
    )


def build_charts(df: pd.DataFrame) -> None:
    if df.empty:
        return

    import altair as alt

    date_col = _find_column(df, ["date", "posted_date", "publish_date"])
    views_col = _find_column(df, ["views", "view", "plays", "play_count"])
    likes_col = _find_column(df, ["likes", "like", "hearts"])
    comments_col = _find_column(df, ["comments", "comment"])
    shares_col = _find_column(df, ["shares", "share"])

    st.subheader("Performance over time")

    if date_col and views_col:
        agg_cols = {views_col: "sum"}
        if likes_col:
            agg_cols[likes_col] = "sum"
        if comments_col:
            agg_cols[comments_col] = "sum"
        if shares_col:
            agg_cols[shares_col] = "sum"

        ts = df.groupby(date_col).agg(agg_cols).reset_index()
        ts_melt = ts.melt(id_vars=[date_col], var_name="metric", value_name="value")

        line_chart = (
            alt.Chart(ts_melt)
            .mark_line()
            .encode(
                x=alt.X(date_col, title="Date"),
                y=alt.Y("value:Q", title="Count"),
                color=alt.Color("metric:N", title="Metric"),
                tooltip=[date_col, "metric:N", "value:Q"],
            )
            .interactive()
        )
        st.altair_chart(line_chart, use_container_width=True)
    else:
        st.info("No date / views columns found for time-series chart.")


def build_top_videos_table(df: pd.DataFrame) -> None:
    if df.empty:
        return

    views_col = _find_column(df, ["views", "view", "plays", "play_count"])
    likes_col = _find_column(df, ["likes", "like", "hearts"])
    comments_col = _find_column(df, ["comments", "comment"])
    shares_col = _find_column(df, ["shares", "share"])

    video_title_col = _find_column(
        df, ["video_title", "title", "caption", "content", "post"]
    )

    if not views_col:
        st.info("No views column found to compute top videos.")
        return

    df_sorted = df.sort_values(by=views_col, ascending=False).copy()

    total_engagements = 0
    if likes_col:
        total_engagements += df_sorted[likes_col].fillna(0)
    if comments_col:
        total_engagements += df_sorted[comments_col].fillna(0)
    if shares_col:
        total_engagements += df_sorted[shares_col].fillna(0)

    df_sorted["engagements"] = total_engagements
    df_sorted["engagement_rate_%"] = (
        df_sorted["engagements"] / df_sorted[views_col].replace(0, pd.NA) * 100
    )

    display_cols = []
    if video_title_col:
        display_cols.append(video_title_col)
    display_cols.extend(
        col
        for col in [views_col, "engagements", "engagement_rate_%"]
        if col in df_sorted.columns
    )

    st.subheader("Top videos by views")
    st.dataframe(
        df_sorted[display_cols].head(20),
        use_container_width=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="TikTok Engagement Dashboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Dark theme + Space Grotesk font, minimal & clean
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Space Grotesk', sans-serif !important;
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: 'Space Grotesk', sans-serif !important;
            font-weight: 600 !important;
            color: #F8FAFC !important;
        }

        [data-testid="stMetricValue"] {
            font-family: 'Space Grotesk', sans-serif !important;
            font-size: 1.5rem !important;
            font-weight: 600 !important;
            color: #F8FAFC !important;
        }

        [data-testid="stMetricLabel"] {
            font-family: 'Space Grotesk', sans-serif !important;
            font-weight: 500 !important;
            color: #94A3B8 !important;
        }

        .stButton > button {
            font-family: 'Space Grotesk', sans-serif !important;
            font-weight: 500 !important;
            border-radius: 6px !important;
            border: 1px solid #334155 !important;
        }

        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
            max-width: 1200px !important;
        }

        [data-testid="stSidebar"] {
            font-family: 'Space Grotesk', sans-serif !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("TikTok Engagement Dashboard")
    st.caption(
        "Live report powered by Google Sheets. "
        f"Data refreshes automatically every {REFRESH_MINUTES} minute(s)."
    )

    with st.sidebar:
        st.markdown("### Data refresh")
        st.write(f"Auto-refresh interval: **{REFRESH_MINUTES} minute(s)**")
        if st.button("🔄 Refresh now"):
            fetch_tiktok_data.clear()
            st.rerun()

    # Load data
    try:
        df, last_updated = fetch_tiktok_data()
    except Exception as e:
        st.error(f"Error loading data from Google Sheets: {e}")
        return

    if df.empty:
        st.warning(
            "No rows returned from the TikTok Google Sheet. "
            "Check that the sheet has data and that the service account has access."
        )
        return

    st.write(
        f"Last updated at **{last_updated.strftime('%Y-%m-%d %H:%M:%S')} UTC** "
        f"(auto-refresh every {REFRESH_MINUTES} minute(s))."
    )

    df_filtered = build_filters(df)
    build_kpis(df_filtered)

    st.markdown("---")
    col_left, col_right = st.columns((3, 2))

    with col_left:
        build_charts(df_filtered)

    with col_right:
        build_top_videos_table(df_filtered)

    st.markdown("---")
    with st.expander("Show raw data"):
        st.dataframe(df_filtered, use_container_width=True)


if __name__ == "__main__":
    main()

