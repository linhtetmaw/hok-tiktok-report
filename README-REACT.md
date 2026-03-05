# TikTok Dashboard – React + API

## Structure

- **`api/`** – FastAPI backend that reads from Google Sheets
- **`frontend/`** – React app (Vite) that displays the data

## Prerequisites

- Python 3.11+ (for API)
- Node.js 18+ (for React)
- `.env` and `credentials.json` in `tiktok-dashboard/` (same as Streamlit)

## Run locally (macOS)

### 1. Start the API (Terminal 1)

```bash
cd ~/Documents/tiktok-dashboard/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Start the React app (Terminal 2)

```bash
cd ~/Documents/tiktok-dashboard/frontend
npm install
npm run dev
```

### 3. Open the dashboard

Go to **http://localhost:5173** in your browser.

---

## Environment

- **API** uses `.env` from the parent `tiktok-dashboard/` folder.
- **Frontend** uses `frontend/.env` with `VITE_API_URL=http://localhost:8000`.
