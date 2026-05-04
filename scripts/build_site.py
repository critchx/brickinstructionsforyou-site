import json, re, shutil, html
from pathlib import Path
from collections import defaultdict, Counter
import pandas as pd

ROOT=Path('public')
if ROOT.exists(): shutil.rmtree(ROOT)
for d in ['data','sets','2025','2026','themes','assets','scripts','search']:
    (ROOT/d).mkdir(parents=True, exist_ok=True)
BASE='https://www.brickinstructionsforyou.com'
PLAYLISTS={'2025':'https://www.youtube.com/playlist?app=desktop&list=PLQcpf5VzBO0r7AYWpgFpJcBfPDB8rf81V&cbrd=1','2026':'https://www.youtube.com/playlist?list=PLQcpf5VzBO0plGlm2VNlbO53VFPuqbJZv'}

def slug(s): return re.sub(r'[^a-z0-9]+','-',str(s or '').lower().replace('&','and')).strip('-') or 'set'
def esc(s): return html.escape(str(s or ''))
def clean(v):
    if pd.isna(v): return ''
    return str(v).strip()
def img(fn): return f'https://images.brickset.com/sets/images/{fn}.jpg' if fn else ''

sets=[]
for year, path in [('2025','data/2025.csv'),('2026','data/2026.csv')]:
    df=pd.read_csv(path,dtype=str).fillna('')
    for _,r in df.iterrows():
        num=clean(r.get('Number')); name=clean(r.get('SetName')); theme=clean(r.get('Theme')) or 'Other'
        sl=f'{num}-{slug(name)}'
        sets.append({'number':num,'name':name,'year':year,'theme':theme,'subtheme':clean(r.get('Subtheme')),
                     'pieces':clean(r.get('Pieces')),'minifigs':clean(r.get('Minifigs')),'price_uk':clean(r.get('UKRetailPrice')),
                     'launch':clean(r.get('LaunchDate')),'image':img(clean(r.get('ImageFilename'))),'slug':sl,'url':f'/sets/{sl}/'})
shutil.copy('data/2025.csv',ROOT/'data'/'2025.csv'); shutil.copy('data/2026.csv',ROOT/'data'/'2026.csv')
(ROOT/'data'/'videos.csv').write_text('year,playlist_id,set_number,video_type,book_number,title,youtube_url,thumbnail_url,published_at\n',encoding='utf-8-sig')
(ROOT/'data'/'videos.json').write_text('[]',encoding='utf-8')

CSS=""":root{--bg:#f6f8fc;--ink:#122033;--muted:#607086;--brand:#1558d6;--lego:#ffcf00;--line:#e5e9f2}*{box-sizing:border-box}body{margin:0;font-family:Inter,Arial,sans-serif;background:var(--bg);color:var(--ink)}a{color:inherit}.wrap{max-width:1200px;margin:auto;padding:0 22px}.top{background:#071833;color:white;position:sticky;top:0;z-index:10}.nav{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:16px 0}.brand{font-size:22px;font-weight:900;text-decoration:none}.links{display:flex;gap:16px;flex-wrap:wrap}.links a{color:white;text-decoration:none;font-weight:700}.hero{background:radial-gradient(circle at top right,#2875ff,#071833 62%);color:white;padding:70px 0}.heroGrid{display:grid;grid-template-columns:1.15fr .85fr;gap:34px;align-items:center}.hero h1{font-size:clamp(38px,6vw,68px);line-height:1.02;margin:0 0 18px}.hero p{font-size:19px;line-height:1.65}.searchPanel{background:white;color:var(--ink);border-radius:28px;padding:26px;box-shadow:0 25px 55px rgba(0,0,0,.28)}input{width:100%;border:1px solid var(--line);border-radius:14px;padding:15px;font-size:16px}.btn{display:inline-flex;background:var(--lego);color:#111;text-decoration:none;border-radius:14px;font-weight:900;padding:14px 18px;margin:4px}.btn.blue{background:var(--brand);color:white}.btn.dark{background:#071833;color:white}.section{padding:54px 0}.section h2{font-size:34px;margin:0 0 10px}.muted{color:var(--muted);line-height:1.65}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:20px;margin-top:24px}.card{background:white;border:1px solid var(--line);border-radius:24px;padding:22px;box-shadow:0 8px 24px rgba(18,32,51,.06)}.card h3{margin:8px 0;font-size:21px}.card p{color:var(--muted);line-height:1.55}.poster{width:100%;aspect-ratio:16/9;object-fit:contain;background:#fff;border-radius:18px;border:1px solid var(--line)}.pill{display:inline-flex;padding:8px 12px;border-radius:999px;background:#e9f2ff;color:#0f4cb8;font-weight:800;font-size:13px;text-decoration:none;margin:4px}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}.stat{background:white;border:1px solid var(--line);padding:16px;border-radius:18px}.stat b{font-size:24px;display:block}.setHero{display:grid;grid-template-columns:1fr 1.1fr;gap:30px;align-items:start}.crumbs{font-size:14px;color:var(--muted);margin-bottom:16px}.notice{background:#fff8d6;border:1px solid #f4d44d;border-radius:20px;padding:18px}.footer{background:#071833;color:#d7e0ec;padding:36px 0;margin-top:50px}.footer a{color:white}@media(max-width:800px){.heroGrid,.setHero{grid-template-columns:1fr}.links{font-size:14px}}"""
(ROOT/'assets'/'style.css').write_text(CSS,encoding='utf-8')
(ROOT/'assets'/'site.js').write_text("const box=document.querySelector('#siteSearch');if(box){box.addEventListener('input',e=>{const q=e.target.value.toLowerCase().trim();document.querySelectorAll('[data-search]').forEach(c=>c.style.display=c.dataset.search.includes(q)?'':'none')})}",encoding='utf-8')

