# Step 8: full mini-dashboard inside Telegram (free)

This adds a real, graphical dashboard that opens *inside* the Telegram app
when you tap a button — your live chart, temperature and humidity, no
separate browser needed. It builds on everything from `README-DHT22-PI.md`
(Steps 1-7 must already be working, especially Step 7, Tailscale).

## Why this needs one extra thing: HTTPS

Telegram only allows a bot button to open a page as a "mini app" (what
Telegram calls a **Web App**) if that page is served over **HTTPS**. Your
dashboard is currently `http://<pi-ip>:8000` — plain HTTP — so it won't work
for this specific feature (it's still fine for opening in a normal browser).

**Tailscale Serve** gives you a free HTTPS address for the Pi automatically,
no certificates to buy or configure. Run this once, on the Pi:

```
tailscale serve https / http://localhost:8000
```

Then check the address it's using:
```
tailscale serve status
```
It will show something like `https://raspberrypi.tailnet-name.ts.net`. That
full address is your `DASHBOARD_URL`.

This address only works for devices signed into your Tailscale account (your
phone needs the Tailscale app installed and signed in, same as Step 7) — which
is fine, since nobody else should see your room's data anyway.

## Files for this step

| File | What it does |
|---|---|
| `pi/telegram_bot.py` | **New.** Listens for you messaging the bot, replies with the "Open dashboard" button |
| `pi/templates/index.html` | **Updated.** Now tells Telegram "I'm ready" and uses the full screen when opened as a mini-app |
| `pi/telegram_report.py` | **Updated.** The daily/weekly report message now also has an "Open dashboard" button under it |

## Setup

1. Run the `tailscale serve` command above on the Pi.
2. Open `pi/telegram_bot.py`. Fill in:
   ```python
   TELEGRAM_BOT_TOKEN = "123456789:AAE..."     # same token from Step 5
   DASHBOARD_URL = "https://raspberrypi.tailnet-name.ts.net"   # from tailscale serve status
   ```
3. Open `pi/telegram_report.py` and set the same `DASHBOARD_URL` there too.
4. Make sure `pi/app.py` is still running (Step 4) — the mini-app loads that
   same website, just now also reachable over HTTPS through Tailscale Serve.
5. Start the bot, as its own process:
   ```
   cd pi
   python3 telegram_bot.py
   ```
   It prints: `Bot is running. Open Telegram and send /start to your bot.`

## Try it

1. Open Telegram on your phone, go to your bot's chat, send `/start`.
2. You get a message with one button: **Open dashboard**.
3. Tap it — your dashboard opens right inside Telegram (no browser, no new
   app), showing the live temperature, humidity, and chart, styled by your
   `index.html`.
4. Your daily/weekly report messages (Step 6) now also carry this same
   button underneath them, so you can jump straight from a report to the
   live chart.

## Keeping it all running

By the end of Step 8 you have **three** things that need to stay running on
the Pi at the same time:
```
python3 app.py              # the website + database + MQTT listener
python3 telegram_bot.py     # the /start button handler
```
(`telegram_report.py` doesn't stay running — it's only triggered by cron,
Step 6.)

Run each with `nohup ... &` as in Step 4, or ask me to set all of them up as
proper background services (`systemd`) that start automatically every time
the Pi boots — recommended once everything is tested and working.

## Troubleshooting

| Problem | Likely cause |
|---|---|
| Button does nothing when tapped | `DASHBOARD_URL` isn't HTTPS, or doesn't match what `tailscale serve status` shows |
| "Bot is running" but `/start` gets no reply | wrong `TELEGRAM_BOT_TOKEN` in `telegram_bot.py`, or `telegram_bot.py` isn't actually running |
| Dashboard opens but shows no data | `app.py` isn't running, or the ESP32 hasn't sent a reading recently |
| Works at home, not when you're out | your **phone's** Tailscale isn't turned on/signed in — `tailscale serve` addresses only work for devices on your tailnet |
