#!/usr/bin/env python3
"""Damir Job Hunter V9. No AI, no packages, no passwords, no cost.

Every run shows the jobs in three places:
  1. Actions run page -> Summary       (always works, nothing to set up)
  2. Web page (GitHub Pages)           (needs Settings -> Pages -> Source: GitHub Actions)
  3. Email: a comment on the issue "Jobs for Damir" is posted when NEW jobs appear,
     and GitHub emails the comment to you

  python hunter.py         run
  python hunter.py test    check the 60-vacancy benchmark
"""
import functools, html, json, os, re, sys, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ISSUE_TITLE = "Jobs for Damir"
MAX_IN_MAIL = 25                         # jobs listed per email; the rest are on the web page

# =============================== RULES ===============================
REPORT_AT, TIER_A, TIER_B = 25, 50, 35   # score thresholds
TITLE_X = 2                              # a phrase in the job title counts double
CONTEXT_CAP = 25                         # max bonus for employer / location / level

TRACKS = {                               # phrase: weight
  "Construction/PM": {
    "construction manager": 20, "construction engineer": 20, "construction specialist": 18,
    "project manager infrastructure": 20, "project manager construction": 20,
    "construction management": 14, "construction supervision": 12, "site supervision": 12,
    "site engineer": 16, "resident engineer": 16, "supervision engineer": 16, "works engineer": 14,
    "rehabilitation engineer": 16, "clerk of works": 14, "engineering officer": 12,
    "engineering associate": 12, "engineering specialist": 14, "construction": 6,
    "rehabilitation": 6, "reconstruction": 6, "renovation": 5, "civil works": 8, "capital works": 6,
    "contractor": 3, "contractors": 3, "works": 2, "qa/qc": 5, "quality control": 4,
    "health and safety": 3, "hse": 3, "handover": 4, "project controls": 8, "scheduling": 3,
    "cost control": 4, "progress reports": 3},
  "Infrastructure": {
    "infrastructure engineer": 20, "civil engineer": 20, "structural engineer": 20,
    "road engineer": 18, "highway engineer": 18, "bridge engineer": 18, "transport engineer": 14,
    "building services engineer": 16, "mep engineer": 16, "geotechnical engineer": 16,
    "energy efficiency engineer": 14, "infrastructure specialist": 14, "infrastructure": 5,
    "civil engineering": 10, "structural design": 10, "structural engineering": 10,
    "reinforced concrete": 8, "seismic": 6, "foundation design": 5, "roads": 6, "road": 3,
    "bridges": 6, "bridge": 3, "pavement": 6, "mep": 6, "hvac": 5, "plumbing": 4,
    "commissioning": 4, "drainage": 4, "energy efficiency": 4, "solar": 3,
    "public buildings": 5, "public building": 5},
  "WASH infra": {
    "wash engineer": 20, "water engineer": 20, "sanitation engineer": 18, "wash specialist": 12,
    "water supply": 8, "water systems": 7, "sanitation infrastructure": 8, "wastewater": 7,
    "sewerage": 7, "boreholes": 6, "borehole": 6, "water treatment": 7, "pipelines": 4,
    "pipeline": 4, "latrines": 4, "pumping": 4, "water network": 7, "water networks": 7,
    "sanitation": 3, "wash": 3},
  "Contracts/QS": {
    "contract manager": 14, "contracts manager": 14, "quantity surveyor": 18, "cost engineer": 18,
    "procurement specialist": 8, "procurement officer": 6, "fidic": 12, "red book": 6,
    "works contract": 10, "works contracts": 10, "contract administration": 9,
    "contract management": 7, "claims": 5, "variations": 5, "variation order": 6,
    "extension of time": 6, "bill of quantities": 9, "bills of quantities": 9, "boq": 9,
    "boqs": 9, "payment certificate": 7, "payment certificates": 7, "tender documents": 6,
    "tender": 3, "procurement": 3, "cost estimates": 5, "cost planning": 6,
    "engineer determinations": 6, "defects liability": 6},
  "Facilities": {
    "facilities manager": 18, "facility manager": 18, "facilities management": 14, "premises": 6,
    "building maintenance": 8, "maintenance works": 6, "property management": 8,
    "refurbishment": 6, "minor renovations": 6, "fit-out": 6, "common premises": 8,
    "building management": 8},
  "Architecture/Heritage": {
    "architect": 16, "architectural": 8, "architecture": 6, "heritage": 8, "conservation": 6,
    "restoration": 7, "historic buildings": 8, "urban planning": 8, "urban planner": 14,
    "spatial planning": 8, "shelter": 6, "housing reconstruction": 12, "technical drawings": 5,
    "autocad": 4, "bim": 4},
}

