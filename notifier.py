"""
Notifier: Sends Telegram messages (and optionally email)
for new CSE/IT Lecturer job postings.
"""

import json
import os
import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")


def send_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] Credentials missing, skipping.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        print("[Telegram] Message sent!")
    except Exception as e:
        print(f"[Telegram] Error: {e}")


def format_job(job: dict) -> str:
    return (
        f"🎓 <b>New Lecturer Job Found!</b>\n\n"
        f"📌 <b>{job['title']}</b>\n"
        f"🏫 {job['institution']}\n"
        f"🌐 Source: {job['source']}\n"
        f"🔗 <a href='{job['url']}'>View Circular</a>\n"
        f"🕒 Found: {job['found_at'][:10]}"
    )


def notify_all(jobs: list):
    if not jobs:
        print("No new jobs to notify.")
        return

    print(f"📬 Sending {len(jobs)} notification(s)...")
    for job in jobs:
        msg = format_job(job)
        send_telegram(msg)


def main():
    try:
        with open("new_jobs.json", "r", encoding="utf-8") as f:
            jobs = json.load(f)
    except FileNotFoundError:
        print("new_jobs.json not found.")
        return

    notify_all(jobs)

    # Send a summary if many jobs found
    if len(jobs) >= 3:
        summary = (
            f"📊 <b>Summary:</b> {len(jobs)} new CSE/IT Lecturer "
            f"postings found today! Check your dashboard for details."
        )
        send_telegram(summary)


if __name__ == "__main__":
    main()
