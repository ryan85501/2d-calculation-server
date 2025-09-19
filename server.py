import os
import schedule
import time
import random
import subprocess
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pytz

# ---------------------------
# Repo Paths & GitHub Config
# ---------------------------
REPO_PATH = "/opt/render/project/src"
HTML_FILE = os.path.join(REPO_PATH, "index.html")

GITHUB_REPO = "https://github.com/ryan85501/2d-calculation-server.git"
GITHUB_USERNAME = "ryan85501"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "YOUR_TOKEN_HERE")  # better with env var
GITHUB_URL = GITHUB_REPO.replace("https://", f"https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@")

yangon_tz = pytz.timezone("Asia/Yangon")

# Track last run times
last_run = {"am": None, "pm": None, "weekday_8pm": None, "sunday_5pm": None, "advance_date": None}


# ---------------------------
# Git Helpers
# ---------------------------
def git_pull():
    subprocess.run(["git", "pull", "origin", "main"], cwd=REPO_PATH, check=False)

def git_push():
    subprocess.run(["git", "add", "index.html"], cwd=REPO_PATH, check=False)
    subprocess.run(["git", "commit", "-m", "Auto update index.html"], cwd=REPO_PATH, check=False)
    subprocess.run(["git", "push"], cwd=REPO_PATH, check=False)


# ---------------------------
# Utility
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
# Calculation Methods
# ---------------------------
def calculate_mwe_ga_nan(friday_pm):
    """Based on Friday PM result"""
    base = int(friday_pm) if friday_pm.isdigit() else random.randint(0, 99)
    return [str((base + i * 7) % 100).zfill(2) for i in range(5)]

def calculate_one_chain(pm_result):
    return [pm_result[0], pm_result[1]] if pm_result and len(pm_result) == 2 else ["-", "-"]

def calculate_not_broken(pm_result):
    return [str((int(d) + 1) % 10) for d in pm_result] if pm_result and pm_result.isdigit() else ["-", "-", "-"]


# ---------------------------
# HTML Update
# ---------------------------
def update_html(updates=None, new_result=None, period=None, advance_date=False):
    git_pull()
    soup = load_html()

    # Update sections
    if updates:
        for key, value in updates.items():
            target = soup.select_one(f'div[data-id="{key}"]')
            if target:
                target.string = ", ".join(value) if isinstance(value, list) else value

    # Update AM/PM results
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

        # Add to Previous Results
        prev_container = soup.select_one("#previous-results-container")
        if prev_container:
            result_row = soup.new_tag("div", **{"class": "results-row text-4xl font-bold font-serif"})
            number_group = soup.new_tag("div", **{"class": "number-group"})
            for digit in new_result:
                span = soup.new_tag("span", **{"class": "digit-span p-1"})
                span.string = digit
                number_group.append(span)
            result_row.append(number_group)
            prev_container.append(result_row)

    # Advance date
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
    last_run["am"] = get_today_str()
    print(f"✅ AM result updated: {result}")

def update_pm_result():
    result = str(random.randint(0, 99)).zfill(2)
    update_html(new_result=result, period="pm")
    last_run["pm"] = get_today_str()
    print(f"✅ PM result updated: {result}")
    return result

def weekday_evening_update(pm_result):
    updates = {
        "one-chain": calculate_one_chain(pm_result),
        "not-broken": calculate_not_broken(pm_result),
        "one-kwet": "",
        "shwe-pat-tee": "",
        "punch": ""
    }
    update_html(updates=updates)
    last_run["weekday_8pm"] = get_today_str()
    print("🌙 Weekday evening update done.")

def sunday_update(friday_pm):
    updates = {"mwe-ga-nan": calculate_mwe_ga_nan(friday_pm)}
    update_html(updates=updates)
    last_run["sunday_5pm"] = get_today_str()
    print("☀️ Sunday Mwe Ga Nan updated.")

def advance_date_job():
    update_html(advance_date=True)
    last_run["advance_date"] = get_today_str()
    print("📅 Date advanced.")


# ---------------------------
# Missed Schedule Recovery
# ---------------------------
def recover_missed_jobs():
    now = datetime.now(yangon_tz)
    today = get_today_str()
    weekday = now.weekday()

    # AM check
    if now.hour >= 12 and last_run["am"] != today and weekday < 5:
        update_am_result()

    # PM check
    if now.hour >= 16 and now.minute >= 30 and last_run["pm"] != today and weekday < 5:
        pm_result = update_pm_result()
        if weekday < 5 and now.hour >= 20 and last_run["weekday_8pm"] != today:
            weekday_evening_update(pm_result)

    # Advance date (8:01 PM weekdays)
    if weekday < 5 and now.hour >= 20 and now.minute >= 1 and last_run["advance_date"] != today:
        advance_date_job()

    # Sunday check
    if weekday == 6 and now.hour >= 17 and last_run["sunday_5pm"] != today:
        # Need Friday PM result (stub: random here)
        friday_pm = str(random.randint(0, 99)).zfill(2)
        sunday_update(friday_pm)


# ---------------------------
# Scheduler Setup
# ---------------------------
schedule.every().day.at("12:01").do(update_am_result)
schedule.every().day.at("16:30").do(update_pm_result)
schedule.every().monday.at("20:00").do(lambda: weekday_evening_update("45"))
schedule.every().tuesday.at("20:00").do(lambda: weekday_evening_update("45"))
schedule.every().wednesday.at("20:00").do(lambda: weekday_evening_update("45"))
schedule.every().thursday.at("20:00").do(lambda: weekday_evening_update("45"))
schedule.every().friday.at("20:00").do(lambda: weekday_evening_update("45"))
schedule.every().sunday.at("17:00").do(lambda: sunday_update("45"))
schedule.every().monday.at("20:01").do(advance_date_job)
schedule.every().tuesday.at("20:01").do(advance_date_job)
schedule.every().wednesday.at("20:01").do(advance_date_job)
schedule.every().thursday.at("20:01").do(advance_date_job)
schedule.every().friday.at("20:01").do(advance_date_job)
schedule.every(5).minutes.do(recover_missed_jobs)  # recovery check


# ---------------------------
# Main Loop
# ---------------------------
if __name__ == "__main__":
    print("🚀 Scheduler with GitHub sync + missed recovery started...")
    while True:
        schedule.run_pending()
        time.sleep(30)




