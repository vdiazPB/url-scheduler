from flask import Flask, jsonify, request, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler
import requests, time, threading
from datetime import datetime
import os

app = Flask(__name__)

# ── Location names and URLs ───────────────────────────────────────────
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

# ── Scheduler setup ──────────────────────────────────────────────────
auto_run_enabled = True
scheduled_hour, scheduled_minute = 4, 0
log = []
scheduler = BackgroundScheduler()
scheduler.start()

def trigger_urls():
    for idx, (_, url) in enumerate(URL_ENTRIES):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log.append(f"[{ts}] START {url}")
        try:
            r = requests.get(url, timeout=10)
            log.append(f"[{ts}] OK {url} → {r.status_code}")
        except Exception as e:
            log.append(f"[{ts}] ERR {url} → {e}")
        if idx < len(URL_ENTRIES) - 1:
            log.append(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Waiting 2 minutes…")
            time.sleep(120)
    log.append(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] ✅ All URLs completed")

def trigger_by_name(name):
    url = next((u for n, u in URL_ENTRIES if n == name), None)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not url:
        log.append(f"[{ts}] ❌ No match for {name}")
        return
    log.append(f"[{ts}] MANUAL {url}")
    try:
        r = requests.get(url, timeout=10)
        log.append(f"[{ts}] OK {url} → {r.status_code}")
    except Exception as e:
        log.append(f"[{ts}] ERR {url} → {e}")

# ── Flask Routes ─────────────────────────────────────────────────────
@app.route("/")
def index():
    options = ''.join(f'<option value="{name}">{name}</option>' for name, _ in URL_ENTRIES)
    weekdays = ''.join(f'<option value="{i}">{d}</option>' for i, d in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]))
    return render_template_string(TEMPLATE, loc_opts=options, day_opts=weekdays)

@app.route("/log")
def get_log(): return jsonify(log[-50:])

@app.route("/trigger", methods=["POST"])
def trigger_all(): threading.Thread(target=trigger_urls, daemon=True).start(); return "", 204

@app.route("/trigger-name/<name>", methods=["POST"])
def trigger_name(name):
    threading.Thread(target=trigger_by_name, args=(name,), daemon=True).start()
    return "", 204

@app.route("/toggle-auto", methods=["POST"])
def toggle_auto():
    global auto_run_enabled
    auto_run_enabled = not auto_run_enabled
    return jsonify(status=auto_run_enabled)

@app.route("/change-time", methods=["POST"])
def change_time():
    global scheduled_hour, scheduled_minute
    data = request.get_json()
    scheduled_hour = int(data["hour"])
    scheduled_minute = int(data["minute"])
    scheduler.reschedule_job("daily-run", trigger="cron", hour=scheduled_hour, minute=scheduled_minute)
    return jsonify(hour=scheduled_hour, minute=scheduled_minute)

@app.route("/schedule-one", methods=["POST"])
def schedule_one():
    data = request.get_json()
    name = data['name']
    weekday = int(data['weekday'])  # 0=Monday
    hour = int(data['hour'])
    ampm = data['ampm']
    if ampm == 'PM' and hour < 12: hour += 12
    if ampm == 'AM' and hour == 12: hour = 0
    job_id = f"job-{name.replace(' ', '_')}-{weekday}-{hour}"
    scheduler.add_job(lambda: trigger_by_name(name), 'cron', day_of_week=weekday, hour=hour, id=job_id, replace_existing=True)
    log.append(f"[Scheduler] ⏰ Scheduled {name} on {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][weekday]} at {hour:02d}:00")
    return '', 204

scheduler.add_job(lambda: trigger_urls() if auto_run_enabled else None, "cron", hour=scheduled_hour, minute=scheduled_minute, id="daily-run")

