import requests, pandas as pd, re, json
from pathlib import Path

API_KEY = "PASTE_YOUR_YOUTUBE_API_KEY_HERE"
PLAYLISTS = {
    "2025": "PLQcpf5VzBO0r7AYWpgFpJcBfPDB8rf81V",
    "2026": "PLQcpf5VzBO0plGlm2VNlbO53VFPuqbJZv",
}
OUT_CSV = Path("data/videos.csv")
OUT_JSON = Path("data/videos.json")

def detect_video_type(title):
    t = title.lower()
    m = re.search(r"book\s*(\d+)", t)
    if "all books" in t or "all book" in t or "complete build" in t or "full build" in t:
        return "all_books", ""
    if m:
        return "book", m.group(1)
    return "unknown", ""

def detect_set_number(title):
    nums = re.findall(r"(?<!\d)(\d{4,6})(?!\d)", title)
    return nums[0] if nums else ""

rows=[]
for year, playlist_id in PLAYLISTS.items():
    page_token=None
    while True:
        params={"part":"snippet,contentDetails","playlistId":playlist_id,"maxResults":50,"key":API_KEY}
        if page_token:
            params["pageToken"] = page_token
        data=requests.get("https://www.googleapis.com/youtube/v3/playlistItems", params=params, timeout=30).json()
        if "error" in data:
            raise RuntimeError(data["error"])
        for item in data.get("items", []):
            sn=item.get("snippet", {})
            video_id=sn.get("resourceId", {}).get("videoId", "")
            title=sn.get("title", "")
            vtype, book=detect_video_type(title)
            thumbs=sn.get("thumbnails", {})
            thumb=(thumbs.get("maxres") or thumbs.get("high") or thumbs.get("medium") or {}).get("url", "")
            rows.append({"year":year,"playlist_id":playlist_id,"set_number":detect_set_number(title),"video_type":vtype,"book_number":book,"title":title,"youtube_url":f"https://www.youtube.com/watch?v={video_id}","thumbnail_url":thumb,"published_at":sn.get("publishedAt", "")})
        page_token=data.get("nextPageToken")
        if not page_token:
            break
OUT_CSV.parent.mkdir(exist_ok=True)
pd.DataFrame(rows).to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
OUT_JSON.write_text(json.dumps(rows, indent=2), encoding="utf-8")
print(f"Saved {len(rows)} videos")
