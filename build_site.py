
from __future__ import annotations
import json, re, shutil
from pathlib import Path
from urllib.parse import quote_plus
from html import escape
import pandas as pd

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
BRANDING_DIR = ROOT / "branding"
OUTPUT_DIR = ROOT / "output"

def slugify(value: str) -> str:
    value = str(value or "").strip().lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "lego-set"

def clean_text(value, fallback=""):
    if pd.isna(value):
        return fallback
    text = str(value).strip()
    if not text or text in {"{?}", "{Not specified}", "nan", "None"}:
        return fallback
    return text

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lstrip("\ufeff") for c in df.columns]
    lower = {str(c).strip().lstrip("\ufeff").lower(): c for c in df.columns}
    aliases = {
        "number": ["number", "set number", "set_number", "setnumber"],
        "setname": ["setname", "set name", "name"],
        "theme": ["theme"],
        "subtheme": ["subtheme", "sub theme"],
        "yearfrom": ["yearfrom", "year", "release year"],
        "instructionscount": ["instructionscount", "instructions count", "instruction count"],
        "pieces": ["pieces", "piece count"],
        "title": ["title"],
        "video_id": ["video_id", "id"],
        "url": ["url", "video_url", "link"],
        "publish_date": ["publish_date", "publish date", "published", "date"]
    }
    target = {
        "number":"Number","setname":"SetName","theme":"Theme","subtheme":"Subtheme",
        "yearfrom":"YearFrom","instructionscount":"InstructionsCount","pieces":"Pieces",
        "title":"title","video_id":"video_id","url":"url","publish_date":"publish_date"
    }
    rename = {}
    for key, choices in aliases.items():
        for choice in choices:
            if choice in lower:
                rename[lower[choice]] = target[key]
                break
    return df.rename(columns=rename)

def load_config():
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

def read_inputs():
    sets = normalize_columns(pd.read_csv(DATA_DIR / "sets.csv"))
    playlist = normalize_columns(pd.read_csv(DATA_DIR / "playlist.csv"))
    return sets, playlist

def prepare_sets(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    defaults = {"Number":"", "SetName":"LEGO Set", "Theme":"Other", "Subtheme":"", "YearFrom":0, "InstructionsCount":0, "Pieces":pd.NA}
    for k, v in defaults.items():
        if k not in df.columns:
            df[k] = v
    df["Number"] = df["Number"].astype(str).str.strip()
    df["SetName"] = df["SetName"].apply(lambda x: clean_text(x, "LEGO Set"))
    df["Theme"] = df["Theme"].apply(lambda x: clean_text(x, "Other"))
    df["Subtheme"] = df["Subtheme"].apply(lambda x: clean_text(x, ""))
    df["YearFrom"] = pd.to_numeric(df["YearFrom"], errors="coerce").fillna(0).astype(int)
    df["InstructionsCount"] = pd.to_numeric(df["InstructionsCount"], errors="coerce").fillna(0).astype(int)
    df["Pieces"] = pd.to_numeric(df.get("Pieces"), errors="coerce")
    df = df[df["Number"].astype(str).str.len() > 0].copy()
    df["slug"] = df.apply(lambda row: f"{row['Number']}-{slugify(row['SetName'])}", axis=1)
    df["theme_slug"] = df["Theme"].apply(slugify)
    return df.drop_duplicates(subset=["slug"], keep="first")

def prepare_playlist(df: pd.DataFrame) -> pd.DataFrame:
    for col in ("title","video_id","url","publish_date"):
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str).str.strip()
    return df

def match_videos(sets_df: pd.DataFrame, playlist_df: pd.DataFrame):
    matches = {}
    used = set()
    vids = playlist_df.to_dict(orient="records")
    candidates = sorted(sets_df[["Number","slug"]].to_dict(orient="records"), key=lambda x: len(str(x["Number"])), reverse=True)
    for item in candidates:
        pattern = rf"(?<!\d){re.escape(str(item['Number']))}(?!\d)"
        for video in vids:
            if video["video_id"] in used:
                continue
            if re.search(pattern, video["title"]):
                matches[item["slug"]] = video
                used.add(video["video_id"])
                break
    return matches

