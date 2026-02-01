#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import re
import requests
from datetime import datetime, timedelta, timezone
import yt_dlp


# =========================================================
# 固定設定（直書きOK版）
# =========================================================
os.environ["YTDLP_NO_CONFIG"] = "1"
# Twitch APIのClientID/Secret/まいちゃんのUserID(入力済み)
TWITCH_CLIENT_ID = ""
TWITCH_CLIENT_SECRET = ""
TWITCH_USER_ID = "773944657"

if not all([TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET, TWITCH_USER_ID]):
    sys.exit("Missing Twitch config")


# =========================================================
# OAuth: 毎回トークン発行（期限管理不要）
# =========================================================
def fetch_app_token() -> str:
    r = requests.post(
        "https://id.twitch.tv/oauth2/token",
        data={
            "client_id": TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials",
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def make_headers() -> dict:
    return {
        "Client-Id": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {fetch_app_token()}",
    }


# =========================================================
# VOD一覧取得
# =========================================================
# days: 過去何日分を取得するか
def list_recent_vods(days: int = 1) -> list[dict]:
    headers = make_headers()

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
            headers=headers,
            params=params,
            timeout=10,
        )
        r.raise_for_status()

        data = r.json()

        for v in data["data"]:
            created = datetime.fromisoformat(v["created_at"].replace("Z", "+00:00"))
            if created >= start:
                vids.append(v)

        cursor = data.get("pagination", {}).get("cursor")
        if not cursor:
            break

    return vids


# =========================================================
# ファイル名サニタイズ
# =========================================================
def sanitize_for_processing(title: str) -> str:
    safe = re.sub(r'[\\/:*?"<>|]', "_", title)
    safe = re.sub(r"\s+", " ", safe).strip()
    return safe if safe else "video"


# =========================================================
# yt-dlp設定
# =========================================================
def make_ydl_opts(download_dir: str, video_id: str) -> dict:
    os.makedirs(download_dir, exist_ok=True)

    return {
        "outtmpl": os.path.join(download_dir, f"{video_id}_temp.%(ext)s"),
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "download_archive": os.path.join(download_dir, "archive_ids.txt"),
        "retries": 20,
        "fragment_retries": 50,
        "ignoreerrors": True,
        "noprogress": True,
    }


# =========================================================
# 1本DL
# =========================================================
def download_one(vod: dict, download_dir: str) -> None:
    video_id = vod["id"]
    title = vod["title"]

    print(f"[INFO] Downloading: {title}")

    with yt_dlp.YoutubeDL(make_ydl_opts(download_dir, video_id)) as ydl:
        ydl.download([f"https://www.twitch.tv/videos/{video_id}"])

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
            print(f"[ERROR] {v['id']} : {e}")


if __name__ == "__main__":
    main()
