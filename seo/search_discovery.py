"""Publish an accurate LEGO update feed and notify IndexNow on GitHub site pushes.

Runs inside GitHub Actions after Build_Website.py pushes generated files.
Google still controls its own crawl/indexing schedule; this script never calls
Google's restricted Indexing API. Uses Python standard library only.
"""

from __future__ import annotations

import base64
import datetime as dt
import html
from html.parser import HTMLParser
import json
import os
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

REPO = "critchx/brickinstructionsforyou-site"
HOST = "www.brickinstructionsforyou.com"
BASE = f"https://{HOST}"
FEED_PATH = "public/lego-updates.xml"
FEED_URL = f"{BASE}/lego-updates.xml"
INDEXNOW_KEY = "52fdcd9f9582abe35aadda14d1e33718"
KEY_URL = f"{BASE}/{INDEXNOW_KEY}.txt"
HUB = "https://pubsubhubbub.appspot.com/"
XML_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
ATOM_NS = "http://www.w3.org/2005/Atom"
ET.register_namespace("atom", ATOM_NS)
TIMEOUT = 20
MAX_FEED_ITEMS = 75
MAX_NOTIFICATIONS = 300


def http(url: str, *, method: str = "GET", payload: bytes | None = None,
         headers: dict[str, str] | None = None, timeout: int = TIMEOUT) -> tuple[int, bytes]:
    request = Request(url, data=payload, headers=headers or {}, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except HTTPError as exc:
        details = exc.read(400).decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {details}") from exc


def github(method: str, path: str, data: dict | None = None) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN missing")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "bify-seo-discovery/1.0",
    }
    payload = None if data is None else json.dumps(data).encode("utf-8")
    if payload is not None:
        headers["Content-Type"] = "application/json"
    status, body = http(f"https://api.github.com/repos/{REPO}/{path}", method=method,
                        payload=payload, headers=headers)
    return json.loads(body) if body else {}


def repo_text(path: str, ref: str | None = None) -> tuple[str, str | None]:
    api_path = f"contents/{quote(path, safe='/')}"
    if ref:
        api_path += "?ref=" + quote(ref, safe="")
    obj = github("GET", api_path)
    if obj.get("encoding") != "base64":
        raise RuntimeError(f"GitHub did not return base64 content for {path}")
    return base64.b64decode(obj["content"]).decode("utf-8"), obj.get("sha")


def save_repo_text(path: str, value: str, previous_sha: str | None) -> None:
    data = {
        "message": f"SEO discovery: refresh {path}",
        "content": base64.b64encode(value.encode("utf-8")).decode("ascii"),
        "branch": "main",
    }
    if previous_sha:
        data["sha"] = previous_sha
    github("PUT", f"contents/{quote(path, safe='/')}", data)
    print(f"Updated {path} on main")


def sitemap_urls(xml: str) -> dict[str, str]:
    root = ET.fromstring(xml)
    out: dict[str, str] = {}
    for item in root.findall(f"{XML_NS}url"):
        loc = (item.findtext(f"{XML_NS}loc") or "").strip()
        lastmod = (item.findtext(f"{XML_NS}lastmod") or "").strip()
        parsed = urlsplit(loc)
        if parsed.scheme != "https" or parsed.netloc != HOST:
            continue
        if not parsed.path.startswith("/lego-instructions/") or not parsed.path.endswith("/"):
            continue
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", lastmod):
            out[loc] = lastmod
    return out