def latest_uploads(matched, sets_df):
    by_slug = {row["slug"]: row for _, row in sets_df.iterrows()}
    items = []
    for slug, video in matched.items():
        row = by_slug.get(slug)
        if row is None:
            continue
        items.append({
            "slug": slug,
            "set_number": row["Number"],
            "set_name": row["SetName"],
            "theme": row["Theme"],
            "video_title": video["title"],
            "video_url": video["url"],
            "video_id": video["video_id"],
            "publish_date": video.get("publish_date", "")
        })
    return items

def ensure_dirs():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    (OUTPUT_DIR / "assets").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "themes").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "sets").mkdir(parents=True, exist_ok=True)

def copy_branding():
    for name in ("logo.svg","banner.svg","logo.png","banner.png","avatar.png"):
        src = BRANDING_DIR / name
        if src.exists():
            shutil.copy(src, OUTPUT_DIR / "assets" / name)

def logo_src():
    for name in ("logo.svg","logo.png","avatar.png"):
        if (OUTPUT_DIR / "assets" / name).exists():
            return "/assets/" + name
    return ""

def banner_src():
    for name in ("banner.svg","banner.png"):
        if (OUTPUT_DIR / "assets" / name).exists():
            return "/assets/" + name
    return ""

def yt_thumb(video_id):
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

def official_search_url(set_number):
    return "https://www.google.com/search?q=" + quote_plus(f"site:lego.com {set_number} instructions")

def channel_search_url(config, query):
    return config["channel_search_base"] + quote_plus(query + " " + config["site_name"])