CONTEXT = {                              # added only if the technical score is >= 20
  "unops": 8, "unicef": 8, "undp": 6, "iom": 6, "un-habitat": 6, "unhcr": 5, "who": 3, "giz": 5,
  "world bank": 5, "ebrd": 5, "european union": 4, "ipa": 5, "sarajevo": 15,
  "bosnia and herzegovina": 15, "bosnia": 12, "western balkans": 9, "balkans": 7, "remote": 4,
  "home-based": 4, "schools": 4, "preschools": 5, "health facilities": 5, "hospital": 4,
  "p-3": 4, "p-4": 4, "no-c": 4, "no-b": 3, "senior": 3}

SOFT = {                                 # cancelled if the job mentions PHYSICAL works
  "digital public infrastructure": -60, "digital infrastructure": -60, "it infrastructure": -60,
  "cloud": -60, "software": -60, "data platforms": -60, "cybersecurity": -60, "devops": -60,
  "network infrastructure": -60, "solutions architect": -60, "enterprise architect": -60,
  "data architect": -60, "digital transformation": -60, "hygiene promotion": -30,
  "behaviour change": -30, "community outreach": -30, "community engagement": -30,
  "medical supplies": -25, "vaccines": -25, "pharmaceuticals": -25, "it equipment": -25,
  "office supplies": -25, "goods and services": -25}

HARD = [                                 # -80, never cancelled
  "internship", "intern", "internal candidates only", "internal applicants only",
  "medical doctor", "nurse", "driver", "security officer", "software engineer", "data engineer",
  "machine learning", "data scientist", "communications officer", "finance officer",
  "human resources", "hr officer", "translator", "interpreter"]

PHYSICAL = [
  "construction", "civil works", "works contract", "building", "buildings", "site supervision",
  "contractor", "contractors", "concrete", "roads", "bridges", "water supply", "boreholes",
  "sewerage", "wastewater", "latrines", "pipelines", "renovation", "boq", "bill of quantities",
  "structural", "hvac", "plumbing", "pavement", "water systems", "water networks"]

FEEDS = [
  ("UN Careers", "https://careers.un.org/jobfeed?isPage=true"),
  ("UNOPS", "https://rss.careers.unops.org/"),
  ("UNDP Europe & CIS", "https://jobs.undp.org/rss_feeds/RER.xml"),
  ("UNDP Individual Contracts", "https://jobs.undp.org/rss_feeds/ICE.xml"),
  ("UNDP Other Opportunities", "https://jobs.undp.org/rss_feeds/Other_Opportunities.xml"),
  ("UNDP CPR", "https://jobs.undp.org/rss_feeds/CPR.xml"),
]
# =====================================================================


def norm(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or "")).lower().replace("'", " ")
    s = re.sub(r"(?<![a-z0-9])-|-(?![a-z0-9])|[–—]", " ", s)
    return " " + re.sub(r"[^a-z0-9/+-]+", " ", s).strip() + " "


@functools.cache
def rx(p):
    return re.compile(r"(?<![a-z0-9])" + re.escape(norm(p).strip()) + r"(?![a-z0-9])")


def has(text, p):
    return rx(p).search(text) is not None


def score(title, desc=""):
    t, d = norm(title), norm(desc)
    a, why, per = t + d, [], {}
    for track, terms in TRACKS.items():
        s = 0
        for p, w in terms.items():
            if has(t, p):   s += w * TITLE_X; why.append(p)
            elif has(d, p): s += w;           why.append(p)
        per[track] = s
    track, total = max(per.items(), key=lambda x: x[1])
    if total >= 20:
        total += min(CONTEXT_CAP, sum(w for p, w in CONTEXT.items() if has(a, p)))
    if not any(has(a, p) for p in PHYSICAL):
        total += sum({w for p, w in SOFT.items() if has(a, p)})  # each penalty size once
    if any(has(a, p) for p in HARD):
        total -= 80
    tier = "A" if total >= TIER_A else "B" if total >= TIER_B else "C" if total >= REPORT_AT else ""
    return total, tier, track if per[track] else "", why[:6]


