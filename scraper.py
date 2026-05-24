"""
BD Lecturer Job Tracker
Scrapes BDJobs + University websites for CSE/IT Lecturer positions
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import hashlib
from datetime import datetime
import time

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# ─── University job/notice pages ─────────────────────────────────────────────
UNIVERSITIES = [
    # Public Universities
    {"name": "BUET",            "url": "https://www.buet.ac.bd/web/#/noticeboard/vacancy"},
    {"name": "Dhaka University","url": "https://www.du.ac.bd/body/notice_list/NTC"},
    {"name": "CUET",            "url": "https://www.cuet.ac.bd/notice"},
    {"name": "RUET",            "url": "https://www.ruet.ac.bd/all-notice-circular"},
    {"name": "KUET",            "url": "https://www.kuet.ac.bd/index.php/notice-circulars/"},
    {"name": "DUET",            "url": "https://duet.ac.bd/notices/"},
    {"name": "SUST",            "url": "https://www.sust.edu/4"},
    {"name": "JU (Jahangirnagar)", "url": "https://www.juniv.edu/notice"},
    {"name": "Rajshahi University","url": "https://www.ru.ac.bd/notice/"},
    {"name": "Chittagong University","url":"https://cu.ac.bd/notice/"},
    {"name": "Khulna University","url": "https://www.ku.ac.bd/notice/"},
    {"name": "Comilla University","url":"https://www.cou.ac.bd/notice/"},
    {"name": "Noakhali Sci & Tech","url":"https://nstu.edu.bd/notice/"},
    {"name": "Pabna Uni Sci & Tech","url":"https://www.pust.ac.bd/notices/"},
    {"name": "Shahjalal Univ (SUST)","url":"https://www.sust.edu/notices"},
    {"name": "MBSTU",           "url": "https://www.mbstu.ac.bd/notice"},
    {"name": "HSTU",            "url": "https://www.hstu.ac.bd/notice"},
    {"name": "Barishal University","url":"https://barisaluniv.edu.bd/notice/"},
    {"name": "Begum Rokeya Univ","url":"https://www.brur.ac.bd/notice/"},
    {"name": "Rangamati Sci & Tech","url":"https://www.rmstu.edu.bd/notice/"},
    # Private Universities
    {"name": "BRAC University", "url": "https://www.bracu.ac.bd/about/offices/human-resources/job-opportunities"},
    {"name": "North South Univ","url": "https://www.northsouth.edu/about-nsu/faculty-and-staff-resources/vacancy-announcements.html"},
    {"name": "AIUB",            "url": "https://www.aiub.edu/career"},
    {"name": "DIU (Daffodil)",  "url": "https://daffodilvarsity.edu.bd/article/career"},
    {"name": "UIU",             "url": "https://www.uiu.ac.bd/career/"},
    {"name": "EWU",             "url": "https://www.ewubd.edu/job-circular"},
    {"name": "IUB",             "url": "https://iub.edu.bd/career"},
    {"name": "AUST",            "url": "https://www.aust.edu/career"},
    {"name": "American Intl Univ (AIUB)","url":"https://www.aiub.edu/career"},
    {"name": "Southeast University","url":"https://seu.edu.bd/career/"},
    {"name": "Stamford University","url":"https://www.stamforduniversity.edu.bd/job-circular"},
    {"name": "Green University", "url":"https://green.edu.bd/career/"},
    {"name": "Metropolitan Univ","url":"https://metrouni.edu.bd/career"},
    {"name": "Premier University","url":"https://www.puc.ac.bd/career/"},
    {"name": "IUBAT",           "url": "https://iubat.edu/career/"},
    {"name": "BGC Trust Univ",  "url": "https://bgctub.ac.bd/career/"},
    {"name": "BAUST",           "url": "https://baust.edu.bd/career/"},
    {"name": "Leading University","url":"https://lus.ac.bd/career/"},
    {"name": "Port City Intl Univ","url":"https://portcityuc.edu.bd/career/"},
    {"name": "Sylhet Intl Univ","url":"https://siu.edu.bd/career/"},
    {"name": "Manarat Intl Univ","url":"https://manarat.ac.bd/career/"},
    {"name": "Primeasia Univ",  "url":"https://primeasia.edu.bd/career/"},
    {"name": "Uttara University","url":"https://uttarauniversity.edu.bd/career/"},
    {"name": "Victoria University","url":"https://vub.edu.bd/career/"},
    {"name": "World University BD","url":"https://wub.edu.bd/career/"},
]

CSE_KEYWORDS = [
    "lecturer", "assistant professor", "faculty",
    "computer science", "computer engineering",
    "information technology", "software engineering",
    "cse", "ict", "it department",
    "লেকচারার", "শিক্ষক নিয়োগ"
]

DATA_FILE = "docs/jobs.json"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_id(title: str, source: str) -> str:
    return hashlib.md5(f"{title}{source}".encode()).hexdigest()[:12]


def is_cse_related(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in CSE_KEYWORDS)


def load_existing() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"jobs": [], "last_updated": ""}


def save_data(data: dict):
    os.makedirs("docs", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── BDJobs Scraper ───────────────────────────────────────────────────────────

def scrape_bdjobs() -> list:
    jobs = []
    search_urls = [
        "https://jobs.bdjobs.com/jobsearch.asp?txtsearch=lecturer+computer+science&fcat=10&Country=0",
        "https://jobs.bdjobs.com/jobsearch.asp?txtsearch=lecturer+CSE&fcat=10&Country=0",
        "https://jobs.bdjobs.com/jobsearch.asp?txtsearch=lecturer+IT&fcat=10&Country=0",
        "https://jobs.bdjobs.com/jobsearch.asp?txtsearch=assistant+professor+CSE&fcat=10&Country=0",
    ]

    seen = set()
    for url in search_urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")

            # BDJobs listing cards
            for item in soup.select("div.job-tittle, .norm-job-tittle, .internship-job-tittle"):
                link_tag = item.find("a")
                if not link_tag:
                    continue
                title = link_tag.get_text(strip=True)
                href = link_tag.get("href", "")
                job_url = href if href.startswith("http") else "https://jobs.bdjobs.com/" + href

                if not is_cse_related(title):
                    continue

                # Company / university name
                company_tag = item.find_next("span", class_="comp-name")
                company = company_tag.get_text(strip=True) if company_tag else "Unknown"

                jid = make_id(title, company)
                if jid in seen:
                    continue
                seen.add(jid)

                jobs.append({
                    "id": jid,
                    "title": title,
                    "source": "BDJobs",
                    "institution": company,
                    "url": job_url,
                    "found_at": datetime.utcnow().isoformat(),
                    "notified": False,
                })

            time.sleep(1)
        except Exception as e:
            print(f"[BDJobs] Error: {e}")

    return jobs


# ─── University Website Scraper ───────────────────────────────────────────────

def scrape_university(uni: dict) -> list:
    jobs = []
    try:
        r = requests.get(uni["url"], headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        # Generic: grab all <a> tags whose text contains CSE keywords
        for tag in soup.find_all("a"):
            text = tag.get_text(strip=True)
            if len(text) < 10 or not is_cse_related(text):
                continue

            href = tag.get("href", "")
            if not href:
                continue
            if href.startswith("http"):
                full_url = href
            elif href.startswith("/"):
                base = "/".join(uni["url"].split("/")[:3])
                full_url = base + href
            else:
                full_url = uni["url"].rstrip("/") + "/" + href

            jid = make_id(text, uni["name"])
            jobs.append({
                "id": jid,
                "title": text,
                "source": uni["name"],
                "institution": uni["name"],
                "url": full_url,
                "found_at": datetime.utcnow().isoformat(),
                "notified": False,
            })

    except Exception as e:
        print(f"[{uni['name']}] Error: {e}")

    return jobs


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("📡 Fetching jobs from BDJobs...")
    new_jobs = scrape_bdjobs()

    print(f"🏫 Scraping {len(UNIVERSITIES)} university websites...")
    for uni in UNIVERSITIES:
        results = scrape_university(uni)
        new_jobs.extend(results)
        if results:
            print(f"  ✅ {uni['name']}: {len(results)} match(es)")
        time.sleep(0.5)

    # Merge with existing data
    existing = load_existing()
    existing_ids = {j["id"] for j in existing["jobs"]}

    added = []
    for job in new_jobs:
        if job["id"] not in existing_ids:
            existing["jobs"].insert(0, job)
            added.append(job)
            existing_ids.add(job["id"])

    existing["last_updated"] = datetime.utcnow().isoformat()

    # Keep latest 500 jobs only
    existing["jobs"] = existing["jobs"][:500]

    save_data(existing)
    print(f"\n✅ Done. {len(added)} new job(s) found.")

    # Save new jobs list for notifier
    with open("new_jobs.json", "w", encoding="utf-8") as f:
        json.dump(added, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