def write_assets():
    css = """
:root{--bg:#f7f1dd;--surface:#fffdf7;--surface2:#fff8e8;--ink:#161616;--muted:#655d50;--line:#e0c467;--gold:#efb10a;--shadow:0 14px 40px rgba(35,26,0,.08)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Arial,Helvetica,sans-serif;background:linear-gradient(180deg,#fbf7ea 0%,var(--bg) 100%);color:var(--ink)}
a{text-decoration:none;color:inherit}img{max-width:100%;display:block}
.container{width:min(1200px,calc(100% - 28px));margin:0 auto}
.site-header{position:sticky;top:0;z-index:30;background:rgba(252,248,236,.94);backdrop-filter:blur(10px);border-bottom:2px solid rgba(224,196,103,.85)}
.site-header-inner{display:grid;grid-template-columns:auto 1fr auto;gap:18px;align-items:center;padding:12px 0}
.brand{display:flex;align-items:center;gap:12px;min-width:0}
.brand img{width:56px;height:56px;object-fit:cover;border-radius:18px;border:3px solid #fff4ca;box-shadow:var(--shadow);background:#fff6db}
.brand-title{font-size:1.5rem;font-weight:900;text-transform:uppercase;line-height:1;letter-spacing:.02em}
.brand-tagline{color:var(--muted);font-size:.95rem;margin-top:4px}
.search-wrap{display:flex;justify-content:center}
.search-box{width:min(520px,100%);display:flex;align-items:center;background:#fffdf8;border:2px solid rgba(224,196,103,.95);border-radius:999px;padding:10px 16px}
.search-box input{width:100%;border:0;outline:0;background:transparent;font-size:1rem}
.nav{display:flex;gap:10px;align-items:center;flex-wrap:wrap;justify-content:flex-end}
.nav a{padding:12px 16px;border-radius:999px;font-weight:800}.nav a.active,.nav a:hover{background:#f4e6ab}
.hero{padding:24px 0 12px}.hero-card{overflow:hidden;border:3px solid #e9b40c;border-radius:30px;background:linear-gradient(180deg,#f5d46f 0%,#f2c954 100%);box-shadow:var(--shadow)}
.hero-banner{height:190px;overflow:hidden;background:linear-gradient(90deg,rgba(255,255,255,.12),rgba(255,255,255,0))}
.hero-banner img{width:100%;height:100%;object-fit:cover}.hero-content{display:grid;grid-template-columns:112px 1fr;gap:26px;align-items:center;padding:26px 28px 30px;background:linear-gradient(180deg,#fbf2d2 0%,#fbf6e6 100%)}
.hero-avatar{width:112px;height:112px;border-radius:24px;object-fit:cover;border:6px solid #fff5d5;background:#fff1c3;box-shadow:var(--shadow)}
.hero-copy h1{margin:0 0 10px;font-size:clamp(2rem,5vw,3.8rem);line-height:.95;text-transform:uppercase}
.hero-copy p{margin:0;color:#2f2a1f;font-size:1.12rem;max-width:830px}.hero-actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:18px}
.section{padding:18px 0 8px}.section-title{font-size:clamp(1.65rem,3vw,2.25rem);margin:0 0 8px}.section-subtitle{margin:0 0 18px;color:var(--muted);font-size:1.03rem}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:12px 16px;border-radius:16px;font-weight:800;border:2px solid var(--ink);background:#fffef9}
.btn.primary{background:var(--gold);border-color:#c58f00}.btn.red{background:#fff4f3;border-color:#efb6b0}
.featured-slider,.video-carousel,.search-strip{display:flex;gap:16px;overflow:auto;padding-bottom:6px;scroll-snap-type:x proximity}
.feature-card,.video-card,.theme-card,.set-card,.copy-card,.link-card{background:var(--surface);border:2px solid rgba(224,196,103,.9);border-radius:24px;box-shadow:0 8px 24px rgba(0,0,0,.04)}
.feature-card,.video-card{min-width:290px;max-width:320px;scroll-snap-align:start}
.feature-card{padding:20px;position:relative;overflow:hidden}.feature-card:after{content:"";position:absolute;right:-18px;bottom:-20px;width:110px;height:110px;border-radius:28px;background:linear-gradient(135deg,rgba(239,177,10,.22),rgba(239,177,10,0));transform:rotate(18deg)}
.feature-icon{width:54px;height:54px;border-radius:16px;background:#fff4c7;border:2px solid #f0c85d;display:grid;place-items:center;font-size:28px}
.feature-card h3,.video-card h3,.theme-card h3,.set-card h3{margin:10px 0 6px;font-size:1.35rem;line-height:1.08}
.feature-card p,.video-card p,.theme-card p,.set-card p,.copy-card p,.link-card p{margin:0;color:var(--muted)}
.theme-grid,.set-grid,.two-col{display:grid;gap:18px}.theme-grid{grid-template-columns:repeat(4,minmax(0,1fr))}.theme-card,.set-card,.copy-card,.link-card{padding:20px}
.theme-count,.pill{display:inline-flex;width:fit-content;padding:8px 12px;border-radius:999px;background:#f7e4a0;border:1px solid #d8b545;font-weight:800}
.video-card{overflow:hidden}.video-thumb{aspect-ratio:16/9;background:#f5e7b5;overflow:hidden}.video-thumb img{width:100%;height:100%;object-fit:cover}.video-body{padding:16px}
.kicker{color:var(--muted);text-transform:uppercase;font-weight:800;letter-spacing:.06em;font-size:.84rem}.button-row{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}
.search-chip{background:#fff9e6;border:2px solid rgba(224,196,103,.9);padding:12px 15px;border-radius:999px;font-weight:800;white-space:nowrap}
.two-col{grid-template-columns:1.15fr .85fr;align-items:start}.page-hero{padding:24px 0 8px}.breadcrumbs{color:var(--muted);font-size:.95rem;margin-bottom:10px}
.content-card{background:var(--surface);border:2px solid rgba(224,196,103,.85);border-radius:24px;padding:24px;box-shadow:0 5px 18px rgba(0,0,0,.03)}
.video-wrap{margin-top:18px;position:relative;padding-top:56.25%;overflow:hidden;border-radius:20px;border:2px solid rgba(224,196,103,.9);background:#fff7d8}
.video-wrap iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.meta-list{display:grid;gap:12px;grid-template-columns:repeat(2,minmax(0,1fr));margin-top:18px}.meta-item{background:var(--surface2);border:1px solid rgba(224,196,103,.8);border-radius:16px;padding:14px}
.footer{padding:26px 0 42px;color:var(--muted)}.footer-inner{border-top:2px solid rgba(224,196,103,.95);padding-top:18px;display:grid;gap:18px}.footer-main{display:grid;gap:10px}
.footer-brand{display:flex;align-items:center;gap:12px}.footer-brand img{width:44px;height:44px;border-radius:14px;background:#fff6db;border:2px solid #f3d269}.footer-links{display:flex;gap:16px;flex-wrap:wrap;font-weight:800}.small{font-size:.94rem}
@media (max-width:980px){.site-header-inner{grid-template-columns:1fr}.hero-content{grid-template-columns:1fr}.theme-grid,.set-grid,.two-col,.meta-list{grid-template-columns:1fr 1fr}}
@media (max-width:680px){.container{width:min(100%,calc(100% - 18px))}.hero-banner{height:112px}.hero-content{padding:18px;gap:16px}.hero-avatar{width:86px;height:86px;border-width:5px}.theme-grid,.set-grid,.two-col,.meta-list{grid-template-columns:1fr}.brand-title{font-size:1.2rem}}
"""
    js = """const input=document.querySelector('[data-site-search]');if(input){const links=[...document.querySelectorAll('[data-search-link]')];input.addEventListener('input',()=>{const q=input.value.trim().toLowerCase();links.forEach(el=>{const hay=(el.getAttribute('data-search-link')||'').toLowerCase();const card=el.closest('[data-search-card]')||el;card.style.display=!q||hay.includes(q)?'':'none';});});}"""
    (OUTPUT_DIR/"assets"/"styles.css").write_text(css, encoding="utf-8")
    (OUTPUT_DIR/"assets"/"search.js").write_text(js, encoding="utf-8")

