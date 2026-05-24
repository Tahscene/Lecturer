"""Builds the GitHub Pages dashboard from docs/jobs.json"""

import json, os
from datetime import datetime

DATA_FILE = "docs/jobs.json"
OUTPUT    = "docs/index.html"

def load_jobs():
    if not os.path.exists(DATA_FILE):
        return {"jobs": [], "last_updated": ""}
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)

def time_ago(iso: str) -> str:
    try:
        from datetime import timezone, timedelta
        dt  = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff = now - dt
        d = diff.days
        h = diff.seconds // 3600
        if d == 0 and h == 0: return "Just now"
        if d == 0: return f"{h}h ago"
        if d == 1: return "Yesterday"
        if d < 7:  return f"{d} days ago"
        if d < 30: return f"{d//7}w ago"
        return f"{d//30}mo ago"
    except:
        return ""

SOURCE_COLORS = {
    "BDJobs":       "#059669",
    "Google News":  "#db2777",
}

def source_color(src):
    return SOURCE_COLORS.get(src, "#7c3aed")

def job_card(job):
    ago   = time_ago(job.get("found_at", ""))
    color = source_color(job["source"])
    url   = job["url"]
    inst  = job["institution"]
    title = job["title"]
    src   = job["source"]
    return f'''
    <article class="card" onclick="window.open('{url}','_blank')">
      <div class="card-top">
        <span class="badge" style="background:{color}">{src}</span>
        <span class="ago">{ago}</span>
      </div>
      <h3 class="card-title">{title}</h3>
      <p class="card-inst">🏫 {inst}</p>
      <div class="card-footer">
        <a class="view-btn" href="{url}" target="_blank" onclick="event.stopPropagation()">
          View Circular ↗
        </a>
      </div>
    </article>'''

def build():
    data  = load_jobs()
    jobs  = data.get("jobs", [])
    upd   = data.get("last_updated", "")[:16].replace("T", " ") + " UTC" if data.get("last_updated") else "—"
    cards = "\n".join(job_card(j) for j in jobs) if jobs else \
            '<p class="empty">✨ No new circulars right now — check back soon!</p>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>CSE Lecturer Jobs · BD</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet"/>
