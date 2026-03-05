## TikTok Engagement Dashboard (Standalone)

This is a **separate app** from your Telegram bot project. It is a small **Streamlit** web app that reads TikTok video engagement data from a **Google Sheet** and shows a live dashboard.  
When you change data in the sheet, the dashboard will refresh automatically every few minutes (configurable), or instantly when you hit a manual refresh button.

---

### 1. Google Sheets & API setup

1. **Prepare your TikTok Google Sheet**
   - Use one sheet/tab that contains your TikTok metrics (e.g. columns like `Date`, `Video Title`, `Views`, `Likes`, `Comments`, `Shares`, etc.).
   - You can name the sheet/tab anything (e.g. `TikTok` or `DashboardData`).

2. **Create a Google Cloud project & enable APIs**
   - Go to Google Cloud Console.
   - Create a new project (or use an existing one).
   - In **APIs & Services → Library**, enable:
     - **Google Sheets API**
     - (Optionally) **Google Drive API** if you later need it.

3. **Create a Service Account and JSON key**
   - In **APIs & Services → Credentials**:
     - Click **Create credentials → Service account**.
     - Give it a name (e.g. `tiktok-dashboard-service`).
     - After creation, go to the **Keys** tab → **Add key → Create new key → JSON**.
     - Download the JSON file (e.g. `tiktok-dashboard-credentials.json`) and store it somewhere safe.

4. **Share your TikTok Google Sheet with the service account**
   - Open your TikTok engagement Google Sheet.
   - Click **Share**.
   - Add the **service account email** (ends with `@<project-id>.iam.gserviceaccount.com`) as **Viewer**.
   - This gives the dashboard read-only access to your data.

---

### 2. Environment variables

The app uses environment variables to know which sheet to read and where your credentials file lives.

Required:

- `TIKTOK_SHEET_ID` – The **ID** of your TikTok engagement Google Sheet  
  (the long string in the sheet URL between `/d/` and `/edit`).
- `GOOGLE_APPLICATION_CREDENTIALS` – Absolute path to your service account JSON key file.

Optional:

- `TIKTOK_WORKSHEET_NAME` – Name of the specific worksheet/tab inside the sheet.  
  If not set, the app will use the **first** sheet/tab.
- `DASHBOARD_REFRESH_MINUTES` – Auto-refresh interval in minutes (default is `5` if not set).

You can provide these either via:

- Exporting them in your shell before running, or
- A local `.env` file (not committed) loaded by `python-dotenv`.

Example `.env`:

```env
TIKTOK_SHEET_ID=your_google_sheet_id_here
TIKTOK_WORKSHEET_NAME=TikTok
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/tiktok-dashboard-credentials.json
DASHBOARD_REFRESH_MINUTES=5
```

---

### 3. Install and run locally

1. **Create and activate a virtual environment**

```bash
cd /Users/linhtetmaw/Documents/assistant-bot/tiktok-dashboard
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
```

2. **Install dependencies**

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. **Set environment variables**

- Either export them in your shell:

  ```bash
  export TIKTOK_SHEET_ID="your_sheet_id"
  export GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/credentials.json"
  export TIKTOK_WORKSHEET_NAME="TikTok"
  export DASHBOARD_REFRESH_MINUTES=5
  ```

- Or create a `.env` file as shown above.

4. **Run the dashboard**

```bash
streamlit run streamlit_app.py
```

Then open the local URL (usually `http://localhost:8501`) in your browser.

Any changes you make in the Google Sheet will show in the dashboard automatically after the configured refresh interval, or immediately when you click the **Refresh now** button.

---

### 4. Deployment (later)

When you are happy with the dashboard locally, you can deploy it, for example:

- **Streamlit Community Cloud**:
  - Put this `tiktok-dashboard` folder in a GitHub repo.
  - Connect the repo in Streamlit Cloud.
  - Set the same environment variables and upload the JSON key as a secret/file.
- **Other platforms** (Render, Railway, etc.):
  - Use `streamlit run streamlit_app.py` as the main command.
  - Store your environment variables and JSON credentials in their **secrets** configuration.