def page_shell(config, title, description, body, active=""):
    logo = logo_src()
    footer = f"""
<footer class="footer">
  <div class="container footer-inner">
    <div class="footer-main">
      <div class="footer-brand">{f'<img src="{logo}" alt="{escape(config["site_name"])} logo">' if logo else ''}<div><strong>{escape(config["site_name"])}</strong><div class="small">{escape(config["site_tagline"])}</div></div></div>
      <p class="small">Find LEGO instructions by set number, theme, and set name. Watch matched build videos and move quickly to official LEGO instruction results.</p>
    </div>
    <div class="footer-links"><a href="/">Home</a><a href="/themes/">Themes</a><a href="{escape(config["channel_url"])}">YouTube</a><a href="mailto:{escape(config["contact_email"])}">Contact</a></div>
    <div class="small">Disclaimer: LEGO is a trademark of the LEGO Group of companies (<a href="https://www.lego.com" target="_blank" rel="noopener">https://www.lego.com</a>) which does not sponsor, authorize or endorse this site.</div>
  </div>
</footer>"""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{escape(title)}</title><meta name="description" content="{escape(description)}"><link rel="stylesheet" href="/assets/styles.css">{f'<link rel="icon" href="{logo}">' if logo else ''}</head><body><header class="site-header"><div class="container site-header-inner"><a class="brand" href="/">{f'<img src="{logo}" alt="{escape(config["site_name"])} logo">' if logo else ''}<div><div class="brand-title">{escape(config["site_name"])}</div><div class="brand-tagline">{escape(config["site_tagline"])}</div></div></a><div class="search-wrap"><label class="search-box" aria-label="Search LEGO sets"><input type="text" data-site-search placeholder="Search LEGO set number, name, theme, or subtheme"></label></div><nav class="nav"><a href="/" {'class="active"' if active=='home' else ''}>Home</a><a href="/themes/" {'class="active"' if active=='themes' else ''}>Themes</a></nav></div></header>{body}{footer}<script src="/assets/search.js"></script></body></html>"""

def featured_sets(sets_df, matched, limit):
    df = sets_df.copy()
    df["has_video"] = df["slug"].isin(matched)
    df = df.sort_values(["has_video","InstructionsCount","YearFrom"], ascending=[False,False,False])
    picks=[]; seen=set()
    for _, row in df.iterrows():
        if row["Number"] in seen: continue
        seen.add(row["Number"]); picks.append(row.to_dict())
        if len(picks) >= limit: break
    return picks

def write_home(config, sets_df, matched, latest_items):
    theme_counts = sets_df.groupby(["Theme","theme_slug"]).size().reset_index(name="count").sort_values(["count","Theme"], ascending=[False,True])
    top_themes = theme_counts.head(config["max_featured_themes"]).to_dict(orient="records")
    featured = featured_sets(sets_df, matched, config["max_featured_sets"])
    latest = latest_items[:config["max_latest_uploads"]]
    popular = sets_df.sort_values(["InstructionsCount","YearFrom"], ascending=[False,False]).head(config["max_popular_searches"])
    logo = logo_src(); banner = banner_src()
    icons = {"Technic":"⚙️","Speed Champions":"🏎️","City":"🏙️","Star Wars":"✨","Ideas":"💡","Botanicals":"🌿","Marvel Super Heroes":"🦸","Harry Potter":"🪄","Pokémon":"⚡","Creator":"🧱"}
    featured_html = "".join([
        f'<article class="feature-card" data-search-card><div class="feature-icon">{icons.get(row["Theme"], "🧱")}</div><div class="pill">{escape(row["Theme"])}</div><h3><a data-search-link="{escape(str(row["Number"])+" "+row["SetName"]+" "+row["Theme"])}" href="/sets/{escape(row["slug"])}.html">LEGO {escape(str(row["Number"]))} {escape(row["SetName"])}</a></h3><p>{"Matched build video available." if row["slug"] in matched else "Official instruction search ready."}</p><div class="button-row"><a class="btn primary" href="/sets/{escape(row["slug"])}.html">Open set</a></div></article>'
        for row in featured
    ])
    theme_html = "".join([
        f'<article class="theme-card" data-search-card><div class="pill">{row["count"]} sets</div><h3><a data-search-link="{escape(row["Theme"])}" href="/themes/{escape(row["theme_slug"])}.html">{escape(row["Theme"])}</a></h3><p>Browse LEGO {escape(row["Theme"])} instructions by set number and name.</p><div class="button-row"><a class="btn primary" href="/themes/{escape(row["theme_slug"])}.html">Browse theme</a></div></article>'
        for row in top_themes
    ])
    latest_html = "".join([
        f'<article class="video-card" data-search-card><a class="video-thumb" href="/sets/{escape(item["slug"])}.html"><img src="{yt_thumb(item["video_id"])}" alt="{escape(item["set_name"])} video thumbnail"></a><div class="video-body"><div class="kicker">{escape(item["theme"])}{" · "+escape(item["publish_date"]) if item.get("publish_date") else ""}</div><h3><a data-search-link="{escape(item["set_number"]+" "+item["set_name"]+" "+item["theme"])}" href="/sets/{escape(item["slug"])}.html">LEGO {escape(item["set_number"])} {escape(item["set_name"])}</a></h3><p>{escape(item["video_title"])}</p><div class="button-row"><a class="btn primary" href="/sets/{escape(item["slug"])}.html">Watch build</a></div></div></article>'
        for item in latest
    ])
    chips = "".join([f'<a class="search-chip" href="/sets/{escape(row["slug"])}.html">LEGO {escape(str(row["Number"]))} Instructions</a>' for _, row in popular.iterrows()])
    body = f"""
