#!/usr/bin/env python3
"""Build SixSheet from data.json.

- Validates data.json (structure + required fields). Exits 1 on hard errors.
- Regenerates index.html from tools/template.html (embedded fallback data).
- Writes static, crawlable guide pages to guide/ and a sitemap.xml.

Usage: python3 tools/build.py   (run from the repo root)
"""
import html, json, sys, datetime, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://sixsheet.app/"
ARRAYS = ["facts", "prep", "codes", "money", "tracker", "finds", "gear"]
NEEDS_SOURCE = ["codes", "money", "finds", "facts"]

errors, warnings = [], []
try:
    D = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
except Exception as e:
    print(f"ERROR: data.json is not valid JSON: {e}")
    sys.exit(1)

for k in ["site", "launch"]:
    if not isinstance(D.get(k), dict):
        errors.append(f"missing object '{k}'")
for k in ARRAYS:
    if not isinstance(D.get(k), list):
        errors.append(f"'{k}' must be an array")
if errors:
    print("ERRORS:\n- " + "\n- ".join(errors)); sys.exit(1)

def check_src(sec, i, o):
    if not o.get("source") or not str(o.get("url", "")).startswith("http"):
        warnings.append(f"{sec}[{i}] '{o.get('name') or o.get('title') or o.get('label')}' has no source/url")

for sec in NEEDS_SOURCE:
    for i, o in enumerate(D[sec]):
        if not isinstance(o, dict):
            errors.append(f"{sec}[{i}] is not an object"); continue
        check_src(sec, i, o)
for i, c in enumerate(D["codes"]):
    if not c.get("name"): errors.append(f"codes[{i}] missing name")
    if not any(c.get(k) for k in ("ps", "xbox", "phone")): warnings.append(f"codes[{i}] has no input for any platform")
for i, m in enumerate(D["money"]):
    if not m.get("title"): errors.append(f"money[{i}] missing title")
seen = set()
for ci, cat in enumerate(D["tracker"]):
    for ii, it in enumerate(cat.get("items", [])):
        iid = it.get("id")
        if not iid: errors.append(f"tracker[{ci}].items[{ii}] missing id")
        elif iid in seen: errors.append(f"duplicate tracker id '{iid}'")
        seen.add(iid)
for i, f in enumerate(D["facts"]):
    if isinstance(f, dict) and len(str(f.get("short", ""))) > 14:
        warnings.append(f"facts[{i}] 'short' is over 14 characters; it will wrap on phones")
st = D.get("storage")
if st is not None:
    if not isinstance(st, dict) or not isinstance(st.get("sizeGb"), (int, float)) or not isinstance(st.get("consoles"), list):
        errors.append("'storage' needs a numeric sizeGb and a consoles array")
    else:
        for i, c in enumerate(st["consoles"]):
            if not (isinstance(c, dict) and c.get("id") and c.get("name") and isinstance(c.get("usableGb"), (int, float)) and c["usableGb"] > 0):
                errors.append(f"storage.consoles[{i}] needs id, name and a positive usableGb")
import re as _re
ads = str(D["site"].get("adsenseClient", "") or "").strip()
if ads and not _re.fullmatch(r"ca-pub-\d{16}", ads):
    errors.append("site.adsenseClient must look like ca-pub-1234567890123456 (or be empty)")
aff = str(D["site"].get("affiliateTag", "") or "").strip()
if aff and not _re.fullmatch(r"[A-Za-z0-9-]{3,40}", aff):
    errors.append("site.affiliateTag must be your Amazon tracking ID, like sixsheet-20 (or be empty)")
ld = D["launch"].get("localDate")
if ld is not None:
    try:
        datetime.date.fromisoformat(str(ld))
    except ValueError:
        errors.append("launch.localDate must look like 2026-11-19")
if errors:
    print("ERRORS:\n- " + "\n- ".join(errors)); sys.exit(1)

ADS_HEAD = ""
if ads:
    ADS_HEAD = (f'<meta name="google-adsense-account" content="{ads}">\n'
                f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ads}" crossorigin="anonymous"></script>')