def layout(title, desc, body, canonical='/', schema=None):
    sc=f"<script type='application/ld+json'>{json.dumps(schema)}</script>" if schema else ''
    return f"""<!doctype html><html lang='en-GB'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{esc(title)}</title><meta name='description' content='{esc(desc)}'><link rel='canonical' href='{BASE}{canonical}'><link rel='stylesheet' href='/assets/style.css'>{sc}</head><body><header class='top'><div class='wrap nav'><a class='brand' href='/'>Brick Instructions For You</a><nav class='links'><a href='/2025/'>2025</a><a href='/2026/'>2026</a><a href='/themes/'>Themes</a><a href='/search/'>Search</a><a href='https://www.youtube.com/@LEGOINSTRUCTIONSFORYOU'>YouTube</a></nav></div></header>{body}<footer class='footer'><div class='wrap'><b>Brick Instructions For You</b><p>Free LEGO building instruction videos by set number, theme, year and booklet.</p><p>LEGO® is a trademark of the LEGO Group, which does not sponsor, authorise or endorse this website.</p><p><a href='/sitemap.xml'>Sitemap</a> · <a href='/llms.txt'>AI / LLM information</a></p></div></footer><script src='/assets/site.js'></script></body></html>"""

def card(s):
    ds=esc((s['number']+' '+s['name']+' '+s['theme']+' '+s['year']).lower())
    return f"""<article class='card' data-search='{ds}'><img class='poster' src='{s['image']}' alt='LEGO {esc(s['number'])} {esc(s['name'])} box image' onerror='this.style.display="none"'><span class='pill'>{s['year']}</span><span class='pill'>{esc(s['theme'])}</span><h3><a href='{s['url']}'>LEGO {esc(s['number'])} {esc(s['name'])} Instructions</a></h3><p>{esc(s['pieces'] or 'Unknown')} pieces · {esc(s['subtheme'] or 'LEGO '+s['theme'])}</p></article>"""

by_year=defaultdict(list); by_theme=defaultdict(list)
for s in sets: by_year[s['year']].append(s); by_theme[slug(s['theme'])].append(s)
popular=Counter(s['theme'] for s in sets).most_common(14)

