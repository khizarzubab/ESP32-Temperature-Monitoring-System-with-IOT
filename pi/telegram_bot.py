"""
STEP 8 — the Telegram bot that opens your dashboard as a mini-app inside Telegram.

Run this ALONGSIDE app.py (as a separate process). It listens for you sending
/start or /dashboard in Telegram, and replies with a button that opens your
website right inside the Telegram app.

Requires Step 7 (Tailscale) to already give the Pi an HTTPS address via
Tailscale Serve (see README-TELEGRAM-DASHBOARD.md for the one command needed).

Usage:  python3 telegram_bot.py
"""
import json
import time
import urllib.error
import urllib.request

TELEGRAM_BOT_TOKEN = ""                              # same token as in app.py
DASHBOARD_URL = "https://your-pi-name.your-tailnet.ts.net"   # the HTTPS address from `tailscale serve`

API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def api_call(method, payload):
    """Sends one request to the Telegram Bot API and returns the parsed JSON reply."""
    req = urllib.request.Request(
        f"{API}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.loads(resp.read())


def send_dashboard_button(chat_id):
    """Sends a message with one tappable button. Tapping it opens DASHBOARD_URL
    as a mini-app INSIDE Telegram, not in a separate browser."""
    api_call(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": "Tap below to open the live room dashboard.",
            "reply_markup": {
                "inline_keyboard": [[{"text": "Open dashboard", "web_app": {"url": DASHBOARD_URL}}]]
            },
        },
    )


def main():
    offset = 0   # tracks which messages we've already handled, so we don't repeat replies
    print("Bot is running. Open Telegram and send /start to your bot.")
    while True:
        try:
            # long polling: this call waits up to 30s for a new message, or
            # returns sooner if one arrives. offset=offset means "only give me
            # messages I haven't already seen."
            resp = api_call("getUpdates", {"offset": offset, "timeout": 30})
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"Network hiccup, retrying: {exc}")
            time.sleep(5)
            continue

        for update in resp.get("result", []):
            offset = update["update_id"] + 1   # move past this message so we don't see it again
            msg = update.get("message")
            if not msg or "text" not in msg:
                continue
            text = msg["text"]
            chat_id = msg["chat"]["id"]

            if text in ("/start", "/dashboard"):
                send_dashboard_button(chat_id)


if __name__ == "__main__":
    main()