ads_txt = ROOT / "ads.txt"
if ads:
    ads_txt.write_text(f"google.com, {ads.replace('ca-', '', 1)}, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")
elif ads_txt.exists():
    ads_txt.unlink()

# ---------- index.html ----------
seed = json.dumps(D, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
tpl = (ROOT / "tools" / "template.html").read_text(encoding="utf-8")
(ROOT / "index.html").write_text(tpl.replace("/*SEED*/", seed).replace("<!--ADS-->", ADS_HEAD), encoding="utf-8")

# ---------- guide pages ----------
e = lambda s: html.escape(str(s if s is not None else ""))
CSS = """@font-face{font-family:"Bricolage";src:url(../fonts/bricolage.woff2) format("woff2");font-weight:200 800;font-stretch:75% 100%;font-display:swap}
body{margin:0;background:#1d1c20;color:#f3efe6;font:400 17px/1.5 "Bricolage",system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:inherit;text-underline-offset:3px}.w{max-width:640px;margin:0 auto;padding:20px}
.top a{display:inline-block;text-decoration:none;font-weight:800;font-stretch:75%;font-size:30px;line-height:1;border-bottom:3px solid #ff4f8b;padding-bottom:5px}
h1{font-size:40px;font-weight:800;font-stretch:75%;line-height:1;margin:30px 0 8px}
h2{font-size:25px;font-weight:700;font-stretch:82%;line-height:1.1;margin:34px 0 10px}
.m{color:#a8a3ad;font-size:15px}
.c{border-top:1px solid #3a373f;padding:13px 0}.c b{font-weight:700}.c h2{margin:0 0 6px}
.k{display:inline-block;border:1.5px solid #3a373f;border-bottom-width:3px;border-radius:7px;background:#28262c;padding:1px 8px;font-weight:700}
ol,ul{padding-left:22px}li{margin:8px 0}
details summary{cursor:pointer;color:#ffc247;font-weight:600}
.cta{display:inline-block;margin:10px 0 4px;padding:10px 16px;border-radius:8px;background:#ffc247;color:#201a08;font-weight:700;text-decoration:none}
footer{color:#a8a3ad;font-size:14.5px;border-top:1px solid #3a373f;margin-top:40px;padding-top:16px}"""

def src(o):
    if not o.get("source"): return ""
    s = f'<a href="{e(o.get("url"))}" rel="nofollow noopener">{e(o["source"])}</a>' if o.get("url") else e(o["source"])
    return f'<div class="m">Source: {s}</div>'

def spoil(inner, flag):
    return f"<details><summary>Spoiler-ish. Tap to reveal</summary>{inner}</details>" if flag else inner

def page(slug, title, desc, h1, intro, body, tab):
    updated = e(D["site"].get("updated", ""))
    doc = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{BASE}guide/{slug}.html">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{BASE}brand/header.png"><meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#1d1c20"><link rel="icon" type="image/png" href="../brand/avatar.png">
{ADS_HEAD}
<style>{CSS}</style></head><body><div class="w">
<div class="top"><a href="../index.html">SixSheet</a></div>
<h1>{e(h1)}</h1>{f'<p class="m">Updated {updated[:10]}. No story spoilers.</p>' if tab else ''}<p>{intro}</p>
{f'<a class="cta" href="../index.html#{tab}">Open the interactive version</a>' if tab else ''}
{body}
<footer><p><a href="launch.html">Launch guide</a>, <a href="codes.html">cheat codes</a>, <a href="money.html">money</a>, <a href="collectibles.html">collectibles</a>, <a href="finds.html">finds</a>. <a href="about.html">About</a>, <a href="privacy.html">privacy</a>.</p>
<p>SixSheet is an unofficial fan site, not affiliated with or endorsed by Rockstar Games or Take-Two Interactive.</p></footer>
</div></body></html>"""
    (ROOT / "guide").mkdir(exist_ok=True)
    (ROOT / "guide" / f"{slug}.html").write_text(doc, encoding="utf-8")

def empty(msg): return f'<div class="c m">{e(msg)}</div>'

# Launch
facts = "".join(f'<div class="c"><b>{e(f["label"])}</b><div>{e(f["value"])}</div>{src(f)}</div>' for f in D["facts"])
prep = "".join(f'<li><b>{e(p["text"])}</b>. {e(p.get("detail",""))}</li>' for p in D["prep"])
page("launch", "GTA VI Launch Guide: Unlock Time, Size, Price & Checklist | SixSheet",
     "When GTA VI unlocks, how much space you need, editions and prices, plus a spoiler-free launch checklist.",
     "GTA VI launch guide", "Everything confirmed about launch, with sources. No rumors, no spoilers.",
     f"<h2>Checklist</h2><ul>{prep}</ul><h2>Confirmed facts</h2>{facts}", "prep")

# Codes
if D["codes"]:
    rows = ""
    for c in D["codes"]:
        inputs = "".join(f'<div><b>{lab}:</b> <span class="k">{e(c[k])}</span></div>' for lab, k in (("PS5","ps"),("Xbox","xbox"),("Phone","phone")) if c.get(k))
        badge = "Verified" if c.get("verified") else "Unconfirmed"
        rows += f'<div class="c"><b>{e(c["name"])}</b> <span class="m">({badge})</span><div>{e(c.get("effect",""))}</div>{inputs}{src(c)}</div>'
else:
    rows = empty("No verified codes yet. If GTA VI has cheat codes, each one is tested and added here within hours of launch.")
page("codes", "GTA VI Cheat Codes (PS5 & Xbox), Verified | SixSheet",
     "Every GTA VI cheat code for PS5 and Xbox Series X|S, tested and marked verified. Updated through launch week.",
     "GTA VI cheat codes", f"{len(D['codes'])} codes listed. Only tested codes are marked verified.", rows, "codes")

# Money
if D["money"]:
    rows = ""
    for i, m in enumerate(D["money"], 1):
        meta = ", ".join(x for x in [f'Payout: {e(m["payout"])}' if m.get("payout") else "", f'Time: {e(m["time"])}' if m.get("time") else ""] if x)
        inner = f'<b>#{i} {e(m["title"])}</b> <span class="m">({"Verified" if m.get("verified") else "Unconfirmed"})</span><div>{e(m.get("summary",""))}</div>' + (f'<div class="m">{meta}</div>' if meta else "") + src(m)
        rows += f'<div class="c">{spoil(inner, m.get("spoiler"))}</div>'
else:
    rows = empty("Money methods get ranked by payout per hour once players confirm them after launch.")
page("money", "Fastest Ways to Make Money in GTA VI, Ranked | SixSheet",
     "The fastest legit ways to make money in GTA VI, ranked by payout and time. Spoiler-free, updated daily.",
     "Fastest ways to make money in GTA VI", "Ranked best first. Story spoilers are never included.", rows, "money")

# Collectibles
if D["tracker"]:
    rows = ""
    for cat in D["tracker"]:
        items = "".join("<li>" + spoil(f'<b>{e(it["name"])}</b> {e(it.get("hint",""))}', it.get("spoiler")) + "</li>" for it in cat.get("items", []))
        rows += f'<div class="c"><h2 style="margin:0">{e(cat["category"])} <span class="m">({e(cat.get("total", len(cat.get("items",[]))))} total)</span></h2><ul>{items}</ul></div>'
else:
    rows = empty("Collectible categories and counts go up once they're confirmed in-game.")
page("collectibles", "GTA VI Collectibles Checklist & Locations | SixSheet",
     "Every GTA VI collectible category with counts and hints, plus a checklist that saves your progress.",
     "GTA VI collectibles checklist", "Use the interactive version to tick items off as you go.", rows, "tracker")

# Finds
fl = sorted(D["finds"], key=lambda f: f.get("added", ""), reverse=True)
rows = "".join(f'<div class="c">{spoil(f"<b>{e(f["title"])}</b><div>{e(f.get("summary",""))}</div>{src(f)}", f.get("spoiler"))}</div>' for f in fl) or empty("New discoveries post here, credited to whoever found them.")
page("finds", "GTA VI Secrets, Hidden Spots & Tricks (Spoiler-Free) | SixSheet",
     "The latest GTA VI discoveries: hidden spots, tricks and easter eggs, credited to the players who found them.",
     "Latest GTA VI finds", "Newest first. Anything spoiler-ish is hidden until you tap it.", rows, "finds")

# About
xh = _re.sub(r"[^A-Za-z0-9_]", "", str(D["site"].get("xHandle", "")))
contact = f'<a href="https://x.com/{xh}" rel="noopener">@{xh}</a> on X' if xh else "X"
page("about", "About SixSheet | Spoiler-Free GTA VI Cheat Sheet",
     "What SixSheet is, how entries get checked, and how to reach us.",
     "About SixSheet", "SixSheet is a free, spoiler-free GTA VI cheat sheet: launch prep, tested cheat codes, money methods, collectible trackers and new finds.",
     f"""<h2>How entries get checked</h2>
<ul><li>Every code, money method and find links to where it came from, and credits the player who found it.</li>
<li>Something is marked tested only with clear in-game video or several independent confirmations.</li>
<li>No story spoilers, leaks, rumors or piracy. Secrets that might spoil a surprise stay hidden until you tap them.</li></ul>
<h2>Contact</h2><p>Spotted a mistake or found something new? Message {contact}.</p>
<h2>Not official</h2><p>SixSheet is an independent fan site. It is not affiliated with or endorsed by Rockstar Games or Take-Two Interactive. Grand Theft Auto and related names are their trademarks.</p>""", "")

# Privacy
ad_sec = ("""<h2>Ads</h2><p>SixSheet shows ads from Google AdSense to pay for the site. Google and its partners use cookies to show ads based on your visits to this and other sites. You can turn off personalized ads at <a href="https://adssettings.google.com" rel="noopener">Google Ad Settings</a>, and read how Google uses this data at <a href="https://policies.google.com/technologies/partner-sites" rel="noopener">policies.google.com</a>. Visitors in the EU, UK and Switzerland are asked for consent before personalized ads are shown.</p>"""
          if ads else
          """<h2>Ads</h2><p>SixSheet may show ads from Google AdSense in the future. If it does, this page will explain how they use cookies and how to opt out before they appear.</p>""")
aff_sec = ("""<h2>Affiliate links</h2><p>Some links to Amazon are affiliate links. As an Amazon Associate, SixSheet earns from qualifying purchases, at no extra cost to you. Amazon may set cookies when you follow one.</p>"""
           if aff else "")
page("privacy", "Privacy Policy | SixSheet",
     "How SixSheet handles data: checklist progress stays in your browser, plus ads and affiliate links.",
     "Privacy", f"Last updated {datetime.date.today().isoformat()}. Short version: SixSheet has no accounts and doesn't collect your personal information.",
     f"""<h2>What stays on your device</h2><p>Your checklist and tracker progress, spoiler setting, console choice and similar preferences are saved in your browser's local storage. They never leave your device, and clearing your browser data deletes them.</p>
<h2>Hosting</h2><p>The site is hosted on GitHub Pages. GitHub may log technical data such as IP addresses to run and secure the service. See <a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement" rel="noopener">GitHub's privacy statement</a>.</p>
{ad_sec}{aff_sec}
<h2>Links to other sites</h2><p>Sources link to other websites, which have their own privacy policies.</p>
<h2>Contact</h2><p>Questions about this policy: message {contact}.</p>""", "")

# Sitemap
today = datetime.date.today().isoformat()
urls = [BASE] + [f"{BASE}guide/{s}.html" for s in ("launch", "codes", "money", "collectibles", "finds", "about", "privacy")]
(ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    "".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")

print("BUILD OK")
for w in warnings: print("WARN:", w)
