import os
import schedule
import time
import random
import subprocess
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pytz

# ---------------------------
# Paths & GitHub Config
# ---------------------------
REPO_PATH = "/opt/render/project/src/repo"
HTML_FILE = os.path.join(REPO_PATH, "index.html")


GITHUB_REPO = "https://github.com/ryan85501/Shwe-Pat-Tee.git"
GITHUB_USERNAME = "ryan85501"
GITHUB_TOKEN = "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"   # replace with your real token
GITHUB_URL = GITHUB_REPO.replace("https://", f"https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@")

yangon_tz = pytz.timezone("Asia/Yangon")

# ---------------------------
# Git Helper Functions
# ---------------------------
def git_pull():
    subprocess.run(["git", "pull", GITHUB_URL], cwd=REPO_PATH)

def git_push():
    subprocess.run(["git", "add", "index.html"], cwd=REPO_PATH)
    subprocess.run(["git", "commit", "-m", "Auto update index.html"], cwd=REPO_PATH)
    subprocess.run(["git", "push", GITHUB_URL], cwd=REPO_PATH)

# ---------------------------
# Utility Functions
# ---------------------------
def load_html():
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        return BeautifulSoup(f, "html.parser")

def save_html(soup):
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(str(soup))

def get_today_str():
    now = datetime.now(yangon_tz)
    return now.strftime("%d-%m-%Y")

def get_next_day_str(skip_weekends=True):
    now = datetime.now(yangon_tz)
    next_day = now + timedelta(days=1)
    if skip_weekends and next_day.weekday() == 5:  # Saturday
        next_day += timedelta(days=2)
    elif skip_weekends and next_day.weekday() == 6:  # Sunday
        next_day += timedelta(days=1)
    return next_day.strftime("%d-%m-%Y")

# ---------------------------
# Custom Calculation Methods
# ---------------------------
def calculate_mwe_ga_nan():
    return [str(random.randint(0, 99)).zfill(2) for _ in range(5)]

def calculate_one_chain():
    return [str(random.randint(0, 9)) for _ in range(2)]

def calculate_not_broken():
    return [str(random.randint(0, 9)) for _ in range(3)]

# ---------------------------
# HTML Update Function
# ---------------------------
def update_html(updates=None, new_result=None, period=None, advance_date=False):
    git_pull()
    soup = load_html()

    if updates:
        for key, value in updates.items():
            target = soup.select_one(f'div[data-id="{key}"]')
            if target:
                target.string = ", ".join(value) if isinstance(value, list) else value

    if new_result and period in ["am", "pm"]:
        history_table = soup.select_one("#history-table-body")
        today = get_today_str()

        today_row = None
        for row in history_table.find_all("tr"):
            if today in row.text:
                today_row = row
                break

        if not today_row:
            new_row = soup.new_tag("tr")
            date_td = soup.new_tag("td"); date_td.string = today
            am_td = soup.new_tag("td"); pm_td = soup.new_tag("td")
            new_row.extend([date_td, am_td, pm_td])
            history_table.insert(0, new_row)
            today_row = new_row

        tds = today_row.find_all("td")
        if period == "am":
            tds[1].string = new_result
        elif period == "pm":
            tds[2].string = new_result

        prev_container = soup.select_one("#previous-results-container")
        if prev_container:
            result_row = soup.new_tag("div")
            result_row["class"] = "results-row text-4xl font-bold font-serif"
            number_group = soup.new_tag("div")
            number_group["class"] = "number-group"
            for digit in new_result:
                span = soup.new_tag("span")
                span.string = digit
                span["class"] = "digit-span p-1"
                number_group.append(span)
            result_row.append(number_group)
            prev_container.append(result_row)

    if advance_date:
        date_span = soup.select_one("#current-date")
        if date_span:
            next_date = get_next_day_str(skip_weekends=True)
            day_of_week = datetime.strptime(next_date, "%d-%m-%Y").strftime("%A")
            date_span.string = f"{next_date} - {day_of_week}"

    save_html(soup)
    git_push()

# ---------------------------
# Scheduled Jobs
# ---------------------------
def update_am_result():
    result = str(random.randint(0, 99)).zfill(2)
    update_html(new_result=result, period="am")
    print(f"✅ AM result updated: {result}")

def update_pm_result():
    result = str(random.randint(0, 99)).zfill(2)
    update_html(new_result=result, period="pm")
    print(f"✅ PM result updated: {result}")

def weekday_evening_update():
    updates = {
        "one-chain": calculate_one_chain(),
        "not-broken": calculate_not_broken(),
        "one-kwet": "",
        "shwe-pat-tee": "",
        "punch": ""
    }
    update_html(updates=updates)
    print("🌙 Weekday evening update done.")

def sunday_update():
    updates = {"mwe-ga-nan": calculate_mwe_ga_nan()}
    update_html(updates=updates)
    print("☀️ Sunday Mwe Ga Nan updated.")

def advance_date_job():
    update_html(advance_date=True)
    print("📅 Date advanced for next draw.")

# ---------------------------
# Scheduler Setup
# ---------------------------
schedule.every().day.at("12:01").do(update_am_result)
schedule.every().day.at("16:30").do(update_pm_result)

schedule.every().monday.at("20:00").do(weekday_evening_update)
schedule.every().tuesday.at("20:00").do(weekday_evening_update)
schedule.every().wednesday.at("20:00").do(weekday_evening_update)
schedule.every().thursday.at("20:00").do(weekday_evening_update)
schedule.every().friday.at("20:00").do(weekday_evening_update)

schedule.every().sunday.at("17:00").do(sunday_update)

schedule.every().monday.at("20:01").do(advance_date_job)
schedule.every().tuesday.at("20:01").do(advance_date_job)
schedule.every().wednesday.at("20:01").do(advance_date_job)
schedule.every().thursday.at("20:01").do(advance_date_job)
schedule.every().friday.at("20:01").do(advance_date_job)

# ---------------------------
# Main Loop
# ---------------------------
if __name__ == "__main__":
    print("🚀 Scheduler with GitHub sync started...")
    while True:
        schedule.run_pending()
        time.sleep(30)