home_schema={"@context":"https://schema.org","@type":"WebSite","name":"Brick Instructions For You","url":BASE,"potentialAction":{"@type":"SearchAction","target":BASE+"/search/?q={search_term_string}","query-input":"required name=search_term_string"}}
popular_html=''.join([f"<a class='pill' href='/themes/{slug(t)}/'>{esc(t)} ({n})</a>" for t,n in popular])
home_cards=''.join(card(s) for s in sets[:12])
home=f"""<main><section class='hero'><div class='wrap heroGrid'><div><h1>LEGO Instructions by Set Number, Year and Booklet</h1><p>Browse modern LEGO instruction videos for 2025 and 2026 sets. Every page is made for Google and AI discovery, with All Books and Book 1, Book 2, Book 3+ matching for your YouTube playlists.</p><p><a class='btn' href='/2026/'>Browse 2026 Sets</a><a class='btn blue' href='/2025/'>Browse 2025 Sets</a></p></div><div class='searchPanel'><h2>Find a LEGO set</h2><p class='muted'>Search by set number, set name, theme or year.</p><input id='siteSearch' placeholder='Example: 43016, Speed Champions, Technic'></div></div></section><section class='section'><div class='wrap stats'><div class='stat'><b>{len(by_year['2025'])}</b>2025 sets</div><div class='stat'><b>{len(by_year['2026'])}</b>2026 sets</div><div class='stat'><b>{len(by_theme)}</b>theme pages</div><div class='stat'><b>2</b>YouTube playlists</div></div></section><section class='section'><div class='wrap'><h2>Start by year</h2><div class='grid'><article class='card'><h3><a href='/2025/'>LEGO 2025 Instructions</a></h3><p>All 2025 sets organised by theme, set number and instruction videos.</p><a class='btn' href='/2025/'>Open 2025</a></article><article class='card'><h3><a href='/2026/'>LEGO 2026 Instructions</a></h3><p>All 2026 sets ready for upcoming videos and AI-friendly indexing.</p><a class='btn' href='/2026/'>Open 2026</a></article></div></div></section><section class='section'><div class='wrap'><h2>Popular LEGO themes</h2><p class='muted'>Theme pages create extra SEO landing pages for Google searches.</p><div>{popular_html}</div></div></section><section class='section'><div class='wrap'><h2>Latest set pages</h2><div class='grid'>{home_cards}</div></div></section><section class='section'><div class='wrap'><div class='notice'><h2>YouTube playlist matching is built in</h2><p>Your 2025 and 2026 playlist IDs are saved in the included script. Run the YouTube export script, rebuild the site, and each set page will show only the videos that exist: All Books, Book 1, Book 2, Book 3, Book 4, Book 5 and more.</p></div></div></section></main>"""
(ROOT/'index.html').write_text(layout('LEGO Instructions by Set Number | Brick Instructions For You','Find LEGO building instruction videos by set number, year, theme and booklet. Browse 2025 and 2026 LEGO instructions linked with YouTube playlists.',''+home,'/',home_schema),encoding='utf-8')

for year, arr in by_year.items():
    themes_html=''.join([f"<a class='pill' href='/themes/{slug(t)}/'>{esc(t)} ({n})</a>" for t,n in Counter(s['theme'] for s in arr).most_common(40)])
    cards=''.join(card(s) for s in arr)
    body=f"<main><section class='hero'><div class='wrap'><div class='crumbs'><a href='/'>Home</a> / {year}</div><h1>LEGO {year} Instructions</h1><p>Browse LEGO {year} building instruction videos by set number, theme and booklet.</p><input id='siteSearch' placeholder='Search {year} sets'></div></section><section class='section'><div class='wrap'><h2>LEGO {year} themes</h2><div>{themes_html}</div><div class='grid'>{cards}</div></div></section></main>"
    (ROOT/year/'index.html').write_text(layout(f'LEGO {year} Instructions | Set Number Videos',f'Browse LEGO {year} instruction videos by set number, theme and booklet.',body,f'/{year}/'),encoding='utf-8')

# themes
items=''.join([f"<article class='card'><h3><a href='/themes/{ts}/'>{esc(arr[0]['theme'])}</a></h3><p>{len(arr)} sets available.</p></article>" for ts,arr in sorted(by_theme.items())])
(ROOT/'themes'/'index.html').write_text(layout('LEGO Instructions by Theme','Browse LEGO instruction videos by theme including Technic, City, Speed Champions, Icons and more.',f"<main><section class='hero'><div class='wrap'><h1>LEGO Instructions by Theme</h1><p>Browse LEGO set instruction videos by theme across 2025 and 2026.</p></div></section><section class='section'><div class='wrap'><div class='grid'>{items}</div></div></section></main>",'/themes/'),encoding='utf-8')
for ts, arr in by_theme.items():
    p=ROOT/'themes'/ts; p.mkdir(exist_ok=True)
    theme=arr[0]['theme']; cards=''.join(card(s) for s in arr)
    body=f"<main><section class='hero'><div class='wrap'><div class='crumbs'><a href='/'>Home</a> / <a href='/themes/'>Themes</a> / {esc(theme)}</div><h1>LEGO {esc(theme)} Instructions</h1><p>Browse LEGO {esc(theme)} instruction videos and set pages for 2025 and 2026.</p><input id='siteSearch' placeholder='Search {esc(theme)} sets'></div></section><section class='section'><div class='wrap'><div class='grid'>{cards}</div></div></section></main>"
    (p/'index.html').write_text(layout(f'LEGO {theme} Instructions | 2025 and 2026 Videos',f'Find LEGO {theme} instruction videos by set number, year and booklet.',body,f'/themes/{ts}/'),encoding='utf-8')

