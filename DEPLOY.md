# Deploy: Railway backend + Vercel frontend

Backend (FastAPI) runs on **Railway**, frontend (React) runs on **Vercel**, and the frontend calls the Railway URL via `VITE_API_URL`.

## 1. Push the repo to GitHub

```bash
cd /path/to/tiktok-dashboard
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

## 2. Backend on Railway (FastAPI)

1. In [Railway](https://railway.app), create a new project and **Deploy from GitHub**.
2. Pick this repo and set:
   - **Root directory**: `api` (required — otherwise you may see "Error creating build plan with Railpack").
   - The repo includes an `api/Dockerfile`; Railway will use it automatically when root is `api`. If you prefer Railpack/Nixpacks, you can leave build/start command blank and rely on `api/nixpacks.toml`.
   - Or set explicitly: **Build command** `pip install -r requirements.txt`, **Start command** `uvicorn main:app --host 0.0.0.0 --port 8000`.
3. In the Railway service → **Variables**, add:
   - `TIKTOK_SHEET_ID` = your Google Sheet ID (from the URL)
   - `TIKTOK_WORKSHEET_NAME` = (optional) sheet tab name if not the first
   - `GOOGLE_APPLICATION_CREDENTIALS_JSON` = **full contents** of your `credentials.json` (paste everything, including `{` and `}`).  
     **If the value is too long** for Railway’s UI, use two variables instead (split the JSON at a comma between two keys, e.g. after `"private_key_id": "xxx",`):
   - `GOOGLE_APPLICATION_CREDENTIALS_JSON_1` = from `{` up to and including that comma (e.g. `{"type": "service_account", "project_id": "...", "private_key_id": "xxx",`)
   - `GOOGLE_APPLICATION_CREDENTIALS_JSON_2` = the rest (e.g. `"private_key": "-----BEGIN...", "client_email": "...", ... }`)
4. Deploy. Note the public URL Railway gives you, e.g. `https://hok-tiktok-api.up.railway.app`.

## 3. Frontend on Vercel (React)

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub.
2. **Add New Project** → **Import** your GitHub repo.
3. **Root Directory**: set to `frontend` (so the build runs inside `frontend/`).
4. **Build settings** — use the repo’s `vercel.json` (no override), or set explicitly:
   - **Install command**: `npm install`
   - **Build command**: `npm run build` (do **not** use `cd frontend && npm ci && npm run build` when Root Directory is already `frontend`)
   - **Output directory**: `dist`
5. If you see *Command "cd frontend && npm ci && npm run build" exited with 1*: go to **Settings → General → Build & Development Settings** and set **Build Command** to `npm run build` (and **Install Command** to `npm install`). Root Directory must be `frontend`.
6. In the Vercel project **Settings → Environment Variables**, add:
   - `VITE_API_URL` = your Railway backend URL, e.g. `https://hok-tiktok-api.up.railway.app`
7. Deploy. The frontend will call `GET ${VITE_API_URL}/api/data` to fetch TikTok data.

## 4. Custom domain: hok-tiktok.reindeers.agency

1. In Vercel (frontend project): **Settings → Domains** → Add `hok-tiktok.reindeers.agency`.
2. At your DNS provider (where `reindeers.agency` is managed), add a **CNAME**:
   - **Name:** `hok-tiktok`
   - **Value:** the Vercel target they show (typically `cname.vercel-dns.com`).
3. Wait for DNS to propagate until Vercel shows the domain as active.

## 5. Local development

- **React + API (dev):**
  - Terminal 1: `cd api && pip install -r requirements.txt && uvicorn main:app --reload --port 8000`
  - Terminal 2: `cd frontend && npm install && npm run dev`
- **Streamlit (optional):**
  - `pip install -r requirements-streamlit.txt && streamlit run streamlit_app.py`
