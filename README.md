# ESP32 + DHT22 + Raspberry Pi 

This is the exact order to build and test this version of the project: ESP32 with a
DHT22 sensor, a Raspberry Pi running Mosquitto (MQTT broker) + the website,
Telegram alerts and reports, and Tailscale for access from anywhere. Everything
used here is free.


---

## Wire the sensor and run `esp32_dht22_test.ino`

**Wiring:**
```
DHT22 VCC  -> ESP32 3V3
DHT22 DATA -> ESP32 GPIO 15   (+ 10k resistor between DATA and 3V3)
DHT22 GND  -> ESP32 GND
```

**Why this file first:** it only reads the sensor and prints to Serial — no WiFi,
no MQTT. If something's wrong with the wiring, this is the easiest place to
catch it, rather than debugging wiring and networking at the same time.

Open `firmware/esp32_dht22_test/esp32_dht22_test.ino` in Arduino IDE, select
board **ESP32 Dev Module**, pick the right Port, Upload. Open Serial Monitor at
115200 baud.

**Expected result:** a new line every 2 seconds, like:
```
Temperature: 27.40 C   Humidity: 54.10 %
```
If you see `Failed to read from DHT22 sensor` repeatedly, check the wiring
(especially the 10k resistor) before continuing.

---

## Install Mosquitto on the Raspberry Pi

On the Pi (via keyboard+screen, or SSH):
```
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable mosquitto --now
hostname -I
```
Write down the IP address `hostname -I` prints (e.g. `192.168.1.50`) — you need
it in Step 3.

**Test the broker works**, in two terminals on the Pi:
```
# terminal 1
mosquitto_sub -h localhost -t test -v
# terminal 2
mosquitto_pub -h localhost -t test -m "hello"
```
If terminal 1 prints `test hello`, the broker is working. Stop both with Ctrl+C.

---

## Flash `esp32_dht22_mqtt.ino`

Open `firmware/esp32_dht22_mqtt/esp32_dht22_mqtt.ino`. Edit the settings block
at the top:

| Setting | Value |
|---|---|
| `WIFI_SSID` / `WIFI_PASS` | your home WiFi name/password |
| `MQTT_HOST` | the Pi's IP from Step 2, e.g. `"192.168.1.50"` |
| `SLEEP_MINUTES` | `1` while testing, change to `30` once everything works |

Upload it (same board/port as Step 1). Open Serial Monitor — you should see:
```
Temp: 27.4 C  Humidity: 54.1 %
WiFi connected
{"device":"esp32-room1","temp_c":27.40,"humidity":54.10,"rssi":-58}
Sleeping...
```

**Confirm the Pi is receiving it** — on the Pi:
```
mosquitto_sub -h localhost -t "home/#" -v
```
A new JSON line should appear every cycle (every 1 minute, while testing).

---

## Run `app.py` + `templates/index.html`: store and show the data

Copy the whole `pi/` folder onto the Raspberry Pi (USB stick, `scp`, or just
recreate the files there).

Install the Python packages:
```
cd pi
pip3 install -r requirements.txt
```

Run it:
```
python3 app.py
```
You should see in the terminal:
```
[mqtt] connected: Success
[mqtt] esp32-room1 27.4C 54.1%
```
Open `http://<pi-ip>:8000` from your laptop or phone (same WiFi as the Pi) —
you should see the live temperature, humidity, and a chart filling in over
time.

Leave this running. To keep it running after you close the terminal, use:
```
nohup python3 app.py > app.log 2>&1 &
```
(or set it up as a proper background service later — ask me if you want that).

---

## Telegram bot (get two values, no file to write)

1. In Telegram, search for **@BotFather**, send it `/newbot`, follow the
   prompts (pick a name). It replies with a **bot token**, looking like
   `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`.
2. Send your new bot any message (e.g. "hi"), then open this URL in any
   browser, with your token pasted in:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. In the reply, find `"chat":{"id":123456789,` — that number is your
   **chat ID**.
4. Open `pi/app.py` and `pi/telegram_report.py`, and in **both** files set:
   ```python
   TELEGRAM_BOT_TOKEN = "123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
   TELEGRAM_CHAT_ID = "123456789"
   ```
5. Stop `app.py` (Ctrl+C) and start it again so it picks up the new values.
6. Test it: warm the DHT22 with your hand/breath until the temperature passes
   32°C (`TEMP_HIGH_ALERT` in `app.py`) — you should get a Telegram message
   within one sensor cycle.

---

## Run `telegram_report.py`: daily and weekly summaries

Test it by hand first, on the Pi:
```
cd pi
python3 telegram_report.py daily
```
You should see the summary printed in the terminal **and** receive it on
Telegram.

Once that works, schedule it with cron so it runs automatically:
```
crontab -e
```
Add these two lines at the bottom (adjust the path to wherever you placed the
`pi` folder on the Pi):
```
0 8 * * *   cd /home/pi/esp32-temp-monitor/pi && python3 telegram_report.py daily
0 8 * * 1   cd /home/pi/esp32-temp-monitor/pi && python3 telegram_report.py weekly
```
This runs the daily report at 8 AM every day, and the weekly report at 8 AM
every Monday.

---

## Tailscale: access the website and broker from anywhere

Install Tailscale on the Pi, your phone, and your laptop, signing into the
**same account** on all three (free).

On the Pi:
```
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```
Follow the link it prints to log in. Once connected, run:
```
tailscale ip -4
```
This gives the Pi a private address like `100.x.x.x`, reachable from your
phone or laptop's Tailscale app from anywhere with internet — not just your
home WiFi. Open `http://100.x.x.x:8000` to see the website remotely.

---

## Final checklist

- [ ] Step 1: Serial Monitor shows real temperature/humidity, not "Failed to read"
- [ ] Step 2: `mosquitto_pub`/`mosquitto_sub` test works on the Pi
- [ ] Step 3: Serial Monitor shows "WiFi connected" and the JSON being sent; `mosquitto_sub -t "home/#"` on the Pi shows it arriving
- [ ] Step 4: website at `http://<pi-ip>:8000` shows the live reading and a growing chart
- [ ] Step 5: a test alert message arrives on Telegram
- [ ] Step 6: `python3 telegram_report.py daily` sends a working summary
- [ ] Step 7: website opens from outside your home WiFi via the Tailscale address
- [ ] `SLEEP_MINUTES` changed back to `30` once everything is confirmed working

## Troubleshooting

| Problem | Likely cause |
|---|---|
| "Failed to read from DHT22 sensor" | check wiring, especially the 10k pull-up resistor; DHT22 needs ~2s between reads |
| `WiFi FAILED` | wrong SSID/password; ESP32 only works on 2.4 GHz WiFi, not 5 GHz |
| MQTT `state=-2` on the ESP32 | wrong `MQTT_HOST` IP, Mosquitto not running, or ESP32/Pi on different networks |
| Website shows nothing | check the Pi terminal for `[mqtt] connected: Success`; if missing, Mosquitto might not be running (`sudo systemctl status mosquitto`) |
| No Telegram message | double check the token/chat ID were pasted into **both** `app.py` and `telegram_report.py`, and that `app.py` was restarted after editing |
| Pi's IP changed | reserve a fixed IP for the Pi in your router's DHCP settings so `MQTT_HOST` in the firmware doesn't go stale |

