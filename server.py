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
REPO_PATH = "/opt/render/project/src/repo"   # safe path for Render
HTML_FILE = os.path.join(REPO_PATH, "index.html")
GITHUB_REPO = "https://github.com/ryan85501/Shwe-Pat-Tee.git"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # store token in Render ENV
yangon_tz = pytz.timezone("Asia/Yangon")

# --- Ensure repo is ready ---
def ensure_repo():
    if not os.path.exists(REPO_PATH):
        print("📥 Cloning repo...")
        subprocess.run([
            "git", "clone",
            f"https://{GITHUB_TOKEN}@{GITHUB_REPO.split('https://')[1]}",
            REPO_PATH
        ], check=True)
    else:
        print("🔄 Repo exists, pulling latest...")
        subprocess.run(["git", "-C", REPO_PATH, "pull"], check=True)

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
            f"https://{GITHUB_TOKEN}@{GITHUB_REPO.split('https://')[1]}"
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

# --- Example calculation functions ---
def calculate_one_chain(set_result):
    if not set_result: return []
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
    if not set_result: return []
    set_str = set_result.replace(",", "")
    integer = set_str.split(".")[0]
    if len(integer) < 2:
        return []
    d1, d2 = int(integer[-2]), int(integer[-1])
    s = d1 + d2
    last = s % 10
    return [last - 1, last, last + 1]

# --- HTML update ---
def update_html(updates: dict):
    html = load_html()
    soup = BeautifulSoup(html, "html.parser")

    for key, value in updates.items():
        target = soup.find("div", {"data-id": key})
        if target is not None:
            target.string = value

    save_html(str(soup))
    commit_and_push()

# --- Scheduled tasks ---
def weekday_update():
    """Mon–Fri 8PM update for one-chain + not-broken"""
    now = datetime.now(yangon_tz)
    if now.weekday() >= 5:
        return
    set_result, _ = fetch_set_result()
    one_chain = calculate_one_chain(set_result)
    not_broken = calculate_not_broken(set_result)
    updates = {
        "one-chain": ", ".join(map(str, one_chain)),
        "not-broken": ", ".join(map(str, not_broken)),
    }
    update_html(updates)
    print("✅ Weekday calculation done.")

# --- MAIN ---
if __name__ == "__main__":
    ensure_repo()
    print("📌 Calculation server running...")

    # Schedule
    schedule.every().monday.at("20:00").do(weekday_update)
    schedule.every().tuesday.at("20:00").do(weekday_update)
    schedule.every().wednesday.at("20:00").do(weekday_update)
    schedule.every().thursday.at("20:00").do(weekday_update)
    schedule.every().friday.at("20:00").do(weekday_update)

    while True:
        schedule.run_pending()
        time.sleep(30)
