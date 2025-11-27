<h1 align="center">Vod Recovery</h1>

**A Twitch recovery tool used to retrieve and download live streams, VODs, highlights, and clips**

## 📦 Installation

1. Install [Python](https://www.python.org/downloads/), make sure the box labeled "Add Python to environment variables" is checked
2. Download the app by clicking [here](https://github.com/MacielG1/VodRecovery/archive/refs/heads/main.zip) or download it from the [releases](https://github.com/MacielG1/VodRecovery/releases/latest) page
3. Extract the zip file and run the file: `install_dependencies.py`
4. Start by running `vod_recovery.py` or one of the shortcuts

## 📋 Core Features

- Recover VODs, clips, and highlights (including sub-only)
- Available qualities: 2160p, 1440p, 1080p, 720p, and more
- Record live streams or auto-record when it goes live
- Works with [TwitchTracker](https://twitchtracker.com/), [Sullygnome](https://sullygnome.com/), [Streamscharts](https://streamscharts.com/), and Twitch links
- Downloads using [ffmpeg](https://ffmpeg.org/) or [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- Bulk recover VODs and clips from [Sullygnome](https://sullygnome.com/) CSVs
- Unmute M3U8 files for playback in media players
- Optional CLI mode usage

## 🔖Latest Release

https://github.com/MacielG1/VodRecovery/releases/latest

## 🚀Usage

```
1) VOD Recovery
2) Clip Recovery
3) Download VOD (default mp4)
4) Record Live Stream
5) Search Recent Streams
6) Extra M3U8 Options
7) Options
8) Exit
```

## 🖥️ CLI Mode

```bash
python vod_recovery.py --url https://twitchtracker.com/streamer/streams/1234567890
python vod_recovery.py --url https://www.twitch.tv/videos/1234567890 --start 01:30:00 --end 01:45:00
python vod_recovery.py --url https://www.twitch.tv/streamer --watch
python vod_recovery.py --url https://www.twitch.tv/streamer
python vod_recovery.py --url https://www.twitch.tv/streamer --from-start
python vod_recovery.py --clip https://twitch.tv/streamer/clip/1234567890
python vod_recovery.py --m3u8 "https://example.com/index-dvr.m3u8"
python vod_recovery.py --m3u8 "https://example.com/index-dvr.m3u8" --start 00:10:00 --end 00:20:00
python vod_recovery.py --m3u8 "https://example.com/index-dvr.m3u8" --watch
```

- **URL downloads** `--url <link>` supports Twitch, TwitchTracker, Streamscharts, and SullyGnome pages.
- **Trimmed segments** Combine `--start` and `--end` (HH:MM:SS) to export only a slice of the VOD.
- **Record from live** Add `--from-start` to begin capturing a live channel from the start.
- **Watch live stream** Add `--watch` to watch the live stream in VLC.
- **Clips** Use `--clip <url>` for direct clip retrieval.
- **Direct M3U8** Use `--m3u8 <m3u8_url>` to download, trim, or watch directly from an M3U8 URL.

## 📜Notes

- How Twitch Handles [VOD Storage](https://help.twitch.tv/s/article/video-on-demand#limit)
- Original Repo: [VodRecovery](https://github.com/ArdianaLeek/VodRecovery) by Shishkebaboo
