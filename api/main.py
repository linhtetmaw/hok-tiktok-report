"""
TikTok Dashboard API – serves data from Google Sheets for the React frontend.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import gspread
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2.service_account import Credentials

# Load .env from parent folder (tiktok-dashboard)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="TikTok Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


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
        if cand.lower() in columns_lower:
            return columns_lower[cand.lower()]
    for c in df.columns:
        if any(cand.lower() in c.lower() for cand in candidates):
            return c
    return None


def fetch_sheet_data() -> tuple[list[dict[str, Any]], datetime]:
    """Fetch TikTok engagement data from Google Sheets."""
    creds_path = _get_env("GOOGLE_APPLICATION_CREDENTIALS") or "credentials.json"
    sheet_id = _get_env("TIKTOK_SHEET_ID")
    if not sheet_id:
        raise ValueError("Missing TIKTOK_SHEET_ID")

    credentials = Credentials.from_service_account_file(creds_path, scopes=SCOPE)
    client = gspread.authorize(credentials)

    worksheet_name = _get_env("TIKTOK_WORKSHEET_NAME")
    if worksheet_name:
        worksheet = client.open_by_key(sheet_id).worksheet(worksheet_name)
    else:
        worksheet = client.open_by_key(sheet_id).sheet1

    records = worksheet.get_all_records(expected_headers=None, default_blank="", head=1)
    if not records:
        return [], datetime.utcnow()

    df = pd.DataFrame(records)
    df = _normalize_columns(df)

    # Parse date column
    date_col = _find_column(df, ["date", "posted_date", "publish_date"])
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    # Coerce numeric columns (your sheet headers)
    metric_candidates = [
        ["impression", "impressions"],
        ["engagement", "engagements"],
        ["reach"],
        ["like", "likes"],
        ["cmt", "comment", "comments"],
        ["share", "shares"],
        ["total_plays", "plays", "play_count", "views"],
        ["3sec_vdo_view", "3_sec_vdo_view"],
        ["1_min_video_view", "1min_video_view"],
    ]
    for cands in metric_candidates:
        col = _find_column(df, cands)
        if col:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Convert to list of dicts, handling NaT/NaN for JSON
    def clean_value(v: Any) -> Any:
        if pd.isna(v):
            return None
        if isinstance(v, (pd.Timestamp, datetime)):
            return v.isoformat()
        return v

    rows = []
    for _, row in df.iterrows():
        rows.append({k: clean_value(v) for k, v in row.items()})

    return rows, datetime.utcnow()


@app.get("/api/data")
def get_data():
    """Return TikTok engagement data from Google Sheets."""
    try:
        rows, last_updated = fetch_sheet_data()
        return {
            "rows": rows,
            "last_updated": last_updated.isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "rows": [], "last_updated": None}


@app.get("/api/health")
def health():
    return {"status": "ok"}
