"""
STEP 6 — daily / weekly report.
Run this by hand to test it, then let cron run it automatically
(setup commands are in the README).

Usage:
  python3 telegram_report.py daily
  python3 telegram_report.py weekly
"""
import json
import os
import sqlite3
import sys
import time
import urllib.request

TELEGRAM_BOT_TOKEN = ""   # same token as in app.py and telegram_bot.py
TELEGRAM_CHAT_ID = ""     # same chat id as in app.py
DASHBOARD_URL = "https://your-pi-name.your-tailnet.ts.net"   # same HTTPS address as telegram_bot.py
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "temperature.db")


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        # adds a tappable button under the report that opens the live dashboard
        "reply_markup": {
            "inline_keyboard": [[{"text": "Open dashboard", "web_app": {"url": DASHBOARD_URL}}]]
        },
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10)


def build_report(hours, label):
    since = int(time.time()) - hours * 3600
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT temp_c, humidity FROM readings WHERE ts >= ?", (since,)
    ).fetchall()
    conn.close()

    if not rows:
        return f"{label} report: no readings recorded."

    temps = [r[0] for r in rows]
    hums = [r[1] for r in rows if r[1] is not None]

    lines = [
        f"{label} report ({len(temps)} readings)",
        f"Temp: min {min(temps):.1f}C, avg {sum(temps)/len(temps):.1f}C, max {max(temps):.1f}C",
    ]
    if hums:
        lines.append(f"Humidity: min {min(hums):.0f}%, avg {sum(hums)/len(hums):.0f}%, max {max(hums):.0f}%")
    return "\n".join(lines)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "daily"
    hours = 24 if which == "daily" else 24 * 7
    label = "Daily" if which == "daily" else "Weekly"
    message = build_report(hours, label)
    print(message)          # so you see it when testing by hand
    send_telegram(message)  # and so it also reaches your phone
