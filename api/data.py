"""
Vercel serverless function: GET /api/data – returns TikTok sheet data.
Uses env: TIKTOK_SHEET_ID, TIKTOK_WORKSHEET_NAME (optional), GOOGLE_APPLICATION_CREDENTIALS_JSON.
"""
import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from typing import Any, Optional

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

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
    sheet_id = _get_env("TIKTOK_SHEET_ID")
    if not sheet_id:
        raise ValueError("Missing TIKTOK_SHEET_ID")

    creds_json = _get_env("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not creds_json:
        raise ValueError("Missing GOOGLE_APPLICATION_CREDENTIALS_JSON")
    info = json.loads(creds_json)
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
        return v

    rows = []
    for _, row in df.iterrows():
        rows.append({k: clean_value(v) for k, v in row.items()})

    return rows, datetime.utcnow()


def _send_json(handler: BaseHTTPRequestHandler, status: int, body: dict) -> None:
    handler.send_response(status)
    handler.send_header("Content-type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(json.dumps(body).encode("utf-8"))


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        try:
            rows, last_updated = fetch_sheet_data()
            _send_json(
                self,
                200,
                {"rows": rows, "last_updated": last_updated.isoformat()},
            )
        except Exception as e:
            _send_json(
                self,
                200,
                {"error": str(e), "rows": [], "last_updated": None},
            )
