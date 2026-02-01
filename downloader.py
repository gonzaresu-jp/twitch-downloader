#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import re
import requests
import subprocess
from datetime import datetime, timedelta, timezone
import yt_dlp
from PIL import Image

# ========= 環境 =========
os.environ["YTDLP_NO_CONFIG"] = "1"
# Twitch APIのクライアントID・トークン・まいちゃんのユーザーID
TWITCH_CLIENT_ID = ""
TWITCH_TOKEN = ""
TWITCH_USER_ID = "773944657"

if not all([TWITCH_CLIENT_ID, TWITCH_TOKEN, TWITCH_USER_ID]):
    sys.exit("Missing Twitch env vars")

HEADERS = {
    "Client-Id": TWITCH_CLIENT_ID,
    "Authorization": f"Bearer {TWITCH_TOKEN}",
}

# =========================================================
# Twitch API: 直近N日以内のVOD取得
# =========================================================
# days: 取得する日数
def list_recent_vods(days: int = 1) -> list[dict]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    vids: list[dict] = []
    cursor = None

    while True:
        params = {
            "user_id": TWITCH_USER_ID,
            "type": "archive",
            "first": 100,
        }
        if cursor:
            params["after"] = cursor

        r = requests.get(
            "https://api.twitch.tv/helix/videos",
            headers=HEADERS,
            params=params,
        )
        r.raise_for_status()

        data = r.json()

        for v in data["data"]:
            created = datetime.fromisoformat(v["created_at"].replace("Z","+00:00"))
            if created < start:
                continue

            vids.append(v)

        cursor = data.get("pagination", {}).get("cursor")
        if not cursor:
            break

    return vids


# =========================================================
# ファイル名サニタイズ（流用）
# =========================================================
def sanitize_for_processing(title: str) -> str:
    safe = re.sub(r'[\\/:*?"<>|]', "_", title)
    safe = re.sub(r"\s+", " ", safe).strip()
    return safe if safe else "video"


# =========================================================
# yt-dlp オプション（Twitch用）
# =========================================================
def make_ydl_opts(download_dir: str, video_id: str) -> dict:
    os.makedirs(download_dir, exist_ok=True)

    archive_file = os.path.join(download_dir, "archive_ids.txt")
    temp_template = os.path.join(download_dir, f"{video_id}_temp.%(ext)s")

    return {
        "outtmpl": temp_template,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",

        "download_archive": archive_file,

        "retries": 20,
        "fragment_retries": 50,
        "ignoreerrors": True,
        "noprogress": True,
    }


# =========================================================
# Twitch動画1本DL
# =========================================================
def download_one(vod: dict, download_dir: str) -> None:
    video_id = vod["id"]
    title = vod["title"]

    url = f"https://www.twitch.tv/videos/{video_id}"

    print(f"[INFO] Downloading: {title}")

    opts = make_ydl_opts(download_dir, video_id)

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    temp_file = os.path.join(download_dir, f"{video_id}_temp.mp4")

    safe_title = sanitize_for_processing(title)[:200]
    final_file = os.path.join(download_dir, f"{safe_title}.mp4")

    if os.path.exists(temp_file):
        os.rename(temp_file, final_file)
        print(f"[INFO] Saved -> {final_file}")
    else:
        print(f"[WARN] missing file {temp_file}")


# =========================================================
# main
# =========================================================
def main() -> None:
    # ダウンロード先ディレクトリ
    download_dir = "/mnt/3TB/koinoyamai_Twitch/koinoya_mai"

    vods = list_recent_vods(days=2)

    if not vods:
        print("No recent VODs")
        return

    for v in vods:
        try:
            download_one(v, download_dir)
        except Exception as e:
            print(f"[error] {v['id']}: {e}")


if __name__ == "__main__":
    main()
