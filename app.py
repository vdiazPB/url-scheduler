from flask import Flask, jsonify, request, render_template
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
import requests, time, threading
from datetime import datetime
import os

app = Flask(__name__)
scheduler = BackgroundScheduler(timezone=timezone('US/Pacific'))
scheduler.start()

# Default scheduled time: 4:00 AM
auto_run_hour = 4
auto_run_minute = 0
auto_run_enabled = True

URL_ENTRIES = [
    ("Pinkbox Eastern",    "https://dev.apirequests.com/api/testing/revel?step=14&import=true&website_id=1616"),
    ("Pinkbox Lake Mead",  "https://dev.apirequests.com/api/testing/revel?step=14&import=true&website_id=1617"),
    ("Pinkbox Tropicana",  "https://dev.apirequests.com/api/testing/revel?step=14&import=true&website_id=1618"),
    ("Pinkbox Primm",      "https://dev.apirequests.com/api/testing/revel?step=14&import=true&website_id=1619"),
    ("Pinkbox Sunset",     "https://dev.apirequests.com/api/testing/revel?step=14&import=true&website_id=1620"),
    ("Pinkbox Bagelmania", "https://dev.apirequests.com/api/testing/revel?step=14&import=true&website_id=1621"),
    ("Pinkbox St George",  "https://dev.apirequests.com/api/testing/revel?step=14&import=true&website_id=1622"),
    ("Pinkbox Craig",      "https://dev.apirequests.com/api/testing/revel?step=14&import=true&website_id=1623"),
    ("Pinkbox Laughlin",   "https://dev.apirequests.com/api/testing/revel?step=14&import=true&website_id=1624"),
    ("Pinkbox Plaza",      "https://dev.apirequests.com/api/testing/revel?step=14&import=true&website_id=1625"),
    ("Pinkbox Pahrump",    "https://dev.apirequests.com/api/testing/revel?step=14&import=true&website_id=1636"),
    ("Pinkbox Centennial", "https://dev.apirequests.com/api/testing/revel?step=14&import=true&website_id=1675"),
    ("Pinkbox Boca Park",  "https://dev.apirequests.com/api/testing/revel?step=14&import=true&website_id=1708"),
]

log = []

def schedule_auto_trigger():
    if auto_run_enabled:
        scheduler.add_job(lambda: threading.Thread(target=trigger_urls).start(), CronTrigger(hour=auto_run_hour, minute=auto_run_minute), id="auto_trigger", replace_existing=True)
    else:
        try:
            scheduler.remove_job("auto_trigger")
        except:
            pass

schedule_auto_trigger()

def trigger_urls():
    for idx, (_, url) in enumerate(URL_ENTRIES):
        ts = datetime.now(timezone('US/Pacific')).strftime("%Y-%m-%d %H:%M:%S")
        log.append(f"[{ts}] START {url}")
        try:
            r = requests.get(url, timeout=10)
            log.append(f"[{ts}] OK {url} → {r.status_code}")
        except Exception as e:
            log.append(f"[{ts}] ERR {url} → {e}")
        if idx < len(URL_ENTRIES) - 1:
            log.append(f"[{datetime.now(timezone('US/Pacific')).strftime('%Y-%m-%d %H:%M:%S')}] Waiting 2 minutes...")
            time.sleep(120)
    log.append(f"[{datetime.now(timezone('US/Pacific')).strftime('%Y-%m-%d %H:%M:%S')}] ✅ All URLs completed")

def trigger_by_name(name):
    url = next((u for n, u in URL_ENTRIES if n == name), None)
    ts = datetime.now(timezone('US/Pacific')).strftime("%Y-%m-%d %H:%M:%S")
    if not url:
        log.append(f"[{ts}] ❌ No match for {name}")
        return
    log.append(f"[{ts}] MANUAL {url}")
    try:
        r = requests.get(url, timeout=10)
        log.append(f"[{ts}] OK {url} → {r.status_code}")
    except Exception as e:
        log.append(f"[{ts}] ERR {url} → {e}")

@app.route("/")
def index():
    options = [name for name, _ in URL_ENTRIES]
    current_time = f"{auto_run_hour % 12 or 12} {'AM' if auto_run_hour < 12 else 'PM'}"
    return render_template("index.html", loc_opts=options, current_time=current_time, auto_run_enabled=auto_run_enabled)

@app.route("/log")
def get_log():
    return jsonify(log[-50:])

@app.route("/trigger", methods=["POST"])
def trigger_all():
    threading.Thread(target=trigger_urls, daemon=True).start()
    return "", 204

@app.route("/trigger-name/<name>", methods=["POST"])
def trigger_name(name):
    threading.Thread(target=trigger_by_name, args=(name,), daemon=True).start()
    return "", 204

@app.route("/update-time", methods=["POST"])
def update_time():
    global auto_run_hour, auto_run_minute
    data = request.json
    hour = int(data['hour'])
    ampm = data['ampm']
    if ampm == 'PM' and hour != 12:
        hour += 12
    if ampm == 'AM' and hour == 12:
        hour = 0
    auto_run_hour = hour
    auto_run_minute = 0
    schedule_auto_trigger()
    log.append(f"[SYSTEM] ♻ Auto-run time updated to {auto_run_hour:02d}:00")
    return '', 204

@app.route("/toggle-auto", methods=["POST"])
def toggle_auto():
    global auto_run_enabled
    auto_run_enabled = request.json.get("enabled", True)
    schedule_auto_trigger()
    state = "enabled" if auto_run_enabled else "disabled"
    log.append(f"[SYSTEM] ⚠ Auto-run {state}")
    return '', 204

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
