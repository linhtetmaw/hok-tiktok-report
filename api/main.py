"""
TikTok Dashboard API – serves data from Google Sheets for the React frontend.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import gspread
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2.service_account import Credentials

# Load .env from parent folder (tiktok-dashboard)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="TikTok Dashboard API")

# CORS: allow local dev and deployed frontend (Vercel / custom domain).
# For this internal dashboard we keep it simple and allow all origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    sheet_id = _get_env("TIKTOK_SHEET_ID")
    if not sheet_id:
        raise ValueError("Missing TIKTOK_SHEET_ID")

    # Credentials: full JSON in env, or JSON split in two vars, or path to file.
    creds_json = (
        _get_env("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        or _get_env("GOOGLE_APPLICATION_CREDENTIALS")
    )
    if not creds_json or not creds_json.strip():
        if _get_env("GOOGLE_APPLICATION_CREDENTIALS_JSON_1"):
            p1 = (_get_env("GOOGLE_APPLICATION_CREDENTIALS_JSON_1") or "").strip()
            p2 = (_get_env("GOOGLE_APPLICATION_CREDENTIALS_JSON_2") or "").strip()
            creds_json = p1 + p2
    if creds_json:
        raw = creds_json.strip().lstrip("\ufeff")
        looks_like_json = raw.startswith("{") or ("service_account" in raw and "private_key" in raw)
        if looks_like_json:
            try:
                info = json.loads(raw)
                if isinstance(info, dict) and "client_email" in info:
                    credentials = Credentials.from_service_account_info(info, scopes=SCOPE)
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
                    date_col = _find_column(df, ["date", "posted_date", "publish_date"])
                    if date_col:
                        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
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
                    def clean_value(v: Any) -> Any:
                        if pd.isna(v):
                            return None
                        if isinstance(v, (pd.Timestamp, datetime)):
                            return v.isoformat()
                        if hasattr(v, "item"):
                            try:
                                return v.item()
                            except (ValueError, AttributeError):
                                pass
                        return v
                    rows = []
                    for _, row in df.iterrows():
                        rows.append({k: clean_value(v) for k, v in row.items()})
                    return rows, datetime.utcnow()
            except json.JSONDecodeError:
                pass
    # Fallback: credentials file (local dev), or retry env once (Railway sometimes needs direct os.getenv)
    direct_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON", "").strip().lstrip("\ufeff")
    if direct_json and ("service_account" in direct_json or direct_json.startswith("{")):
        try:
            info = json.loads(direct_json)
            if isinstance(info, dict) and "client_email" in info:
                credentials = Credentials.from_service_account_info(info, scopes=SCOPE)
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
                date_col = _find_column(df, ["date", "posted_date", "publish_date"])
                if date_col:
                    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                metric_candidates = [
                    ["impression", "impressions"], ["engagement", "engagements"], ["reach"],
                    ["like", "likes"], ["cmt", "comment", "comments"], ["share", "shares"],
                    ["total_plays", "plays", "play_count", "views"],
                    ["3sec_vdo_view", "3_sec_vdo_view"], ["1_min_video_view", "1min_video_view"],
                ]
                for cands in metric_candidates:
                    col = _find_column(df, cands)
                    if col:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                def _cv(v: Any) -> Any:
                    if pd.isna(v):
                        return None
                    if isinstance(v, (pd.Timestamp, datetime)):
                        return v.isoformat()
                    if hasattr(v, "item"):
                        try:
                            return v.item()
                        except (ValueError, AttributeError):
                            pass
                    return v
                rows = []
                for _, row in df.iterrows():
                    rows.append({k: _cv(v) for k, v in row.items()})
                return rows, datetime.utcnow()
        except json.JSONDecodeError:
            pass

    raw_path = _get_env("GOOGLE_APPLICATION_CREDENTIALS")
    if raw_path:
        creds_path = Path(raw_path)
    else:
        creds_path = Path(__file__).resolve().parent.parent / "credentials.json"
    if not creds_path.is_file():
        raise FileNotFoundError(
            "Credentials file not found. "
            "Local: put credentials.json in the project root. "
            "Railway: set GOOGLE_APPLICATION_CREDENTIALS_JSON in Variables (or _1 and _2), then Redeploy."
        )
    credentials = Credentials.from_service_account_file(str(creds_path), scopes=SCOPE)

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

    # Convert to list of dicts, handling NaT/NaN and numpy types for JSON
    def clean_value(v: Any) -> Any:
        if pd.isna(v):
            return None
        if isinstance(v, (pd.Timestamp, datetime)):
            return v.isoformat()
        # Ensure native types for JSON (numpy.int64, numpy.float64 etc. can break serialization)
        if hasattr(v, "item"):
            try:
                return v.item()
            except (ValueError, AttributeError):
                pass
        return v

    rows = []
    for _, row in df.iterrows():
        rows.append({k: clean_value(v) for k, v in row.items()})

    return rows, datetime.utcnow()


@app.get("/api/data")
def get_data(response: Response):
    """Return TikTok engagement data from Google Sheets. Always 200; errors in body."""
    try:
        rows, last_updated = fetch_sheet_data()
        body = {
            "rows": rows,
            "last_updated": last_updated.isoformat() if hasattr(last_updated, "isoformat") else str(last_updated),
        }
        return body
    except Exception as e:
        response.status_code = 200
        return {"error": str(e), "rows": [], "last_updated": None}


@app.get("/api/health")
def health():
    return {"status": "ok"}
