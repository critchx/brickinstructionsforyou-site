"""Maintain an evergreen /latest/ landing page from published video pages.

This intentionally does not edit Build_Website.py, sitemap lastmod, set HTML,
product data, affiliate URLs, images or external video embeds. It is a targeted
post-publish repair because Build_Website.py currently chooses a future year
with only one video for the Latest page.

Uses the site homepage's 'Latest YYYY LEGO instructions' grid as its source of
recently uploaded video-guide links, then verifies each page's canonical, indexing
eligibility and embedded VideoObject. Verified releases in the past 90 days are
featured before other newly uploaded guides. The code does not guess dates.
"""
from __future__ import annotations

import base64
from datetime import date, datetime, timedelta, timezone
from html import escape, unescape
from html.parser import HTMLParser
import json
import os
import re
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

REPO = "critchx/brickinstructionsforyou-site"
BASE = "https://www.brickinstructionsforyou.com"
MAIN_PAGE = "public/index.html"
LATEST_PAGE = "public/latest/index.html"
LIMIT = 35
NEW_RELEASE_WINDOW_DAYS = 90


def api(method: str, path: str, payload: dict | None = None) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN missing")
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "bify-latest-published/1.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    url = f"https://api.github.com/repos/{REPO}/{path}"
    with urlopen(Request(url, data=body, method=method, headers=headers), timeout=25) as r:
        return json.load(r)


def fetch(path: str) -> tuple[str, str]:
    obj = api("GET", "contents/" + quote(path, safe="/"))
    if obj.get("encoding") != "base64":
        raise RuntimeError(f"Unexpected encoding for {path}")
    return base64.b64decode(obj["content"]).decode("utf-8"), obj["sha"]


def save(path: str, text: str, sha: str) -> None:
    api("PUT", "contents/" + quote(path, safe="/"), {
        "message": "SEO: keep Latest page focused on published video guides",
        "branch": "main",
        "sha": sha,
        "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
    })


def grid_inner(source: str, after_index: int) -> str:
    """Extract one <div class='grid'> robustly despite inner card <div>s."""
    match = re.search(r'<div\b[^>]*class="[^"]*\bgrid\b[^"]*"[^>]*>', source[after_index:])
    if not match:
        raise ValueError("Latest video grid not found in homepage")
    opening_start = after_index + match.start()
    opening_end = after_index + match.end()
    depth = 1
    for token in re.finditer(r'<div\b[^>]*>|</div\s*>', source[opening_end:], re.I):
        depth += -1 if token.group().lower().startswith('</div') else 1
        if depth == 0:
            return source[opening_end:opening_end + token.start()]
    raise ValueError(f"Unclosed grid at {opening_start}")


def homepage_candidates(homepage: str, today: date) -> tuple[int, list[tuple[str, str, str]]]:
    """(year, [(site-relative URL, full reusable card HTML, readable title)])."""
    matches = list(re.finditer(r'<h2>Latest\s+(20\d{2})\s+LEGO instructions</h2>', homepage, re.I))
    matches = [m for m in matches if int(m.group(1)) <= today.year]
    if not matches:
        raise ValueError("No current/past-year Latest guide section found on homepage")
    match = max(matches, key=lambda m: int(m.group(1)))
    year = int(match.group(1))
    inner = grid_inner(homepage, match.end())
    cards = []
    seen = set()
    for cm in re.finditer(r'(<a class="set-card" href="(?P<href>/lego-instructions/[^"?]+/)">[\s\S]*?</a>)', inner):
        link = cm.group("href")
        if link in seen:
            continue
        seen.add(link)
        content = cm.group(1)
        name = re.search(r'<div class="set-name">([\s\S]*?)</div>', content)
        number = re.search(r'<div class="set-number">([\s\S]*?)</div>', content)
        if not name or not number:
            continue
        title = unescape(re.sub(r'<[^>]+>', '', number.group(1)).strip() + " " + re.sub(r'<[^>]+>', '', name.group(1)).strip())
        cards.append((link, content, title))
        if len(cards) >= LIMIT:
            break
    if len(cards) < 5:
        raise ValueError(f"Homepage has only {len(cards)} new video guides; refusing to replace /latest/")
    return year, cards


