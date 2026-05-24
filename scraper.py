"""
BD Lecturer Job Tracker — Robust Scraper v2
Multiple fallback strategies so site changes don't break everything.
"""

import requests
from bs4 import BeautifulSoup
import json, os, hashlib, time, sys
from datetime import datetime
from urllib.parse import urljoin

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# ── University pages ──────────────────────────────────────────────────────────
UNIVERSITIES = [
    # Public
    {"name": "BUET",               "url": "https://www.buet.ac.bd/web/#/noticeboard/vacancy"},
    {"name": "Dhaka University",   "url": "https://www.du.ac.bd/body/notice_list/NTC"},
    {"name": "CUET",               "url": "https://www.cuet.ac.bd/notice"},
    {"name": "RUET",               "url": "https://www.ruet.ac.bd/all-notice-circular"},
    {"name": "KUET",               "url": "https://www.kuet.ac.bd/index.php/notice-circulars/"},
    {"name": "DUET",               "url": "https://duet.ac.bd/notices/"},
    {"name": "SUST",               "url": "https://www.sust.edu/4"},
    {"name": "JU",                 "url": "https://www.juniv.edu/notice"},
    {"name": "Rajshahi University","url": "https://www.ru.ac.bd/notice/"},
    {"name": "Chittagong Univ",    "url": "https://cu.ac.bd/notice/"},
    {"name": "Khulna University",  "url": "https://www.ku.ac.bd/notice/"},
    {"name": "Comilla University", "url": "https://www.cou.ac.bd/notice/"},
    {"name": "NSTU",               "url": "https://nstu.edu.bd/notice/"},
    {"name": "PUST",               "url": "https://www.pust.ac.bd/notices/"},
    {"name": "MBSTU",              "url": "https://www.mbstu.ac.bd/notice"},
    {"name": "HSTU",               "url": "https://www.hstu.ac.bd/notice"},
    {"name": "Barishal University","url": "https://barisaluniv.edu.bd/notice/"},
    {"name": "BRUR",               "url": "https://www.brur.ac.bd/notice/"},
    {"name": "RMSTU",              "url": "https://www.rmstu.edu.bd/notice/"},
    # Private
    {"name": "BRAC University",    "url": "https://www.bracu.ac.bd/about/offices/human-resources/job-opportunities"},
    {"name": "North South Univ",   "url": "https://www.northsouth.edu/about-nsu/faculty-and-staff-resources/vacancy-announcements.html"},
    {"name": "AIUB",               "url": "https://www.aiub.edu/career"},
    {"name": "Daffodil Univ (DIU)","url": "https://daffodilvarsity.edu.bd/article/career"},
    {"name": "UIU",                "url": "https://www.uiu.ac.bd/career/"},
    {"name": "EWU",                "url": "https://www.ewubd.edu/job-circular"},
    {"name": "IUB",                "url": "https://iub.edu.bd/career"},
    {"name": "AUST",               "url": "https://www.aust.edu/career"},
    {"name": "Southeast University","url": "https://seu.edu.bd/career/"},
    {"name": "Stamford University","url": "https://www.stamforduniversity.edu.bd/job-circular"},
    {"name": "Green University",   "url": "https://green.edu.bd/career/"},
    {"name": "Metropolitan Univ",  "url": "https://metrouni.edu.bd/career"},
    {"name": "Premier University", "url": "https://www.puc.ac.bd/career/"},
    {"name": "IUBAT",              "url": "https://iubat.edu/career/"},
    {"name": "BGC Trust Univ",     "url": "https://bgctub.ac.bd/career/"},
    {"name": "BAUST",              "url": "https://baust.edu.bd/career/"},
    {"name": "Leading University", "url": "https://lus.ac.bd/career/"},
    {"name": "Port City Intl Univ","url": "https://portcityuc.edu.bd/career/"},
    {"name": "Sylhet Intl Univ",   "url": "https://siu.edu.bd/career/"},
    {"name": "Manarat Intl Univ",  "url": "https://manarat.ac.bd/career/"},
    {"name": "Primeasia Univ",     "url": "https://primeasia.edu.bd/career/"},
    {"name": "Uttara University",  "url": "https://uttarauniversity.edu.bd/career/"},
    {"name": "Victoria University","url": "https://vub.edu.bd/career/"},
    {"name": "World University BD","url": "https://wub.edu.bd/career/"},
]

# ── Keywords ─────────────────────────────────────────────────────────────────
MUST_HAVE = ["lecturer", "assistant professor", "associate professor",
             "faculty", "লেকচারার", "শিক্ষক"]

CSE_TERMS  = ["computer science", "computer engineering", "cse",
              "information technology", "software engineering",
              "ict", "it ", "computing", "data science",
              "কম্পিউটার", "তথ্য প্রযুক্তি"]

DATA_FILE  = "docs/jobs.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

def make_id(title: str, inst: str) -> str:
    return hashlib.md5(f"{title.lower().strip()}{inst.lower().strip()}".encode()).hexdigest()[:12]

def is_position(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in MUST_HAVE)

def is_cse(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in CSE_TERMS)

def is_relevant(text: str) -> bool:
    """Either title itself mentions CSE, or it's a faculty/lecturer post (may be on a CSE-dept page)"""
    return is_position(text) and (is_cse(text) or len(text) < 80)

