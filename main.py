import os
import uuid
import tempfile
from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
from playwright.sync_api import sync_playwright

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

job_status = {}

def run_automation(job_id: str, file_path: str):
    try:
        job_status[job_id] = {"status": "running", "logs": [], "total": 0, "passed": 0, "failed": 0, "login": "pending"}

        login_df = pd.read_excel(file_path, sheet_name="Login Details")
        USERNAME = login_df.loc[0, "User Id"]
        PASSWORD = login_df.loc[0, "Password"]
        df = pd.read_excel(file_path, sheet_name="Time Sheet")
        total = len(df)
        job_status[job_id]["total"] = total

        LOGIN_URL = "https://openproject.bicsglobal.com/"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            page.goto(LOGIN_URL, wait_until="networkidle")
            page.locator("//a[@href='/login']").click()
            page.locator("#username-pulldown").fill(USERNAME)
            page.locator("#password-pulldown").fill(PASSWORD)
            page.locator("#login-pulldown").click()
            page.reload()
            try:
                page.wait_for_selector("a[icon='overridden-by-avatar']", timeout=10000)
                job_status[job_id]["login"] = "success"
                job_status[job_id]["logs"].append("✅ Login successful")
            except Exception:
                job_status[job_id]["login"] = "failed"
                job_status[job_id]["status"] = "failed"
                job_status[job_id]["logs"].append("❌ Login failed — check credentials")
                browser.close()
                return

            recent_project_name = 'start project-1'

            for index, row in df.iterrows():
                S_No = row["S.No"]
                Project_Name = row["Project Name"]
                subject = row["Subject"]
                name = row["Name"]
                date = str(row["Date"])
                hour = str(row["Hour"])
                activity = row["Activity"]
                comment = row["Comment"]

                try:
                    if Project_Name != recent_project_name:
                        page.locator("#projects-menu").click()
                        page.locator(f"//a/span[text()='{Project_Name}']").click()
                        if recent_project_name == "start project-1":
                            page.locator("#main-menu-work-packages").click()
                        page.locator("//a/span[text() = 'All open ']").click()

                    page.locator(
                        f"//tr[.//span[@data-field-name='subject' and normalize-space()='{subject}'] "
                        f"and .//span[contains(@class,'op-principal--name') and normalize-space()='{name}']]"
                        f"//a[@title='Log time']"
                    ).click()

                    page.locator("#wp-new-inline-edit--field-spentOn").fill(date)
                    page.locator("#wp-new-inline-edit--field-hours").fill(hour)
                    page.locator("#wp-new-inline-edit--field-comment").fill(comment)

                    page.locator("#wp-new-inline-edit--field-activity").click()
                    page.locator(
                        f"//span[@class='ng-option-label ellipsis' and normalize-space()='{activity}']"
                    ).click()

                    page.locator("//button[@title='Save']").click()
                    recent_project_name = Project_Name

                    job_status[job_id]["passed"] += 1
                    job_status[job_id]["logs"].append(f"✅ [{S_No}] {subject} | {name} | {date} — Logged")

                except Exception as row_err:
                    job_status[job_id]["failed"] += 1
                    job_status[job_id]["logs"].append(f"❌ [{S_No}] {subject} | {name} | {date} — {str(row_err)[:80]}")

            browser.close()

        job_status[job_id]["status"] = "completed"

    except Exception as e:
        job_status[job_id]["status"] = "failed"
        job_status[job_id]["logs"].append(f"❌ Fatal error: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.post("/upload")
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    tmp_dir = tempfile.gettempdir()
    file_path = os.path.join(tmp_dir, f"{job_id}.xlsx")

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    job_status[job_id] = {"status": "queued", "logs": [], "total": 0, "passed": 0, "failed": 0, "login": "pending"}
    background_tasks.add_task(run_automation, job_id, file_path)

    return JSONResponse({"job_id": job_id})


@app.get("/status/{job_id}")
def status(job_id: str):
    return JSONResponse(job_status.get(job_id, {"status": "not_found", "logs": []}))