class PageFacts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.canonical = ""
        self.robots = ""
        self.content = []
        self.in_script = False
        self.visible = []

    def handle_starttag(self, tag: str, attrs):
        d = {k.lower(): v or "" for k, v in attrs}
        if tag == "link" and "canonical" in d.get("rel", "").lower().split():
            self.canonical = d.get("href", "")
        if tag == "meta" and d.get("name", "").lower() in ("robots", "googlebot"):
            self.robots += " " + d.get("content", "").lower()
        if tag == "script":
            self.in_script = True
        if tag == "style":
            self.in_script = True

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.in_script = False

    def handle_data(self, data):
        if not self.in_script:
            self.visible.append(data)


def inspect_published(url: str, page: str, today: date) -> tuple[bool, date | None]:
    facts = PageFacts()
    facts.feed(page)
    if facts.canonical.rstrip("/") != url.rstrip("/"):
        return False, None
    if re.search(r'\b(noindex|none)\b', facts.robots):
        return False, None
    if not re.search(r'"@type"\s*:\s*"VideoObject"', page):
        return False, None
    visible = re.sub(r'\s+', ' ', ' '.join(facts.visible))
    found = re.search(r'\breleased on\s+(\d{1,2}\s+[A-Za-z]+\s+20\d{2})\b', visible, re.I)
    if found:
        try:
            release = datetime.strptime(found.group(1), "%d %B %Y").date()
            if release <= today:
                return True, release
        except ValueError:
            pass
    return True, None


def replacement_main(year: int, released: list[tuple], others: list[tuple]) -> str:
    def section(heading: str, subtitle: str, cards: list[tuple]) -> str:
        if not cards:
            return ""
        return ('<section class="latest-video-section" aria-label="' + escape(heading, quote=True) + '">' +
                '<div class="results-header"><div><h2>' + escape(heading) + '</h2><p>' + escape(subtitle) + '</p></div></div>' +
                '<div class="grid">' + '\n'.join(card for _, card, *_ in cards) + '</div></section>')
    intro = ('<main id="pageContent"><div class="results-header"><div>'
             '<h1>Latest LEGO Building Instructions</h1>'
             '<p>Explore newly published, step-by-step LEGO video guides. Recent releases are shown first when their release dates are verified.</p>'
             '</div><a class="btn-outline" href="/' + str(year) + '/">BROWSE ' + str(year) + ' SETS</a></div>')
    intro += section('Recently released LEGO sets', 'Sets with published video guides and confirmed release dates within the last 90 days.', released)
    intro += section('Newest instruction videos', 'More newly added guides, including promotional and magazine builds. Release dates may vary.', others)
    intro += '<p style="margin-top:24px;">Looking for sets not yet available? <a href="/upcoming/">Browse upcoming LEGO sets</a>.</p></main>'
    return intro


def replace_meta(page: str, label: str, old_pattern: str, new_html: str) -> str:
    out, count = re.subn(old_pattern, lambda _: new_html, page, count=1, flags=re.I | re.S)
    if count != 1:
        raise ValueError(f"Cannot find exactly one {label} in /latest/ page")
    return out


