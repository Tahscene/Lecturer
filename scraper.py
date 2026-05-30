"""
BD CSE Lecturer Job Tracker — Serper.dev Free API Version
Serper.dev: 2500 free searches/month, no credit card needed
Sign up: serper.dev → Get API Key (free)
Add to GitHub Secrets: SERPER_API_KEY
"""

import requests, json, os, hashlib, re, time
from datetime import datetime, timezone, timedelta

SERPER_KEY     = os.environ.get("SERPER_API_KEY", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT  = os.environ.get("TELEGRAM_CHAT_ID", "")
DATA_FILE      = "docs/jobs.json"

SEARCHES = [
    "lecturer CSE computer science Bangladesh university job circular 2026 deadline",
    "lecturer information technology IT Bangladesh university circular 2026",
    "BRAC NSU AIUB UIU EWU lecturer CSE job circular 2026",
    "site:bdjobs.com lecturer CSE OR \"computer science\" Bangladesh 2026",
    "site:thefinancialexpress.com lecturer CSE university Bangladesh 2026",
    "site:thedailystar.net lecturer CSE university Bangladesh 2026",
]

LECTURER_KW = ["lecturer", "senior lecturer", "লেকচারার"]
CSE_KW = ["computer science", "cse", "information technology", " it ",
          "software engineering", "computing", "ict", "কম্পিউটার"]
REJECT = ["professor", "india", "admission", "result", "scholarship",
          "united states", "uk ", "australia", "canada"]


def is_valid(text):
    t = text.lower()
    if any(r in t for r in REJECT): return False
    return any(l in t for l in LECTURER_KW) and any(c in t for c in CSE_KW)


def make_id(url):
    return hashlib.md5(url.encode()).hexdigest()[:12]


def google_search(query):
    """Search Google via Serper.dev API — free 2500/month."""
    if not SERPER_KEY:
        print("  ❌ No SERPER_API_KEY — add it to GitHub Secrets")
        return []
    try:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
            json={"q": query, "gl": "bd", "hl": "en", "num": 10},
            timeout=15
        )
        if r.status_code != 200:
            print(f"  ❌ Serper error: {r.status_code}")
            return []
        data = r.json()
        results = data.get("organic", [])
        print(f"  ✅ {len(results)} results")
        return results
    except Exception as e:
        print(f"  ❌ {e}")
        return []


def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"jobs": [], "last_updated": ""}


def save_data(data):
    os.makedirs("docs", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": False},
            timeout=10
        )
    except Exception:
        pass


def main():
    print("\n🔍 BD CSE Lecturer Tracker — Serper.dev Free Search")
    print("=" * 52)

    all_found = []
    seen_urls = set()

    for i, q in enumerate(SEARCHES, 1):
        print(f"\n[{i}/{len(SEARCHES)}] {q[:55]}...")
        results = google_search(q)

        for item in results:
            title   = item.get("title", "").strip()
            url     = item.get("link", "").strip()
            snippet = item.get("snippet", "").strip()
            combined = f"{title} {snippet}"

            if not url or url in seen_urls:
                continue
            if not is_valid(combined):
                continue

            # Extract deadline from snippet
            deadline = ""
            dl_match = re.search(
                r"(deadline|last date|apply by)[:\s]*([A-Za-z]+ \d{1,2},?\s*\d{4}|\d{1,2} [A-Za-z]+ \d{4}|\d{1,2}/\d{1,2}/\d{4})",
                snippet, re.I
            )
            if dl_match:
                deadline = dl_match.group(2).strip()

            # Determine source
            source = "Web"
            if "bdjobs.com" in url:    source = "BDJobs"
            elif "bracu.ac.bd" in url: source = "BRAC University"
            elif "northsouth.edu" in url: source = "North South University"
            elif "aiub.edu" in url:    source = "AIUB"
            elif "uiu.ac.bd" in url:   source = "UIU"
            elif "ewubd.edu" in url:   source = "East West University"
            elif "thefinancialexpress.com" in url: source = "Financial Express"
            elif "thedailystar.net" in url: source = "The Daily Star"

            # Institution from title/snippet
            inst = source
            for uni in ["BRAC", "North South", "NSU", "AIUB", "UIU", "EWU",
                        "IUB", "AUST", "DIU", "Daffodil", "Stamford", "BUET",
                        "CUET", "RUET", "Dhaka University"]:
                if uni.lower() in combined.lower():
                    inst = uni
                    break

            seen_urls.add(url)
            all_found.append({
                "id":          make_id(url),
                "title":       title,
                "institution": inst,
                "source":      source,
                "url":         url,
                "deadline":    deadline,
                "snippet":     snippet[:150],
                "found_at":    datetime.now(timezone.utc).isoformat(),
                "notified":    False,
            })

        time.sleep(1)   # be gentle with the API

    print(f"\n📋 Found: {len(all_found)} relevant results")

    # Merge with existing, remove >45 day old jobs
    existing = load_existing()
    cutoff = datetime.now(timezone.utc) - timedelta(days=45)
    existing["jobs"] = [
        j for j in existing["jobs"]
        if datetime.fromisoformat(
            j.get("found_at", "2000-01-01").replace("Z", "+00:00")
        ).replace(tzinfo=timezone.utc) > cutoff
    ]

    existing_ids  = {j["id"] for j in existing["jobs"]}
    existing_urls = {j["url"] for j in existing["jobs"]}

    added = []
    for job in all_found:
        if job["id"] not in existing_ids and job["url"] not in existing_urls:
            existing["jobs"].insert(0, job)
            added.append(job)
            existing_ids.add(job["id"])
            existing_urls.add(job["url"])

    existing["last_updated"] = datetime.now(timezone.utc).isoformat()
    existing["jobs"] = existing["jobs"][:300]
    save_data(existing)

    with open("new_jobs.json", "w", encoding="utf-8") as f:
        json.dump(added, f, ensure_ascii=False, indent=2)

    print(f"✅ New: {len(added)} | Stored: {len(existing['jobs'])}")

    # Telegram notifications
    for job in added:
        dl  = f"\n⏰ <b>Deadline:</b> {job['deadline']}" if job.get("deadline") else ""
        msg = (f"🎓 <b>New CSE/IT Lecturer Job!</b>\n\n"
               f"📌 <b>{job['title']}</b>\n"
               f"🏫 {job['institution']}\n"
               f"🌐 {job['source']}{dl}\n"
               f"🔗 <a href='{job['url']}'>View Circular →</a>")
        send_telegram(msg)
        time.sleep(0.8)

    if len(added) >= 3:
        send_telegram(f"📊 <b>Summary:</b> {len(added)} new CSE/IT Lecturer jobs found! 🎉")


if __name__ == "__main__":
    main()
