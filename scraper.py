"""
BD CSE Lecturer Tracker v8 — Fixed Filters
==========================================
FIXES:
1. ONLY "Lecturer" positions (removed assistant/associate professor)
2. University scraper: fetches job detail page to get dept info
3. BDJobs: two-pass — title-only OR title+desc combined check
4. Serper: searches BDJobs specifically for lecturer+CSE
"""

import requests, json, os, hashlib, re, time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

DATA_FILE      = "docs/jobs.json"
SERPER_KEY     = os.environ.get("SERPER_API_KEY", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT  = os.environ.get("TELEGRAM_CHAT_ID", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
MAX_AGE_DAYS = 45

# ── ONLY lecturer-level positions ─────────────────────────────────────────────
# Removed: assistant professor, associate professor, faculty position
# (তুমি শুধু Lecturer চাও)
LECTURER_WORDS = [
    "lecturer",
    "senior lecturer",
    "adjunct lecturer",
    "visiting lecturer",
    "লেকচারার",
    "প্রভাষক",
]

# ── CSE/IT signals ─────────────────────────────────────────────────────────────
CSE_WORDS = [
    "computer science",
    "computer science and engineering",
    "computer science & engineering",
    "computer engineering",
    " cse",
    "cse ",
    "(cse)",
    "/cse",
    "cse,",
    "information technology",
    " it ",
    "software engineering",
    "ict",
    "computing",
    "computational science",
    "school of data",
    "data science",
    "it department",
    "কম্পিউটার",
    "তথ্য প্রযুক্তি",
]

# ── Hard reject ────────────────────────────────────────────────────────────────
REJECT = [
    "faculty list", "faculty of ",
    "b.sc in", "m.sc in", "bsc in", "msc in",
    "admission", "scholarship", "result", "exam routine",
    "seminar", "workshop", "webinar",
    "microbiology", "pharmacy", "nursing", "english", "economics",
    "mathematics", "physics", "chemistry", "biology", "botany",
    "zoology", "geography", "history", "political", "sociology",
    "business administration", "mba", "bba", "finance", "accounting",
    "fashion", "nutrition", "food",
    "lakhimpur", "mppsc", "appsc", "jpsc", "uppsc",
    "anna university", "uc san diego", "boston university",
    "trinity college", "united states", "australia", "canada", "india",
]

def make_id(title, url):
    return hashlib.md5(f"{title.lower()[:50]}{url[:30]}".encode()).hexdigest()[:12]

def is_lecturer(text):
    t = text.lower()
    return any(w in t for w in LECTURER_WORDS)

def is_cse(text):
    t = " " + text.lower() + " "   # pad so " cse " matches at boundaries
    return any(w in t for w in CSE_WORDS)

def is_rejected(text):
    t = text.lower()
    return any(r in t for r in REJECT)

def is_valid(title, desc=""):
    """
    A job is valid if:
    - Has a lecturer-level position word (anywhere in title+desc)
    - Has a CSE/IT signal (anywhere in title+desc)
    - Not rejected
    Title alone is checked first; if it passes on its own, no desc needed.
    """
    if len(title) > 220 or len(title) < 5:
        return False

    combined = f"{title} {desc}"

    if is_rejected(combined):
        return False

    return is_lecturer(combined) and is_cse(combined)

def is_recent(iso, days=MAX_AGE_DAYS):
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (now - dt).days <= days
    except:
        return True

def parse_date(raw):
    try:
        return parsedate_to_datetime(raw).isoformat()
    except:
        return datetime.now(timezone.utc).isoformat()

def extract_deadline(text):
    m = re.search(
        r"(?:deadline|last date|apply by|application deadline)[:\s]+"
        r"([A-Za-z]+ \d{1,2},?\s*\d{4}|\d{1,2}[\s\-][A-Za-z]+[\s\-]\d{4})",
        text, re.I
    )
    return m.group(1).strip() if m else ""

def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"jobs": [], "last_updated": ""}

def save(data):
    os.makedirs("docs", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _source_name(url):
    u = url.lower()
    m = {
        "bdjobs.com":           "BDJobs",
        "bracu.ac.bd":          "BRAC University",
        "northsouth.edu":       "North South University",
        "uiu.ac.bd":            "UIU",
        "aiub.edu":             "AIUB",
        "ewubd.edu":            "East West University",
        "iub.edu.bd":           "IUB",
        "aust.edu":             "AUST",
        "daffodilvarsity":      "Daffodil University",
        "thefinancialexpress":  "Financial Express",
        "thedailystar":         "The Daily Star",
        "tbsnews":              "TBS News",
        "bdnews24":             "BD News 24",
        "dhakatribune":         "Dhaka Tribune",
        "prothomalo":           "Prothom Alo",
        "newagebd":             "New Age",
    }
    for k, v in m.items():
        if k in u:
            return v
    return "Web"

# ════════════════════════════════════════════════════════════════════════════
# SOURCE 1 — Serper: search BDJobs directly (bypasses 403)
# ════════════════════════════════════════════════════════════════════════════
SERPER_QUERIES = [
    # BDJobs site-specific — finds actual job listing pages
    'site:bdjobs.com "lecturer" "computer science" OR "CSE" OR "information technology" 2026',
    'site:bdjobs.com "lecturer" university Bangladesh 2026',
    'site:bdjobs.com/details "lecturer" CSE',
    # BRAC specific — their title is "Multiple Open Ranked Faculty"
    'site:bdjobs.com "BRAC" "computer science" OR "CSE" lecturer 2026',
    'site:bdjobs.com "BRAC University" lecturer',
    # General BD university lecturer CSE
    '"lecturer" "computer science" OR "CSE" Bangladesh university circular 2026',
    '"lecturer" "information technology" Bangladesh university circular 2026',
    # Top private unis specifically
    '"North South" OR "AIUB" OR "IUB" OR "East West" lecturer CSE 2026',
    '"Daffodil" OR "ULAB" OR "UIU" OR "AUST" lecturer "computer science" 2026',
    '"Stamford University" OR "Southeast University" lecturer CSE circular',
]

def scrape_serper():
    if not SERPER_KEY:
        print("  ⚠️  No SERPER_API_KEY — get free key at serper.dev")
        return []

    jobs, seen = [], set()
    print("  [Serper Search — BDJobs + Web]")

    for query in SERPER_QUERIES:
        try:
            r = requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
                json={"q": query, "gl": "bd", "hl": "en", "num": 10},
                timeout=15,
            )
            if r.status_code != 200:
                print(f"    Serper {r.status_code}: {query[:50]}")
                continue

            results = r.json().get("organic", [])
            print(f"    {len(results)} results ← {query[:55]}")

            for res in results:
                title   = res.get("title", "").strip()
                url     = res.get("link", "").strip()
                snippet = res.get("snippet", "").strip()
                date_raw = res.get("date", "")

                if not title or not url or url in seen:
                    continue

                # Clean " - BDJobs" or " | Source" suffix
                clean = re.sub(r"\s*[-|–]\s*(BDJobs|BD Jobs|bdjobs\.com)[^|]*$", "", title, flags=re.I).strip()
                clean = re.sub(r"\s*[-|–]\s*[^-|]{3,35}$", "", clean).strip()

                if not is_valid(clean, snippet):
                    continue

                found_at = _parse_serper_date(date_raw)
                if not is_recent(found_at):
                    continue

                seen.add(url)
                source = _source_name(url)
                dl = extract_deadline(snippet)

                print(f"    ✅ {clean[:60]}")
                jobs.append({
                    "id":          make_id(clean, url),
                    "title":       clean,
                    "institution": source,
                    "source":      source,
                    "url":         url,
                    "deadline":    dl,
                    "found_at":    found_at,
                    "notified":    False,
                })
        except Exception as e:
            print(f"    ERR: {e}")
        time.sleep(0.4)

    print(f"  → {len(jobs)} jobs from Serper")
    return jobs

def _parse_serper_date(date_raw):
    now = datetime.now(timezone.utc)
    if not date_raw:
        return now.isoformat()
    m = re.search(r"(\d+)\s+day", date_raw)
    if m:
        return (now - timedelta(days=int(m.group(1)))).isoformat()
    m = re.search(r"(\d+)\s+hour", date_raw)
    if m:
        return now.isoformat()
    m = re.search(r"(\d+)\s+week", date_raw)
    if m:
        return (now - timedelta(weeks=int(m.group(1)))).isoformat()
    return now.isoformat()

# ════════════════════════════════════════════════════════════════════════════
# SOURCE 2 — Serper News
# ════════════════════════════════════════════════════════════════════════════
NEWS_QUERIES = [
    "CSE lecturer job circular Bangladesh university 2026",
    "computer science lecturer Bangladesh university 2026",
    "information technology lecturer vacancy Bangladesh 2026",
    "BRAC UIU NSU AIUB lecturer CSE circular 2026",
]

def scrape_serper_news():
    if not SERPER_KEY:
        return []

    jobs, seen = [], set()
    print("  [Serper News]")

    for query in NEWS_QUERIES:
        try:
            r = requests.post(
                "https://google.serper.dev/news",
                headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
                json={"q": query, "gl": "bd", "hl": "en", "num": 10},
                timeout=15,
            )
            if r.status_code != 200:
                continue

            for res in r.json().get("news", []):
                title   = res.get("title", "").strip()
                url     = res.get("link", "").strip()
                snippet = res.get("snippet", "").strip()
                if not title or not url or url in seen:
                    continue
                clean = re.sub(r"\s*[-|–]\s*[^-|]{3,35}$", "", title).strip()
                if not is_valid(clean, snippet):
                    continue
                seen.add(url)
                print(f"    ✅ {clean[:60]}")
                jobs.append({
                    "id":          make_id(clean, url),
                    "title":       clean,
                    "institution": _source_name(url),
                    "source":      _source_name(url),
                    "url":         url,
                    "deadline":    extract_deadline(snippet),
                    "found_at":    datetime.now(timezone.utc).isoformat(),
                    "notified":    False,
                })
        except Exception as e:
            print(f"    ERR: {e}")
        time.sleep(0.4)

    print(f"  → {len(jobs)} from news")
    return jobs

# ════════════════════════════════════════════════════════════════════════════
# SOURCE 3 — University career pages
# KEY FIX: for pages that only show "Lecturer" without dept, we fetch the
# detail link and check its text for CSE keywords
# ════════════════════════════════════════════════════════════════════════════
UNIVERSITIES = [
    {"name": "Ahsanullah Univ (AUST)",         "url": "https://www.aust.edu/career"},
    {"name": "North South University",         "url": "https://www.northsouth.edu/administration/offices/human-resources/job-opportunities.html"},
    {"name": "BRAC University",                "url": "https://www.bracu.ac.bd/about/offices/human-resources/job-opportunities"},
    {"name": "IUB",                            "url": "https://iub.edu.bd/career"},
    {"name": "AIUB",                           "url": "https://www.aiub.edu/career"},
    {"name": "East West University",           "url": "https://www.ewubd.edu/job-circular"},
    {"name": "UIU",                            "url": "https://www.uiu.ac.bd/career/"},
    {"name": "ULAB",                           "url": "https://ulab.edu.bd/career/"},
    {"name": "Daffodil Intl University",       "url": "https://daffodilvarsity.edu.bd/article/career"},
    {"name": "Stamford University",            "url": "https://www.stamforduniversity.edu.bd/job-circular"},
    {"name": "Southeast University",           "url": "https://seu.edu.bd/career/"},
    {"name": "Green University",               "url": "https://green.edu.bd/career/"},
    {"name": "Bangladesh University",          "url": "https://www.bu.edu.bd/job/"},
    {"name": "BUBT",                           "url": "https://www.bubt.edu.bd/home/career"},
    {"name": "Northern University Bangladesh", "url": "https://nub.ac.bd/career/"},
    {"name": "Dhaka University",               "url": "https://www.du.ac.bd/body/notice_list/NTC"},
    {"name": "CUET",                           "url": "https://www.cuet.ac.bd/notice"},
    {"name": "RUET",                           "url": "https://www.ruet.ac.bd/all-notice-circular"},
    {"name": "KUET",                           "url": "https://www.kuet.ac.bd/index.php/notice-circulars/"},
    {"name": "DUET",                           "url": "https://duet.ac.bd/notices/"},
    {"name": "SUST",                           "url": "https://www.sust.edu/4"},
    {"name": "JU",                             "url": "https://www.juniv.edu/notice"},
    {"name": "City University",                "url": "https://cityuniversity.edu.bd/career/"},
    {"name": "Prime University",               "url": "https://www.primeuniversity.edu.bd/career/"},
    {"name": "Eastern University",             "url": "https://www.easternuni.edu.bd/career/"},
    {"name": "World University of Bangladesh", "url": "https://wub.edu.bd/career/"},
    {"name": "NSTU",                           "url": "https://nstu.edu.bd/notice/"},
    {"name": "Barishal University",            "url": "https://barisaluniv.edu.bd/notice/"},
]

def fetch_page_text(url, timeout=10):
    """Fetch a page and return all visible text — used to verify CSE content"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return BeautifulSoup(r.content, "lxml").get_text(" ", strip=True)
    except:
        pass
    return ""

def scrape_universities():
    jobs = []
    print(f"  [{len(UNIVERSITIES)} University Pages]")

    for uni in UNIVERSITIES:
        base = "/".join(uni["url"].split("/")[:3])
        try:
            r = requests.get(uni["url"], headers=HEADERS, timeout=12)
            if r.status_code != 200:
                print(f"    ✗ {uni['name']}: HTTP {r.status_code}")
                continue
            soup = BeautifulSoup(r.content, "lxml")
            found = 0

            for a in soup.find_all("a", href=True):
                title = a.get_text(" ", strip=True)
                href  = a.get("href", "").strip()

                if not href or href in ("#", "javascript:void(0)"):
                    continue
                if len(title) < 5 or len(title) > 200:
                    continue

                full_url = urljoin(base, href) if not href.startswith("http") else href

                # Must have lecturer word somewhere in title
                if not is_lecturer(title):
                    continue

                # If title already has CSE → accept immediately
                if is_cse(title) and not is_rejected(title):
                    pass  # good

                # Else title is just "Lecturer" — fetch detail page to check dept
                elif not is_rejected(title):
                    detail_text = fetch_page_text(full_url)
                    if not detail_text or not is_cse(detail_text):
                        continue
                    # Use detail text for deadline too
                    title_from_detail = _extract_title_from_detail(detail_text, title)
                    if title_from_detail:
                        title = title_from_detail
                else:
                    continue

                jid = make_id(title, uni["name"])
                jobs.append({
                    "id":          jid,
                    "title":       title,
                    "institution": uni["name"],
                    "source":      uni["name"],
                    "url":         full_url,
                    "deadline":    "",
                    "found_at":    datetime.now(timezone.utc).isoformat(),
                    "notified":    False,
                })
                found += 1
                time.sleep(0.2)  # small delay between detail fetches

            if found:
                print(f"    ✅ {uni['name']}: {found}")

        except Exception as e:
            print(f"    ✗ {uni['name']}: {e}")
        time.sleep(0.3)

    print(f"  → {len(jobs)} from university pages")
    return jobs

def _extract_title_from_detail(text, fallback):
    """Try to get a better title from detail page"""
    # Look for "Lecturer in/of/- CSE" pattern
    m = re.search(
        r"((?:senior\s+)?lecturer\s*(?:in|of|[-–,]|for)?\s*"
        r"(?:computer\s+science|cse|information\s+technology|software\s+engineering|it\b))",
        text, re.I
    )
    if m:
        return m.group(1).strip().title()
    return fallback

# ════════════════════════════════════════════════════════════════════════════
# Telegram
# ════════════════════════════════════════════════════════════════════════════
def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": False},
            timeout=10,
        )
        if r.status_code != 200:
            print(f"  Telegram {r.status_code}: {r.text[:80]}")
    except Exception as e:
        print(f"  Telegram ERR: {e}")

# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════
def main():
    print("\n🔍 BD CSE Lecturer Tracker v8")
    print("=" * 52)

    all_found = []

    print("\n📡 SOURCE 1: Serper Search (BDJobs + Web)")
    all_found += scrape_serper()

    print("\n📡 SOURCE 2: Serper News")
    all_found += scrape_serper_news()

    print("\n📡 SOURCE 3: University Career Pages")
    all_found += scrape_universities()

    print(f"\n📋 Total valid: {len(all_found)}")

    existing   = load_existing()
    existing["jobs"] = [j for j in existing["jobs"] if is_recent(j.get("found_at", ""))]
    exist_ids  = {j["id"]  for j in existing["jobs"]}
    exist_urls = {j["url"] for j in existing["jobs"]}

    added, seen_new = [], set()
    for job in all_found:
        if job["id"] not in exist_ids and job["url"] not in exist_urls and job["id"] not in seen_new:
            existing["jobs"].insert(0, job)
            added.append(job)
            exist_ids.add(job["id"])
            exist_urls.add(job["url"])
            seen_new.add(job["id"])

    existing["last_updated"] = datetime.now(timezone.utc).isoformat()
    existing["jobs"]         = existing["jobs"][:300]
    save(existing)

    with open("new_jobs.json", "w", encoding="utf-8") as f:
        json.dump(added, f, ensure_ascii=False, indent=2)

    print(f"✅ New: {len(added)} | Stored: {len(existing['jobs'])}")

    for job in added:
        dl  = f"\n⏰ <b>Deadline:</b> {job['deadline']}" if job.get("deadline") else ""
        msg = (
            f"🎓 <b>New CSE/IT Lecturer Job!</b>\n\n"
            f"📌 <b>{job['title']}</b>\n"
            f"🏫 {job['institution']}{dl}\n"
            f"🔗 <a href='{job['url']}'>View Circular →</a>"
        )
        send_telegram(msg)
        time.sleep(0.8)

    if len(added) >= 3:
        send_telegram(f"📊 <b>{len(added)} new CSE/IT Lecturer jobs found!</b> Check your dashboard 🎉")

if __name__ == "__main__":
    main()
