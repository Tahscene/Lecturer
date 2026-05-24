"""
Run this ONCE to wipe all old/garbage jobs from jobs.json
python reset_jobs.py
"""
import json, os

DATA_FILE = "docs/jobs.json"
clean = {"jobs": [], "last_updated": ""}
os.makedirs("docs", exist_ok=True)
with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(clean, f)
print("✅ jobs.json cleared. Fresh start!")