def get_page(url: str, timeout: int = 15):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return BeautifulSoup(r.text, "lxml")
    except Exception as e:
        print(f"    [WARN] {url[:60]}… → {e}")
        return None

def load_existing() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"jobs": [], "last_updated": ""}

def save_data(data: dict):
    os.makedirs("docs", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── BDJobs ────────────────────────────────────────────────────────────────────
BDJOBS_SEARCHES = [
    "https://jobs.bdjobs.com/jobsearch.asp?txtsearch=lecturer+CSE&Country=0",
    "https://jobs.bdjobs.com/jobsearch.asp?txtsearch=lecturer+computer&Country=0",
    "https://jobs.bdjobs.com/jobsearch.asp?txtsearch=lecturer+IT&Country=0",
    "https://jobs.bdjobs.com/jobsearch.asp?txtsearch=assistant+professor+CSE&Country=0",
    "https://jobs.bdjobs.com/jobsearch.asp?txtsearch=faculty+CSE+university&Country=0",
]

def scrape_bdjobs() -> list:
    jobs, seen = [], set()
    print("  Scraping BDJobs...")

    for url in BDJOBS_SEARCHES:
        soup = get_page(url)
        if not soup:
            continue

        # ── Strategy 1: known BDJobs div classes (try multiple) ──
        candidates = []
        for sel in ["div.job-tittle", "div.norm-job-tittle", "div.internship-job-tittle",
                    ".job-title-text", ".position-title", "h2.job-title", "h3.job-title"]:
            candidates += soup.select(sel)

        # ── Strategy 2: fallback — ALL links with hiring/job words ──
        if not candidates:
            for a in soup.find_all("a", href=True):
                txt = a.get_text(strip=True)
                if len(txt) > 8 and is_position(txt):
                    candidates.append(a)

        for item in candidates:
            # get link
            link_tag = item if item.name == "a" else item.find("a")
            if not link_tag:
                continue
            title = link_tag.get_text(strip=True)
            href  = link_tag.get("href", "")
            if not href:
                continue

            job_url = href if href.startswith("http") else "https://jobs.bdjobs.com/" + href

            if not is_relevant(title):
                continue

            # institution: look sibling/parent spans
            inst = "Unknown"
            for cls in ["comp-name", "comp_name", "company-name", "org-name"]:
                t = item.find_next("span", class_=cls) or item.find_next("a", class_=cls)
                if t:
                    inst = t.get_text(strip=True)
                    break

            jid = make_id(title, inst)
            if jid in seen:
                continue
            seen.add(jid)
            jobs.append({"id": jid, "title": title, "source": "BDJobs",
                         "institution": inst, "url": job_url,
                         "found_at": datetime.utcnow().isoformat(), "notified": False})

        time.sleep(1)

    print(f"    → {len(jobs)} job(s) from BDJobs")
    return jobs

# ── University scraper ────────────────────────────────────────────────────────

def scrape_university(uni: dict) -> list:
    jobs, seen = [], set()
    base_url = "/".join(uni["url"].split("/")[:3])

    soup = get_page(uni["url"])
    if not soup:
        return jobs

    # Collect all <a> text + href pairs
    for a in soup.find_all("a", href=True):
        title = a.get_text(" ", strip=True)
        href  = a.get("href", "").strip()

        if len(title) < 8 or len(title) > 300:
            continue
        if not href or href in ("#", "javascript:void(0)"):
            continue
        if not is_relevant(title):
            continue

        full_url = urljoin(base_url, href) if not href.startswith("http") else href

        jid = make_id(title, uni["name"])
        if jid in seen:
            continue
        seen.add(jid)

        jobs.append({"id": jid, "title": title, "source": uni["name"],
                     "institution": uni["name"], "url": full_url,
                     "found_at": datetime.utcnow().isoformat(), "notified": False})

    return jobs

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    all_new = []

    # 1) BDJobs
    all_new += scrape_bdjobs()

    # 2) Universities
    print(f"  Scraping {len(UNIVERSITIES)} universities...")
    for uni in UNIVERSITIES:
        results = scrape_university(uni)
        if results:
            print(f"    ✅ {uni['name']}: {len(results)} match(es)")
        all_new += results
        time.sleep(0.4)

    # 3) Merge with existing
    existing     = load_existing()
    existing_ids = {j["id"] for j in existing["jobs"]}

    added = []
    for job in all_new:
        if job["id"] not in existing_ids:
            existing["jobs"].insert(0, job)
            added.append(job)
            existing_ids.add(job["id"])

    existing["last_updated"] = datetime.utcnow().isoformat()
    existing["jobs"] = existing["jobs"][:500]

    save_data(existing)

    # 4) Save new jobs for notifier
    with open("new_jobs.json", "w", encoding="utf-8") as f:
        json.dump(added, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Done. {len(all_new)} scraped | {len(added)} new")

    if len(all_new) == 0:
        print("\n⚠️  WARNING: 0 jobs found across all sources.")
        print("   Possible reasons:")
        print("   1. BDJobs/university sites blocked the scraper (add delays)")
        print("   2. HTML structure changed — check GitHub Actions log")
        print("   3. Network issue in GitHub Actions runner")
        sys.exit(0)   # don't fail the workflow

if __name__ == "__main__":
    main()
