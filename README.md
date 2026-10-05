# OpenProject Timesheet Automation

A web-based automation tool that reads an Excel timesheet and automatically logs time entries into [OpenProject](https://openproject.bicsglobal.com/) using Playwright browser automation.

## Tech Stack

| Layer     | Technology                        |
|-----------|-----------------------------------|
| Backend   | Python 3.11, FastAPI, Uvicorn     |
| Automation| Playwright (Chromium)             |
| Data      | Pandas, OpenPyXL                  |
| Frontend  | Vanilla HTML/CSS/JS (single page) |

## Project Structure

```
openproject/
├── main.py                              # FastAPI app + Playwright automation
├── requirements.txt                     # Python dependencies
├── Procfile                             # Railway deployment command
├── runtime.txt                          # Python version (3.11.0)
├── .gitignore
└── static/
    ├── index.html                       # Web UI
    └── openproject_timesheet_sample.xlsx  # Sample Excel template
```

## Excel Format Required

The uploaded `.xlsx` file must contain exactly **2 sheets**:

**Sheet 1 — `Login Details`**

| User Id | Password |
|---------|----------|
| your_username | your_password |

**Sheet 2 — `Time Sheet`**

| S.No | Project Name | Subject | Name | Date | Hour | Activity | Comment |
|------|-------------|---------|------|------|------|----------|---------|

- `Project Name` — must match exactly as shown in OpenProject's project menu
- `Subject` — work package subject name
- `Name` — assignee name shown in the work package list
- `Date` — date for the time entry
- `Hour` — hours to log (e.g. `2` or `1.5`)
- `Activity` — must match an activity option in OpenProject's log time dialog
- `Comment` — optional comment for the time entry

> Download the sample file from the web UI to get started quickly.

## How It Works

1. User uploads the Excel file via the web UI
2. FastAPI saves the file to a temp directory and starts a background job
3. Playwright launches a Chromium browser (non-headless), logs into OpenProject, and iterates through each row in the Time Sheet
4. For each row it navigates to the correct project → work package → clicks "Log time" → fills in date, hours, comment, activity → saves
5. The UI polls `/status/{job_id}` every second and shows live logs, progress bar, and pass/fail counts
6. The temp file is deleted after the job completes

## API Endpoints

| Method | Endpoint            | Description                        |
|--------|---------------------|------------------------------------|
| GET    | `/`                 | Serves the web UI                  |
| POST   | `/upload`           | Accepts `.xlsx`, starts background job, returns `job_id` |
| GET    | `/status/{job_id}`  | Returns job status, logs, and counts |

## Run Locally

```bash
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000)

> **Note:** Playwright runs in **non-headless** mode (`headless=False`), so a visible browser window will open on the server machine during automation.

## Deploy to Railway

1. Push this repo to GitHub
2. Go to [https://railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Select your repo — Railway auto-detects the `Procfile` and deploys
4. The `Procfile` installs Chromium and starts the server:
   ```
   web: playwright install chromium && uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
5. Your app will be live at `https://<your-app>.railway.app`

## Dependencies

```
fastapi
uvicorn
playwright
pandas
openpyxl
python-multipart
```

## Notes

- Only `.xlsx` files are accepted
- Credentials are read directly from the Excel file and never stored
- Job status is held in memory — restarting the server clears all job history
- The automation targets `https://openproject.bicsglobal.com/` — update `LOGIN_URL` in `main.py` to point to a different instance
