# Deploy to hok-tiktok.reindeers.agency (GitHub + Vercel)

Deploy from **GitHub only**; no Railway or other server. The app runs on **Vercel** (frontend + serverless API from one repo).

## 1. Push the repo to GitHub

```bash
cd /path/to/tiktok-dashboard
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

## 2. Connect the repo to Vercel

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub.
2. **Add New Project** → **Import** your GitHub repo.
3. Leave **Root Directory** empty (repo root).
4. Vercel uses `vercel.json`: build runs in `frontend`, output is `frontend/dist`, and `api/data.py` serves `/api/data`.
5. Click **Deploy**. Add env vars (step 3) and redeploy for the dashboard to work.

## 3. Set environment variables in Vercel

**Settings → Environment Variables** in the Vercel project. Add:

| Name | Value |
|------|--------|
| `TIKTOK_SHEET_ID` | Your Google Sheet ID (from the sheet URL) |
| `TIKTOK_WORKSHEET_NAME` | (optional) Sheet tab name if not the first |
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | **Full contents** of your `credentials.json` (paste as one string) |

Redeploy after saving (Deployments → … → Redeploy).

## 4. Custom domain: hok-tiktok.reindeers.agency

1. In Vercel: **Settings → Domains** → Add `hok-tiktok.reindeers.agency`.
2. Add the CNAME record at your DNS provider (where reindeers.agency is managed):
   - **Name:** `hok-tiktok` (or the hostname Vercel shows)
   - **Value:** `cname.vercel-dns.com`
3. Wait for DNS to propagate. Vercel will show a checkmark when it’s active.

## 5. Local development

- **React + API:** Terminal 1: `cd api && uvicorn main:app --reload --port 8000`; Terminal 2: `cd frontend && npm run dev`
- **Streamlit:** `pip install -r requirements.txt && streamlit run streamlit_app.py`