# sets
for s in sets:
    p=ROOT/'sets'/s['slug']; p.mkdir(exist_ok=True)
    related=''.join(card(x) for x in by_theme[slug(s['theme'])][:5] if x['url']!=s['url'])
    detail=f"<div class='stats'><div class='stat'><b>{esc(s['number'])}</b>Set number</div><div class='stat'><b>{s['year']}</b>Year</div><div class='stat'><b>{esc(s['pieces'] or '—')}</b>Pieces</div><div class='stat'><b>{esc(s['price_uk'] or '—')}</b>UK RRP</div></div>"
    vids=f"<div class='notice'><h2>Instruction videos</h2><p>This page is ready for automatic video matching. After running the included YouTube export script, this section will display only the videos that exist for this set.</p><p><span class='pill'>All Books</span><span class='pill'>Book 1</span><span class='pill'>Book 2</span><span class='pill'>Book 3+</span></p><p><a class='btn dark' href='{PLAYLISTS[s['year']]}'>Open LEGO {s['year']} YouTube playlist</a></p></div>"
    body=f"<main><section class='section'><div class='wrap'><div class='crumbs'><a href='/'>Home</a> / <a href='/{s['year']}/'>{s['year']}</a> / <a href='/themes/{slug(s['theme'])}/'>{esc(s['theme'])}</a></div><div class='setHero'><div><img class='poster' src='{s['image']}' alt='LEGO {esc(s['number'])} {esc(s['name'])}' onerror='this.style.display=\"none\"'></div><div><span class='pill'>{s['year']}</span><span class='pill'>{esc(s['theme'])}</span><h1>LEGO {esc(s['number'])} {esc(s['name'])} Instructions</h1><p class='muted'>Watch LEGO {esc(s['number'])} {esc(s['name'])} building instructions by set number, booklet and All Books video. This page is designed for Google and AI search results.</p>{detail}</div></div></div></section><section class='section'><div class='wrap'>{vids}</div></section><section class='section'><div class='wrap'><h2>Related {esc(s['theme'])} sets</h2><div class='grid'>{related}</div></div></section></main>"
    schema={"@context":"https://schema.org","@type":"WebPage","name":f"LEGO {s['number']} {s['name']} Instructions","description":f"LEGO {s['number']} {s['name']} instruction videos with All Books and individual booklets."}
    (p/'index.html').write_text(layout(f'LEGO {s["number"]} {s["name"]} Instructions | All Books & Booklets',f'Watch LEGO {s["number"]} {s["name"]} instructions with All Books and individual booklet video matching.',body,s['url'],schema),encoding='utf-8')

allcards=''.join(card(s) for s in sets)
(ROOT/'search'/'index.html').write_text(layout('Search LEGO Instructions by Set Number','Search LEGO 2025 and 2026 instruction videos by set number, name, theme and booklet.',f"<main><section class='hero'><div class='wrap'><h1>Search LEGO Instructions</h1><p>Search every 2025 and 2026 LEGO set by number, name, year or theme.</p><input id='siteSearch' placeholder='Search set number, name or theme'></div></section><section class='section'><div class='wrap'><div class='grid'>{allcards}</div></div></section></main>",'/search/'),encoding='utf-8')

