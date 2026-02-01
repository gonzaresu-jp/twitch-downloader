# Twitch VOD Auto Downloader

Twitch の過去配信（VOD）を自動取得してローカル保存する Python バッチスクリプト。

- Twitch API で VOD 一覧取得
- yt-dlp で動画ダウンロード
- ffmpeg で映像＋音声を自動結合（mux）
- OAuth トークンは **毎回自動取得（期限管理不要）**
- cron / タスクスケジューラによる定期実行前提

---

# 必要な環境

## 必須

- Python 3.10+
- yt-dlp
- ffmpeg

---

## インストール例（Ubuntu/Debian）

```bash
sudo apt install ffmpeg
pip install yt-dlp requests
