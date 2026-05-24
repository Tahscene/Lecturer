"""
BD Lecturer Job Tracker — v4
STRICT: Only CSE/IT Lecturer positions, last 60 days only.
"""

import requests, json, os, hashlib, time, sys
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as ET

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://www.google.com/",
})

DATA_FILE    = "docs/jobs.json"
MAX_AGE_DAYS = 60   # discard jobs older than this

# ── STRICT keyword filters ────────────────────────────────────────────────────
# BOTH of these must match for a job to be accepted

LECTURER_KW = [
    "lecturer", "লেকচারার",
    "assistant professor", "associate professor",
    "adjunct lecturer", "visiting lecturer",
]

CSE_KW = [
    "computer science", "computer engineering",
    "cse", "information technology", " it ",
    "software engineering", "ict",
    "computing", "data science",
    "artificial intelligence", "machine learning",
    "কম্পিউটার", "তথ্য প্রযুক্তি",
]

# These words in any matched job → SKIP (false positives)
REJECT_KW = [
    "student", "admission", "scholarship", "result", "exam",
    "routine", "seminar", "workshop", "conference", "tender",
    "phd", "internship", "research assistant", "lab assistant",
    "non-teaching", "accounts", "registrar", "librarian",
    "nurse", "doctor", "security", "driver", "peon",
    "civil", "mechanical", "electrical", "eee", "business",
    "marketing", "finance", "english", "bangla", "economics",
    "mathematics", "physics", "chemistry", "biology",
    "pharmacy", "law", "architecture",
]

def is_strict_cse_lecturer(text: str) -> bool:
    t = text.lower()
    if any(r in t for r in REJECT_KW):
        return False
    has_lecturer = any(k in t for k in LECTURER_KW)
    has_cse      = any(k in t for k in CSE_KW)
    return has_lecturer and has_cse

def make_id(title, source):
    return hashlib.md5(f"{title.lower().strip()}{source.lower()}".encode()).hexdigest()[:12]

def is_recent(date_str: str) -> bool:
    """Return True if date_str (ISO format) is within MAX_AGE_DAYS."""
    try:
        dt  = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (now - dt).days <= MAX_AGE_DAYS
    except Exception:
        return True  # unknown date → keep it

def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"jobs": [], "last_updated": ""}