<style>
:root{{
  --em:  #059669;   /* emerald */
  --em2: #10b981;
  --em3: #d1fae5;
  --pk:  #db2777;   /* pink */
  --pk2: #f472b6;
  --pk3: #fce7f3;
  --bg:  #f8fffe;
  --card:#ffffff;
  --border:#e2e8f0;
  --text:#1e293b;
  --muted:#64748b;
  --radius:16px;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{
  font-family:'DM Sans',sans-serif;
  background:var(--bg);
  color:var(--text);
  min-height:100vh;
  overflow-x:hidden;
}}

/* ── Cute background pattern ── */
body::before{{
  content:'';
  position:fixed;
  inset:0;
  z-index:0;
  background-image:
    radial-gradient(circle at 20% 20%, #d1fae580 0%, transparent 40%),
    radial-gradient(circle at 80% 10%, #fce7f360 0%, transparent 35%),
    radial-gradient(circle at 60% 80%, #d1fae540 0%, transparent 40%),
    radial-gradient(circle at 10% 75%, #fce7f340 0%, transparent 35%);
  pointer-events:none;
}}

/* floating deco blobs */
.blob{{
  position:fixed;
  border-radius:50%;
  filter:blur(60px);
  opacity:.18;
  z-index:0;
  pointer-events:none;
  animation:drift 12s ease-in-out infinite alternate;
}}
.blob1{{width:340px;height:340px;background:var(--em2);top:-100px;left:-80px;}}
.blob2{{width:280px;height:280px;background:var(--pk2);top:60px;right:-60px;animation-delay:3s;}}
.blob3{{width:220px;height:220px;background:var(--em2);bottom:80px;left:30%;animation-delay:6s;}}
.blob4{{width:180px;height:180px;background:var(--pk2);bottom:-60px;right:15%;animation-delay:2s;}}
@keyframes drift{{from{{transform:translate(0,0) scale(1)}}to{{transform:translate(20px,15px) scale(1.08)}}}}

/* dots pattern overlay */
body::after{{
  content:'';
  position:fixed;inset:0;z-index:0;
  background-image:radial-gradient(circle, #05966920 1px, transparent 1px);
  background-size:28px 28px;
  pointer-events:none;
  opacity:.5;
}}

/* ── Layout ── */
.page{{position:relative;z-index:1}}

/* ── Hero ── */
header{{
  text-align:center;
  padding:4rem 1.5rem 2.5rem;
}}
.hero-pill{{
  display:inline-flex;align-items:center;gap:.5rem;
  background:linear-gradient(135deg,var(--em3),var(--pk3));
  border:1.5px solid #10b98140;
  border-radius:99px;
  padding:.35rem 1.1rem;
  font-size:.78rem;
  font-weight:600;
  color:var(--em);
  margin-bottom:1.4rem;
  letter-spacing:.03em;
  text-transform:uppercase;
}}
.hero-pill span{{font-size:1rem}}
header h1{{
  font-family:'Playfair Display',serif;
  font-size:clamp(2rem,5vw,3.4rem);
  font-weight:900;
  line-height:1.15;
  margin-bottom:1rem;
  background:linear-gradient(135deg,var(--em) 0%,var(--pk) 100%);
  -webkit-background-clip:text;
  -webkit-text-fill-color:transparent;
  background-clip:text;
}}
.subtitle{{
  color:var(--muted);
  font-size:1rem;
  max-width:460px;
  margin:0 auto 2rem;
  line-height:1.6;
}}
.stats{{
  display:inline-flex;
  gap:.75rem;
  flex-wrap:wrap;
  justify-content:center;
}}
.stat{{
  background:white;
  border:1.5px solid var(--border);
  border-radius:12px;
  padding:.5rem 1rem;
  font-size:.82rem;
  color:var(--muted);
  box-shadow:0 2px 8px #0000000a;
}}
.stat b{{color:var(--em);font-weight:700;}}

/* ── Search bar ── */
.search-wrap{{
  max-width:680px;
  margin:0 auto 2.5rem;
  padding:0 1.5rem;
}}
.search-box{{
  display:flex;
  gap:.75rem;
  background:white;
  border:2px solid var(--border);
  border-radius:14px;
  padding:.6rem .6rem .6rem 1.1rem;
  box-shadow:0 4px 20px #05966915;
  transition:border-color .2s;
}}
.search-box:focus-within{{border-color:var(--em);}}
.search-box input{{
  flex:1;border:none;outline:none;
  font-family:inherit;font-size:.95rem;color:var(--text);
  background:transparent;
}}
.search-box input::placeholder{{color:#94a3b8;}}
.filter-btn{{
  background:linear-gradient(135deg,var(--em),var(--em2));
  color:white;border:none;border-radius:10px;
  padding:.45rem 1.1rem;font-size:.82rem;font-weight:600;
  cursor:pointer;font-family:inherit;white-space:nowrap;
  transition:opacity .2s;
}}
.filter-btn:hover{{opacity:.88;}}
.src-filters{{
  display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.75rem;
}}
.chip{{
  border:1.5px solid var(--border);background:white;
  border-radius:99px;padding:.3rem .9rem;
  font-size:.78rem;font-weight:500;color:var(--muted);
  cursor:pointer;transition:all .18s;
}}
.chip.active{{background:var(--em);border-color:var(--em);color:white;}}

/* ── Grid ── */
.grid{{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(310px,1fr));
  gap:1rem;
  padding:0 1.5rem 4rem;
  max-width:1200px;
  margin:0 auto;
}}
.card{{
  background:var(--card);
  border:1.5px solid var(--border);
  border-radius:var(--radius);
  padding:1.3rem;
  cursor:pointer;
  transition:border-color .2s,transform .2s,box-shadow .2s;
  position:relative;
  overflow:hidden;
}}
.card::before{{
  content:'';
  position:absolute;inset:0;
  background:linear-gradient(135deg,var(--em3)00,var(--em3)00);
  transition:background .25s;
  pointer-events:none;
}}
.card:hover{{
  border-color:var(--em);
  transform:translateY(-3px);
  box-shadow:0 12px 32px #05966918;
}}
.card:hover::before{{
  background:linear-gradient(135deg,#d1fae518,#fce7f318);
}}
.card-top{{
  display:flex;align-items:center;
  justify-content:space-between;
  margin-bottom:.9rem;
}}
.badge{{
  color:white;font-size:.7rem;font-weight:700;
  padding:.22rem .7rem;border-radius:99px;
  text-transform:uppercase;letter-spacing:.04em;
}}
.ago{{
  font-size:.75rem;color:var(--muted);
  font-weight:500;
}}
.card-title{{
  font-size:.95rem;font-weight:600;
  line-height:1.45;color:var(--text);
  margin-bottom:.55rem;
}}
.card-inst{{
  font-size:.83rem;color:var(--muted);
  margin-bottom:1rem;
}}
.card-footer{{display:flex;justify-content:flex-end;}}
.view-btn{{
  display:inline-block;
  background:linear-gradient(135deg,var(--em),var(--pk));
  color:white;text-decoration:none;
  font-size:.8rem;font-weight:600;
  padding:.38rem .9rem;border-radius:8px;
  transition:opacity .18s;
}}
.view-btn:hover{{opacity:.85;}}
.empty{{
  text-align:center;color:var(--muted);
  padding:4rem 2rem;grid-column:1/-1;
  font-size:1rem;line-height:2;
}}
footer{{
  text-align:center;padding:1.5rem;
  border-top:1px solid var(--border);
  color:var(--muted);font-size:.8rem;
  position:relative;z-index:1;
}}
footer a{{color:var(--em);text-decoration:none;}}

/* cute floating hearts/stars deco */
.deco{{
  position:fixed;
  font-size:1.4rem;
  opacity:.13;
  pointer-events:none;
  z-index:0;
  animation:float 6s ease-in-out infinite alternate;
}}
@keyframes float{{from{{transform:translateY(0) rotate(0deg)}}to{{transform:translateY(-18px) rotate(12deg)}}}}
</style>
</head>
<body>
<div class="blob blob1"></div>
<div class="blob blob2"></div>
<div class="blob blob3"></div>
<div class="blob blob4"></div>
<div class="deco" style="top:12%;left:6%;animation-delay:0s">🌿</div>
<div class="deco" style="top:8%;right:8%;animation-delay:2s">💗</div>
<div class="deco" style="top:45%;left:3%;animation-delay:4s">✨</div>
<div class="deco" style="bottom:20%;right:5%;animation-delay:1s">🌸</div>
<div class="deco" style="bottom:35%;left:8%;animation-delay:3s">💚</div>

<div class="page">
<header>
  <div class="hero-pill"><span>🎓</span> CSE / IT · Bangladesh</div>
  <h1>Hello Ma'am,<br>Find Lecturer Jobs<br>Before Others ✨</h1>
  <p class="subtitle">
    Auto-fetches from BDJobs + {len(UNIVERSITIES) if False else "50+"} universities every 3 hours —
    only <strong>CSE &amp; IT Lecturer</strong> positions, always fresh.
  </p>
  <div class="stats">
    <div class="stat">📋 <b>{len(jobs)}</b> active jobs</div>
    <div class="stat">🔄 Updated <b>{upd}</b></div>
    <div class="stat">🏫 <b>50+</b> universities</div>
    <div class="stat">⏱ Checks every <b>3 hrs</b></div>
  </div>
</header>

<div class="search-wrap">
  <div class="search-box">
    <input type="text" id="q" placeholder="Search by title or university..." oninput="filter()"/>
    <button class="filter-btn" onclick="document.getElementById('q').value='';filter()">Clear</button>
  </div>
  <div class="src-filters" id="chips"></div>
</div>

<div class="grid" id="grid">
{cards}
</div>

<footer>
  Made with 💚 &amp; 💗 · Auto-updates via GitHub Actions ·
  <a href="https://github.com" target="_blank">View Source</a>
</footer>
</div>

<script>
const cards   = [...document.querySelectorAll('.card')];
const qInput  = document.getElementById('q');
const chipsEl = document.getElementById('chips');

// Build source chips
const sources = [...new Set(cards.map(c => c.querySelector('.badge').innerText))];
let activeSrc = null;

function buildChips() {{
  chipsEl.innerHTML = '';
  const all = document.createElement('button');
  all.className = 'chip' + (activeSrc === null ? ' active' : '');
  all.textContent = 'All';
  all.onclick = () => {{ activeSrc = null; buildChips(); filter(); }};
  chipsEl.appendChild(all);

  sources.forEach(src => {{
    const b = document.createElement('button');
    b.className = 'chip' + (activeSrc === src ? ' active' : '');
    b.textContent = src;
    b.onclick = () => {{ activeSrc = src; buildChips(); filter(); }};
    chipsEl.appendChild(b);
  }});
}}

function filter() {{
  const q = qInput.value.toLowerCase();
  cards.forEach(c => {{
    const text = c.innerText.toLowerCase();
    const src  = c.querySelector('.badge').innerText;
    const mQ   = !q || text.includes(q);
    const mS   = activeSrc === null || src === activeSrc;
    c.style.display = mQ && mS ? '' : 'none';
  }});
}}

buildChips();
// Auto-refresh every 30 min
setTimeout(() => location.reload(), 30 * 60 * 1000);
</script>
</body>
</html>"""

    os.makedirs("docs", exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Dashboard built → {OUTPUT}  ({len(jobs)} jobs)")

if __name__ == "__main__":
    build()