class PageMeta(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonical = ""
        self.robots = ""
        self.description = ""
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {k.lower(): v or "" for k, v in attrs}
        if tag == "link" and "canonical" in data.get("rel", "").lower().split():
            self.canonical = data.get("href", "")
        if tag == "meta":
            name = data.get("name", "").lower()
            if name in {"robots", "googlebot", "bingbot"}:
                self.robots += " " + data.get("content", "").lower()
            if name == "description":
                self.description = html.unescape(data.get("content", ""))
        if tag == "title":
            self.in_title = True

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False


def page_path(url: str) -> str:
    p = urlsplit(url)
    if p.scheme != "https" or p.netloc != HOST or not p.path.startswith("/lego-instructions/"):
        raise ValueError(f"Invalid set URL: {url}")
    return "public" + p.path + "index.html"


def eligible(meta: PageMeta, url: str) -> bool:
    directives = {s.strip() for s in meta.robots.split(",")}
    if "noindex" in directives or "none" in directives or "noindex" in meta.robots:
        return False
    return meta.canonical.rstrip("/") == url.rstrip("/")


def xml_elem(parent: ET.Element, name: str, value: str) -> ET.Element:
    elem = ET.SubElement(parent, name)
    elem.text = value
    return elem


def build_feed(entries: list[tuple[str, str, PageMeta]]) -> str:
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    xml_elem(channel, "title", "Brick Instructions For You — latest LEGO set pages")
    xml_elem(channel, "link", BASE + "/")
    xml_elem(channel, "description", "Recently published and updated LEGO instruction and coming-soon set pages.")
    xml_elem(channel, "language", "en-gb")
    ET.SubElement(channel, f"{{{ATOM_NS}}}link", {
        "href": FEED_URL, "rel": "self", "type": "application/rss+xml",
    })
    ET.SubElement(channel, f"{{{ATOM_NS}}}link", {"href": HUB, "rel": "hub"})
    for url, lastmod, meta in entries:
        item = ET.SubElement(channel, "item")
        xml_elem(item, "title", meta.title.strip() or url.rsplit("/", 2)[-2])
        xml_elem(item, "link", url)
        guid = xml_elem(item, "guid", url)
        guid.set("isPermaLink", "true")
        xml_elem(item, "description", meta.description.strip() or "LEGO set information and instruction availability.")
        date = dt.date.fromisoformat(lastmod)
        xml_elem(item, "pubDate", dt.datetime.combine(date, dt.time(), dt.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z"))
    return ET.tostring(rss, encoding="unicode", xml_declaration=True) + "\n"


def check_public(url: str, expected: str | None = None, attempts: int = 6) -> bool:
    for attempt in range(attempts):
        try:
            _, body = http(url, headers={"User-Agent": "bify-seo-discovery/1.0"}, timeout=10)
            contents = body.decode("utf-8")
            if (expected is None and contents) or (expected is not None and contents.strip() == expected.strip()):
                return True
        except (RuntimeError, TimeoutError, URLError):
            pass
        if attempt < attempts - 1:
            time.sleep(15)
    print(f"WARN: {url} not yet deployed; skipping notification")
    return False


def notify_indexnow(urls: list[str]) -> None:
    if not urls:
        print("IndexNow: no changed eligible set URLs")
        return
    if not check_public(KEY_URL, INDEXNOW_KEY):
        return
    data = json.dumps({
        "host": HOST, "key": INDEXNOW_KEY, "keyLocation": KEY_URL,
        "urlList": urls[:MAX_NOTIFICATIONS],
    }).encode("utf-8")
    try:
        status, _ = http("https://api.indexnow.org/indexnow", method="POST", payload=data,
                          headers={"Content-Type": "application/json; charset=utf-8"})
        print(f"IndexNow accepted {len(urls[:MAX_NOTIFICATIONS])} URLs: HTTP {status} (indexing not guaranteed)")
    except (RuntimeError, URLError) as exc:
        print(f"WARN: IndexNow notification failed: {exc}")


def ping_websub(feed: str) -> None:
    if not check_public(FEED_URL, feed):
        return
    try:
        status, _ = http(HUB, method="POST", payload=urlencode({
            "hub.mode": "publish", "hub.url": FEED_URL,
        }).encode("utf-8"), headers={"Content-Type": "application/x-www-form-urlencoded"})
        print(f"WebSub notification: HTTP {status} (Google indexing not guaranteed)")
    except (RuntimeError, URLError) as exc:
        print(f"WARN: WebSub ping failed: {exc}")


def changed_from_compare(before: str, after: str) -> set[str]:
    if not before or before == "0" * 40:
        return set()
    try:
        response = github("GET", f"compare/{quote(before, safe='')}...{quote(after, safe='')}")
    except RuntimeError as exc:
        print(f"WARN: compare unavailable: {exc}")
        return set()
    out = set()
    for item in response.get("files", []):
        path = item.get("filename", "")
        if path.startswith("public/lego-instructions/") and path.endswith("/index.html") and item.get("status") != "removed":
            out.add(BASE + "/" + path[len("public/"):-len("index.html")])
    return out


def main() -> None:
    if os.environ.get("GITHUB_REPOSITORY") != REPO:
        raise RuntimeError("This task is restricted to the Brick Instructions For You repo")
    after = os.environ.get("GITHUB_SHA", "")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    before = ""
    if event_path and os.path.isfile(event_path):
        with open(event_path, encoding="utf-8") as f:
            before = json.load(f).get("before", "")

    sitemap, _ = repo_text("public/sitemap-sets.xml", after)
    current = sitemap_urls(sitemap)
    print(f"Found {len(current)} candidate LEGO set URLs in sitemap")
    previous: dict[str, str] = {}
    if before and before != "0" * 40:
        try:
            previous = sitemap_urls(repo_text("public/sitemap-sets.xml", before)[0])
        except RuntimeError as exc:
            print(f"WARN: previous sitemap unavailable: {exc}")
    changed = {u for u, m in current.items() if previous.get(u) != m}
    changed |= changed_from_compare(before, after)
    changed &= current.keys()
    print(f"Detected {len(changed)} added or changed sitemap/HTML set pages")

    # On first install, notify recently updated URLs as well. The initial
    # bootstrap also covers 75495 without artificially changing its lastmod.
    try:
        repo_text(FEED_PATH)
        first_install = False
    except RuntimeError as exc:
        if "404" not in str(exc):
            raise
        first_install = True
    if first_install:
        cutoff = (dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=4)).isoformat()
        bootstrap = {url for url, lastmod in current.items() if lastmod >= cutoff}
        changed |= bootstrap
        print(f"Initial bootstrap added {len(bootstrap)} recently changed set URLs")

    recent = sorted(current.items(), key=lambda x: (x[1], x[0]), reverse=True)[:MAX_FEED_ITEMS]
    changed_order = sorted(changed, key=lambda u: (current[u], u), reverse=True)
    inspect_urls = {u for u, _ in recent} | set(changed_order[:MAX_NOTIFICATIONS])
    metas: dict[str, PageMeta] = {}
    for url in sorted(inspect_urls):
        try:
            page, _ = repo_text(page_path(url), after)
            meta = PageMeta()
            meta.feed(page)
            if eligible(meta, url):
                metas[url] = meta
            else:
                print(f"SKIP non-indexable or canonical-mismatched: {url}")
        except RuntimeError as exc:
            print(f"WARN: page not available: {url}: {exc}")
    entries = [(u, m, metas[u]) for u, m in recent if u in metas]
    feed = build_feed(entries)
    try:
        existing, sha = repo_text(FEED_PATH)
    except RuntimeError as exc:
        if "404" not in str(exc):
            raise
        existing, sha = "", None
    if feed != existing:
        save_repo_text(FEED_PATH, feed, sha)
    else:
        print("RSS feed unchanged")

    robots, robots_sha = repo_text("public/robots.txt")
    rss_sitemap = f"Sitemap: {FEED_URL}"
    if rss_sitemap not in robots:
        save_repo_text("public/robots.txt", robots.rstrip() + "\n" + rss_sitemap + "\n", robots_sha)
    else:
        print("RSS discoverable from robots.txt")

    eligible_changed = [u for u in changed_order if u in metas]
    if len(changed) > MAX_NOTIFICATIONS:
        print(f"WARN: truncating IndexNow batch to {MAX_NOTIFICATIONS} pages")
    notify_indexnow(eligible_changed)
    if feed != existing:
        ping_websub(feed)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"SEO discovery failed (website deployment not affected): {exc}", file=sys.stderr)
        raise
