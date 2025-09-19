import os
import schedule
import time
import random
import subprocess
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pytz
import requests

# ---------------------------
# Repo Paths & GitHub Config
# ---------------------------
# Render mounts the repository at /opt/render/project/src
REPO_PATH = "/opt/render/project/src"
HTML_FILE = os.path.join(REPO_PATH, "index.html")

GITHUB_REPO = "https://github.com/ryan85501/Shwe-Pat-Tee.git"
GITHUB_USERNAME = "ryan85501"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_URL = GITHUB_REPO.replace("https://", f"https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@")

yangon_tz = pytz.timezone("Asia/Yangon")

# Track last run times
last_run = {"am": None, "pm": None, "weekday_8pm": None, "sunday_5pm": None, "advance_date": None}

# ---------------------------
# Git Helpers
# ---------------------------

def git_pull():
    try:
        # A simple pull is enough now that the build command guarantees a clean state.
        subprocess.run(["git", "pull", "--rebase", GITHUB_URL, "main"], cwd=REPO_PATH, check=True)
        print("✅ Git repository updated via rebase.")
    except subprocess.CalledProcessError as e:
        print(f"Error during git pull: {e}")
def git_push():
    try:
        subprocess.run(["git", "config", "user.email", "ryan85501@gmail.com"], cwd=REPO_PATH, check=True)
        subprocess.run(["git", "config", "user.name", "ryan85501"], cwd=REPO_PATH, check=True)
        
        subprocess.run(["git", "add", "index.html"], cwd=REPO_PATH, check=True)
        subprocess.run(["git", "commit", "-m", "Auto update index.html"], cwd=REPO_PATH, check=True)
        
        # Add the --force flag to ensure the push is accepted
        subprocess.run(["git", "push", "--force", GITHUB_URL, "main"], cwd=REPO_PATH, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error during git push: {e}")

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
    if skip_weekends and next_day.weekday() == 5:
        next_day += timedelta(days=2)
    elif skip_weekends and next_day.weekday() == 6:
        next_day += timedelta(days=1)
    return next_day.strftime("%d-%m-%Y")

def get_live_results():
    try:
        response = requests.get('https://set-scraper-server.onrender.com/get_set_data')
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching live data: {e}")
        return None

# ---------------------------
# Calculation Methods
# ---------------------------
def calculate_mwe_ga_nan(friday_pm):
    if not friday_pm or not friday_pm.isdigit():
        return [str(random.randint(0, 99)).zfill(2) for _ in range(5)]
    base = int(friday_pm)
    return [str((base + i * 7) % 100).zfill(2) for i in range(5)]

def calculate_one_chain(pm_result):
    if not pm_result or len(pm_result) != 2:
        return ["-", "-"]
    return [pm_result[0], pm_result[1]]

def calculate_not_broken(pm_result):
    if not pm_result or not pm_result.isdigit():
        return ["-", "-", "-"]
    return [str((int(d) + 1) % 10) for d in pm_result]

# ---------------------------
# HTML Update
# ---------------------------
def update_html(updates=None, new_result=None, period=None, advance_date=False, initial_date=False):
    soup = load_html()

    if initial_date:
        date_span = soup.select_one("#current-date")
        if date_span:
            today_date = get_today_str()
            day_of_week = datetime.strptime(today_date, "%d-%m-%Y").strftime("%A")
            date_span.string = f"{today_date} - {day_of_week}"

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
            date_td = soup.new_tag("td")
            date_td.string = today
            am_td = soup.new_tag("td")
            pm_td = soup.new_tag("td")
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
            result_row = soup.new_tag("div", **{"class": "results-row text-4xl font-bold font-serif"})
            number_group = soup.new_tag("div", **{"class": "number-group"})
            for digit in new_result:
                span = soup.new_tag("span", **{"class": "digit-span p-1"})
                span.string = digit
                number_group.append(span)
            result_row.append(number_group)
            prev_container.insert(0, result_row)

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
    data = get_live_results()
    if data and "live_am_result" in data:
        result = data["live_am_result"]
        update_html(new_result=result, period="am")
        last_run["am"] = get_today_str()
        print(f"✅ AM result updated: {result}")
    else:
        print("❌ Failed to get live AM result.")

def update_pm_result():
    data = get_live_results()
    if data and "live_pm_result" in data:
        result = data["live_pm_result"]
        update_html(new_result=result, period="pm")
        last_run["pm"] = get_today_str()
        print(f"✅ PM result updated: {result}")
        return result
    else:
        print("❌ Failed to get live PM result.")
        return None

def weekday_evening_update():
    soup = load_html()
    history_table = soup.select_one("#history-table-body")
    today = get_today_str()
    today_row = next((row for row in history_table.find_all("tr") if today in row.text), None)
    if today_row:
        pm_result = today_row.find_all("td")[2].string.strip()
        updates = {
            "one-chain": calculate_one_chain(pm_result),
            "not-broken": calculate_not_broken(pm_result)
        }
        update_html(updates=updates)
        last_run["weekday_8pm"] = get_today_str()
        print("🌙 Weekday evening update done.")
    else:
        print("❌ Could not find today's PM result to perform evening update.")

def sunday_update():
    friday_pm = "45"
    updates = {"mwe-ga-nan": calculate_mwe_ga_nan(friday_pm)}
    update_html(updates=updates)
    last_run["sunday_5pm"] = get_today_str()
    print("☀️ Sunday Mwe Ga Nan updated.")

def advance_date_job():
    update_html(advance_date=True)
    last_run["advance_date"] = get_today_str()
    print("📅 Date advanced.")

# ---------------------------
# Scheduler Setup
# ---------------------------
def setup_schedules():
    schedule.every().day.at("12:01", yangon_tz).do(update_am_result)
    schedule.every().day.at("16:30", yangon_tz).do(update_pm_result)
    schedule.every().monday.at("20:00", yangon_tz).do(weekday_evening_update)
    schedule.every().tuesday.at("20:00", yangon_tz).do(weekday_evening_update)
    schedule.every().wednesday.at("20:00", yangon_tz).do(weekday_evening_update)
    schedule.every().thursday.at("20:00", yangon_tz).do(weekday_evening_update)
    schedule.every().friday.at("20:00", yangon_tz).do(weekday_evening_update)
    schedule.every().sunday.at("17:00", yangon_tz).do(sunday_update)
    schedule.every().monday.at("20:01", yangon_tz).do(advance_date_job)
    schedule.every().tuesday.at("20:01", yangon_tz).do(advance_date_job)
    schedule.every().wednesday.at("20:01", yangon_tz).do(advance_date_job)
    schedule.every().thursday.at("20:01", yangon_tz).do(advance_date_job)
    schedule.every().friday.at("20:01", yangon_tz).do(advance_date_job)
    schedule.every(5).minutes.do(recover_missed_jobs)

def recover_missed_jobs():
    now = datetime.now(yangon_tz)
    today = get_today_str()
    weekday = now.weekday()

    if now.hour >= 12 and last_run["am"] != today and weekday < 5:
        update_am_result()

    if now.hour >= 16 and now.minute >= 30 and last_run["pm"] != today and weekday < 5:
        pm_result = update_pm_result()
        if weekday < 5 and now.hour >= 20 and last_run["weekday_8pm"] != today:
            weekday_evening_update(pm_result)

    if weekday < 5 and now.hour >= 20 and now.minute >= 1 and last_run["advance_date"] != today:
        advance_date_job()

    if weekday == 6 and now.hour >= 17 and last_run["sunday_5pm"] != today:
        friday_pm = str(random.randint(0, 99)).zfill(2)
        sunday_update(friday_pm)

# ---------------------------
# Main Loop
# ---------------------------
if __name__ == "__main__":
    git_pull()
    update_html(initial_date=True)
    setup_schedules()
    print("🚀 Scheduler with GitHub sync + missed recovery started...")

    while True:
        schedule.run_pending()
        time.sleep(1)







