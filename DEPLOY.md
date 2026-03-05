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
   - **Root directory**: `api`
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `uvicorn main:app --host 0.0.0.0 --port 8000`
3. In the Railway service → **Variables**, add:
   - `TIKTOK_SHEET_ID` = your Google Sheet ID (from the URL)
   - `TIKTOK_WORKSHEET_NAME` = (optional) sheet tab name if not the first
   - `GOOGLE_APPLICATION_CREDENTIALS` = `/app/credentials.json` (path inside the container)
4. In the Railway service **Files** tab (or via Docker volume), upload your local `credentials.json` into the container at `/app/credentials.json`.
5. Deploy. Note the public URL Railway gives you, e.g. `https://hok-tiktok-api.up.railway.app`.

## 3. Frontend on Vercel (React)

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub.
2. **Add New Project** → **Import** your GitHub repo.
3. When asked for **Root Directory**, choose `frontend`.
4. Build settings (Vercel should auto-detect, but you can set explicitly):
   - **Framework preset**: Vite
   - **Build command**: `npm run build`
   - **Output directory**: `dist`
5. In the Vercel project **Settings → Environment Variables**, add:
   - `VITE_API_URL` = your Railway backend URL, e.g. `https://hok-tiktok-api.up.railway.app`
6. Deploy. The frontend will call `GET ${VITE_API_URL}/api/data` to fetch TikTok data.

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
