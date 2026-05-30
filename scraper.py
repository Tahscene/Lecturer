"""
BD CSE Lecturer Tracker — RSS Only (No API Key Needed)
Sources: BDJobs RSS + Google News RSS
These are plain XML — never blocked by GitHub Actions.
"""
import requests, json, os, hashlib, re, time
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

DATA_FILE = "docs/jobs.json"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT  = os.environ.get("TELEGRAM_CHAT_ID", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

# ── ONLY these words count as a lecturer position ────────────────────────────
LECTURER_WORDS = ["lecturer", "senior lecturer", "লেকচারার"]

# ── ONLY these count as CSE/IT ───────────────────────────────────────────────
CSE_WORDS = [
    "computer science", "computer engineering",
    "cse", "information technology", "software engineering",
    "ict", "computing", "it department", "কম্পিউটার"
]

# ── Hard reject — these are never job ads ────────────────────────────────────
REJECT = [
    "professor", "associate prof", "assistant prof",
    "faculty members", "faculty list", "faculty of ",
    "department of", "dept of", "b.sc in", "m.sc in",
    "admission", "scholarship", "result", "exam", "seminar",
    "india", "united states", "uk ", "australia", "canada",
    "lakhimpur", "mppsc", "appsc", "jpsc", "uppsc",  # Indian job boards
    "trinity college", "university of cincinnati", "boston university",
    "anna university", "uc san diego",  # foreign unis
]

RSS_FEEDS = [
    # BDJobs Education category + lecturer keyword
    "https://jobs.bdjobs.com/rss/rss.asp?fcat=10&txtsearch=lecturer",
    "https://jobs.bdjobs.com/rss/rss.asp?fcat=10&txtsearch=senior+lecturer",
    # Google News — BD specific
    "https://news.google.com/rss/search?q=lecturer+CSE+university+Bangladesh+circular+2026&hl=en-BD&gl=BD&ceid=BD:en",
    "https://news.google.com/rss/search?q=lecturer+%22computer+science%22+Bangladesh+university+circular&hl=en-BD&gl=BD&ceid=BD:en",
    "https://news.google.com/rss/search?q=lecturer+%22information+technology%22+Bangladesh+university+2026&hl=en-BD&gl=BD&ceid=BD:en",
    "https://news.google.com/rss/search?q=CSE+lecturer+job+circular+Bangladesh+2026&hl=en-BD&gl=BD&ceid=BD:en",
    # Financial Express BD — they post university job ads
    "https://thefinancialexpress.com.bd/rss/jobs",
]

BD_DOMAINS = [
    ".bd/", "bdjobs.com", "thefinancialexpress.com.bd",
    "thedailystar.net", "tbsnews.net", "newagebd.net",
    "bdnews24.com", "dhakatribune.com", "prothomalo.com",
]

def is_bd(url):
    return any(d in url.lower() for d in BD_DOMAINS)

def is_lecturer(text):
    t = text.lower()
    return any(w in t for w in LECTURER_WORDS)

def is_cse(text):
    t = text.lower()
    return any(w in t for w in CSE_WORDS)

def is_rejected(text):
    t = text.lower()
    return any(r in t for r in REJECT)

def is_valid(title, desc="", url=""):
    combined = f"{title} {desc}".lower()
    if is_rejected(combined): return False
    if not is_lecturer(combined): return False
    if not is_cse(combined): return False
    # For Google News results, must be from BD source
    if "news.google.com" in url or "google.com" in url:
        return True  # Google already filtered by ceid=BD:en
    return True

def make_id(title, url):
    return hashlib.md5(f"{title.lower()[:50]}{url[:30]}".encode()).hexdigest()[:12]

def parse_date(raw):
    try:
        return parsedate_to_datetime(raw).isoformat()
    except:
        return datetime.now(timezone.utc).isoformat()

def is_recent(iso, days=45):
    try:
        dt = datetime.fromisoformat(iso.replace("Z","+00:00"))
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return (now - dt).days <= days
    except:
        return True

def fetch_rss(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return ET.fromstring(r.content)
        print(f"  HTTP {r.status_code} ← {url[:55]}")
    except Exception as e:
        print(f"  ERR ← {url[:55]} | {e}")
    return None

def source_name(url):
    if "bdjobs.com" in url:             return "BDJobs"
    if "thefinancialexpress" in url:    return "Financial Express"
    if "thedailystar" in url:           return "The Daily Star"
    if "tbsnews" in url:                return "TBS News"
    if "newagebd" in url:               return "New Age"
    if "bdnews24" in url:               return "BD News 24"
    if "dhakatribune" in url:           return "Dhaka Tribune"
    if "bracu.ac.bd" in url:            return "BRAC University"
    if "northsouth.edu" in url:         return "North South University"
    if "uiu.ac.bd" in url:              return "UIU"
    if "aiub.edu" in url:               return "AIUB"
    if "ewubd.edu" in url:              return "East West University"
    if "iub.edu.bd" in url:             return "IUB"
    if "aust.edu" in url:               return "AUST"
    if "daffodilvarsity" in url:        return "Daffodil University"
    return "Web"

def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"jobs": [], "last_updated": ""}

def save(data):
    os.makedirs("docs", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT: return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": False},
            timeout=10
        )
    except: pass

def main():
    print("\n🔍 BD CSE Lecturer Tracker — RSS Mode (No API Key)")
    print("=" * 52)

    found, seen = [], set()

    for feed_url in RSS_FEEDS:
        print(f"\n📡 {feed_url[:60]}")
        root = fetch_rss(feed_url)
        if root is None: continue

        items = root.findall(".//item")
        print(f"   {len(items)} items in feed")

        for item in items:
            title = (item.findtext("title") or "").strip()
            link  = (item.findtext("link")  or "").strip()
            desc  = BeautifulSoup(item.findtext("description") or "", "lxml").get_text(" ")
            pub   = item.findtext("pubDate") or ""

            if not title or not link or link in seen:
                continue

            # Clean Google News title (removes " - Source Name" suffix)
            clean_title = re.sub(r"\s*-\s*[^-]{3,40}$", "", title).strip()

            combined = f"{clean_title} {desc}"

            if not is_valid(clean_title, desc, link):
                print(f"   ✗ {clean_title[:60]}")
                continue

            found_at = parse_date(pub)
            if not is_recent(found_at):
                print(f"   ⏭ OLD: {clean_title[:50]}")
                continue

            seen.add(link)
            src = source_name(link)

            # Try to extract deadline from description
            deadline = ""
            m = re.search(
                r"(deadline|last date|apply by|application deadline)[:\s]+([A-Za-z]+ \d{1,2},?\s*\d{4}|\d{1,2}[\s\-][A-Za-z]+[\s\-]\d{4})",
                combined, re.I
            )
            if m: deadline = m.group(2).strip()

            print(f"   ✅ {clean_title[:60]}")
            found.append({
                "id":          make_id(clean_title, link),
                "title":       clean_title,
                "institution": src,
                "source":      src,
                "url":         link,
                "deadline":    deadline,
                "found_at":    found_at,
                "notified":    False,
            })
        time.sleep(0.5)

    print(f"\n📋 Total valid jobs: {len(found)}")

    # Merge
    existing = load_existing()
    existing["jobs"] = [j for j in existing["jobs"] if is_recent(j.get("found_at",""))]
    exist_ids  = {j["id"] for j in existing["jobs"]}
    exist_urls = {j["url"] for j in existing["jobs"]}

    added = []
    for job in found:
        if job["id"] not in exist_ids and job["url"] not in exist_urls:
            existing["jobs"].insert(0, job)
            added.append(job)
            exist_ids.add(job["id"])
            exist_urls.add(job["url"])

    existing["last_updated"] = datetime.now(timezone.utc).isoformat()
    existing["jobs"] = existing["jobs"][:300]
    save(existing)

    with open("new_jobs.json","w",encoding="utf-8") as f:
        json.dump(added, f, ensure_ascii=False, indent=2)

    print(f"✅ New: {len(added)} | Total stored: {len(existing['jobs'])}")

    for job in added:
        dl  = f"\n⏰ <b>Deadline:</b> {job['deadline']}" if job.get("deadline") else ""
        msg = (f"🎓 <b>New CSE/IT Lecturer Job!</b>\n\n"
               f"📌 <b>{job['title']}</b>\n"
               f"🏫 {job['institution']}{dl}\n"
               f"🔗 <a href='{job['url']}'>View Circular →</a>")
        send_telegram(msg)
        time.sleep(0.8)

    if len(added) >= 3:
        send_telegram(f"📊 <b>{len(added)} new CSE/IT Lecturer jobs found!</b> Check your dashboard 🎉")

if __name__ == "__main__":
    main()
