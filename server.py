# --- Calculation + GitHub Update Server ---
import os
import subprocess
from datetime import datetime, timedelta
import pytz
import schedule
import time
from bs4 import BeautifulSoup

# === CONFIG ===
REPO_PATH = "/app/repo"   # path where your repo is cloned
HTML_FILE = f"https://github.com/ryan85501/Shwe-Pat-Tee/index.html"
GITHUB_REPO = "https://github.com/ryan85501/Shwe-Pat-Tee.git"
GITHUB_TOKEN = "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"   # replace with your token
yangon_tz = pytz.timezone("Asia/Yangon")


# --- Utility: read/write HTML ---
def load_html():
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        return f.read()

def save_html(content):
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(content)

def commit_and_push():
    try:
        subprocess.run(["git", "-C", REPO_PATH, "add", "index.html"], check=True)
        subprocess.run(["git", "-C", REPO_PATH, "commit", "-m", "Auto-update results"], check=True)
        subprocess.run([
            "git", "-C", REPO_PATH, "push",
            f"https://{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}@{https://github.com/ryan85501/Shwe-Pat-Tee.split('https://')[1]}"
        ], check=True)
        print("✅ Changes pushed to GitHub")
    except Exception as e:
        print(f"❌ Git push failed: {e}")
# Update History
history_table = soup.find("tbody", {"id": "history-table-body"})
new_row = soup.new_tag("tr")
new_row.string = f"<td>{date}</td><td>{am}</td><td>{pm}</td>"
history_table.insert(0, new_row)

# Update Calendar
prev_results = soup.find("div", {"id": "previous-results-container"})
new_div = soup.new_tag("div")
new_div.string = result
prev_results.append(new_div)


# --- Calculation functions ---
def calculate_one_chain(set_result):
    set_str = set_result.replace(",", "")
    if "." not in set_str:
        return []
    decimals = set_str.split(".")[1]
    if len(decimals) < 2:
        return []
    d1, d2 = int(decimals[-2]), int(decimals[-1])
    s = d1 + d2
    return [s - 1, s]

def calculate_not_broken(set_result):
    set_str = set_result.replace(",", "")
    integer = set_str.split(".")[0]
    if len(integer) < 2:
        return []
    d1, d2 = int(integer[-2]), int(integer[-1])
    s = d1 + d2
    last = s % 10
    return [last - 1, last, last + 1]

def calculate_mwe_ga_nan(friday_pm):
    first = int(friday_pm[0])
    second = int(friday_pm[1])
    first_digits = [(first + x) % 10 for x in [0, 2, 4, 6, 8]]
    second_digits = [(second + y) % 10 for y in [1, 3, 5, 7, 9]]
    results = [f"{a}{b}" for a, b in zip(first_digits, second_digits)]
    return ", ".join(results)


# --- HTML update ---
def update_html(updates: dict, update_date=None):
    html = load_html()
    soup = BeautifulSoup(html, "html.parser")

    # Update number blocks
    for key, value in updates.items():
        target = soup.find("div", {"data-id": key})
        if target:
            target.string = value

    # Update current date if provided
    if update_date:
        date_span = soup.find("span", {"id": "current-date"})
        if date_span:
            date_span.string = update_date

    save_html(str(soup))
    commit_and_push()


# --- Scheduled tasks ---
def weekday_update():
    """Mon–Fri 8PM update for ဝမ်းချိန် + ရွှေကီး"""
    now = datetime.now(yangon_tz)
    if now.weekday() >= 5:
        return

    set_result = "1,293.62"  # replace with live fetch if needed
    one_chain = calculate_one_chain(set_result)
    not_broken = calculate_not_broken(set_result)

    updates = {
        "one-chain": ", ".join(map(str, one_chain)),
        "not-broken": ", ".join(map(str, not_broken)),
        "one-kwet": "",
        "shwe-pat-tee": "",
        "punch": ""
    }
    update_html(updates)
    print("✅ Weekday calculation done.")


def sunday_update():
    """Sunday 5PM update for မွေးဂဏန်း"""
    now = datetime.now(yangon_tz)
    if now.weekday() != 6:
        return

    friday_pm = "25"  # you should fetch the real Friday PM result
    mwe_ga_nan = calculate_mwe_ga_nan(friday_pm)

    updates = {
        "mwe-ga-nan": mwe_ga_nan
    }
    update_html(updates)
    print("✅ Sunday update done.")


def update_date_task():
    """Change date at 8:01PM (skip weekends, jump to Monday if Friday)"""
    now = datetime.now(yangon_tz)
    next_day = now + timedelta(days=1)

    # If Friday, skip to Monday
    if now.weekday() == 4:  # Friday
        next_day += timedelta(days=2)

    # If Saturday, skip to Monday
    if next_day.weekday() == 5:
        next_day += timedelta(days=2)

    formatted = f"{next_day.strftime('%d-%m-%Y')} - {next_day.strftime('%A')}"
    update_html({}, update_date=formatted)
    print(f"📅 Date updated to {formatted}")


# --- Scheduling ---
schedule.every().monday.at("20:00").do(weekday_update)
schedule.every().tuesday.at("20:00").do(weekday_update)
schedule.every().wednesday.at("20:00").do(weekday_update)
schedule.every().thursday.at("20:00").do(weekday_update)
schedule.every().friday.at("20:00").do(weekday_update)
schedule.every().sunday.at("17:00").do(sunday_update)
schedule.every().day.at("12:01").do(update_am_result)
schedule.every().day.at("16:30").do(update_pm_result)


# Date change at 8:01PM (Mon–Fri)
schedule.every().monday.at("20:01").do(update_date_task)
schedule.every().tuesday.at("20:01").do(update_date_task)
schedule.every().wednesday.at("20:01").do(update_date_task)
schedule.every().thursday.at("20:01").do(update_date_task)
schedule.every().friday.at("20:01").do(update_date_task)

print("📌 Calculation server with date updater running...")

while True:
    schedule.run_pending()
    time.sleep(30)