# ── HTML Template ─────────────────────────────────────────────────────
TEMPLATE = '''
<!DOCTYPE html><html><head><title>URL Scheduler</title>
<style>
 body { font-family: Arial; background: #f4f4f4; padding: 20px; }
 h2 { color: #333; }
 input, select, button { margin: 5px 5px 5px 0; padding: 5px; }
 button { background: #007bff; color: #fff; border: 0; border-radius: 5px; cursor: pointer; }
 button:hover { background: #0056b3; }
 pre { background: #222; color: #0f0; padding: 10px; border-radius: 5px; max-height: 300px; overflow-y: scroll; }
 .section { background: #fff; padding: 15px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,.1); }
 .switch { position: relative; display: inline-block; width: 60px; height: 34px; }
 .switch input { opacity: 0; width: 0; height: 0; }
 .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background: #ccc; transition: .4s; border-radius: 34px; }
 .slider:before { content: ''; position: absolute; height: 26px; width: 26px; left: 4px; bottom: 4px; background: #fff; transition: .4s; border-radius: 50%; }
 .switch input:checked + .slider { background: #28a745; }
 .switch input:checked + .slider:before { transform: translateX(26px); }
</style></head><body>
<h2>URL Scheduler Dashboard</h2>
<div class='section'>
  <p>⏰ <b>Auto-run Time:</b> change below:</p>
  <form onsubmit="event.preventDefault();setTime()">
    <input id='h' size='2' value='4'>
    <select id='ampm'><option>AM</option><option>PM</option></select>
    <button>Set Time</button>
  </form>
  <p><b>Auto Run Toggle:</b></p>
  <label class='switch'>
    <input type='checkbox' id='autoToggle' onchange="toggleAutoRun()">
    <span class='slider'></span>
  </label>
</div>
<div class='section'>
  <p>📍 <b>Trigger by Location:</b></p>
  <select id='loc'>{{ loc_opts | safe }}</select>
  <button onclick="triggerSingle()">Go</button>
</div>
<div class='section'>
  <p>🚀 <b>Run All URLs Now:</b></p>
  <button onclick="confirmRunAll()">Run</button>
</div>
<div class='section'>
  <p>🕒 <b>Schedule a Location by Weekday & Hour:</b></p>
  <form onsubmit="event.preventDefault(); scheduleOne()">
    <select id='day'>{{ day_opts | safe }}</select>
    <select id='locname'>{{ loc_opts | safe }}</select>
    <select id='hour'>
      {% for i in range(1,13) %}<option>{{ i }}</option>{% endfor %}
    </select>
    <select id='ampm2'><option>AM</option><option>PM</option></select>
    <button>Schedule</button>
  </form>
</div>
<div class='section'><h4>📜 Logs</h4><pre id='logbox'>Loading…</pre></div>
<script>
function refreshLog() {
  fetch('/log').then(r => r.json()).then(d => logbox.textContent = d.join('\n'));
}
setInterval(refreshLog, 5000); refreshLog();
function triggerSingle() {
  let n = loc.value;
  if (confirm('Run URL for ' + n + '?'))
    fetch('/trigger-name/' + encodeURIComponent(n), { method: 'POST' });
}
function confirmRunAll() {
  if (confirm('Run full URL sequence?')) fetch('/trigger', { method: 'POST' });
}
function toggleAutoRun() {
  fetch('/toggle-auto', { method: 'POST' })
    .then(r => r.json()).then(d => alert('Auto-run is now: ' + d.status));
}
function setTime() {
  let hVal = parseInt(h.value), ap = ampm.value;
  if (ap === 'PM' && hVal < 12) hVal += 12;
  if (ap === 'AM' && hVal === 12) hVal = 0;
  fetch('/change-time', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hour: hVal, minute: 0 })
  }).then(() => alert('Time updated'));
}
function scheduleOne() {
  let name = locname.value, weekday = day.value, hour = hour.value, ap = ampm2.value;
  fetch('/schedule-one', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: name, weekday: weekday, hour: hour, ampm: ap })
  }).then(() => alert('Schedule created'));
}
</script></body></html>
'''

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