urls=['/','/2025/','/2026/','/themes/','/search/']+[f'/themes/{ts}/' for ts in by_theme]+[s['url'] for s in sets]
(ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{BASE}{u}</loc></url>\n' for u in urls)+'</urlset>',encoding='utf-8')
(ROOT/'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n',encoding='utf-8')
(ROOT/'llms.txt').write_text(f"""# Brick Instructions For You

This website helps users find LEGO building instruction videos by set number, year, theme and booklet.

Important pages:
- {BASE}/2025/ - LEGO 2025 instructions
- {BASE}/2026/ - LEGO 2026 instructions
- {BASE}/themes/ - LEGO theme pages
- {BASE}/search/ - set number search

YouTube playlists:
- 2025: {PLAYLISTS['2025']}
- 2026: {PLAYLISTS['2026']}

Each set page supports All Books plus individual Book 1, Book 2, Book 3+ video matching.
""",encoding='utf-8')

update_script='''import requests, pandas as pd, re, json\nfrom pathlib import Path\n\nAPI_KEY = "PASTE_YOUR_YOUTUBE_API_KEY_HERE"\nPLAYLISTS = {\n    "2025": "PLQcpf5VzBO0r7AYWpgFpJcBfPDB8rf81V",\n    "2026": "PLQcpf5VzBO0plGlm2VNlbO53VFPuqbJZv",\n}\nOUT_CSV = Path("data/videos.csv")\nOUT_JSON = Path("data/videos.json")\n\ndef detect_video_type(title):\n    t = title.lower()\n    m = re.search(r"book\\s*(\\d+)", t)\n    if "all books" in t or "all book" in t or "complete build" in t or "full build" in t:\n        return "all_books", ""\n    if m:\n        return "book", m.group(1)\n    return "unknown", ""\n\ndef detect_set_number(title):\n    nums = re.findall(r"(?<!\\d)(\\d{4,6})(?!\\d)", title)\n    return nums[0] if nums else ""\n\nrows=[]\nfor year, playlist_id in PLAYLISTS.items():\n    page_token=None\n    while True:\n        params={"part":"snippet,contentDetails","playlistId":playlist_id,"maxResults":50,"key":API_KEY}\n        if page_token:\n            params["pageToken"] = page_token\n        data=requests.get("https://www.googleapis.com/youtube/v3/playlistItems", params=params, timeout=30).json()\n        if "error" in data:\n            raise RuntimeError(data["error"])\n        for item in data.get("items", []):\n            sn=item.get("snippet", {})\n            video_id=sn.get("resourceId", {}).get("videoId", "")\n            title=sn.get("title", "")\n            vtype, book=detect_video_type(title)\n            thumbs=sn.get("thumbnails", {})\n            thumb=(thumbs.get("maxres") or thumbs.get("high") or thumbs.get("medium") or {}).get("url", "")\n            rows.append({"year":year,"playlist_id":playlist_id,"set_number":detect_set_number(title),"video_type":vtype,"book_number":book,"title":title,"youtube_url":f"https://www.youtube.com/watch?v={video_id}","thumbnail_url":thumb,"published_at":sn.get("publishedAt", "")})\n        page_token=data.get("nextPageToken")\n        if not page_token:\n            break\nOUT_CSV.parent.mkdir(exist_ok=True)\npd.DataFrame(rows).to_csv(OUT_CSV, index=False, encoding="utf-8-sig")\nOUT_JSON.write_text(json.dumps(rows, indent=2), encoding="utf-8")\nprint(f"Saved {len(rows)} videos")\n'''
(ROOT/'scripts'/'update_youtube_videos.py').write_text(update_script,encoding='utf-8')
(ROOT/'scripts'/'build_site.py').write_text(Path('/mnt/data/build_site_v3_fixed.py').read_text(encoding='utf-8').replace("ROOT=Path('public')","ROOT=Path('public')").replace("'data/2025.csv'","'data/2025.csv'").replace("'data/2026.csv'","'data/2026.csv'").replace("shutil.copy('data/2025.csv',ROOT/'data'/'2025.csv'); shutil.copy('data/2026.csv',ROOT/'data'/'2026.csv')","# CSVs already copied into data folder"),encoding='utf-8')
(ROOT/'README.txt').write_text(f"""BRICK INSTRUCTIONS FOR YOU - UPDATED WEBSITE

Included:
- Modern SEO homepage
- /2025/ and /2026/ year pages
- Theme pages
- Individual set pages for every row in your CSV files
- Search page
- sitemap.xml, robots.txt and llms.txt for AI discovery
- YouTube playlist export script

Playlists configured:
2025: {PLAYLISTS['2025']}
2026: {PLAYLISTS['2026']}

How to connect your YouTube videos:
1. Open scripts/update_youtube_videos.py
2. Paste your YouTube API key
3. Run: python scripts/update_youtube_videos.py
4. Run: python scripts/build_site.py
5. Upload the public folder to Cloudflare Pages

Video matching supports All Books and Book 1, Book 2, Book 3, Book 4, Book 5+.
""",encoding='utf-8')
shutil.make_archive('/mnt/data/brick-instructions-seo-website-2025-2026-playlists','zip',ROOT)
print('created', len(sets), 'sets', len(urls), 'urls')
