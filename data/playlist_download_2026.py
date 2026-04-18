import csv
import json
import subprocess
import sys
from pathlib import Path


PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLQcpf5VzBO0pL1tWvGeI-1Wp6TcmBNo3j"
OUTPUT_JSON = "playlist.json"
OUTPUT_CSV = "playlist.csv"


def run_ytdlp(playlist_url: str, output_json: str) -> None:
    command = [
        "yt-dlp",
        "--flat-playlist",
        "-J",
        playlist_url,
    ]

    print("Getting playlist data with yt-dlp...")

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8"
    )

    if result.returncode != 0:
        print("yt-dlp failed.")
        print(result.stderr)
        sys.exit(1)

    with open(output_json, "w", encoding="utf-8") as f:
        f.write(result.stdout)

    print(f"Saved JSON to: {output_json}")


def json_to_csv(input_json: str, output_csv: str) -> None:
    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    videos = data.get("entries", [])

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "video_id", "url"])

        for video in videos:
            video_id = video.get("id", "")
            title = video.get("title", "")
            url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""

            writer.writerow([title, video_id, url])

    print(f"Saved CSV to: {output_csv}")
    print(f"Exported {len(videos)} videos.")


def main() -> None:
    run_ytdlp(PLAYLIST_URL, OUTPUT_JSON)
    json_to_csv(OUTPUT_JSON, OUTPUT_CSV)
    print("Done.")


if __name__ == "__main__":
    main()