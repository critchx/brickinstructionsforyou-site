import csv
import json
import re
import sys
from pathlib import Path

import requests


# =========================
# SETTINGS
# =========================

API_KEY = "AIzaSyChETIX73w3p9ZXVpAb_HW_T5ee5v8rnOY"

PLAYLISTS = {
    "2025": "PLQcpf5VzBO0r7AYWpgFpJcBfPDB8rf81V",
    "2026": "PLQcpf5VzBO0plGlm2VNlbO53VFPuqbJZv",
}

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

OUT_CSV = DATA_DIR / "videos.csv"
OUT_JSON = DATA_DIR / "videos.json"


# =========================
# HELPERS
# =========================

def clean_api_key(key: str) -> str:
    return key.strip().replace('"', "").replace("'", "")


def extract_set_number(title: str):
    match = re.search(r"\b(\d{4,7})\b", title)
    return match.group(1) if match else ""


def detect_video_type(title: str):
    title_lower = title.lower()

    if "all books" in title_lower or "complete build" in title_lower or "full build" in title_lower:
        return "all_books", ""

    match = re.search(r"book\s*(\d+)", title_lower)
    if match:
        return "book", match.group(1)

    return "unknown", ""


def get_thumbnail(snippet):
    thumbs = snippet.get("thumbnails", {})
    for size in ["maxres", "standard", "high", "medium", "default"]:
        if size in thumbs:
            return thumbs[size].get("url", "")
    return ""


def youtube_api_get(params):
    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    response = requests.get(url, params=params, timeout=30)

    try:
        data = response.json()
    except Exception:
        print("ERROR: YouTube did not return JSON.")
        print(response.text)
        sys.exit(1)

    if "error" in data:
        print("\nYOUTUBE API ERROR")
        print("=================")
        print(json.dumps(data["error"], indent=2))
        print("\nChecks:")
        print("1. Make sure API_KEY is your full real API key.")
        print("2. Make sure YouTube Data API v3 is enabled.")
        print("3. Make sure playlist IDs are not full URLs.")
        print("4. Wait 5 minutes after changing Google Cloud settings.")
        sys.exit(1)

    return data


# =========================
# MAIN
# =========================

def export_playlists():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    api_key = clean_api_key(API_KEY)

    print("Using API key:", api_key[:8] + "...", "length:", len(api_key))

    if not api_key or api_key == "PASTE_YOUR_REAL_YOUTUBE_API_KEY_HERE":
        print("ERROR: Add your real YouTube API key first.")
        sys.exit(1)

    rows = []

    for year, playlist_id in PLAYLISTS.items():
        print(f"\nDownloading playlist {year}: {playlist_id}")

        page_token = None
        count = 0

        while True:
            params = {
                "part": "snippet,contentDetails",
                "playlistId": playlist_id,
                "maxResults": 50,
                "key": api_key,
            }

            if page_token:
                params["pageToken"] = page_token

            data = youtube_api_get(params)

            items = data.get("items", [])

            for item in items:
                snippet = item.get("snippet", {})

                # Skip deleted/private playlist entries
                title = snippet.get("title", "")
                if title.lower() in ["deleted video", "private video"]:
                    continue

                resource = snippet.get("resourceId", {})
                video_id = resource.get("videoId", "")

                if not video_id:
                    continue

                set_number = extract_set_number(title)
                video_type, book_number = detect_video_type(title)

                row = {
                    "year": year,
                    "playlist_id": playlist_id,
                    "video_id": video_id,
                    "set_number": set_number,
                    "video_type": video_type,
                    "book_number": book_number,
                    "title": title,
                    "description": snippet.get("description", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
                    "embed_url": f"https://www.youtube.com/embed/{video_id}",
                    "thumbnail_url": get_thumbnail(snippet),
                }

                rows.append(row)
                count += 1

            page_token = data.get("nextPageToken")

            if not page_token:
                break

        print(f"Found {count} videos for {year}")

    fieldnames = [
        "year",
        "playlist_id",
        "video_id",
        "set_number",
        "video_type",
        "book_number",
        "title",
        "description",
        "published_at",
        "youtube_url",
        "embed_url",
        "thumbnail_url",
    ]

    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    print("\nDONE")
    print("====")
    print(f"Saved CSV:  {OUT_CSV}")
    print(f"Saved JSON: {OUT_JSON}")
    print(f"Total videos saved: {len(rows)}")


if __name__ == "__main__":
    export_playlists()