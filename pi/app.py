"""
STEP 4 — the Pi-side program.
Subscribes to Mosquitto, saves every reading to a database file, sends
Telegram alerts, and serves the website.

Run it with:   python3 app.py
Website then opens at:  http://<pi-ip>:8000   (or http://localhost:8000 on the Pi itself)
"""
import json
import os
import sqlite3
import time
import urllib.request
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from flask import Flask, jsonify, render_template, request

# ---------------------------------------------------------------- settings
MQTT_HOST = "localhost"            # Mosquitto runs on this same Pi
MQTT_PORT = 1883
MQTT_TOPIC = "home/+/temperature"  # the + means "any room"

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "temperature.db")
OFFLINE_AFTER_S = 45 * 60          # mark "offline" if nothing arrives for 45 min

# Telegram: fill these in during Step 5. Leave empty for now and alerts are
# simply skipped (everything else still works).
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""
TEMP_HIGH_ALERT = 32.0             # send a message if temperature goes above this
TEMP_LOW_ALERT = 10.0              # ...or below this

app = Flask(__name__)
_last_alert_state = "normal"       # remembers if we already warned, so we don't spam


# ---------------------------------------------------------------- database
def db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row   # lets us read columns by name, e.g. row["temp_c"]
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS readings (
                   id       INTEGER PRIMARY KEY AUTOINCREMENT,
                   device   TEXT    NOT NULL,
                   ts       INTEGER NOT NULL,
                   temp_c   REAL    NOT NULL,
                   humidity REAL,
                   rssi     INTEGER,
                   UNIQUE(device, ts)
               )"""
        )


# ---------------------------------------------------------------- telegram
def send_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return   # not configured yet, do nothing
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": text}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as exc:
        print(f"[telegram] failed to send: {exc}")


def check_alert(temp):
    """Sends a message only when the state CHANGES, so you get one alert,
    not one every 30 minutes while it stays hot."""
    global _last_alert_state
    if temp > TEMP_HIGH_ALERT:
        state = "high"
    elif temp < TEMP_LOW_ALERT:
        state = "low"
    else:
        state = "normal"

    if state != _last_alert_state:
        if state == "high":
            send_telegram(f"Room is warm: {temp:.1f}C (above {TEMP_HIGH_ALERT}C)")
        elif state == "low":
            send_telegram(f"Room is cold: {temp:.1f}C (below {TEMP_LOW_ALERT}C)")
        elif _last_alert_state != "normal":
            send_telegram(f"Room temperature is back to normal: {temp:.1f}C")
        _last_alert_state = state


# ---------------------------------------------------------------- MQTT
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"[mqtt] connected: {reason_code}")
    client.subscribe(MQTT_TOPIC, qos=1)


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        temp = float(data["temp_c"])
        hum = data.get("humidity")
        device = str(data.get("device") or msg.topic.split("/")[1])

        if not -50 <= temp <= 100:    # sanity check: ignore obviously broken readings
            return

        with db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO readings(device, ts, temp_c, humidity, rssi) VALUES (?,?,?,?,?)",
                (device, int(time.time()), temp, hum, data.get("rssi")),
            )
        print(f"[mqtt] {device} {temp:.1f}C {hum}%")
        check_alert(temp)
    except Exception as exc:
        print(f"[mqtt] ignored bad message: {exc}")


def start_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="pi-webapp")
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=60)   # retries forever if Mosquitto restarts
    client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()    # runs on its own background thread


# ---------------------------------------------------------------- web pages
@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/latest")
def api_latest():
    with db() as conn:
        row = conn.execute("SELECT * FROM readings ORDER BY ts DESC LIMIT 1").fetchone()
    if not row:
        return jsonify(empty=True)
    age = int(time.time()) - row["ts"]
    return jsonify(
        empty=False,
        device=row["device"],
        temp_c=row["temp_c"],
        humidity=row["humidity"],
        ts=row["ts"],
        online=age <= OFFLINE_AFTER_S,
    )


@app.get("/api/history")
def api_history():
    hours = request.args.get("hours", default=24, type=int)
    since = int(time.time()) - hours * 3600
    with db() as conn:
        rows = conn.execute(
            "SELECT ts, temp_c, humidity FROM readings WHERE ts>=? ORDER BY ts", (since,)
        ).fetchall()
    return jsonify(points=[[r["ts"], r["temp_c"], r["humidity"]] for r in rows])


init_db()
start_mqtt()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