def save_data(data):
    os.makedirs("docs", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_html(url, timeout=15):
    try:
        r = SESSION.get(url, timeout=timeout, allow_redirects=True)
        if r.status_code == 200:
            return BeautifulSoup(r.content, "lxml")
        print(f"    HTTP {r.status_code} → {url[:55]}")
    except Exception as e:
        print(f"    ERR → {url[:55]} | {e}")
    return None

def get_rss(url, timeout=15):
    try:
        r = SESSION.get(url, timeout=timeout, allow_redirects=True)
        if r.status_code == 200:
            return ET.fromstring(r.content)
    except Exception as e:
        print(f"    RSS ERR → {url[:55]} | {e}")
    return None

# ════════════════════════════════════════════════════════════════════════════════
# SOURCE 1 — BDJobs RSS (Education category)
# ════════════════════════════════════════════════════════════════════════════════
BDJOBS_RSS_URLS = [
    "https://jobs.bdjobs.com/rss/rss.asp?fcat=10",
    "https://jobs.bdjobs.com/rss/rss.asp?txtsearch=lecturer+CSE",
    "https://jobs.bdjobs.com/rss/rss.asp?txtsearch=lecturer+computer",
    "https://jobs.bdjobs.com/rss/rss.asp?txtsearch=lecturer+IT",
]

def scrape_bdjobs_rss():
    jobs, seen = [], set()
    print("  [BDJobs RSS]")
    for url in BDJOBS_RSS_URLS:
        root = get_rss(url)
        if root is None: continue
        items = root.findall(".//item")
        print(f"    {len(items)} items ← {url[-35:]}")
        for item in items:
            title = (item.findtext("title") or "").strip()
            link  = (item.findtext("link")  or "").strip()
            desc  = (item.findtext("description") or "").strip()
            pub   = (item.findtext("pubDate") or "").strip()

            combined = f"{title} {desc}"
            if not is_strict_cse_lecturer(combined):
                continue

            # parse pubDate → ISO
            found_at = datetime.utcnow().isoformat()
            if pub:
                try:
                    from email.utils import parsedate_to_datetime
                    found_at = parsedate_to_datetime(pub).isoformat()
                except Exception:
                    pass

            if not is_recent(found_at):
                continue

            jid = make_id(title, link)
            if jid in seen: continue
            seen.add(jid)

            soup_d = BeautifulSoup(desc, "lxml")
            inst   = soup_d.get_text(" ", strip=True)[:80] or "Unknown"
            jobs.append({"id": jid, "title": title, "source": "BDJobs",
                         "institution": inst, "url": link,
                         "found_at": found_at, "notified": False})
        time.sleep(0.5)

    print(f"    → {len(jobs)} CSE lecturer jobs")
    return jobs

# ════════════════════════════════════════════════════════════════════════════════
# SOURCE 2 — Google News RSS
# ════════════════════════════════════════════════════════════════════════════════
GNEWS_QUERIES = [
    "lecturer+CSE+university+Bangladesh+job+circular",
    "assistant+professor+computer+science+Bangladesh+university",
    "lecturer+IT+university+Bangladesh+circular+2025",
    "lecturer+information+technology+Bangladesh+university",
]
GNEWS_BASE = "https://news.google.com/rss/search?q={q}&hl=en-BD&gl=BD&ceid=BD:en"

def scrape_google_news():
    jobs, seen = [], set()
    print("  [Google News RSS]")
    for q in GNEWS_QUERIES:
        root = get_rss(GNEWS_BASE.format(q=q))
        if root is None: continue
        items = root.findall(".//item")
        print(f"    {len(items)} items ← {q[:45]}")
        for item in items:
            title = (item.findtext("title") or "").strip()
            link  = (item.findtext("link")  or "").strip()
            desc  = (item.findtext("description") or "").strip()
            pub   = (item.findtext("pubDate") or "").strip()

            combined = f"{title} {desc}"
            if not is_strict_cse_lecturer(combined):
                continue

            found_at = datetime.utcnow().isoformat()
            if pub:
                try:
                    from email.utils import parsedate_to_datetime
                    found_at = parsedate_to_datetime(pub).isoformat()
                except Exception:
                    pass

            if not is_recent(found_at):
                continue

            jid = make_id(title, link[:30])
            if jid in seen: continue
            seen.add(jid)

            jobs.append({"id": jid, "title": title, "source": "Google News",
                         "institution": "See link", "url": link,
                         "found_at": found_at, "notified": False})
        time.sleep(0.5)

    print(f"    → {len(jobs)} relevant items")
    return jobs

# ════════════════════════════════════════════════════════════════════════════════
# SOURCE 3 — Universities (comprehensive list)
# ════════════════════════════════════════════════════════════════════════════════
UNIVERSITIES = [
    # ── Tier 1 Private ───────────────────────────────────────────────────────
    {"name": "North South University",         "url": "https://www.northsouth.edu/administration/offices/human-resources/job-opportunities.html"},
    {"name": "BRAC University",                "url": "https://www.bracu.ac.bd/about/offices/human-resources/job-opportunities",
                                                "alt": "https://career.bracu.ac.bd/"},
    {"name": "IUB",                            "url": "https://iub.edu.bd/career"},
    {"name": "AIUB",                           "url": "https://www.aiub.edu/career"},
    {"name": "AUST",                           "url": "https://www.aust.edu/career"},
    {"name": "East West University",           "url": "https://www.ewubd.edu/job-circular"},
    {"name": "UIU",                            "url": "https://www.uiu.ac.bd/career/"},
    {"name": "ULAB",                           "url": "https://ulab.edu.bd/career/"},
    {"name": "Daffodil Intl University",       "url": "https://daffodilvarsity.edu.bd/article/career"},
    {"name": "Stamford University",            "url": "https://www.stamforduniversity.edu.bd/job-circular"},
    # ── Strong Dhaka Private ─────────────────────────────────────────────────
    {"name": "Southeast University",           "url": "https://seu.edu.bd/career/"},
    {"name": "Prime University",               "url": "https://www.primeuniversity.edu.bd/career/"},
    {"name": "City University",                "url": "https://cityuniversity.edu.bd/career/"},
    {"name": "Eastern University",             "url": "https://www.easternuni.edu.bd/career/"},
    {"name": "Green University",               "url": "https://green.edu.bd/career/"},
    {"name": "World University of Bangladesh", "url": "https://wub.edu.bd/career/"},
    {"name": "Bangladesh University (BU)",     "url": "https://www.bu.edu.bd/job/"},
    {"name": "Primeasia University",           "url": "https://primeasia.edu.bd/career/"},
    {"name": "UODA",                           "url": "https://uda.ac.bd/career/"},
    {"name": "Dhaka Intl University (DIU)",    "url": "https://diu.ac/career/"},
    # ── Mid-tier active ──────────────────────────────────────────────────────
    {"name": "Manarat Intl University",        "url": "https://manarat.ac.bd/career/"},
    {"name": "Sonargaon University",           "url": "https://su.edu.bd/career/"},
    {"name": "State University of Bangladesh", "url": "https://sub.edu.bd/career/"},
    {"name": "Northern University Bangladesh", "url": "https://nub.ac.bd/career/"},
    {"name": "Atish Dipankar Univ",           "url": "https://adust.edu.bd/career/"},
    {"name": "BUBT",                           "url": "https://www.bubt.edu.bd/home/career"},
    {"name": "BUP",                            "url": "https://www.bup.edu.bd/notice"},
    {"name": "Notre Dame Univ Bangladesh",     "url": "https://ndub.edu.bd/career/"},
    {"name": "Presidency University",          "url": "https://presidency.edu.bd/career/"},
    # ── Public Universities ───────────────────────────────────────────────────
    {"name": "BUET",                           "url": "https://www.buet.ac.bd/web/#/noticeboard/vacancy", "type": "spa"},
    {"name": "Dhaka University",               "url": "https://www.du.ac.bd/body/notice_list/NTC"},
    {"name": "CUET",                           "url": "https://www.cuet.ac.bd/notice"},
    {"name": "RUET",                           "url": "https://www.ruet.ac.bd/all-notice-circular"},
    {"name": "KUET",                           "url": "https://www.kuet.ac.bd/index.php/notice-circulars/"},
    {"name": "DUET",                           "url": "https://duet.ac.bd/notices/"},
    {"name": "SUST",                           "url": "https://www.sust.edu/4"},
    {"name": "JU",                             "url": "https://www.juniv.edu/notice"},
    {"name": "Rajshahi University",            "url": "https://www.ru.ac.bd/notice/"},
    {"name": "Chittagong University",          "url": "https://cu.ac.bd/notice/"},
    {"name": "Khulna University",              "url": "https://www.ku.ac.bd/notice/"},
    {"name": "NSTU",                           "url": "https://nstu.edu.bd/notice/"},
    {"name": "MBSTU",                          "url": "https://www.mbstu.ac.bd/notice"},
    {"name": "HSTU",                           "url": "https://www.hstu.ac.bd/notice"},
    {"name": "Barishal University",            "url": "https://barisaluniv.edu.bd/notice/"},
    {"name": "BRUR",                           "url": "https://www.brur.ac.bd/notice/"},
]

def scrape_university(uni):
    jobs, seen = [], set()
    base = "/".join(uni["url"].split("/")[:3])

    soup = get_html(uni["url"])
    if soup is None and uni.get("alt"):
        soup = get_html(uni["alt"])
    if soup is None:
        return jobs

    for a in soup.find_all("a", href=True):
        title = a.get_text(" ", strip=True)
        href  = a.get("href", "").strip()
        if not href or href in ("#", "javascript:void(0)"): continue
        if len(title) < 6 or len(title) > 300: continue

        full_url = urljoin(base, href) if not href.startswith("http") else href

        # Strict: title must explicitly be CSE lecturer
        if not is_strict_cse_lecturer(title):
            # Last chance: PDF whose URL has recruitment keywords
            if not (href.lower().endswith(".pdf") and
                    any(k in href.lower() for k in ["lecturer", "faculty", "cse", "recruit", "vacancy"])):
                continue

        jid = make_id(title, uni["name"])
        if jid in seen: continue
        seen.add(jid)

        jobs.append({"id": jid, "title": title, "source": uni["name"],
                     "institution": uni["name"], "url": full_url,
                     "found_at": datetime.utcnow().isoformat(), "notified": False})
    return jobs

# ════════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════════
def main():
    all_new = []

    print("\n📡 SOURCE 1: BDJobs RSS")
    all_new += scrape_bdjobs_rss()

    print("\n📡 SOURCE 2: Google News RSS")
    all_new += scrape_google_news()

    print(f"\n📡 SOURCE 3: {len(UNIVERSITIES)} Universities")
    for uni in UNIVERSITIES:
        if uni.get("type") == "spa":
            print(f"    ⏭  {uni['name']} (JS-rendered, skip)")
            continue
        results = scrape_university(uni)
        if results:
            print(f"    ✅ {uni['name']}: {len(results)}")
        all_new += results
        time.sleep(0.35)

    # ── Prune old jobs from existing data ──────────────────────────────────
    existing = load_existing()
    existing["jobs"] = [j for j in existing["jobs"] if is_recent(j.get("found_at", ""))]

    existing_ids = {j["id"] for j in existing["jobs"]}
    added = []
    for job in all_new:
        if job["id"] not in existing_ids:
            existing["jobs"].insert(0, job)
            added.append(job)
            existing_ids.add(job["id"])

    existing["last_updated"] = datetime.utcnow().isoformat()
    existing["jobs"]         = existing["jobs"][:300]
    save_data(existing)

    with open("new_jobs.json", "w", encoding="utf-8") as f:
        json.dump(added, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*55}")
    print(f"✅ {len(all_new)} scraped | {len(added)} NEW | "
          f"{len(existing['jobs'])} total (last {MAX_AGE_DAYS}d)")
    print(f"{'='*55}")

if __name__ == "__main__":
    main()
