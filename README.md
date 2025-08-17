<h1 style="display: flex; align-items: center; justify-content: center;">
  Welcome to Vod Recovery
</h1>

<h3>A Twitch recovery tool used to retrieve and download VODs, highlights, and clips</h3>

## Installation

1. Install [Python](https://www.python.org/downloads/), make sure the box labeled "Add Python to environment variables" is checked
2. Download the app by clicking [here](https://github.com/MacielG1/VodRecovery/archive/refs/heads/main.zip)
3. Extract the zip file and run the file: `install_dependencies.py`
4. Start the program by running `vod_recovery.py` or one of the shortcuts

## Core Features

- Video & Clip Recovery: Find VODs and clips using the listed websites or by manually inputting the values, including sub-only vods.
- Video Format: Recovered VODs and highlights can be downloaded in various formats such as MP4, MKV, AVI, MOV and TS.
- Download Highlights: Retrieve highlights and VODs using a direct Twitch URL.
- Download Live Streams: Download a live stream from a Twitch URL.
- Multiple Formats: Recovered M3U8 links are available in these formats: Chunked (Source Quality), 1440p60, 1440p30, 1080p60, 1080p30, etc.
- Platform Compatibility: Compatible with popular platforms such as [TwitchTracker](https://twitchtracker.com/), [Sullygnome](https://sullygnome.com/), and [Streamscharts](https://streamscharts.com/) and also direct Twitch links.
- Bulk Video & Clip Recovery: Recovers multiple VODs and Clips using CSV files from [Sullygnome](https://sullygnome.com/).
- Multiple Downloaders: Download VODs using [yt-dlp](https://github.com/yt-dlp/yt-dlp) or [ffmpeg](https://ffmpeg.org/)
- Unmute VODs: Unmute M3U8 files so that they can be played in media players.

## Latest Release

https://github.com/MacielG1/VodRecovery/releases/latest

## Usage

This is the interactive menu:

```
1) VOD Recovery
2) Clip Recovery
3) Download VOD (default mp4)
4) Download Live Stream
5) Search Recent Streams
6) Extra M3U8 Options
7) Options
8) Exit
```

## Notes

- Original Repo: [VodRecovery](https://github.com/ArdianaLeek/VodRecovery) by Shishkebaboo
- How Twitch Handles [VOD Storage](https://help.twitch.tv/s/article/video-on-demand)