def rewrite(home: str, latest: str, pages: dict[str, str], today: date) -> tuple[str, dict]:
    year, cards = homepage_candidates(home, today)
    released = []
    other = []
    skipped = []
    for link, card, name in cards:
        url = BASE + link
        if link not in pages:
            skipped.append((link, "HTML unavailable"))
            continue
        valid, release = inspect_published(url, pages[link], today)
        if not valid:
            skipped.append((link, "missing video, canonical mismatch or noindex"))
            continue
        item = (link, card, name, release)
        if release and today >= release and (today - release).days <= NEW_RELEASE_WINDOW_DAYS:
            released.append(item)
        else:
            other.append(item)
    released.sort(key=lambda item: item[3], reverse=True)
    if len(released) + len(other) < 5:
        raise ValueError("Not enough verified published guides to replace Latest hub")
    title = "Latest LEGO Building Instructions – New Video Guides"
    desc = "Browse recently released LEGO sets and the latest published step-by-step instruction videos, with set details and video chapters where available."
    out = latest
    out = replace_meta(out, "HTML title", r'<title>[\s\S]*?</title>', '<title>' + title + '</title>')
    out = replace_meta(out, "description", r'<meta name="description" content="[^"]*"\s*/?>', '<meta name="description" content="' + escape(desc, quote=True) + '">')
    for prop in ("og:title", "twitter:title"):
        out = replace_meta(out, prop, r'<meta (?:name|property)="' + re.escape(prop) + r'" content="[^"]*"\s*/?>', '<meta ' + ('property' if prop.startswith('og:') else 'name') + '="' + prop + '" content="' + escape(title, quote=True) + '">')
    for prop in ("og:description", "twitter:description"):
        out = replace_meta(out, prop, r'<meta (?:name|property)="' + re.escape(prop) + r'" content="[^"]*"\s*/?>', '<meta ' + ('property' if prop.startswith('og:') else 'name') + '="' + prop + '" content="' + escape(desc, quote=True) + '">')
    out = re.sub(r'LATEST\s+20\d{2}\s+VIDEOS', 'LATEST VIDEO GUIDES', out, flags=re.I)
    out = replace_meta(out, "main page content", r'<main id="pageContent">[\s\S]*?</main>', replacement_main(year, released, other))
    items = released + other
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "@id": BASE + "/latest/#webpage",
        "url": BASE + "/latest/",
        "name": title,
        "description": desc,
        "isPartOf": {"@id": BASE + "/#website"},
        "mainEntity": {
            "@type": "ItemList",
            "itemListElement": [
                {"@type": "ListItem", "position": i, "url": BASE + item[0], "name": item[2]}
                for i, item in enumerate(items, 1)
            ],
        },
    }
    script = '<script id="latestPublishedItemList" type="application/ld+json">' + json.dumps(schema, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c") + '</script>'
    if 'id="latestPublishedItemList"' in out:
        out = replace_meta(out, "latest JSON-LD", r'<script id="latestPublishedItemList" type="application/ld\+json">[\s\S]*?</script>', script)
    else:
        out = replace_meta(out, "head closing tag", r'</head>', script + '\n</head>')
    return out, {"year": year, "recently_released": len(released), "newest_guides": len(other), "skipped": skipped,
                 "release_titles": [x[2] for x in released]}


def main() -> None:
    if os.environ.get("GITHUB_REPOSITORY") != REPO:
        raise RuntimeError("This script is restricted to the correct website repository")
    home, _ = fetch(MAIN_PAGE)
    latest, sha = fetch(LATEST_PAGE)
    today = datetime.now(timezone.utc).date()
    year, cards = homepage_candidates(home, today)
    page_text = {}
    for link, card, name in cards:
        relative_path = "public" + urlsplit(link).path + "index.html"
        try:
            page_text[link], _ = fetch(relative_path)
        except Exception as exc:
            print(f"WARN: skipped {link}, cannot read page ({type(exc).__name__})")
    updated, result = rewrite(home, latest, page_text, today)
    print(json.dumps(result, ensure_ascii=False))
    if updated == latest:
        print("Latest hub already up to date; no commit")
    else:
        save(LATEST_PAGE, updated, sha)
        print("Updated /latest/ page in GitHub; automatic site deployment can publish it")
    print("Note: Google's indexing decision remains independent of these changes")


if __name__ == "__main__":
    main()