CSS = """body{font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:1000px;margin:0 auto;padding:16px;color:#1b1b1b}
h1{margin:0 0 4px}.meta{color:#555;margin:0 0 16px}input{width:100%;padding:10px;font-size:16px;
border:1px solid #bbb;border-radius:8px;box-sizing:border-box;margin-bottom:12px}table{width:100%;
border-collapse:collapse}th,td{text-align:left;padding:8px;border-bottom:1px solid #e3e3e3;vertical-align:top}
th{background:#f4f6f8}.A{background:#1a7f37;color:#fff}.B{background:#bf8700;color:#fff}.C{background:#6e7781;color:#fff}
.t{display:inline-block;min-width:22px;text-align:center;border-radius:6px;font-weight:700;padding:2px 6px}
.new{background:#0969da;color:#fff;border-radius:6px;padding:1px 6px;font-size:12px;margin-right:6px}
.why{color:#666;font-size:12px}.warn{background:#fff8c5;border:1px solid #d4a72c;padding:10px;border-radius:8px}
.ok{color:#1a7f37}.bad{color:#cf222e}a{color:#0969da;text-decoration:none}a:hover{text-decoration:underline}
@media(max-width:640px){.hide{display:none}}"""


def fetch():
    jobs, status = {}, []
    for name, url in FEEDS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 DamirJobHunter/9"})
            items = list(ET.fromstring(urllib.request.urlopen(req, timeout=30).read()).iter("item"))
            for it in items:
                g = lambda n: (it.findtext(n) or "").strip()
                link = g("link") or g("guid")
                if link.startswith("http"):
                    jobs.setdefault(link, (g("title"), g("description") + " " + name, name))
            status.append((name, True, f"{len(items)} listings"))
        except Exception as e:
            status.append((name, False, f"{type(e).__name__}: {str(e)[:80]}"))
    return jobs, status


def benchmark():
    fails = []
    for title, desc, want in CASES:
        s, _, track, _ = score(title, desc)
        if (s >= REPORT_AT) != (want is not None) or (want and track != want):
            fails.append(f"{title}: score {s}, track {track or '-'} (expected {want or 'excluded'})")
    return fails


def md(text):
    return re.sub(r"[\[\]|<>*_`]", " ", text).strip()


def mdlink(url):
    return url.replace(" ", "%20").replace("(", "%28").replace(")", "%29")


def sent_links(memory):
    return set(re.findall(r"\]\((https?://[^)\s]+)\)", memory))


def match(jobs, seen):
    found = []
    for link, (title, desc, src) in jobs.items():
        s, tier, track, why = score(title, desc)
        if s >= REPORT_AT:
            found.append(dict(score=s, tier=tier, track=track, title=title or "(no title)",
                              link=link, source=src, new=mdlink(link) not in seen, why=why))
    found.sort(key=lambda j: (-j["score"], j["title"]))
    return found


