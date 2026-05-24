"""
Builds the static GitHub Pages dashboard from jobs.json
"""

import json
import os
from datetime import datetime

DATA_FILE = "docs/jobs.json"
OUTPUT    = "docs/index.html"


def load_jobs() -> dict:
    if not os.path.exists(DATA_FILE):
        return {"jobs": [], "last_updated": ""}
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def job_card(job: dict) -> str:
    source_badge = {
        "BDJobs": "#e74c3c",
        "BUET":   "#2c3e50",
        "BRAC University": "#8e44ad",
    }.get(job["source"], "#2980b9")

    return f"""
    <div class="card" onclick="window.open('{job['url']}','_blank')">
      <span class="badge" style="background:{source_badge}">{job['source']}</span>
      <h3>{job['title']}</h3>
      <p class="inst">🏫 {job['institution']}</p>
      <p class="date">📅 Found: {job['found_at'][:10]}</p>
      <a href="{job['url']}" target="_blank" onclick="event.stopPropagation()">
        View Circular →
      </a>
    </div>"""


def build():
    data = load_jobs()
    jobs = data.get("jobs", [])
    updated = data.get("last_updated", "")[:16].replace("T", " ") + " UTC"

    cards_html = "\n".join(job_card(j) for j in jobs) if jobs else (
        '<p class="empty">No jobs found yet. Check back soon! 🔄</p>'
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>BD CSE Lecturer Job Tracker</title>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet"/>
  <style>
    :root {{
      --bg: #0d1117;
      --surface: #161b22;
      --border: #30363d;
      --accent: #58a6ff;
      --accent2: #3fb950;
      --text: #e6edf3;
      --muted: #8b949e;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: 'Space Grotesk', sans-serif;
      min-height: 100vh;
    }}
    header {{
      background: linear-gradient(135deg, #0d1117 0%, #1a2332 100%);
      border-bottom: 1px solid var(--border);
      padding: 2rem;
      text-align: center;
    }}
    header h1 {{
      font-size: 2rem;
      font-weight: 700;
      background: linear-gradient(90deg, var(--accent), var(--accent2));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 0.5rem;
    }}
    header p {{ color: var(--muted); font-size: 0.9rem; }}
    .meta {{
      display: flex;
      gap: 1rem;
      justify-content: center;
      flex-wrap: wrap;
      margin-top: 1rem;
    }}
    .meta span {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 0.3rem 0.9rem;
      font-size: 0.82rem;
      color: var(--muted);
    }}
    .meta span b {{ color: var(--accent); }}
    .filters {{
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
      padding: 1.5rem 2rem;
      max-width: 1200px;
      margin: 0 auto;
      align-items: center;
    }}
    .filters input {{
      flex: 1;
      min-width: 200px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.6rem 1rem;
      color: var(--text);
      font-family: inherit;
      font-size: 0.9rem;
      outline: none;
    }}
    .filters input:focus {{ border-color: var(--accent); }}
    .filters select {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.6rem 1rem;
      color: var(--text);
      font-family: inherit;
      font-size: 0.9rem;
      outline: none;
      cursor: pointer;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 1rem;
      padding: 0 2rem 3rem;
      max-width: 1200px;
      margin: 0 auto;
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.25rem;
      cursor: pointer;
      transition: border-color 0.2s, transform 0.2s, box-shadow 0.2s;
      position: relative;
    }}
    .card:hover {{
      border-color: var(--accent);
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(88,166,255,0.1);
    }}
    .badge {{
      display: inline-block;
      color: white;
      font-size: 0.7rem;
      font-weight: 600;
      padding: 0.2rem 0.6rem;
      border-radius: 4px;
      margin-bottom: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .card h3 {{
      font-size: 0.95rem;
      font-weight: 600;
      line-height: 1.4;
      margin-bottom: 0.5rem;
      color: var(--text);
    }}
    .card .inst {{
      font-size: 0.85rem;
      color: var(--muted);
      margin-bottom: 0.3rem;
    }}
    .card .date {{
      font-size: 0.78rem;
      color: var(--muted);
      margin-bottom: 0.75rem;
      font-family: 'JetBrains Mono', monospace;
    }}
    .card a {{
      color: var(--accent);
      font-size: 0.85rem;
      text-decoration: none;
      font-weight: 600;
    }}
    .card a:hover {{ text-decoration: underline; }}
    .empty {{
      text-align: center;
      color: var(--muted);
      padding: 3rem;
      grid-column: 1/-1;
      font-size: 1rem;
    }}
    footer {{
      text-align: center;
      padding: 1.5rem;
      border-top: 1px solid var(--border);
      color: var(--muted);
      font-size: 0.8rem;
    }}
  </style>
</head>
<body>

<header>
  <h1>🎓 BD CSE/IT Lecturer Job Tracker</h1>
  <p>Auto-fetches from BDJobs + 40+ university websites every 3 hours</p>
  <div class="meta">
    <span>📋 Total Jobs: <b>{len(jobs)}</b></span>
    <span>🔄 Last updated: <b>{updated}</b></span>
    <span>🏫 <b>40+</b> universities monitored</span>
  </div>
</header>

<div class="filters">
  <input type="text" id="search" placeholder="🔍 Search by title or institution..."/>
  <select id="sourceFilter">
    <option value="">All Sources</option>
    <option value="BDJobs">BDJobs</option>
    <option value="university">University Websites</option>
  </select>
</div>

<div class="grid" id="grid">
{cards_html}
</div>

<footer>
  Built with ❤️ · Auto-updates via GitHub Actions · 
  <a href="https://github.com" style="color:var(--accent)">View Source</a>
</footer>

<script>
  const cards = document.querySelectorAll('.card');
  const search = document.getElementById('search');
  const sourceFilter = document.getElementById('sourceFilter');

  function filter() {{
    const q = search.value.toLowerCase();
    const src = sourceFilter.value.toLowerCase();
    cards.forEach(c => {{
      const text = c.innerText.toLowerCase();
      const badge = c.querySelector('.badge').innerText.toLowerCase();
      const matchQ = !q || text.includes(q);
      const matchS = !src || (src === 'university' ? badge !== 'bdjobs' : badge.includes(src));
      c.style.display = matchQ && matchS ? '' : 'none';
    }});
  }}

  search.addEventListener('input', filter);
  sourceFilter.addEventListener('change', filter);

  // Auto-refresh every 30 minutes
  setTimeout(() => location.reload(), 30 * 60 * 1000);
</script>
</body>
</html>"""

    os.makedirs("docs", exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Dashboard built: {OUTPUT} ({len(jobs)} jobs)")


if __name__ == "__main__":
    build()
