import os
import uuid
import tempfile

from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

import pandas as pd
from playwright.sync_api import sync_playwright


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


job_status = {}


# ============================================================
# SEO - ROBOTS.TXT
# ============================================================

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return """User-agent: *
Allow: /

Sitemap: https://openproject-automation.onrender.com/sitemap.xml
"""


# ============================================================
# SEO - SITEMAP.XML
# ============================================================

@app.get("/sitemap.xml")
def sitemap():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://openproject-automation.onrender.com/</loc>
    </url>
</urlset>
"""

    return Response(
        content=xml,
        media_type="application/xml"
    )


# ============================================================
# GC - google verification
# ============================================================
@app.get("/google1234567890abcdef.html")
def google_verification():
    return FileResponse("static/googlec4137777644ad008.html")

# ============================================================
# AUTOMATION
# ============================================================

def run_automation(job_id: str, file_path: str):

    try:

        job_status[job_id] = {
            "status": "running",
            "logs": [],
            "total": 0,
            "passed": 0,
            "failed": 0,
            "login": "pending"
        }


        # ====================================================
        # READ LOGIN DETAILS
        # ====================================================

        login_df = pd.read_excel(
            file_path,
            sheet_name="Login Details"
        )

        USERNAME = login_df.loc[0, "User Id"]
        PASSWORD = login_df.loc[0, "Password"]


        # ====================================================
        # READ TIME SHEET
        # ====================================================

        df = pd.read_excel(
            file_path,
            sheet_name="Time Sheet"
        )

        total = len(df)

        job_status[job_id]["total"] = total


        # ====================================================
        # OPENPROJECT LOGIN
        # ====================================================

        LOGIN_URL = "https://openproject.bicsglobal.com/"


        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True
            )

            page = browser.new_page()


            # ------------------------------------------------
            # OPEN LOGIN PAGE
            # ------------------------------------------------

            page.goto(
                LOGIN_URL,
                wait_until="networkidle"
            )

            page.locator(
                "//a[@href='/login']"
            ).click()


            page.locator(
                "#username-pulldown"
            ).fill(USERNAME)


            page.locator(
                "#password-pulldown"
            ).fill(PASSWORD)


            page.locator(
                "#login-pulldown"
            ).click()


            page.reload()


            # ------------------------------------------------
            # CHECK LOGIN
            # ------------------------------------------------

            try:

                page.wait_for_selector(
                    "a[icon='overridden-by-avatar']",
                    timeout=10000
                )

                job_status[job_id]["login"] = "success"

                job_status[job_id]["logs"].append(
                    "✅ Login successful"
                )


            except Exception:

                job_status[job_id]["login"] = "failed"

                job_status[job_id]["status"] = "failed"

                job_status[job_id]["logs"].append(
                    "❌ Login failed — check credentials"
                )

                browser.close()

                return


            # =================================================
            # PROCESS TIME SHEET
            # =================================================

            recent_project_name = "start project-1"
            recent_subject_name = "start project-1"

            for index, row in df.iterrows():

                S_No = row["S.No"]
                Project_Name = row["Project Name"]
                subject = row["Subject"]
                name = row["Name"]
                date = str(row["Date"])
                hour = str(row["Hour"])
                activity = row["Activity"]
                comment = row["Comment"]

                import time
                try:

                    # -----------------------------------------
                    # CHANGE PROJECT IF REQUIRED
                    # -----------------------------------------
                    if Project_Name != recent_project_name or subject != recent_subject_name:
                        
                        page.locator(
                            "#projects-menu"
                        ).click()

                        page.locator(
                            f"//a/span[text()='{Project_Name}']"
                        ).click()
                        recent_project_name = Project_Name

                        work_packages_menu = page.locator("#main-menu-work-packages")

                        if work_packages_menu.count() > 0 and work_packages_menu.first.is_visible():
                            work_packages_menu.first.click()

                        page.locator(
                            "//a/span[text() = 'All open ']"
                        ).click()

                        page.locator("#work-packages-filter-toggle-button").click()

                        page.locator("#add_filter_select").click()

                        page.locator("//div[@role='option']//span[@class='ng-option-label' and normalize-space()='Assignee']").click()

                        page.locator("#values-assignee").click()

                        page.locator("#values-assignee input").fill(name)

                        page.locator(f"//div[@role='option' and normalize-space()='{name}']").click()

                        page.locator("#add_filter_select").click()

                        page.locator("//*[@id ='add_filter_select']//input").fill('Subject')

                        page.locator("//div[@role='option']//span[@class='ng-option-label' and normalize-space()='Subject']").click()

                        page.locator("//div[@id = 'div-values-Subject']/input").fill(subject)

                        recent_subject_name = subject

                    # -----------------------------------------
                    # FIND WORK PACKAGE
                    # -----------------------------------------

                    page.locator(
                        f"//tr[.//span[@data-field-name='subject' "
                        f"and normalize-space()='{subject}'] "
                        f"and .//span[contains(@class,'op-principal--name') "
                        f"and normalize-space()='{name}']]"
                        f"//a[@title='Log time']"
                    ).click()


                    # -----------------------------------------
                    # ENTER TIME DETAILS
                    # -----------------------------------------
                    if pd.notna(date):
                        page.locator(
                            "#wp-new-inline-edit--field-spentOn"
                        ).fill(date)

                    if pd.notna(hour):
                        page.locator(
                            "#wp-new-inline-edit--field-hours"
                        ).fill(hour)

                    if pd.notna(comment):
                        page.locator(
                            "#wp-new-inline-edit--field-comment"
                        ).fill(comment)

                    # -----------------------------------------
                    # SELECT ACTIVITY
                    # -----------------------------------------
                    if pd.notna(activity):
                        page.locator(
                            "#wp-new-inline-edit--field-activity"
                        ).click()

                        page.locator(
                            f"//span[@class='ng-option-label ellipsis' "
                            f"and normalize-space()='{activity}']"
                        ).click()

                    # -----------------------------------------
                    # SAVE
                    # -----------------------------------------

                    page.locator(
                        "//button[@title='Save']"
                    ).click()

                    # -----------------------------------------
                    # SUCCESS
                    # -----------------------------------------

                    job_status[job_id]["passed"] += 1

                    job_status[job_id]["logs"].append(
                        f"✅ [{S_No}] {subject} | {name} | {date} — Logged"
                    )


                except Exception as row_err:

                    # -----------------------------------------
                    # ROW FAILED
                    # -----------------------------------------

                    cancel_button = page.locator("//button[normalize-space()='Cancel']")

                    if cancel_button.count() > 0 and cancel_button.first.is_visible():
                        cancel_button.first.click()

                    job_status[job_id]["failed"] += 1

                    job_status[job_id]["logs"].append(
                        f"❌ [{S_No}] {subject} | {name} | {date} — "
                        f"{str(row_err)[:80]}"
                    )

            # =================================================
            # CLOSE BROWSER
            # =================================================

            browser.close()


        # ====================================================
        # JOB COMPLETED
        # ====================================================

        job_status[job_id]["status"] = "completed"


    except Exception as e:

        # ====================================================
        # FATAL ERROR
        # ====================================================

        job_status[job_id]["status"] = "failed"

        job_status[job_id]["logs"].append(
            f"❌ Fatal error: {str(e)}"
        )


    finally:

        # ====================================================
        # DELETE TEMP FILE
        # ====================================================

        if os.path.exists(file_path):

            os.remove(file_path)


# ============================================================
# HOME PAGE
# ============================================================

@app.get("/")
def index():

    return FileResponse(
        "static/index.html"
    )


# ============================================================
# FILE UPLOAD
# ============================================================

@app.post("/upload")
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):

    job_id = str(uuid.uuid4())


    tmp_dir = tempfile.gettempdir()

    file_path = os.path.join(
        tmp_dir,
        f"{job_id}.xlsx"
    )


    contents = await file.read()


    with open(file_path, "wb") as f:

        f.write(contents)


    job_status[job_id] = {
        "status": "queued",
        "logs": [],
        "total": 0,
        "passed": 0,
        "failed": 0,
        "login": "pending"
    }


    background_tasks.add_task(
        run_automation,
        job_id,
        file_path
    )


    return JSONResponse(
        {
            "job_id": job_id
        }
    )


# ============================================================
# JOB STATUS
# ============================================================

@app.get("/status/{job_id}")
def status(job_id: str):

    return JSONResponse(
        job_status.get(
            job_id,
            {
                "status": "not_found",
                "logs": []
            }
        )
    )
