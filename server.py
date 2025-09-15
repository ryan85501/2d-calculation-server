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
REPO_PATH = "/app/repo"   # path where your repo is cloned
HTML_FILE = f"https://github.com/ryan85501/Shwe-Pat-Tee/blob/main/index.html"
GITHUB_REPO = "https://github.com/ryan85501/Shwe-Pat-Tee.git"
GITHUB_TOKEN = "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"   # replace with your token
yangon_tz = pytz.timezone("Asia/Yangon")


#  --- Utility: read/write HTML ---
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
            f"https://{GITHUB_TOKEN}@{GITHUB_URL}"
        ], check=True)
        print("✅ Changes pushed to GitHub")
    except Exception as e:
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

# --- AM update (12:01 PM) ---
def update_am_result():
    set_result, live_result = fetch_set_result()
    if not live_result:
        print("⚠️ No AM live result available.")
        return
    update_html({}, new_result=live_result, period="am")
    print(f"✅ AM result updated: {live_result}")

# --- PM update (4:30 PM) ---
def update_pm_result():
    set_result, live_result = fetch_set_result()
    if not live_result:
        print("⚠️ No PM live result available.")
        return
    update_html({}, new_result=live_result, period="pm")
    print(f"✅ PM result updated: {live_result}")

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
def update_html(updates: dict, update_date=None, new_result=None, period=None):
    html = load_html()
    soup = BeautifulSoup(html, "html.parser")

    # Update number blocks
    for key, value in updates.items():
        target = soup.find("div", {"data-id": key})
        if target is not None:
            target.string = value

    # Update current date if provided
    if update_date:
        date_span = soup.find("span", {"id": "current-date"})
        if date_span:
            date_span.string = update_date

    # Update history table
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

    # Update previous results (calendar view)
    if new_result and len(new_result) == 4:
        prev_container = soup.find("div", {"id": "previous-results-container"})
        if prev_container:
            new_div = soup.new_tag("div", **{"class": "results-row text-4xl font-bold font-serif"})
            num_group = soup.new_tag("div", **{"class": "number-group"})
            for digit in new_result:
                span = soup.new_tag("span", **{"class": "digit-span cursor-pointer p-1 rounded-md"})
                span.string = digit
                num_group.append(span)
            new_div.append(num_group)
            prev_container.append(new_div)  # append bottom

    save_html(str(soup))
    commit_and_push()

# --- Scheduled tasks ---
def weekday_update():
    """Mon–Fri 8PM update for ဝမ်းချိန် + ရွှေကီး"""
    now = datetime.now(yangon_tz)
    if now.weekday() >= 5:
        return
    set_result, _ = fetch_set_result()

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
    friday_pm = get_friday_pm_result() # TODO: pull real Friday PM
    mwe_ga_nan = calculate_mwe_ga_nan(friday_pm)
    updates = {
        "mwe-ga-nan": mwe_ga_nan
    }
    update_html(updates)
    print("✅ Sunday update done.")

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
# AM/PM schedules
schedule.every().day.at("12:01").do(update_am_result)
schedule.every().day.at("16:30").do(update_pm_result)

print("📌 Calculation server running...")

while True:
    schedule.run_pending()
    time.sleep(30)





