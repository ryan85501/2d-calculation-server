import os
import schedule
import time
import subprocess
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pytz
import requests

# ---------------------------
# Paths & GitHub Config
# ---------------------------
REPO_PATH = "/opt/render/project/src"   # fixed path
HTML_FILE = os.path.join(REPO_PATH, "index.html")

GITHUB_REPO = "https://github.com/ryan85501/Shwe-Pat-Tee.git"
GITHUB_USERNAME = "ryan85501"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "YOUR_TOKEN_HERE")   # use env var
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
# Fetch Set Result
# ---------------------------
def fetch_set_result():
    try:
        resp = requests.get("https://set-scraper-server.onrender.com/get_set_data", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("set_result"), data.get("live_result")
    except Exception as e:
        print(f"⚠️ Error fetching set result: {e}")
        return None, None

# ---------------------------
# Custom Calculation Methods
# ---------------------------
def calculate_one_chain(set_result: str):
    """From PM result decimals"""
    set_str = set_result.replace(",", "")
    if "." not in set_str:
        return []
    decimals = set_str.split(".")[1]
    if len(decimals) < 2:
        return []
    d1, d2 = int(decimals[-2]), int(decimals[-1])
    s = d1 + d2
    return [s - 1, s]

def calculate_not_broken(set_result: str):
    """From PM result integer part"""
    set_str = set_result.replace(",", "")
    integer = set_str.split(".")[0]
    if len(integer) < 2:
        return []
    d1, d2 = int(integer[-2]), int(integer[-1])
    s = d1 + d2
    last = s % 10
    return [last - 1, last, last + 1]

def calculate_mwe_ga_nan(friday_pm: str):
    """From Friday PM result"""
    first = int(friday_pm[0])
    second = int(friday_pm[1])
    first_digits = [(first + x) % 10 for x in [0, 2, 4, 6, 8]]
    second_digits = [(second + y) % 10 for y in [1, 3, 5, 7, 9]]
    results = [f"{a}{b}" for a, b in zip(first_digits, second_digits)]
    return results

# ---------------------------
# HTML Update Function
# ---------------------------
def update_html(updates=None, new_result=None, period=None, advance_date=False):
    git_pull()
    soup = load_html()

    # Update divs
    if updates:
        for key, value in updates.items():
            target = soup.select_one(f'div[data-id="{key}"]')
            if target:
                target.string = ", ".join(map(str, value)) if isinstance(value, list) else str(value)

    # Update history table + previous results
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
                span["class"] = "digit-span cursor-pointer p-1 rounded-md"
                number_group.append(span)
            result_row.append(number_group)
            prev_container.append(result_row)

    # Update date
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
    _, live_result = fetch_set_result()
    if live_result:
        update_html(new_result=live_result, period="am")
        print(f"✅ AM result updated: {live_result}")

def update_pm_result():
    set_result, live_result = fetch_set_result()
    if live_result:
        update_html(new_result=live_result, period="pm")
        print(f"✅ PM result updated: {live_result}")

def weekday_evening_update():
    set_result, _ = fetch_set_result()
    if not set_result:
        return
    updates = {
        "one-chain": calculate_one_chain(set_result),
        "not-broken": calculate_not_broken(set_result),
        "one-kwet": "",
        "shwe-pat-tee": "",
        "punch": ""
    }
    update_html(updates=updates)
    print("🌙 Weekday evening update done.")

def sunday_update():
    friday_pm = "23"  # TODO: fetch actual Friday PM result
    updates = {"mwe-ga-nan": calculate_mwe_ga_nan(friday_pm)}
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