# ---------------- GitHub issue = email + memory of jobs already sent ----------------
def api(path, data=None):
    req = urllib.request.Request(
        "https://api.github.com/repos/" + os.environ["GITHUB_REPOSITORY"] + path,
        data=json.dumps(data).encode() if data is not None else None,
        method="POST" if data is not None else "GET",
        headers={"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                 "Accept": "application/vnd.github+json", "User-Agent": "DamirJobHunter/9"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read() or b"null")


def issue_memory():
    """Return (issue_number, text of the issue + all comments). Creates the issue if missing."""
    if not (os.environ.get("GITHUB_TOKEN") and os.environ.get("GITHUB_REPOSITORY")):
        return None, ""
    number = None
    for page in range(1, 11):
        batch = api(f"/issues?state=all&per_page=100&page={page}")
        hit = [i for i in batch if i["title"] == ISSUE_TITLE and "pull_request" not in i]
        if hit:
            number, text = hit[0]["number"], hit[0].get("body") or ""
            break
        if len(batch) < 100:
            break
    if number is None:
        new = api("/issues", {"title": ISSUE_TITLE, "body":
                  "New matching jobs are posted here as comments. GitHub emails each comment to you.\n"
                  "Keep this issue open. Do not delete it: it is also the list of jobs already sent."})
        return new["number"], ""
    for page in range(1, 51):
        batch = api(f"/issues/{number}/comments?per_page=100&page={page}")
        text += "\n".join(c.get("body") or "" for c in batch)
        if len(batch) < 100:
            break
    return number, text


def mail_text(new, status, page_url):
    rows = [f"- **{j['tier']} {j['score']}** · [{md(j['title'])}]({mdlink(j['link'])}) · {j['source']} · {j['track']}"
            for j in new[:MAX_IN_MAIL]]
    more = len(new) - MAX_IN_MAIL
    if more > 0:
        rows.append(f"- … and {more} more on the web page")
    broken = [n for n, ok, _ in status if not ok]
    return "\n".join([f"### {len(new)} new job(s), {datetime.now(timezone.utc):%d %b %Y %H:%M} UTC", ""] + rows
                     + ([""] + [f"Feeds not working: {', '.join(broken)}"] if broken else [])
                     + ([""] + [f"All jobs: {page_url}"] if page_url else []))


# ---------------- outputs ----------------
def summary_md(found, status, fails, scanned, page_url, issue):
    new = sum(j["new"] for j in found)
    L = [f"# {ISSUE_TITLE}", "",
         f"**{len(found)}** matching jobs · **{new}** new · {scanned} listings scanned", ""]
    if page_url:
        L += [f"Web page: {page_url}", ""]
    if fails:
        L += ["> ⚠️ Scoring test failed: " + "; ".join(fails), ""]
    L += ["| Tier | Score | Job | Source | Track |", "|---|---:|---|---|---|"]
    L += [f"| {j['tier']} | {j['score']} | {'🆕 ' if j['new'] else ''}[{md(j['title'])}]({mdlink(j['link'])}) "
          f"| {j['source']} | {j['track']} |" for j in found]
    if not found:
        L += ["| – | – | No matching jobs right now | – | – |"]
    L += ["", "**Feeds**", ""] + [f"- {'✅' if ok else '❌'} {n}: {m}" for n, ok, m in status]
    L += ["", f"Email: {issue}"]
    return "\n".join(L) + "\n"


def page(found, status, fails, scanned, now):
    e = html.escape
    rows = "".join(
        f"<tr><td><span class='t {j['tier']}'>{j['tier']}</span></td><td>{j['score']}</td>"
        f"<td>{'<span class=new>NEW</span>' if j['new'] else ''}<a href='{e(j['link'])}' target=_blank rel=noopener>"
        f"{e(j['title'])}</a><div class=why>{e(', '.join(j['why']))}</div></td>"
        f"<td class=hide>{e(j['track'])}</td><td class=hide>{e(j['source'])}</td></tr>"
        for j in found) or "<tr><td colspan=5>No matching jobs right now. See feed status below.</td></tr>"
    feeds = "".join(f"<li class={'ok' if ok else 'bad'}>{'✔' if ok else '✘'} {e(n)}: {e(m)}</li>" for n, ok, m in status)
    warn = ("<p class=warn>⚠ Scoring test failed, results may be wrong:<br>" + "<br>".join(map(e, fails)) + "</p>") if fails else ""
    new = sum(j["new"] for j in found)
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>{ISSUE_TITLE}</title><style>{CSS}</style></head><body>
<h1>{ISSUE_TITLE}</h1><p class=meta>Updated {now:%d %b %Y, %H:%M} UTC · <b>{len(found)}</b> matching jobs · <b>{new}</b> new · {scanned} listings scanned</p>
{warn}<input id=q placeholder="Filter: e.g. UNOPS, WASH, Sarajevo, A" oninput="f()">
<table id=t><tr><th>Tier</th><th>Score</th><th>Job</th><th class=hide>Track</th><th class=hide>Source</th></tr>{rows}</table>
<h3>Feed status</h3><ul>{feeds}</ul>
<p class=meta>Tier A ≥ {TIER_A} · B ≥ {TIER_B} · C ≥ {REPORT_AT}. A tier is reading order, not an apply decision. Always check eligibility and deadline on the original vacancy.</p>
<script>function f(){{const q=document.getElementById('q').value.toLowerCase();
document.querySelectorAll('#t tr:not(:first-child)').forEach(r=>r.style.display=r.innerText.toLowerCase().includes(q)?'':'none')}}</script>
</body></html>"""


def run():
    now = datetime.now(timezone.utc)
    owner, _, repo = os.environ.get("GITHUB_REPOSITORY", "").partition("/")
    page_url = f"https://{owner.lower()}.github.io/{repo}/" if repo else ""
    jobs, status = fetch()
    fails = benchmark()

    try:
        number, memory = issue_memory()
        issue = f"issue #{number}" if number else "off (only runs on GitHub)"
    except Exception as e:
        number, memory, issue = None, "", f"FAILED to read issue ({type(e).__name__}: {e})"
    found = match(jobs, sent_links(memory))
    new = [j for j in found if j["new"]]

    if number and new:
        try:
            api(f"/issues/{number}/comments", {"body": mail_text(new, status, page_url)})
            issue += f": {len(new)} new job(s) posted, GitHub will email you"
        except Exception as e:
            issue += f": FAILED to post ({type(e).__name__}: {e})"
    elif number:
        issue += ": nothing new, no email"

    Path("site").mkdir(exist_ok=True)
    Path("site/index.html").write_text(page(found, status, fails, len(jobs), now), encoding="utf-8")
    md = summary_md(found, status, fails, len(jobs), page_url, issue)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(md)
    print(f"{len(found)} matching, {len(new)} new, {len(jobs)} scanned")
    for n, ok, m in status:
        print(("  ok   " if ok else "  FAIL ") + f"{n}: {m}")
    print("email:", issue)


# ============================= BENCHMARK =============================
# (title, description + source, expected track, or None = must be excluded)
CASES = [
  ("Construction Engineer", "Supervise rehabilitation of preschools; review BoQ, payment certificates, QA/QC, handover. Sarajevo, NO-B. UNICEF", "Construction/PM"),
  ("Project Manager (Infrastructure)", "Manage civil works portfolio, construction supervision, contract management, procurement of works. Western Balkans. UNOPS", "Construction/PM"),
  ("Construction Manager", "Lead site teams, contractors, schedule, HSE and cost control for a hospital construction project.", "Construction/PM"),
  ("Senior Construction Specialist", "Technical oversight of construction of schools and health facilities; review designs and contractor reports. World Bank", "Construction/PM"),
  ("Site Engineer", "Daily site supervision, quality control, concrete works, progress reports.", "Construction/PM"),
  ("Resident Engineer", "FIDIC Red Book works contract; supervise contractor, certify payments, approve variations. EBRD", "Construction/PM"),
  ("Rehabilitation Engineer", "Rehabilitation of collective centres and public buildings; prepare BoQs and supervise contractors. UNHCR", "Construction/PM"),
  ("Engineering Associate", "Support construction supervision of civil works, prepare BoQ and site reports. UNOPS", "Construction/PM"),
  ("Clerk of Works", "Inspect construction quality on building renovation sites.", "Construction/PM"),
  ("Project Controls Manager - Construction", "Scheduling, cost control, risk and progress reporting on construction programme.", "Construction/PM"),
  ("Senior Project Manager - Construction", "Deliver construction of vocational schools; contractor management, works contracts, quality control. GIZ", "Construction/PM"),
  ("Engineering Officer", "Prepare bills of quantities and supervise rehabilitation of collective centres by contractors. IOM", "Construction/PM"),
  ("Civil Engineer", "Design and supervise civil works for shelters and drainage. IOM", "Infrastructure"),
  ("Structural Engineer", "Structural design of buildings, reinforced concrete, seismic assessment, site inspections.", "Infrastructure"),
  ("Road Engineer", "Road rehabilitation, pavement design, bridges, supervision of works.", "Infrastructure"),
  ("Bridge Engineer", "Inspection and rehabilitation design of bridges.", "Infrastructure"),
  ("Building Services Engineer", "MEP coordination, HVAC, plumbing, commissioning on construction sites.", "Infrastructure"),
  ("Infrastructure Specialist", "Oversee energy efficiency rehabilitation of public buildings in Bosnia and Herzegovina. UNDP", "Infrastructure"),
  ("Infrastructure Engineer", "Urban infrastructure, drainage and roads upgrading. UN-Habitat", "Infrastructure"),
  ("Energy Efficiency Engineer", "Energy audits and renovation of public buildings, solar installations, supervision of contractors. UNDP", "Infrastructure"),
  ("Highway Engineer", "Supervise highway rehabilitation, pavement and drainage works. EBRD", "Infrastructure"),
  ("Geotechnical Engineer", "Site investigations and foundation design for buildings.", "Infrastructure"),
  ("WASH Engineer", "Design and supervise water supply and sanitation infrastructure in schools. UNICEF", "WASH infra"),
  ("Water and Sanitation Engineer", "Rehabilitation of water networks, boreholes, pumping stations. ICRC", "WASH infra"),
  ("WASH Specialist (Infrastructure)", "Lead construction of water systems, wastewater treatment and latrines; manage contractors. UNICEF", "WASH infra"),
  ("Water Engineer", "Water treatment plant upgrades and pipeline construction.", "WASH infra"),
  ("Sanitation Engineer", "Design and construction of sewerage systems and latrines in camps. UNHCR", "WASH infra"),
  ("Quantity Surveyor", "Cost planning, bills of quantities, payment certificates, variations.", "Contracts/QS"),
  ("FIDIC Contract Manager", "Administer FIDIC Red Book construction contracts, claims, variations, engineer determinations, extension of time.", "Contracts/QS"),
  ("Procurement Specialist - Infrastructure", "Procure civil works, prepare tender documents for construction contracts, evaluate BoQs. UNOPS", "Contracts/QS"),
  ("Cost Engineer", "Cost estimates, cost control and claims on infrastructure projects.", "Contracts/QS"),
  ("Contracts Manager", "Works contracts administration, contractor claims and defects liability.", "Contracts/QS"),
  ("Facilities Manager", "Capital works, building maintenance, contractor management, minor renovations, health and safety. UNICEF", "Facilities"),
  ("Common Premises Specialist", "Plan fit-out and refurbishment of UN common premises; manage works contractors. UNDP", "Facilities"),
  ("Property Management Officer", "Building management, maintenance works and contractor oversight.", "Facilities"),
  ("Facility Manager", "Building maintenance, HVAC contracts, refurbishment of offices.", "Facilities"),
  ("Architect - Rehabilitation", "Architectural design and rehabilitation of schools and heritage buildings; tender documentation. UNDP", "Architecture/Heritage"),
  ("Heritage Conservation Architect", "Restoration of historic buildings, conservation plans, site supervision. UNESCO", "Architecture/Heritage"),
  ("Shelter Programme Manager", "Housing reconstruction, contractor oversight, budget and procurement. UNHCR", "Architecture/Heritage"),
  ("Urban Planner", "Spatial planning and urban regeneration projects. UN-Habitat", "Architecture/Heritage"),
  ("Restoration Architect", "Restoration and conservation of historic buildings, technical drawings in AutoCAD.", "Architecture/Heritage"),
  ("Infrastructure Specialist - Digital Public Infrastructure", "Digital public infrastructure, data governance, digital transformation. UNDP", None),
  ("Project Manager", "Software implementation project for cloud migration in Sarajevo. UNOPS", None),
  ("WASH Programme Officer", "Hygiene promotion, behaviour change, community outreach. UNICEF", None),
  ("Solutions Architect", "Cloud architecture, software systems, data platforms.", None),
  ("IT Infrastructure Engineer", "Network infrastructure, servers, cybersecurity. WHO", None),
  ("Procurement Officer", "Procurement of medical supplies, vaccines and pharmaceuticals. WHO", None),
  ("Construction Engineering Intern", "Internship supporting site supervision. UNOPS", None),
  ("Communications Officer", "Communications for school construction programme. UNICEF", None),
  ("Driver", "Drive staff to construction sites in Bosnia and Herzegovina. UNDP", None),
  ("Finance Officer", "Financial reporting for infrastructure portfolio. UNOPS", None),
  ("Programme Manager - Social Protection", "Social welfare reform, policy dialogue, Sarajevo. UNICEF", None),
  ("Data Engineer", "Build data pipelines and pipeline orchestration.", None),
  ("Enterprise Architect", "Enterprise architecture and digital transformation. UNDP", None),
  ("Construction Engineer (Internal Candidates Only)", "Construction supervision. Internal candidates only. UNICEF", None),
  ("Cloud Infrastructure Engineer", "Azure cloud infrastructure, DevOps, Sarajevo. UNICEF", None),
  ("Hygiene Promotion Officer", "Hygiene promotion and community engagement in WASH programmes. UNICEF", None),
  ("Procurement Assistant", "Purchase office supplies and IT equipment, goods and services. WHO", None),
  ("Human Resources Officer", "Recruitment for infrastructure projects. UNOPS", None),
  ("Data Architect", "Data architecture and data platforms for digital transformation. UNDP", None),
]


def test():
    fails = benchmark()
    print(*fails, f"benchmark {len(CASES) - len(fails)}/{len(CASES)}", sep="\n")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    test() if sys.argv[1:] == ["test"] else run()