<main>
<section class="hero"><div class="container"><div class="hero-card">{f'<div class="hero-banner"><img src="{banner}" alt="Channel banner"></div>' if banner else ''}<div class="hero-content">{f'<img class="hero-avatar" src="{logo}" alt="Channel logo">' if logo else ''}<div class="hero-copy"><h1>Find LEGO Instructions for Any Set</h1><p>Search by set number, theme, or name to find official LEGO building instructions and step-by-step video guides from LEGO Instructions For You.</p><div class="hero-actions"><a class="btn primary" href="#featured-sets">Featured sets</a><a class="btn" href="#latest-videos">Latest videos</a><a class="btn red" href="/themes/">Browse themes</a></div></div></div></div></div></section>
<section class="section" id="featured-sets"><div class="container"><h2 class="section-title">Featured LEGO instruction pages</h2><p class="section-subtitle">A more premium homepage starts with strong featured sets that people actually search for.</p><div class="featured-slider">{featured_html}</div></div></section>
<section class="section"><div class="container"><h2 class="section-title">Browse by theme</h2><p class="section-subtitle">Use the biggest LEGO themes to drill into exact set pages fast.</p><div class="theme-grid">{theme_html}</div></div></section>
<section class="section" id="latest-videos"><div class="container"><h2 class="section-title">Latest matched videos</h2><p class="section-subtitle">Fresh build videos from your channel, now presented with thumbnails in a clean horizontal carousel.</p><div class="video-carousel">{latest_html}</div></div></section>
<section class="section"><div class="container two-col"><article class="link-card"><h2 class="section-title">Popular LEGO instruction searches</h2><p class="section-subtitle">Quick links for the exact set-number searches people use in Google and YouTube.</p><div class="search-strip">{chips}</div></article><article class="copy-card"><h2 class="section-title">Why use this site?</h2><p>This version is built to feel more premium and help visitors get to the right build faster.</p><div class="button-row" style="margin-top:16px"><a class="btn primary" href="{escape(config["channel_url"])}">Visit YouTube</a><a class="btn" href="mailto:{escape(config["contact_email"])}">Contact</a></div></article></div></section>
</main>"""
    (OUTPUT_DIR/"index.html").write_text(page_shell(config,"Find LEGO Instructions for Any Set | LEGO Instructions For You","Search LEGO instructions by set number, theme, or set name. Find official LEGO building instructions and matched video build guides from LEGO Instructions For You.",body,"home"), encoding="utf-8")

def write_theme_index(config, theme_rows):
    cards = "".join([f'<article class="theme-card" data-search-card><div class="pill">{row["count"]} sets</div><h3><a data-search-link="{escape(row["Theme"])}" href="/themes/{escape(row["theme_slug"])}.html">{escape(row["Theme"])}</a></h3><p>LEGO {escape(row["Theme"])} building instructions, matched videos, and set pages.</p><div class="button-row"><a class="btn primary" href="/themes/{escape(row["theme_slug"])}.html">Open theme</a></div></article>' for _, row in theme_rows.iterrows()])
    body = f'<main class="page-hero"><div class="container"><div class="breadcrumbs"><a href="/">Home</a> / Themes</div><div class="content-card"><h1 class="section-title">Browse all LEGO themes</h1><p class="section-subtitle">Browse LEGO instructions by theme to find the right set number, set name, and matching build video.</p><div class="theme-grid">{cards}</div></div></div></main>'
    (OUTPUT_DIR/"themes"/"index.html").write_text(page_shell(config,"Browse LEGO Themes | LEGO Instructions For You","Browse LEGO instructions by theme including City, Technic, Speed Champions, Botanical, Ideas, and more.",body,"themes"), encoding="utf-8")

def write_theme_pages(config, sets_df, matched):
    theme_rows = sets_df.groupby(["Theme","theme_slug"]).size().reset_index(name="count").sort_values(["count","Theme"], ascending=[False,True])
    write_theme_index(config, theme_rows)
    for (theme, theme_slug), frame in sets_df.groupby(["Theme","theme_slug"]):
        frame = frame.sort_values(["YearFrom","Number"], ascending=[False,True])
        cards = "".join([f'<article class="set-card" data-search-card><div class="kicker">{escape(r["Subtheme"] or theme)}</div><h3><a data-search-link="{escape(str(r["Number"])+" "+r["SetName"]+" "+r["Theme"]+" "+r["Subtheme"])}" href="/sets/{escape(r["slug"])}.html">LEGO {escape(str(r["Number"]))} {escape(r["SetName"])}</a></h3><p>{"Matched build video available." if r["slug"] in matched else "Set page with instruction search link."}</p><div class="button-row"><a class="btn primary" href="/sets/{escape(r["slug"])}.html">Open set page</a></div></article>' for _, r in frame.iterrows()])
        body = f'<main class="page-hero"><div class="container"><div class="breadcrumbs"><a href="/">Home</a> / <a href="/themes/">Themes</a> / {escape(theme)}</div><div class="content-card"><h1 class="section-title">{escape(theme)} LEGO Instructions</h1><p class="section-subtitle">Browse LEGO {escape(theme)} set pages by set number and set name.</p><div class="set-grid">{cards}</div></div></div></main>'
        (OUTPUT_DIR/"themes"/f"{theme_slug}.html").write_text(page_shell(config,f"{theme} LEGO Instructions | LEGO Instructions For You",f"Browse LEGO {theme} instructions by set number and set name. Find official building instructions and matched video guides.",body,"themes"), encoding="utf-8")

def related_sets_html(config, row, sets_df):
    same = sets_df[(sets_df["Theme"] == row["Theme"]) & (sets_df["slug"] != row["slug"])].head(config["max_related_sets"])
    if same.empty: return ""
    cards = "".join([f'<article class="set-card"><div class="kicker">{escape(r["Theme"])}</div><h3><a href="/sets/{escape(r["slug"])}.html">LEGO {escape(str(r["Number"]))} {escape(r["SetName"])}</a></h3><div class="button-row"><a class="btn primary" href="/sets/{escape(r["slug"])}.html">View set</a></div></article>' for _, r in same.iterrows()])
    return f'<section class="section"><div class="container"><h2 class="section-title">Related {escape(row["Theme"])} sets</h2><div class="set-grid">{cards}</div></div></section>'

def write_set_pages(config, sets_df, matched):
    for _, row in sets_df.iterrows():
        match = matched.get(row["slug"])
        official = official_search_url(row["Number"])
        channel = channel_search_url(config, f"LEGO {row['Number']} {row['SetName']} instructions")
        buttons=[]; video=""
        if match:
            buttons.append(f'<a class="btn primary" href="{escape(match["url"])}">Watch on YouTube</a>')
            video = f'<div class="video-wrap"><iframe src="https://www.youtube.com/embed/{escape(match["video_id"])}" title="{escape(match["title"])}" allowfullscreen loading="lazy"></iframe></div>'
        else:
            buttons.append(f'<a class="btn primary" href="{escape(channel)}">Search this set on YouTube</a>')
        buttons.append(f'<a class="btn red" href="{escape(official)}">Find official instructions</a>')
        pieces="Unknown"
        try:
            if pd.notna(row["Pieces"]):
                pieces = str(int(row["Pieces"])) if float(row["Pieces"]).is_integer() else str(row["Pieces"])
        except Exception:
            pass
        body = f'<main class="page-hero"><div class="container"><div class="breadcrumbs"><a href="/">Home</a> / <a href="/themes/">Themes</a> / <a href="/themes/{escape(row["theme_slug"])}.html">{escape(row["Theme"])}</a> / LEGO {escape(str(row["Number"]))}</div><article class="content-card"><div class="kicker">{escape(row["Theme"])}{(" · "+escape(row["Subtheme"])) if row["Subtheme"] else ""}</div><h1 class="section-title">LEGO {escape(str(row["Number"]))} Instructions – {escape(row["SetName"])}</h1><p class="section-subtitle">Find LEGO {escape(str(row["Number"]))} building instructions, a matched video build guide, and fast links to official instructions.</p><div class="button-row">{"".join(buttons)}</div>{video}<div class="meta-list"><div class="meta-item"><strong>Set number:</strong> {escape(str(row["Number"]))}</div><div class="meta-item"><strong>Set name:</strong> {escape(row["SetName"])}</div><div class="meta-item"><strong>Theme:</strong> {escape(row["Theme"])}</div><div class="meta-item"><strong>Subtheme:</strong> {escape(row["Subtheme"] or "—")}</div><div class="meta-item"><strong>Year:</strong> {row["YearFrom"] if row["YearFrom"] else "—"}</div><div class="meta-item"><strong>Pieces:</strong> {escape(pieces)}</div></div></article></div></main>{related_sets_html(config,row,sets_df)}'
        (OUTPUT_DIR/"sets"/f"{row['slug']}.html").write_text(page_shell(config,f"LEGO {row['Number']} Instructions – {row['SetName']} | LEGO Instructions For You",f"Find LEGO {row['Number']} instructions for {row['SetName']}. Watch a build video, browse the theme, and find official LEGO building instructions.",body), encoding="utf-8")

def write_robots(config):
    (OUTPUT_DIR/"robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {config['domain'].rstrip('/')}/sitemap.xml\n", encoding="utf-8")

def write_sitemap(config, sets_df):
    base = config["domain"].rstrip("/")
    urls = [f"{base}/", f"{base}/themes/"] + [f"{base}/themes/{slug}.html" for slug in sorted(sets_df["theme_slug"].unique())] + [f"{base}/sets/{slug}.html" for slug in sets_df["slug"].tolist()]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'] + [f"  <url><loc>{escape(u)}</loc></url>" for u in urls] + ["</urlset>"]
    (OUTPUT_DIR/"sitemap.xml").write_text("\n".join(xml), encoding="utf-8")

def main():
    config = load_config()
    sets_df, playlist_df = read_inputs()
    sets_df = prepare_sets(sets_df)
    playlist_df = prepare_playlist(playlist_df)
    matched = match_videos(sets_df, playlist_df)
    latest = latest_uploads(matched, sets_df)
    ensure_dirs()
    copy_branding()
    write_assets()
    write_home(config, sets_df, matched, latest)
    write_theme_pages(config, sets_df, matched)
    write_set_pages(config, sets_df, matched)
    write_robots(config)
    write_sitemap(config, sets_df)
    print("Build complete.")
    print(f"Set pages: {len(sets_df)}")
    print(f"Matched videos: {len(matched)}")
    print(f"Output folder: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
