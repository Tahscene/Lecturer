"""
Notifier — sends Telegram alert for every new CSE/IT Lecturer job
"""
import json, os, requests, time
from datetime import datetime

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN","")
CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID","")

def send(text):
    if not BOT_TOKEN or not CHAT_ID: return False
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id":CHAT_ID,"text":text,"parse_mode":"HTML","disable_web_page_preview":False},
        timeout=10
    )
    return r.status_code == 200

def fmt(job):
    dl = f"\n⏰ <b>Deadline:</b> {job['deadline']}" if job.get("deadline") else ""
    return (
        f"🎓 <b>New CSE/IT Lecturer Job!</b>\n\n"
        f"📌 <b>{job['title']}</b>\n"
        f"🏫 {job['institution']}\n"
        f"🌐 {job['source']}"
        f"{dl}\n"
        f"🔗 <a href='{job['url']}'>View Circular →</a>"
    )

def main():
    try:
        with open("new_jobs.json",encoding="utf-8") as f:
            jobs = json.load(f)
    except FileNotFoundError:
        print("new_jobs.json not found"); return

    if not jobs:
        print("No new jobs to notify."); return

    print(f"📬 Sending {len(jobs)} alert(s)...")
    sent = 0
    for job in jobs:
        if send(fmt(job)):
            sent += 1
        time.sleep(0.8)

    print(f"✅ {sent}/{len(jobs)} sent")

    if len(jobs) >= 3:
        send(f"📊 <b>Summary:</b> {len(jobs)} new CSE/IT Lecturer circulars found!\nCheck your dashboard 🎉")

if __name__ == "__main__":
    main()
