# --- Calculation + GitHub Update Server ---
import os
import subprocess
from datetime import datetime, timedelta
import pytz
import schedule
import time
import requests
from bs4 import BeautifulSoup

# === CONFIG ===
REPO_PATH = "/app/repo"   # Path where your repo is cloned
HTML_FILE = os.path.join(REPO_PATH, "index.html")  # Local file inside repo
GITHUB_REPO = "https://github.com/ryan85501/Shwe-Pat-Tee.git"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # Better to use env var
yangon_tz = pytz.timezone("Asia/Yangon")


# --- Utility: read/write HTML ---
def load_html():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"❌ Error loading HTML: {e}")
        return None


def save_html(content):
    try:
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ HTML updated locally.")
    except Exception as e:
        print(f"❌ Error saving HTML: {e}")


def commit_and_push():
    try:
        subprocess.run(["git", "-C", REPO_PATH, "add", "index.html"], check=True)
        subprocess.run(["git", "-C", REPO_PATH, "commit", "-m", "Auto-update results"], check=True)
        subprocess.run([
            "git", "-C", REPO_PATH, "push",
            f"https://{GITHUB_TOKEN}@{GITHUB_REPO.split('https://')[1]}"
        ], check=True)
        print("✅ Changes pushed to GitHub")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git push failed: {e}")


# --- Fetch live set/2D result from scraper ---
def fetch_set_result():
    try:
        response = requests.get("https://set-scraper-server.onrender.com/get_set_data", timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("set_result"), data.get("live_result")
    except Exception as e:
        print(f"⚠️ Error fetching set_result: {e}")
        return None, None


# --- Calculation functions ---
def calculate_one_chain(set_result):
    if not set_result:
        return []
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
    if not set_result:
        return []
    set_str = set_result.replace(",", "")
    integer = set_str.split(".")[0]
    if len(integer) < 2:
        return []
    d1, d2 = int(integer[-2]), int(integer[-1])
    s = d1 + d2
    last = s % 10
    return [last - 1, last, last + 1]


def calculate_mwe_ga_nan(friday_pm):
    if not friday_pm or len(friday_pm) < 2:
        return ""
    first = int(friday_pm[0])
    second = int(friday_pm[1])
    first_digits = [(first + x) % 10 for x in [0, 2, 4, 6, 8]]
    second_digits = [(second + y) % 10 for y in [1, 3, 5, 7, 9]]
    results = [f"{a}{b}" for a, b in zip(first_digits, second_digits)]
    return ", ".join(results)


# --- HTML update ---
def update_html(updates: dict, update_date=None, new_result=None, period=None):
    html = load_html()
    if not html:
        return

    soup = BeautifulSoup(html, "html.parser")

    # Update number blocks (without breaking structure)
    for key, value in updates.items():
        target = soup.find("div", {"data-id": key})
        if target is not None:
            target.string = value

    # Update current date if provided
    if update_date:
        date_span = soup.find("span", {"id": "current-date"})
        if date_span:
            date_span.string = update_date

    # Update history table (safe insert)
    if new_result and period in ["am", "pm"]:
        table_body = soup.find("tbody", {"id": "history-table-body"})
        if table_body:
            new_row = soup.new_tag("tr")
            date_td = soup.new_tag("td")
            date_td.string = datetime.now(yangon_tz).strftime("%d-%m-%Y")
            am_td = soup.new_tag("td")
            am_td.string = new_result if period == "am" else "--"
            pm_td = soup.new_tag("td")
            pm_td.string = new_result if period == "pm" else "--"
            new_row.extend([date_td, am_td, pm_td])
            table_body.insert(0, new_row)  # prepend row

    save_html(str(soup))
    commit_and_push()


# --- Scheduled tasks ---
def update_am_result():
    _, live_result = fetch_set_result()
    if not live_result:
        print("⚠️ No AM live result available.")
        return
    update_html({}, new_result=live_result, period="am")
    print(f"✅ AM result updated: {live_result}")


def update_pm_result():
    _, live_result = fetch_set_result()
    if not live_result:
        print("⚠️ No PM live result available.")
        return
    update_html({}, new_result=live_result, period="pm")
    print(f"✅ PM result updated: {live_result}")


def weekday_update():
    """Mon–Fri 8PM update for one-chain + not-broken"""
    now = datetime.now(yangon_tz)
    if now.weekday() >= 5:
        return

    set_result, _ = fetch_set_result()
    if not set_result:
        print("⚠️ No set_result fetched.")
        return

    one_chain = calculate_one_chain(set_result)
    not_broken = calculate_not_broken(set_result)

    updates = {
        "one-chain": ", ".join(map(str, one_chain)) if one_chain else "--",
        "not-broken": ", ".join(map(str, not_broken)) if not_broken else "--",
        "one-kwet": "",
        "shwe-pat-tee": "",
        "punch": ""
    }
    update_html(updates)
    print(f"✅ Weekday calculation done → one-chain={one_chain}, not-broken={not_broken}")


def sunday_update():
    """Sunday 5PM update for မွေးဂဏန်း"""
    now = datetime.now(yangon_tz)
    if now.weekday() != 6:
        return
    friday_pm = "25"  # TODO: replace with real Friday PM fetcher
    mwe_ga_nan = calculate_mwe_ga_nan(friday_pm)
    updates = {"mwe-ga-nan": mwe_ga_nan}
    update_html(updates)
    print(f"✅ Sunday update done → mwe-ga-nan={mwe_ga_nan}")


def update_date_task():
    """Change date at 8:01PM (skip weekends)"""
    now = datetime.now(yangon_tz)
    next_day = now + timedelta(days=1)
    if now.weekday() == 4:  # Friday → Monday
        next_day += timedelta(days=2)
    if next_day.weekday() == 5:  # Saturday → Monday
        next_day += timedelta(days=2)
    formatted = f"{next_day.strftime('%d-%m-%Y')} - {next_day.strftime('%A')}"
    update_html({}, update_date=formatted)
    print(f"📅 Date updated to {formatted}")


# --- Schedule ---
schedule.every().day.at("12:01").do(update_am_result)
schedule.every().day.at("16:30").do(update_pm_result)
schedule.every().monday.at("20:00").do(weekday_update)
schedule.every().tuesday.at("20:00").do(weekday_update)
schedule.every().wednesday.at("20:00").do(weekday_update)
schedule.every().thursday.at("20:00").do(weekday_update)
schedule.every().friday.at("20:00").do(weekday_update)
schedule.every().sunday.at("17:00").do(sunday_update)
schedule.every().monday.at("20:01").do(update_date_task)
schedule.every().tuesday.at("20:01").do(update_date_task)
schedule.every().wednesday.at("20:01").do(update_date_task)
schedule.every().thursday.at("20:01").do(update_date_task)
schedule.every().friday.at("20:01").do(update_date_task)

print("📌 Calculation server running...")

while True:
    schedule.run_pending()
    time.sleep(30)

