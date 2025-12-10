import argparse
import hashlib
import json
import csv
import os
import random
import re
import subprocess
import tkinter as tk
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime, timedelta, timezone
from tkinter import filedialog
import shutil
from urllib.parse import urlparse
from pathlib import Path
from unicodedata import normalize
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from seleniumbase import SB
import requests
from packaging import version
import ffmpeg_downloader as ffdl
from tqdm import tqdm
from ffmpeg_progress_yield import FfmpegProgress
import logging
import importlib.metadata
import tempfile
import zipfile


logging.getLogger('asyncio').setLevel(logging.CRITICAL)
logging.getLogger('aiohttp').setLevel(logging.CRITICAL)


CURRENT_VERSION = "1.5.10"
SUPPORTED_FORMATS = [".mp4", ".mkv", ".mov", ".avi", ".ts"]
RESOLUTIONS = ["chunked", "2160p60", "2160p30", "2160p20", "1440p60", "1440p30", "1440p20", "1080p60", "1080p30", "1080p20", "720p60", "720p30", "720p20", "480p60", "480p30", "360p60", "360p30", "160p60", "160p30"]

CLI_MODE = False
CLI_DOWNLOAD_FROM_START = False


if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception as e:
            print(f"Error setting event loop policy: {e}")


class ReturnToMain(Exception):
    pass
                
def return_to_main_menu():
    raise ReturnToMain()


def read_config_by_key(config_file, key):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(script_dir, "config", f"{config_file}.json")
    if not os.path.exists(config_path):
        try:
            temp_dirs = set()
            try:
                temp_dirs.add(tempfile.gettempdir().lower())
            except Exception:
                pass
            if os.name == "nt":
                for env in ("TEMP", "TMP", "LOCALAPPDATA"):
                    v = os.environ.get(env)
                    if v:
                        temp_dirs.add(v.lower())
            in_temp = any(str(script_dir).lower().startswith(td) for td in temp_dirs if td)
            looks_like_zip = ".zip" in str(script_dir).lower() or "\\zip\\" in str(script_dir).lower()

            print("\n✖  Required file not found:")
            print(f"   {config_path}")
            if in_temp or looks_like_zip:
                print("\nIt looks like you launched VodRecovery directly from a ZIP or a temporary folder.")
                print("Please extract the entire VodRecovery folder first, then run vod_recovery.py (or the shortcut)")
            else:
                print("\nThe configuration folder is missing. Make sure you extracted the full release with the 'config' folder next to vod_recovery.py.")
            try:
                input("\nPress Enter to exit...")
            except Exception:
                pass
            sys.exit(1)
        except SystemExit:
            raise
        except Exception:
            return None

    with open(config_path, "r", encoding="utf-8") as input_config_file:
        config = json.load(input_config_file)

    return config.get(key, None)


def get_default_video_format():
    default_video_format = read_config_by_key("settings", "DEFAULT_VIDEO_FORMAT")
    if default_video_format in SUPPORTED_FORMATS:
        return default_video_format
    return ".mp4"


def get_ffmpeg_format(file_extension):
    format_map = {
        '.mp4': 'mp4',
        '.mkv': 'matroska',
        '.ts': 'mpegts',
        '.mov': 'mov',
        '.avi': 'avi'
    }
    return format_map.get(file_extension, 'mp4')


def get_default_directory():
    default_directory = read_config_by_key("settings", "DEFAULT_DIRECTORY")

    if not default_directory:
        default_directory = "~/Downloads/"

    default_directory = os.path.expanduser(default_directory)

    if not os.path.exists(default_directory):
        try:
            os.makedirs(default_directory)
        except Exception:
            default_directory = os.path.expanduser("~/Downloads/")
            if not os.path.exists(default_directory):
                os.makedirs(default_directory)

    if os.name == "nt":
        default_directory = default_directory.replace("/", "\\")

    return default_directory


def get_default_downloader():
    try:
        default_downloader = read_config_by_key("settings", "DEFAULT_DOWNLOADER")
        if default_downloader in ["ffmpeg", "yt-dlp"]:
            return default_downloader
        return "ffmpeg"
    except Exception:
        return "ffmpeg"
    

def get_yt_dlp_custom_options():
    try:
        custom_options = read_config_by_key("settings", "YT_DLP_OPTIONS") 
        if custom_options:
            return custom_options.split()
        return []
    except Exception:
        return []


def print_main_menu():
    default_video_format = get_default_video_format() or "mp4"
    menu_options = [
        "1) VOD Recovery",
        "2) Clip Recovery",
        f"3) Download VOD ({default_video_format.lstrip('.')})",
        "4) Record Live Stream",
        "5) Search Recent Streams",
        "6) Extra M3U8 Options",
        "7) Options",
        "8) Exit",
    ]
    while True:
        print("\n".join(menu_options))
        try:
            choice = int(input("\nChoose an option: "))
            if choice not in range(1, len(menu_options) + 1):
                raise ValueError("Invalid option")
            return choice
        except ValueError:
            print("\n✖  Invalid option! Please try again:\n")


def print_video_mode_menu():
    vod_type_options = [
        "1) Website Video Recovery",
        "2) Manual Recovery",
        "3) Bulk Recovery from SullyGnome CSV Export",
        "4) Return",
    ]
    while True:
        print("\n".join(vod_type_options))
        try:
            choice = int(input("\nSelect VOD Recovery Type: "))
            if choice not in range(1, len(vod_type_options) + 1):
                raise ValueError("Invalid option")
            return choice
        except ValueError:
            print("\n✖  Invalid option! Please try again:\n")


def print_clip_type_menu():
    clip_type_options = [
        "1) Recover All Clips from a VOD",
        "2) Find Random Clips from a VOD",
        "3) Download Clip from Twitch URL",
        "4) Bulk Recover Clips from SullyGnome CSV Export",
        "5) Return",
    ]
    while True:
        print("\n".join(clip_type_options))
        try:
            choice = int(input("\nSelect Clip Recovery Type: "))
            if choice not in range(1, len(clip_type_options) + 1):
                raise ValueError("Invalid option")
            return choice
        except ValueError:
            print("\n✖  Invalid option! Please try again:\n")


def print_clip_recovery_menu():
    clip_recovery_options = [
        "1) Website Clip Recovery",
        "2) Manual Clip Recovery",
        "3) Return",
    ]
    while True:
        print("\n".join(clip_recovery_options))
        try:
            choice = int(input("\nSelect Clip Recovery Method: "))
            if choice not in range(1, len(clip_recovery_options) + 1):
                raise ValueError("Invalid option")
            return choice
        except ValueError:
            print("\n✖  Invalid option! Please try again:\n")


def print_bulk_clip_recovery_menu():
    bulk_clip_recovery_options = [
        "1) Single CSV File",
        "2) Multiple CSV Files",
        "3) Return",
    ]
    while True:
        print("\n".join(bulk_clip_recovery_options))
        try:
            choice = int(input("\nSelect Bulk Clip Recovery Source: "))
            if choice not in range(1, len(bulk_clip_recovery_options) + 1):
                raise ValueError("Invalid option")
            return str(choice)
        except ValueError:
            print("\n✖  Invalid option! Please try again:\n")


def print_clip_format_menu():
    clip_format_options = [
        "1) Default Format ([VodID]-offset-[interval])",
        "2) Alternate Format (vod-[VodID]-offset-[interval])",
        "3) Legacy Format ([VodID]-index-[interval])",
        "4) Return",
    ]
    print()
    while True:
        print("\n".join(clip_format_options))
        try:
            choice = int(input("\nSelect Clip URL Format: "))
            if choice == 4:
                return_to_main_menu()
            if choice not in range(1, len(clip_format_options) + 1):
                raise ValueError("Invalid option")
            else:
                return str(choice)
        except ValueError:
            print("\n✖  Invalid option! Please try again:\n")


def print_download_type_menu():
    download_type_options = [
        "1) From M3U8 Link",
        "2) From M3U8 File",
        "3) From Twitch URL",
        "4) Return",
    ]
    while True:
        print("\n".join(download_type_options))
        try:
            choice = int(input("\nSelect Download Type: "))
            if choice not in range(1, len(download_type_options) + 1):
                raise ValueError("Invalid option")
            return choice
        except ValueError:
            print("\n✖  Invalid option! Please try again:\n")


def print_handle_m3u8_availability_menu():
    handle_m3u8_availability_options = [
        "1) Check if M3U8 file has muted segments",
        "2) Unmute & Remove invalid segments",
        "3) Write M3U8 to file",
        "4) Return",
    ]
    while True:
        print("\n".join(handle_m3u8_availability_options))
        try:
            choice = int(input("\nSelect Option: "))
            if choice not in range(1, len(handle_m3u8_availability_options) + 1):
                raise ValueError("Invalid option")
            return choice
        except ValueError:
            print("\n✖  Invalid option! Please try again:\n")


def print_options_menu():
    options_menu = [
        f"1) Set Default Video Format \033[94m({get_default_video_format().lstrip('.') or 'mp4'})\033[0m",
        f"2) Set Download Directory \033[94m({get_default_directory() or '~/Downloads/'})\033[0m",
        f"3) Set Default Downloader \033[94m({read_config_by_key('settings', 'DEFAULT_DOWNLOADER') or 'ffmpeg'})\033[0m",
        "4) Check for Updates",
        "5) Update yt-dlp",
        "6) Open settings.json File",
        "7) Help",
        "8) Return",
    ]
    while True:
        print("\n".join(options_menu))
        try:
            choice = int(input("\nSelect Option: "))
            if choice not in range(1, len(options_menu) + 1):
                raise ValueError("Invalid option")
            return choice
        except ValueError:
            print("\n✖  Invalid option! Please try again:\n")


def print_get_m3u8_link_menu():
    while True:
        m3u8_url = input("Enter M3U8 Link: ").strip(" \"'")
        if m3u8_url.endswith(".m3u8"):
            return m3u8_url
        else:
            print("✖  Invalid M3U8 link! Please try again:\n")


def quote_filename(filename):
    if not filename.startswith("'") and not filename.endswith("'"):
        filename = filename.replace("'", "'\"'\"'")
        filename = f"'{filename}'"
    return filename


def get_yes_no_choice(prompt):
    while True:
        choice = input(f"\n{prompt} (Y/N): ").strip().lower()
        if choice in ['y', 'yes']:
            return True
        elif choice in ['n', 'no']:
            return False
        print("Invalid input! Please enter 'Y' for Yes or 'N' for No.")


def get_websites_tracker_url():
    while True:
        tracker_url = input("Enter Twitchtracker/Streamscharts/Sullygnome url: ").strip()
        if re.match(r"^(https?:\/\/)?(www\.)?(twitchtracker\.com|streamscharts\.com|sullygnome\.com)\/.*", tracker_url):
            return tracker_url

        print("\n✖  Invalid URL! Please enter a URL from Twitchtracker, Streamscharts, or Sullygnome.\n")


def format_iso_datetime(iso_datetime: str):   
    if not iso_datetime:
        return None
    iso_datetime = iso_datetime.strip()
    try:
        if iso_datetime.endswith('Z'):
            dt = datetime.fromisoformat(iso_datetime.replace("Z", "+00:00"))
        elif '+' in iso_datetime or iso_datetime.endswith(('UTC', 'GMT')):
            cleaned = iso_datetime.replace('UTC', '').replace('GMT', '').strip()
            if not cleaned.endswith(('+', '-')):
                cleaned += '+00:00' if 'UTC' in iso_datetime or 'GMT' in iso_datetime else ''
            dt = datetime.fromisoformat(cleaned)
        else:
            # Assume UTC if no timezone info
            dt = datetime.fromisoformat(iso_datetime + '+00:00')
            
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        print(f"Error parsing datetime '{iso_datetime}'")
        return None


def print_get_twitch_url_menu():
    while True:
        twitch_url = input("Enter Twitch URL: ").strip(" \"'")
        if "twitch.tv" in twitch_url:
            return twitch_url
        else:
            print("✖  Invalid Twitch URL! Please try again:\n")


def extract_slug_and_streamer_from_clip_url(url):
    pattern = r"twitch\.tv/([^/]+)/clip/([^/?]+)"
    match = re.search(pattern, url)
    if not match:
        raise ValueError("Invalid Twitch Clip URL")
    return match.group(1), match.group(2)


def print_get_twitch_clip_url_menu():
    while True:
        twitch_clip_url = input("Enter Twitch Clip URL: ").strip(" \"'")
        try:
            extract_slug_and_streamer_from_clip_url(twitch_clip_url)
            return twitch_clip_url
        except ValueError:
            print("✖  Invalid Twitch Clip URL! Please try again:\n")


def print_get_twitch_url_or_name_menu():
    user_input = input("Enter Stream URL or streamer name: ").strip(" \"'")
    
    if "twitch.tv" in user_input:
        return user_input
    
    if user_input and not user_input.startswith("http"):
        streamer_name = user_input.lstrip("@")
        return f"https://www.twitch.tv/{streamer_name}"
    
    if user_input.startswith("http"):
        return user_input
    
    print("\n✖  Invalid input! Please try again:\n")
    return print_get_twitch_url_or_name_menu()


def get_twitch_or_tracker_url():
    while True:
        url = input("Enter Twitchtracker/Streamscharts/Sullygnome/Twitch URL: ").strip()

        if re.match(r"^(https?:\/\/)?(www\.)?(twitchtracker\.com|streamscharts\.com|sullygnome\.com|twitch\.tv)\/.*", url):
            return url

        print("\n✖  Invalid URL! Please enter a URL from Twitchtracker, Streamscharts, Sullygnome, or Twitch.\n")


def get_latest_version(retries=3):
    for attempt in range(retries):
        try:
            res = requests.get("https://api.github.com/repos/MacielG1/VodRecovery/releases/latest", timeout=30)
            if res.status_code == 200:
                release_info = res.json()
                return release_info["tag_name"]
            else:
                return None
        except Exception:
            if attempt < retries - 1: 
                time.sleep(3)  
                continue 
            else:
                return None


def get_latest_release_info(retries=3):
    for attempt in range(retries):
        try:
            response = requests.get("https://api.github.com/repos/MacielG1/VodRecovery/releases/latest", timeout=30)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            if attempt < retries - 1:
                time.sleep(3)
                continue
            return None


def get_latest_release_zip_url():
    release_info = get_latest_release_info()
    if not release_info:
        return None
    try:
        assets = release_info.get("assets") or []
        for asset in assets:
            name = (asset.get("name") or "").lower()
            url = asset.get("browser_download_url")
            if name.endswith(".zip") and url:
                return url
        if release_info.get("zipball_url"):
            return release_info["zipball_url"]
    except Exception:
        pass
    return "https://github.com/MacielG1/VodRecovery/archive/refs/heads/main.zip"


def enumerate_zip_top_folder(zip_path):
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            names = zip_ref.namelist()
            if not names:
                return None
            root = names[0].split('/')[0]
            return root
    except Exception:
        return None


def copy_tree_overwrite(source_dir, destination_dir, preserve_relative_paths=None, ignore_dirs=None, ignore_files=None):
    preserve_relative_paths = preserve_relative_paths or set()
    ignore_dirs = ignore_dirs or {"__pycache__", ".git", ".github"}
    ignore_files = ignore_files or set()

    for root_dir, dir_names, file_names in os.walk(source_dir):
        dir_names[:] = [d for d in dir_names if d not in ignore_dirs]

        relative_root = os.path.relpath(root_dir, source_dir)
        destination_root = destination_dir if relative_root == "." else os.path.join(destination_dir, relative_root)
        os.makedirs(destination_root, exist_ok=True)

        for file_name in file_names:
            relative_path = file_name if relative_root == "." else os.path.join(relative_root, file_name)

            if file_name in ignore_files:
                continue
            if relative_path.replace("\\", "/") in preserve_relative_paths:
                continue

            source_file_path = os.path.join(root_dir, file_name)
            destination_file_path = os.path.join(destination_root, file_name)
            try:
                os.makedirs(os.path.dirname(destination_file_path), exist_ok=True)
                shutil.copy2(source_file_path, destination_file_path)
            except Exception:
                pass


def merge_settings_defaults(new_settings_path, user_settings_path):
    try:
        if not os.path.exists(user_settings_path):
            os.makedirs(os.path.dirname(user_settings_path), exist_ok=True)
            shutil.copy2(new_settings_path, user_settings_path)
            return True

        with open(user_settings_path, "r", encoding="utf-8") as f_user:
            user_config = json.load(f_user)
        with open(new_settings_path, "r", encoding="utf-8") as f_new:
            new_defaults = json.load(f_new)

        updated = False
        for key, default_value in new_defaults.items():
            if key not in user_config:
                user_config[key] = default_value
                updated = True

        if updated:
            with open(user_settings_path, "w", encoding="utf-8") as f_out:
                json.dump(user_config, f_out, indent=4)
        return True
    except Exception:
        return False


def perform_self_update(latest_version_str=None):
    temp_directory = None
    try:
        print("\nPreparing to update...")
        zip_url = get_latest_release_zip_url()
        if not zip_url:
            print("\n✖  Could not resolve latest release URL!")
            return False

        temp_directory = tempfile.mkdtemp(prefix="vodrecovery_update_")
        zip_destination_path = os.path.join(temp_directory, "update.zip")

        with requests.get(zip_url, stream=True, timeout=60) as response:
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            chunk_size = 1024 * 1024
            downloaded = 0
            with open(zip_destination_path, 'wb') as file_out:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        file_out.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            percent = (downloaded / total_size) * 100
                            print(f"\rDownloading update... {percent:.1f}%", end="", flush=True)
        print("\nDownload complete. Extracting...")

        with zipfile.ZipFile(zip_destination_path, 'r') as zip_ref:
            zip_ref.extractall(temp_directory)

        # Identify root folder inside extracted content
        root_folder_name = enumerate_zip_top_folder(zip_destination_path)
        if root_folder_name is None:
            candidates = [name for name in os.listdir(temp_directory) if os.path.isdir(os.path.join(temp_directory, name))]
            if not candidates:
                print("\n✖  Could not find extracted content!")
                return False
            root_folder_name = candidates[0]
        extracted_root_path = os.path.join(temp_directory, root_folder_name)

        # Copy files over, preserving user settings
        current_directory = os.path.dirname(os.path.realpath(__file__))
        preserve_paths = {"config/settings.json"}
        copy_tree_overwrite(
            source_dir=extracted_root_path,
            destination_dir=current_directory,
            preserve_relative_paths=preserve_paths,
        )

        # Merge any new default settings keys into user's settings
        new_settings_path = os.path.join(extracted_root_path, "config", "settings.json")
        user_settings_path = os.path.join(current_directory, "config", "settings.json")
        if os.path.exists(new_settings_path):
            merge_settings_defaults(new_settings_path, user_settings_path)

        try:
            global CURRENT_VERSION
            if latest_version_str:
                CURRENT_VERSION = latest_version_str.lstrip('vV')
        except Exception:
            pass

        print("\n\033[92m✓ Update complete.\033[0m")
        if latest_version_str:
            print(f"Updated to version {latest_version_str}.")
        return True
    except Exception as e:
        print(f"\n✖  Update failed: {e}")
        return False
    finally:
        try:
            if temp_directory and os.path.isdir(temp_directory):
                shutil.rmtree(temp_directory, ignore_errors=True)
        except Exception:
            pass


def fetch_vod_vod_streams(streamer_name):
    try:
        response = requests.get(f"https://api.vodvod.top/channels/@{streamer_name}", headers=return_user_agent(), timeout=15)
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        
        if not data or not isinstance(data, list):
            return None
            
        streams = []
        for item in data:
            try:
                metadata = item.get('Metadata', {})
                start_time = metadata.get('StartTime', '')
                
                if start_time:
                    dt_utc = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    dt_local = dt_utc.astimezone()
                    
                    dt_utc_str = dt_utc.strftime("%Y-%m-%d %H:%M:%S")
                    dt_local_str = dt_local.strftime("%Y-%m-%d %H:%M:%S")
                    
                    duration_hours = None
                    hls_duration = metadata.get('HlsDurationSeconds', {})
                    if isinstance(hls_duration, dict) and hls_duration.get('Valid'):
                        duration_seconds = hls_duration.get('Float64', 0)
                        if duration_seconds > 0:
                            duration_hours = round(duration_seconds / 3600, 1)
                    
                    stream = {
                        'dt_utc': dt_utc_str,
                        'dt_local': dt_local_str,
                        'title': metadata.get('TitleAtStart', ''),
                        'duration': duration_hours,
                        'stream_id': metadata.get('StreamID', ''),
                    }
                    streams.append(stream)
                    
            except Exception as e:
                continue
                
        return streams if streams else None
        
    except Exception:
        return None


def get_datetime_from_vod_vod(url):
    try:
        if "streamscharts.com" in url:
            streamer_name, stream_id = parse_streamscharts_url(url)
        elif "twitchtracker.com" in url:
            streamer_name, stream_id = parse_twitchtracker_url(url)
        elif "sullygnome.com" in url:
            streamer_name, stream_id = parse_sullygnome_url(url)
        else:
            return None
        
        response = requests.get(f"https://api.vodvod.top/channels/@{streamer_name}", headers=return_user_agent(), timeout=15)
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        
        if not data or not isinstance(data, list):
            return None
            
        for item in data:
            try:
                metadata = item.get('Metadata', {})
                found_stream_id = metadata.get('StreamID', '')
                
                if str(found_stream_id) == str(stream_id):
                    start_time = metadata.get('StartTime', '')
                    
                    if start_time:
                        dt_utc = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        return dt_utc.strftime("%Y-%m-%d %H:%M:%S"), None
                    
            except Exception:
                continue
                
        return None, None
        
    except Exception:
        return None, None


def merge_api_and_vod_streams(api_streams, vod_streams):
    api_streams = api_streams or []
    vod_streams = vod_streams or []

    if not api_streams and not vod_streams:
        return None

    merged = {}
    order = []
    fallback_counter = 0

    def make_key(stream):
        nonlocal fallback_counter
        stream_id = stream.get('stream_id') if isinstance(stream, dict) else None
        if stream_id:
            return f"id:{stream_id}"
        dt_utc = stream.get('dt_utc') if isinstance(stream, dict) else None
        if dt_utc:
            return f"utc:{dt_utc}"
        fallback_counter += 1
        return f"idx:{fallback_counter}"

    for stream in api_streams:
        key = make_key(stream)
        if key not in merged:
            merged[key] = stream
            order.append(key)

    for stream in vod_streams:
        key = make_key(stream)
        if key in merged:
            combined = merged[key].copy()
            combined.update(stream)
            merged[key] = combined
        else:
            merged[key] = stream
            order.append(key)

    result = [merged[key] for key in order]
    try:
        result.sort(key=lambda s: s.get('dt_utc') or '', reverse=True)
    except Exception:
        pass

    return result if result else None

def fetch_recent_streams_api(streamer_name, max_streams=100):
    try:        
        query = """
        query($login: String!, $first: Int!) {
            user(login: $login) {
                videos(first: $first) {
                    edges {
                        node {
                            id
                            title
                            createdAt
                            publishedAt
                            lengthSeconds
                            previewThumbnailURL
                            animatedPreviewURL
                        }
                    }
                }
            }
        }
        """
        
        variables = {"login": streamer_name, "first": max_streams}
        payload = {"query": query, "variables": variables}
        
        res = requests.post(
            "https://gql.twitch.tv/gql",
            json=payload,
            headers={
                "Client-ID": "ue6666qo983tsx6so1t0vnawi233wa",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0",
            },
            timeout=30,
        )
        
        
        if res.status_code != 200:
            return None
            
        data = res.json()
            
        if not data or "data" not in data or not data["data"]:
            return None
            
        user_data = data["data"].get("user")
        
        if not user_data:
            return None
            
        videos = user_data.get("videos", {}).get("edges", [])
        streams = []
        
        for i, edge in enumerate(videos):
            node = edge.get("node", {})
            if not node:
                continue
                
            try:
                created_at_iso = node.get("createdAt") or node.get("publishedAt")
                if not created_at_iso:
                    continue
                    
                dt_utc = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
                dt_utc_str = dt_utc.strftime("%Y-%m-%d %H:%M:%S")

                # Convert to local time only for display purposes
                dt_local = dt_utc.astimezone()
                dt_local_str = dt_local.strftime("%Y-%m-%d %H:%M:%S")

                length_seconds = node.get("lengthSeconds", 0)
                duration_hours = length_seconds / 3600.0

                current_date = datetime.now(dt_utc.tzinfo)
                old_date = current_date - timedelta(days=60)
                if dt_utc < old_date:
                    continue

                preview_url = node.get("previewThumbnailURL", "")
                animated_url = node.get("animatedPreviewURL", "")
                extracted_vod_id = None
                extracted_timestamp = None
                
                if preview_url:
                    try:
                        url_parts = preview_url.split('/')
                        for part in url_parts:
                            if f'_{streamer_name}_' in part:
                                segments = part.split('_')
                                if len(segments) >= 4:
                                    extracted_vod_id = segments[2]
                                    extracted_timestamp = segments[3]
                                    break
                    except Exception as e:
                        pass
                
                if not extracted_vod_id and animated_url:
                    try:
                        url_parts = animated_url.split('/')
                        for part in url_parts:
                            if f'_{streamer_name}_' in part:
                                segments = part.split('_')
                                if len(segments) >= 4:
                                    extracted_vod_id = segments[2]
                                    extracted_timestamp = segments[3]
                                    break
                    except Exception as e:
                        pass
                
                final_timestamp = dt_utc_str
                final_local_timestamp = dt_local_str
                if extracted_timestamp:
                    try:
                        dt_from_url = datetime.fromtimestamp(int(extracted_timestamp), timezone.utc)
                        final_timestamp = dt_from_url.strftime("%Y-%m-%d %H:%M:%S")
                        dt_local_from_url = dt_from_url.astimezone()
                        final_local_timestamp = dt_local_from_url.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception as e:
                        pass

                stream = {
                    'dt_utc': final_timestamp,
                    'dt_local': final_local_timestamp,
                    'title': node.get("title", ""),
                    'duration': duration_hours,
                    'stream_id': extracted_vod_id or node.get("id", ""),
                }
                streams.append(stream)
                
            except Exception as e:
                pass
                continue
        
        return streams
        
    except Exception as e:
        return None


def get_latest_streams(streamer_name=None, skip_gql=False):
    if not streamer_name:   
        streamer_name = input("\nEnter streamer name: ").strip().lower()
    url = f"https://twitchtracker.com/{streamer_name}/streams"
    
    current_page = 1
    
    print("\nSearching for streams...")
    streams = None
    if not skip_gql:
        def fetch_with_retry(func, *args):
            for _ in range(3):
                try:
                    res = func(*args)
                    if res:
                        return res
                except Exception:
                    pass
                time.sleep(1)
            return None

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_api = executor.submit(fetch_with_retry, fetch_recent_streams_api, streamer_name)
            future_vod = executor.submit(fetch_with_retry, fetch_vod_vod_streams, streamer_name)
            
            api_streams = future_api.result()
            vod_streams = future_vod.result()

        streams = merge_api_and_vod_streams(api_streams, vod_streams)

    if streams:
        print(f"✓ Found {len(streams)} streams")
    else:
        
        max_retries = 5
        for attempt in range(max_retries):
            try:
                print("\nOpening TwitchTracker with browser...")
                streams = selenium_get_latest_streams_from_twitchtracker(streamer_name)

                if not streams:
                    if attempt < max_retries - 1:
                        print("Retrying...")
                        continue
                    else:
                        print("Unable to get streams from TwitchTracker!")
                        return
                skip_gql = True
                break
            except Exception as e:
                print(f"\n✖  Error occurred: {str(e)}")
                if attempt < max_retries - 1:
                    print("Retrying...")
                    continue
                else:
                    print("Max retries reached!")
                    return

    if not streams:
        print("\n✖  No streams found!")
        return

    # Show 10 vods per page
    rows_per_page = 10
    total_rows = len(streams)
    total_pages = (total_rows + rows_per_page - 1) // rows_per_page
    
    def display_streams(page_num):
        start_idx = (page_num - 1) * 10
        end_idx = min(start_idx + 10, total_rows)
        rows_to_display = streams[start_idx:end_idx]
        
        has_duration = any(row.get('duration') is not None for row in rows_to_display)
        
        if has_duration:
            print("\n#   Date                Duration    Title")
            print("-" * 80)
        else:
            print("\n#   Date                Title")
            print("-" * 60)
        
        stream_info = []
        valid_streams = []
        for idx, row in enumerate(rows_to_display, start_idx + 1):
            try:
                date_utc = row['dt_utc']
                idx_str = str(idx).ljust(3)
                date_str = row['dt_local'].ljust(20)
                title = row['title']
                if len(title) > 75:
                    title = title[:72] + "..."
                video_id = row['stream_id']
                
                if not video_id or video_id == 'None' or str(video_id).strip() == '':
                    continue
                
                stream_info.append((video_id, date_str, date_utc, title))
                valid_streams.append(idx)
                
                if has_duration:
                    duration_str = (str(round(row['duration'], 1)) + " hrs" if row['duration'] is not None else "").ljust(10)
                    print(f"{idx_str} {date_str} {duration_str} {title}")
                else:
                    print(f"{idx_str} {date_str} {title}")
                    
            except Exception as e:
                print(f"\n✖  Error processing stream {idx}: {str(e)}")
                continue
        return stream_info, valid_streams
    
    stream_info, valid_streams = display_streams(current_page)
    
    if not stream_info:
        print("\n✖  No valid streams found!")
        return
    while True:
        print("\nOptions:")
        print("1. Recover specific stream")
        print("2. Recover all streams")
        if current_page < total_pages:
            print("3. Show next page")
            if not skip_gql:
                print("4. Use Browser Search")
                print("5. Return")
            else:
                print("4. Return")
        else:
            if not skip_gql:
                print("3. Use Browser Search")
                print("4. Return")
            else:
                print("3. Return")
        choice = input("\nSelect Option: ")
        if choice == "1":
            try:
                stream_num = int(input("\nEnter the number of the stream: "))
            except ValueError:
                print("Please enter a valid number.")
                continue

            streams_to_check = valid_streams
            if stream_num not in streams_to_check:
                print("Invalid stream number. Please try again.")
                continue

            try:
                list_index = valid_streams.index(stream_num)
                video_id, date_str, date_utc, title = stream_info[list_index]
            except Exception as e:
                print(f"✖ Failed to resolve selected stream: {e}")
                continue

            print(f"\nRecovering VOD: {date_str.strip()} - {title}")

            try:
                timestamp = datetime.strptime(date_utc, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
            except ValueError as ve:
                fallback = format_iso_datetime(date_utc) if date_utc else None
                if fallback:
                    timestamp = fallback
                else:
                    print(f"✖ Timestamp parse error for '{date_utc}': {ve}")
                    continue

            try:
                m3u8_source = vod_recover(streamer_name, video_id, timestamp, url)
            except Exception as e:
                print(f"✖ Recovery failed for VOD {video_id}: {e}")
                continue

            if m3u8_source:
                handle_download_menu(m3u8_source, title=title, stream_datetime=timestamp)
            else:
                print(f"\n✖  Could not recover VOD {video_id}!")
            break
        elif choice == "2":
            print("\nRecovering all streams...")
            for video_id, date_str, date_utc, title in stream_info:
                print(f"\nRecovering Video: {date_str} - {title}")  # Show local time
                try:
                    timestamp = datetime.strptime(date_utc, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                except ValueError as ve:
                    fallback = format_iso_datetime(date_utc) if date_utc else None
                    if fallback:
                        timestamp = fallback
                    else:
                        print(f"✖ Skipping {video_id}: timestamp parse error for '{date_utc}': {ve}")
                        continue
                try:
                    m3u8_source = vod_recover(streamer_name, video_id, timestamp, url)
                except Exception as e:
                    print(f"✖ Recovery failed for VOD {video_id}: {e}")
                    continue
                if m3u8_source:
                    print(f"\nRecovering VOD {video_id}...")
                    handle_vod_url_normal(m3u8_source, title=title, stream_date=timestamp)
                else:
                    print(f"\n✖  Could not recover VOD {video_id}!")
            break
        elif choice == "3":
            if current_page < total_pages:
                current_page += 1
                stream_info, valid_streams = display_streams(current_page)
            else:
                if not skip_gql:
                    get_latest_streams(streamer_name=streamer_name, skip_gql=True)
                    return
                else:
                    break
        elif choice == "4":
            if current_page < total_pages:
                if not skip_gql:
                    get_latest_streams(streamer_name=streamer_name, skip_gql=True)
                    return
                else:
                    break
            else:
                break
        elif choice == "5":
            break
        else:
            print("\nInvalid option. Please try again.")


def check_for_updates():
    latest_tag = get_latest_version()
    normalized_tag = latest_tag.lstrip('vV') if latest_tag else None
    try:
        latest_version = version.parse(normalized_tag) if normalized_tag else None
    except Exception:
        latest_version = None
    current_version = version.parse(CURRENT_VERSION)
    if latest_version and current_version:
        if latest_version > current_version:
            print(f"\n\033[94mNew version available: {normalized_tag} (current: {CURRENT_VERSION})\033[0m")
            if get_yes_no_choice("Do you want to download and install it now?"):
                ok = perform_self_update(latest_tag)
                if ok:
                    try:
                        script_dir = os.path.dirname(os.path.realpath(__file__))
                        deps_script = os.path.join(script_dir, "install_dependencies.py")
                        if os.path.isfile(deps_script):
                            print("\nUpdating dependencies...")
                            subprocess.check_call([sys.executable, deps_script])
                    except Exception as dep_err:
                        print(f"\nWarning: Could not update dependencies automatically: {dep_err}")
                    if get_yes_no_choice("Restart Vod Recovery now?"):
                        try:
                            script_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "vod_recovery.py")
                            os.execl(sys.executable, sys.executable, script_path)
                        except Exception:
                            try:
                                subprocess.Popen([sys.executable, script_path])
                            except Exception:
                                pass
                            sys.exit(0)
                input("\nPress Enter to continue...")
                return_to_main_menu()
            else:
                input("\nPress Enter to continue...")
                return
        else:
            print(f"\n\033[92m\u2713 Vod Recovery is up to date ({CURRENT_VERSION}).\033[0m")
            input("\nPress Enter to continue...")
            return
    else:
        print("\n✖  Could not check for updates!")


def sanitize_filename(filename, restricted=False):
    if filename == "":
        return ""

    def replace_insane(char):
        if not restricted and char == "\n":
            return "\0 "
        elif not restricted and char in '"*:<>?|/\\':
            return {"/": "\u29f8", "\\": "\u29f9"}.get(char, chr(ord(char) + 0xFEE0))
        elif char == "?" or ord(char) < 32 or ord(char) == 127:
            return ""
        elif char == '"':
            return "" if restricted else "'"
        elif char == ":":
            return "\0_\0-" if restricted else "\0 \0-"
        elif char in "\\/|*<>":
            return "\0_"
        if restricted and (
            char in "!&'()[]{}$;`^,#" or char.isspace() or ord(char) > 127
        ):
            return "\0_"
        return char

    if restricted:
        filename = normalize("NFKC", filename)
    filename = re.sub(
        r"[0-9]+(?::[0-9]+)+", lambda m: m.group(0).replace(":", "_"), filename
    )
    result = "".join(map(replace_insane, filename))
    result = re.sub(r"(\0.)(?:(?=\1)..)+", r"\1", result)
    strip_re = r"(?:\0.|[ _-])*"
    result = re.sub(f"^\0.{strip_re}|{strip_re}\0.$", "", result)
    result = result.replace("\0", "") or "_"

    while "__" in result:
        result = result.replace("__", "_")
    result = result.strip("_")
    if restricted and result.startswith("-_"):
        result = result[2:]
    if result.startswith("-"):
        result = "_" + result[len("-") :]
    result = result.lstrip(".")
    if not result:
        result = "_"
    return result


def read_config_file(config_file):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "config", f"{config_file}.json")
    with open(config_path, encoding="utf-8") as config_file:
        config = json.load(config_file)
    return config


def open_file(file_path):
    if sys.platform.startswith("darwin"):
        subprocess.call(("open", file_path))
    elif os.name == "nt":
        subprocess.Popen(["start", file_path], shell=True)
    elif os.name == "posix":
        subprocess.call(("xdg-open", file_path))
    else:
        print(f"\nFile Location: {file_path}")


def print_help():
    try:
        help_data = read_config_file("help")
        print("\n--------------- Help Section ---------------")
        for menu, options in help_data.items():
            print(f"\n{menu.replace('_', ' ').title()}:")
            for option, description in options.items():
                print(f"  {option}: {description}")
        print("\n --------------- End of Help Section ---------------\n")
    except Exception as error:
        print(f"An unexpected error occurred: {error}")


def read_text_file(text_file_path):
    lines = []
    with open(text_file_path, "r", encoding="utf-8") as text_file:
        for line in text_file:
            lines.append(line.rstrip())
    return lines


def write_text_file(input_text, destination_path):
    with open(destination_path, "a+", encoding="utf-8") as text_file:
        text_file.write(input_text + "\n")


def write_m3u8_to_file(m3u8_link, destination_path, max_retries=5):
    attempt = 0
    while attempt < max_retries:
        try:
            with open(destination_path, "w", encoding="utf-8") as m3u8_file:
                m3u8_file.write(requests.get(m3u8_link, timeout=30).text)
            return m3u8_file
        except Exception:
            attempt += 1
            time.sleep(1)
    raise Exception(f"Failed to write M3U8 after {max_retries} attempts.")


def ensure_absolute_uri(uri: str, base_link: str) -> str:
    uri = uri.strip()
    if uri.startswith("http://") or uri.startswith("https://"):
        return uri
    return f"{base_link}{uri}"


def read_csv_file(csv_file_path):
    with open(csv_file_path, "r", encoding="utf-8") as csv_file:
        return [row for row in csv.reader(csv_file)]


def get_use_progress_bar():
    try:
        use_progress_bar = read_config_by_key("settings", "USE_PROGRESS_BAR")
        return use_progress_bar if use_progress_bar is not None else True
    except Exception:
        return True
        

def get_current_version():
    current_version = read_config_by_key("settings", "CURRENT_VERSION")
    if current_version:
        return current_version
    else:
        sys.exit("\033[91m \n✖  Unable to retrieve CURRENT_VERSION from the settings.json files \n\033[0m")


def get_log_filepath(streamer_name, video_id):
    log_filename = os.path.join(get_default_directory(), f"{streamer_name}_{video_id}_log.txt")
    return log_filename


def get_vod_filepath(streamer_name, video_id):
    vod_filename = os.path.join(get_default_directory(), f"{streamer_name}_{video_id}.m3u8")
    return vod_filename


def get_script_directory():
    return os.path.dirname(os.path.realpath(__file__))


def return_user_agent():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    user_agents = read_text_file(os.path.join(script_dir, "lib", "user_agents.txt"))
    header = {"user-agent": random.choice(user_agents)}
    return header


def calculate_epoch_timestamp(timestamp, seconds):
    try:
        epoch_timestamp = ((datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S") + timedelta(seconds=seconds)) - datetime(1970, 1, 1)).total_seconds()
        return epoch_timestamp
    except ValueError:
        return None


def calculate_days_since_broadcast(start_timestamp):
    if start_timestamp is None:
        return 0
    vod_age = datetime.today() - datetime.strptime(start_timestamp, "%Y-%m-%d %H:%M:%S")
    return max(vod_age.days, 0)


def is_video_muted(m3u8_link):
    response = requests.get(m3u8_link, timeout=20).text
    return bool("unmuted" in response)


def is_twitch_livestream_url(url):
    streamer_pattern = r"^https?://(?:www\.)?twitch\.tv/[^/]+/?$"
    return re.match(streamer_pattern, url) is not None


def calculate_broadcast_duration_in_minutes(hours, minutes):
    return (int(hours) * 60) + int(minutes)


def calculate_max_clip_offset(video_duration):
    return (video_duration * 60) + 2000


def parse_streamer_from_csv_filename(csv_filename):
    _, file_name = os.path.split(csv_filename)
    streamer_name = file_name.strip()
    return streamer_name.split()[0]


def parse_streamer_from_m3u8_link(m3u8_link):
    indices = [i.start() for i in re.finditer("_", m3u8_link)]
    streamer_name = m3u8_link[indices[0] + 1 : indices[-2]]
    return streamer_name


def parse_video_id_from_m3u8_link(m3u8_link):
    indices = [i.start() for i in re.finditer("_", m3u8_link)]
    video_id = m3u8_link[
        indices[0] + len(parse_streamer_from_m3u8_link(m3u8_link)) + 2 : indices[-1]
    ]
    return video_id


def parse_streamer_and_video_id_from_m3u8_link(m3u8_link):
    indices = [i.start() for i in re.finditer("_", m3u8_link)]
    streamer_name = m3u8_link[indices[0] + 1 : indices[-2]]
    video_id = m3u8_link[indices[0] + len(streamer_name) + 2 : indices[-1]]
    return f" - {streamer_name} [{video_id}]"


def parse_streamscharts_url(streamscharts_url):
    try:
        streamer_name = streamscharts_url.split("/channels/", 1)[1].split("/streams/")[0]
        video_id = streamscharts_url.split("/streams/", 1)[1]
        return streamer_name, video_id
    except IndexError:
        print("\033[91m \n✖  Invalid Streamscharts URL! Please try again:\n \033[0m")
        input("Press Enter to continue...")
        return_to_main_menu()


def parse_twitchtracker_url(twitchtracker_url):
    try:
        streamer_name = twitchtracker_url.split(".com/", 1)[1].split("/streams/")[0]
        video_id = twitchtracker_url.split("/streams/", 1)[1]
        return streamer_name, video_id
    except IndexError:
        print("\033[91m \n✖  Invalid Twitchtracker URL! Please try again:\n \033[0m")
        input("Press Enter to continue...")
        return_to_main_menu()


def parse_sullygnome_url(sullygnome_url):
    try:
        streamer_name = sullygnome_url.split("/channel/", 1)[1].split("/")[0]
        video_id = sullygnome_url.split("/stream/", 1)[1]
        return streamer_name, video_id
    except IndexError:
        print("\033[91m \n✖  Invalid SullyGnome URL! Please try again:\n \033[0m")
        input("Press Enter to continue...")
        return_to_main_menu()


def set_default_video_format():
    print("\nSelect the default video format")

    for i, format_option in enumerate(SUPPORTED_FORMATS, start=1):
        print(f"{i}) {format_option.lstrip('.')}")

    user_option = str(input("\nChoose a video format: "))
    if user_option in [str(i) for i in range(1, len(SUPPORTED_FORMATS) + 1)]:
        selected_format = SUPPORTED_FORMATS[int(user_option) - 1]
        script_dir = get_script_directory()
        config_file_path = os.path.join(script_dir, "config", "settings.json")
        try:
            with open(config_file_path, "r", encoding="utf-8") as config_file:
                config_data = json.load(config_file)

            if not config_data:
                print("Error: No config file found.")
                return

            config_data["DEFAULT_VIDEO_FORMAT"] = selected_format

            with open(config_file_path, "w", encoding="utf-8") as config_file:
                json.dump(config_data, config_file, indent=4)

            print(f"\n\033[92m\u2713  Default video format set to: {selected_format.lstrip('.')}\033[0m")

        except (FileNotFoundError, json.JSONDecodeError) as error:
            print(f"Error: {error}")
    else:
        print("\n✖  Invalid option! Please try again:\n")
        return


def set_default_directory():
    try:
        print("\nSelect the default directory")
        window = tk.Tk()
        window.wm_attributes("-topmost", 1)
        window.withdraw()
        file_path = filedialog.askdirectory(
            parent=window, initialdir=get_default_directory(), title="Select A Default Directory"
        )

        if file_path:
            if not file_path.endswith("/"):
                file_path += "/"
            script_dir = get_script_directory()
            config_file_path = os.path.join(script_dir, "config", "settings.json")

            try:
                with open(config_file_path, "r", encoding="utf-8") as config_file:
                    config_data = json.load(config_file)

                config_data["DEFAULT_DIRECTORY"] = file_path
                with open(config_file_path, "w", encoding="utf-8") as config_file:
                    json.dump(config_data, config_file, indent=4)

                print(f"\n\033[92m\u2713  Default directory set to: {file_path}\033[0m")

            except (FileNotFoundError, json.JSONDecodeError) as error:
                print(f"Error: {error}")
        else:
            print("\nNo folder selected! Returning to main menu...")

        window.destroy()
    except tk.TclError:
        file_path = input("Enter the full path to the default directory: ").strip(' "\'')
        while True:
            if not file_path:
                print("\nNo directory entered! Returning to main menu...")
                return
            
            file_path = os.path.expanduser(file_path)
            
            try:
                os.makedirs(file_path, exist_ok=True)
            except Exception as e:
                file_path = input(f"Error creating directory: {e}\nEnter a valid path: ").strip(' "\'')
                continue

            if not file_path.endswith("/"):
                file_path += "/"

            script_dir = get_script_directory()
            config_file_path = os.path.join(script_dir, "config", "settings.json")

            try:
                with open(config_file_path, "r", encoding="utf-8") as config_file:
                    config_data = json.load(config_file)

                config_data["DEFAULT_DIRECTORY"] = file_path
                with open(config_file_path, "w", encoding="utf-8") as config_file:
                    json.dump(config_data, config_file, indent=4)

                print(f"\n\033[92m\u2713  Default directory set to: {file_path}\033[0m")
                break

            except (FileNotFoundError, json.JSONDecodeError) as error:
                print(f"Error: {error}")
                return


def set_default_downloader():
    # Choose between ffmpeg and yt-dlp
    print("\nSelect the default downloader")
    DOWNLOADERS = ["ffmpeg", "yt-dlp"]
    for i, downloader_option in enumerate(DOWNLOADERS, start=1):
        print(f"{i}) {downloader_option.lstrip('.')}")

    user_option = str(input("\nChoose a downloader: "))
    if user_option in [str(i) for i in range(1, len(DOWNLOADERS) + 1)]:
        selected_downloader = DOWNLOADERS[int(user_option) - 1]

        if selected_downloader == "yt-dlp":
            get_yt_dlp_path()
        script_dir = get_script_directory()
        config_file_path = os.path.join(script_dir, "config", "settings.json")
        try:
            with open(config_file_path, "r", encoding="utf-8") as config_file:
                config_data = json.load(config_file)

            config_data["DEFAULT_DOWNLOADER"] = selected_downloader
            with open(config_file_path, "w", encoding="utf-8") as config_file:
                json.dump(config_data, config_file, indent=4)

            print(f"\n\033[92m\u2713  Default downloader set to: {selected_downloader}\033[0m")

        except (FileNotFoundError, json.JSONDecodeError) as error:
            print(f"Error: {error}")
    else:
        print("\n✖  Invalid option! Please try again:\n")
        return


def get_m3u8_file_dialog():
    try:
        window = tk.Tk()
        window.wm_attributes("-topmost", 1)
        window.withdraw()
        directory = get_default_directory()
        file_path = filedialog.askopenfilename(
            parent=window,
            initialdir=directory,
            title="Select A File",
            filetypes=(("M3U8 files", "*.m3u8"), ("All files", "*")),
        )
        window.destroy()
        return file_path
    except tk.TclError:
        file_path = input("Enter the full path to the M3U8 file: ").strip(' "\'')
        while not file_path:
            return None
        while not os.path.exists(file_path):
            file_path = input("File does not exist! Enter a valid path: ").strip(' "\'')
        return file_path


def parse_vod_filename(m3u8_video_filename):
    base = os.path.basename(m3u8_video_filename)
    try:
        streamer_name, video_id = base.split(".m3u8", 1)[0].rsplit("_", 1)
        return streamer_name, video_id
    except ValueError:
        print(f"Error: {base}")
        return "Video", "Output"


def parse_vod_filename_with_Brackets(m3u8_video_filename):
    base = os.path.basename(m3u8_video_filename)
    streamer_name, video_id = base.split(".m3u8", 1)[0].rsplit("_", 1)
    return f" - {streamer_name} [{video_id}]"


def remove_chars_from_ordinal_numbers(datetime_string):
    ordinal_numbers = ["th", "nd", "st", "rd"]
    for exclude_string in ordinal_numbers:
        if exclude_string in datetime_string:
            return datetime_string.replace(datetime_string.split(" ")[1], datetime_string.split(" ")[1][:-len(exclude_string)])


def generate_website_links(streamer_name, video_id, tracker_url=None):
    website_list = [
        f"https://sullygnome.com/channel/{streamer_name}/stream/{video_id}",
        f"https://twitchtracker.com/{streamer_name}/streams/{video_id}",
        f"https://streamscharts.com/channels/{streamer_name}/streams/{video_id}",
    ]
    if tracker_url:
        website_list = [link for link in website_list if tracker_url not in link]
    return website_list


def convert_url(url, target):
    # converts url to the specified target website
    patterns = {
        "sullygnome": "https://sullygnome.com/channel/{}/stream/{}",
        "twitchtracker": "https://twitchtracker.com/{}/streams/{}",
        "streamscharts": "https://streamscharts.com/channels/{}/streams/{}",
    }
    parsed_url = urlparse(url)
    streamer, video_id = None, None

    if "sullygnome" in url:
        streamer = parsed_url.path.split("/")[2]
        video_id = parsed_url.path.split("/")[4]

    elif "twitchtracker" in url:
        streamer = parsed_url.path.split("/")[1]
        video_id = parsed_url.path.split("/")[3]

    elif "streamscharts" in url:
        streamer = parsed_url.path.split("/")[2]
        video_id = parsed_url.path.split("/")[4]

    if streamer and video_id:
        return patterns[target].format(streamer, video_id)


def extract_offset(clip_url):
    clip_offset = re.search(r"(?:-offset|-index)-(\d+)", clip_url)
    return clip_offset.group(1)


def get_clip_format(video_id, offsets):
    default_clip_list = [f"https://clips-media-assets2.twitch.tv/{video_id}-offset-{i}.mp4" for i in range(0, offsets, 2)]
    alternate_clip_list = [f"https://clips-media-assets2.twitch.tv/vod-{video_id}-offset-{i}.mp4" for i in range(0, offsets, 2)]
    legacy_clip_list = [f"https://clips-media-assets2.twitch.tv/{video_id}-index-{i:010}.mp4" for i in range(offsets)]

    clip_format_dict = {
        "1": default_clip_list,
        "2": alternate_clip_list,
        "3": legacy_clip_list,
    }
    return clip_format_dict


def get_random_clip_information():
    while True:
        url = get_websites_tracker_url()

        if "streamscharts" in url:
            _, video_id = parse_streamscharts_url(url)
            break
        if "twitchtracker" in url:
            _, video_id = parse_twitchtracker_url(url)
            break
        if "sullygnome" in url:
            _, video_id = parse_sullygnome_url(url)
            break

        print("\n✖  Link not supported! Please try again:\n")

    while True:
        duration = get_time_input_HH_MM("Enter stream duration in (HH:MM) format: ")
        hours, minutes = map(int, duration.split(":"))
        if hours >= 0 and minutes >= 0:
            break
    return video_id, hours, minutes


def manual_clip_recover():
    while True:
        streamer_name = input("Enter the Streamer Name: ")
        if streamer_name.strip():
            break
        else:
            print("\n✖  No streamer name! Please try again:\n")
    while True:
        video_id = input("Enter the Video ID (from: Twitchtracker/Streamscharts/Sullygnome): ")
        if video_id.strip():
            break
        else:
            print("\n✖  No video ID! Please try again:\n")

    while True:
        duration = get_time_input_HH_MM("Enter stream duration in (HH:MM) format: ")

        hours, minutes = map(int, duration.split(":"))
        if hours >= 0 and minutes >= 0:
            total_minutes = hours * 60 + minutes
            break

    clip_recover(streamer_name, video_id, total_minutes)


def website_clip_recover():
    tracker_url = get_websites_tracker_url()

    if not tracker_url.startswith("https://"):
        tracker_url = "https://" + tracker_url
    if "streamscharts" in tracker_url:
        streamer, video_id = parse_streamscharts_url(tracker_url)

        print("\nRetrieving stream duration from Streamscharts")
        duration_streamscharts = parse_duration_streamscharts(tracker_url)
        # print(f"Duration: {duration_streamscharts}")

        clip_recover(streamer, video_id, int(duration_streamscharts))
    elif "twitchtracker" in tracker_url:
        streamer, video_id = parse_twitchtracker_url(tracker_url)

        print("\nRetrieving stream duration from Twitchtracker")
        duration_twitchtracker = parse_duration_twitchtracker(tracker_url)
        # print(f"Duration: {duration_twitchtracker}")

        clip_recover(streamer, video_id, int(duration_twitchtracker))
    elif "sullygnome" in tracker_url:
        streamer, video_id = parse_sullygnome_url(tracker_url)

        print("\nRetrieving stream duration from Sullygnome")
        duration_sullygnome = parse_duration_sullygnome(tracker_url)
        if duration_sullygnome is None:
            print("Could not retrieve duration from Sullygnome. Try a different URL.\n")
            return print_main_menu()
        # print(f"Duration: {duration_sullygnome}")
        clip_recover(streamer, video_id, int(duration_sullygnome))
    else:
        print("\n✖  Link not supported! Try again...\n")
        return_to_main_menu()


def manual_vod_recover():
    while True:
        streamer_name = input("Enter the Streamer Name: ")
        if streamer_name.lower().strip():
            break
        else:
            print("\n✖  No streamer name! Please try again:\n")
        
    while True:
        video_id = input("Enter the Video ID (from: Twitchtracker/Streamscharts/Sullygnome URL): ")
        if video_id.strip():
            break
        else:
            print("\n✖  No video ID! Please try again:\n")

    timestamp = get_time_input_YYYY_MM_DD_HH_MM_SS("Enter VOD Datetime YYYY-MM-DD HH:MM:SS (24-hour format, UTC): ")

    streamer_name = streamer_name.lower().strip()
    print(f"\nRecovering VOD for {streamer_name} with ID {video_id}")
    m3u8_link = vod_recover(streamer_name, video_id, timestamp)
    if m3u8_link is None:
        sys.exit("No M3U8 link found! Exiting...")

    m3u8_source = process_m3u8_configuration(m3u8_link)
    handle_download_menu(m3u8_source)


def handle_vod_recover(url, url_parser, datetime_parser, website_name):
    streamer, video_id = url_parser(url)
    print(f"Checking {streamer} VOD ID: {video_id}")

    stream_datetime, source_duration = datetime_parser(url)
    m3u8_link = vod_recover(streamer, video_id, stream_datetime, url)

    if m3u8_link is None:
        message = f"\nNo M3U8 link found from {website_name}!"
        print(message)
        if CLI_MODE:
            raise ReturnToMain()
        input(" Press Enter to return...")
        return_to_main_menu()

    m3u8_source = process_m3u8_configuration(m3u8_link)
    m3u8_duration = return_m3u8_duration(m3u8_link)

    if source_duration and int(source_duration) >= m3u8_duration + 10:
        print(f"The duration from {website_name} exceeds the M3U8 duration. This may indicate a split stream, try checking Streamscharts for another URL.\n")
    return m3u8_source, stream_datetime


def website_vod_recover():
    url = get_twitch_or_tracker_url()
    if not url.startswith("https://"):
        url = "https://" + url

    if "streamscharts" in url:
        return handle_vod_recover(url, parse_streamscharts_url, parse_datetime_streamscharts, "Streamscharts")

    if "twitchtracker" in url:
        return handle_vod_recover(url, parse_twitchtracker_url, parse_datetime_twitchtracker, "Twitchtracker")

    if "sullygnome" in url:
        new_tracker_url = re.sub(r"/\d+/", "/", url)
        return handle_vod_recover(new_tracker_url, parse_sullygnome_url, parse_datetime_sullygnome, "Sullygnome")

    if "twitch.tv" in url:
        if is_twitch_livestream_url(url):
            return record_live_from_start(url)
        return twitch_recover(url)

    print("\n✖  Link not supported! Returning to main menu...")
    return_to_main_menu()


def get_all_clip_urls(clip_format_dict, clip_format_list):
    combined_clip_format_list = []
    for key, value in clip_format_dict.items():
        if key in clip_format_list:
            combined_clip_format_list += value
    return combined_clip_format_list


async def fetch_status(session, url, retries=5, timeout=30):
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    if url.endswith('.m3u8'):
                        data = await response.text()
                        if data and "#EXTM3U" in data:
                            return url
                    elif url.endswith('.ts'):
                        return url
                    else:
                        data = await response.read()
                        if data:
                            return url
        except asyncio.TimeoutError:
            if attempt == retries - 1:
                pass
        except Exception as e:
            pass
        if attempt != retries - 1:
            await asyncio.sleep(1)
    return None


async def get_vod_urls(streamer_name, video_id, start_timestamp):
    script_dir = get_script_directory()
    domains = read_text_file(os.path.join(script_dir, "lib", "domains.txt"))
    qualities = ["chunked", "1080p60"]

    print("\nSearching for M3U8 URL...")

    m3u8_link_list = [
        f"{domain.strip()}{str(hashlib.sha1(f'{streamer_name}_{video_id}_{int(calculate_epoch_timestamp(start_timestamp, seconds))}'.encode('utf-8')).hexdigest())[:20]}_{streamer_name}_{video_id}_{int(calculate_epoch_timestamp(start_timestamp, seconds))}/{quality}/index-dvr.m3u8"
        for seconds in range(-30, 60)
        for domain in domains if domain.strip()
        for quality in qualities
    ]

    successful_url = None
    progress_printed = False

    try:
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_status(session, url) for url in m3u8_link_list]
            task_objects = [asyncio.create_task(task) for task in tasks]

            for index, task in enumerate(asyncio.as_completed(task_objects), 1):
                try:
                    url = await task
                    print(f"\rSearching {index}/{len(m3u8_link_list)} URLs", end="", flush=True)
                    progress_printed = True
                    if url:
                        successful_url = url
                        print("\n" if progress_printed else "\n\n")
                        print(f"\033[92m✓ Found URL: {successful_url}\033[0m\n")
                        for task_obj in task_objects:
                            try:
                                task_obj.cancel()
                            except Exception:
                                pass
                        break
                except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionResetError, OSError):
                    continue
                except Exception:
                    continue

    except Exception as e:
        print(f"\n\033[91m✖ Error during URL search: {str(e)}\033[0m")
        return None

    return successful_url


def get_chunked_actual_resolution(m3u8_url):
    try:
        ffprobe_path = get_ffprobe_path()
        
        m3u8_command = [
            ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-select_streams", "v:0",
            m3u8_url
        ]
        
        result = subprocess.run(m3u8_command, capture_output=True, text=True, timeout=15, check=False)
        if result.returncode != 0 or not result.stdout:
            return None
        
        probe_data = json.loads(result.stdout)
        
        if not probe_data.get("streams"):
            return None
            
        video_stream = probe_data["streams"][0]
        width = video_stream.get("width")
        height = video_stream.get("height")
        
        fps_str = video_stream.get("r_frame_rate", "30/1")
        try:
            if "/" in fps_str:
                num, den = fps_str.split("/")
                fps = round(float(num) / float(den))
            else:
                fps = round(float(fps_str))
        except (ValueError, ZeroDivisionError):
            fps = 30
            
        if not width or not height:
            return None
            
        if height >= 2160:
            res_name = "2160p"
        elif height >= 1440:
            res_name = "1440p"
        elif height >= 1080:
            res_name = "1080p"
        elif height >= 720:
            res_name = "720p"
        elif height >= 480:
            res_name = "480p"
        elif height >= 360:
            res_name = "360p"
        else:
            res_name = "160p"
            
        return f"{res_name}{fps}"
        
    except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError, ValueError):
        return None


def return_supported_qualities(m3u8_link):
    if m3u8_link is None:
        return None

    always_best_quality = read_config_by_key("settings", "ALWAYS_BEST_QUALITY")

    found_quality = None
    for res in RESOLUTIONS:
        if f"/{res}/" in m3u8_link:
            found_quality = res
            break
    if not found_quality:
        found_quality = "chunked"

    if always_best_quality is True and found_quality == "chunked":
        return m3u8_link

    print("Checking for available qualities...")

    def check_quality(resolution):
        url = m3u8_link.replace(f"/{found_quality}/", f"/{resolution}/")
        try:
            response = requests.get(url, timeout=20)
            if response.status_code == 200:
                return resolution
        except Exception as e:
            pass
        return None

    with ThreadPoolExecutor() as executor:
        quality_futures = {executor.submit(check_quality, res): res for res in RESOLUTIONS}
        
        chunked_future = None
        if "chunked" in RESOLUTIONS:
            chunked_url = m3u8_link.replace(f"/{found_quality}/", "/chunked/")
            chunked_future = executor.submit(get_chunked_actual_resolution, chunked_url)
        
        valid_resolutions = []
        for future in quality_futures:
            try:
                result = future.result(timeout=15)
                if result:
                    valid_resolutions.append(result)
            except Exception:
                continue
        
        chunked_resolution_info = None
        if chunked_future and "chunked" in valid_resolutions:
            try:
                chunked_resolution_info = chunked_future.result(timeout=15)
            except Exception:
                chunked_resolution_info = None

    if not valid_resolutions:
        return None

    valid_resolutions.sort(key=RESOLUTIONS.index)

    if always_best_quality:
        best_resolution = valid_resolutions[0]
        if best_resolution == found_quality:
            return m3u8_link
        return m3u8_link.replace(f"/{found_quality}/", f"/{best_resolution}/")


    print("\nQuality Options:")
    for idx, resolution in enumerate(valid_resolutions, 1):
        if "chunked" in resolution:
            if chunked_resolution_info:
                print(f"{idx}. {chunked_resolution_info}")
            else:
                print(f"{idx}. Source (Best Quality)")
        else:
            print(f"{idx}. {resolution}")
    print()
    user_option = get_user_resolution_choice(m3u8_link, valid_resolutions, found_quality)
    return user_option


def get_user_resolution_choice(m3u8_link, valid_resolutions, found_quality):
    prompt = f"Choose a quality: "
    while True:
        raw = input(prompt).strip()
        if raw == "":
            continue
        if raw.isdigit():
            choice = int(raw)
            if 1 <= choice <= len(valid_resolutions):
                quality = valid_resolutions[choice - 1]
                return m3u8_link.replace(f"/{found_quality}/", f"/{quality}/")
        print("\n✖  Invalid option! Please try again:\n")


def parse_website_duration(duration_string):
    if isinstance(duration_string, list):
        duration_string = " ".join(duration_string)
    if not isinstance(duration_string, str):
        try:
            duration_string = str(duration_string)
        except Exception:
            return 0
    pattern = r"(\d+)\s*(h(?:ou)?r?s?|m(?:in)?(?:ute)?s?)"
    matches = re.findall(pattern, duration_string, re.IGNORECASE)
    if not matches:
        try:
            minutes = int(duration_string)
            return calculate_broadcast_duration_in_minutes(0, minutes)
        except ValueError:
            return 0

    time_units = {"h": 0, "m": 0}
    for value, unit in matches:
        time_units[unit[0].lower()] = int(value)

    return calculate_broadcast_duration_in_minutes(time_units["h"], time_units["m"])


def check_seleniumbase_version():
    try:
        requirements_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib", "requirements.txt")
        required_version = None

        with open(requirements_path, "r", encoding="utf-8") as req_file:
            for line in req_file:
                match = re.match(r"seleniumbase==([\d.]+)", line.strip())
                if match:
                    required_version = match.group(1)
                    break
        installed_version = importlib.metadata.version("seleniumbase")
        if required_version and version.parse(installed_version) < version.parse(required_version):
            print(f"Upgrading seleniumbase from {installed_version} to {required_version}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", f"seleniumbase=={required_version}"])
                print(f"seleniumbase upgraded to {required_version}")
            except Exception as pip_e:
                print(f"\033[91m[ERROR]\033[0m Could not upgrade seleniumbase: {pip_e}")
    except Exception as e:
        pass


def handle_selenium(url):
    try:
        check_seleniumbase_version()
        with SB(uc=True) as sb:
            try:
                sb.activate_cdp_mode(url)
                sb.sleep(5)
                sb.uc_gui_click_captcha()
                sb.sleep(3)
                source = sb.cdp.get_page_source()
                if f"Waiting for {url.split('/')[2]} to respond..." in source:
                    raise Exception("Error: Waiting for website to respond...")
                return source
                
            except Exception:
                try:
                    sb.activate_cdp_mode(url)
                    sb.sleep(5)
                    sb.uc_gui_handle_captcha()
                    sb.sleep(3)
                    source = sb.cdp.get_page_source()
                    return source
                except Exception as e:
                    print(e)
            finally:
                selenium_cleanup()
    except Exception as e:
        print(e)


def selenium_get_latest_streams_from_twitchtracker(streamer_name):
    url = f"https://twitchtracker.com/{streamer_name}/streams"
    try:
        check_seleniumbase_version()
        with SB(uc=True) as sb:
            try:
                sb.activate_cdp_mode(url)
                sb.sleep(5)
                sb.uc_gui_click_captcha()
                sb.sleep(4)
                sb.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            except Exception:
                try:
                    sb.activate_cdp_mode(url)
                    sb.sleep(5)
                    sb.uc_gui_handle_captcha()
                    sb.sleep(4)
                    sb.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                except Exception as e:
                    print(e)
            finally:
                selenium_cleanup()

            timezone_offset_hours = 0
            timezone_offset_mins = 0
            try:
                try:
                    offset_minutes = sb.execute_script("return (new Date()).getTimezoneOffset();")
                    offset_hours = -int(offset_minutes) // 60
                    offset_mins = abs(int(offset_minutes)) % 60
                    timezone_offset_hours = offset_hours
                    timezone_offset_mins = offset_mins
                except Exception:
                    try:
                        timezone_text = sb.execute_script("document.querySelector('#timezone-switch > span')?.textContent || null")
                        if timezone_text is not None:
                            timezone_match = re.match(r'UTC([+-]\d{1,2})(?::?(\d{2}))?', timezone_text)
                            timezone_offset_hours = int(timezone_match.group(1) if timezone_match else 0)
                            timezone_offset_mins = int(timezone_match.group(2) if timezone_match and timezone_match.group(2) else 0)
                        else:
                            raise ValueError("No timezone text found")
                    except Exception as e2:
                        try:
                            local_off = datetime.now().astimezone().utcoffset() or timedelta(0)
                            total_minutes = int(local_off.total_seconds() // 60)
                            timezone_offset_hours = total_minutes // 60
                            timezone_offset_mins = abs(total_minutes) % 60
                        except Exception:
                            print(f"\nWarning: Could not determine timezone, defaulting to UTC: {str(e2)}")
                            timezone_offset_hours = 0
                            timezone_offset_mins = 0
            except Exception:
                try:
                    timezone_element = sb.execute_script("var el = document.getElementById('timezone-switch'); if (el) { var span = el.querySelector('span'); span ? span.textContent : null; } else { null; }")
                    timezone_text = timezone_element if timezone_element else "UTC"
                    timezone_match = re.match(r'UTC([+-]\d+)', timezone_text)
                    timezone_offset_hours = int(timezone_match.group(1)) if timezone_match else 0
                    timezone_offset_mins = 0
                except Exception as e2:
                    print(f"\nWarning: Could not determine timezone, defaulting to UTC: {str(e2)}")
                    timezone_offset_hours = 0
                    timezone_offset_mins = 0

            streams = []
            try:
                data = sb.execute_script("try { return $('#streams').DataTable().data(); } catch(e) { return null; }")
                compl = sb.execute_script("try { return Y && Y.complicator ? Y.complicator : null; } catch(e) { return null; }")
                if compl is None or data is None:
                    raise Exception("Could not find stream data with DataTable JS")
                for key in data:
                    if not key.isdigit():
                        continue
                    row = data[key]
                    raw_dt_key = row[0].get('@data-order') if isinstance(row[0], dict) else None
                    if not raw_dt_key:
                        continue
                    try:
                        try:
                            dt_utc_obj = datetime.strptime(raw_dt_key, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            dt_utc_obj = datetime.strptime(raw_dt_key, "%Y-%m-%d %H:%M")
                    except Exception as pe:
                        continue
                    dt_utc_norm = dt_utc_obj.strftime("%Y-%m-%d %H:%M:%S")
                    dt_local = datetime.strftime(dt_utc_obj + timedelta(hours=timezone_offset_hours, minutes=timezone_offset_mins), "%Y-%m-%d %H:%M:%S")
                    title = row[6]
                    duration = 0
                    try:
                        dur_order = row[1]['@data-order'] if isinstance(row[1], dict) else None
                        if dur_order is not None:
                            dur_minutes = float(dur_order)
                            duration = dur_minutes // 60 + (dur_minutes % 60 / 60)
                        else:
                            duration = parse_website_duration(row[1]) // 60 if isinstance(row[1], str) else 0
                    except Exception:
                        try:
                            duration_minutes = parse_website_duration(str(row[1]))
                            duration = duration_minutes // 60 + (duration_minutes % 60 / 60)
                        except Exception:
                            duration = 0
                    current_utc = datetime.utcnow()
                    old_utc = current_utc - timedelta(days=60)
                    if dt_utc_obj < old_utc:
                        continue
                    if raw_dt_key not in compl:
                        continue
                    assist = compl[raw_dt_key]
                    stream_id = assist['id']
                    stream = {
                        'dt_utc': dt_utc_norm,
                        'dt_local': dt_local,
                        'title': title,
                        'duration': duration,
                        'stream_id': stream_id,
                    }
                    streams.append(stream)
                streams.reverse()
                return streams
            except Exception:
                try:
                    table_data = sb.execute_script("""
                        var table = document.getElementById('streams');
                        if (!table) { null; }
                        else {
                            var rows = table.querySelectorAll('tbody tr');
                            var result = [];
                            rows.forEach(function(row) {
                                var cells = row.querySelectorAll('td');
                                if (cells.length < 7) return;
                                var date = cells[0].querySelector('span') ? cells[0].querySelector('span').textContent.trim() : '';
                                var duration = cells[1].querySelector('span') ? cells[1].querySelector('span').textContent.trim() : '';
                                var title = cells[6].textContent.trim();
                                var link = cells[0].querySelector('a');
                                var video_id = link && link.href ? link.href.split('/').pop() : '';
                                result.push({
                                    'dt_local': date,
                                    'title': title,
                                    'duration': duration,
                                    'stream_id': video_id,
                                });
                            });
                            result;
                        }
                    """)
                    if table_data and len(table_data) > 0:
                        first_date = table_data[0]['dt_local']
                        if not re.match(r'^\d{2}/[A-Za-z]{3}/\d{4} \d{2}:\d{2}$', first_date.strip()):
                            raise Exception("Invalid date format in fallback table")
                    for row in table_data or []:
                        try:
                            dt_local_obj = datetime.strptime(row['dt_local'], "%d/%b/%Y %H:%M")
                            dt_utc_obj = dt_local_obj - timedelta(hours=timezone_offset_hours, minutes=timezone_offset_mins)
                            dt_utc = dt_utc_obj.strftime("%Y-%m-%d %H:%M:%S")
                            dt_local = dt_local_obj.strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            dt_utc = row.get('dt_utc') or ''
                            try:
                                if dt_utc and len(dt_utc.strip()) > 0:
                                    parsed = format_iso_datetime(dt_utc)
                                    if parsed:
                                        dt_utc = parsed
                            except Exception:
                                pass
                            dt_local = row['dt_local']
                        try:
                            duration_minutes = parse_website_duration(row['duration'])
                            duration = duration_minutes // 60 + (duration_minutes % 60 / 60)
                        except Exception:
                            duration = 0
                        try:
                            if dt_utc:
                                dt_utc_check = datetime.strptime(dt_utc, "%Y-%m-%d %H:%M:%S")
                                if dt_utc_check < datetime.now(timezone.utc) - timedelta(days=60):
                                    continue
                        except Exception:
                            pass
                        streams.append({
                            'dt_utc': dt_utc,
                            'dt_local': dt_local,
                            'title': row['title'],
                            'duration': duration,
                            'stream_id': row['stream_id'],
                        })
                    return streams
                except Exception as e2:
                    print(f"\nError extracting stream data: {str(e2)}")
                    return None
    except Exception as e:
        print(e)


def selenium_cleanup():
    try:
        if os.path.exists("downloaded_files"):
            shutil.rmtree("downloaded_files", ignore_errors=True)
    except Exception:
        pass


def parse_streamscharts_duration_data(bs):
    streamscharts_duration = bs.find_all("div", {"class": "text-xs font-bold"})[3].text
    streamscharts_duration_in_minutes = parse_website_duration(streamscharts_duration)
    return streamscharts_duration_in_minutes


def parse_duration_streamscharts(streamscharts_url):
    try:
        # Method 1: Using requests
        response = requests.get(streamscharts_url, headers=return_user_agent(), timeout=10)
        if response.status_code == 200:
            bs = BeautifulSoup(response.content, "html.parser")
            return parse_streamscharts_duration_data(bs)

        # Method 2: Using Selenium
        print("Opening Streamcharts with browser...")
        source = handle_selenium(streamscharts_url)
        bs = BeautifulSoup(source, "html.parser")
        return parse_streamscharts_duration_data(bs)

    except Exception:
        pass

    sullygnome_url = convert_url(streamscharts_url, "sullygnome")
    if sullygnome_url:
        return parse_duration_sullygnome(sullygnome_url)
    return None


def parse_twitchtracker_duration_data(bs):
    twitchtracker_duration = bs.find_all("div", {"class": "g-x-s-value"})[0].text
    twitchtracker_duration_in_minutes = parse_website_duration(twitchtracker_duration)
    return twitchtracker_duration_in_minutes


def parse_duration_twitchtracker(twitchtracker_url, try_alternative=True):
    try:
        # Method 1: Using requests
        response = requests.get(twitchtracker_url, headers=return_user_agent(), timeout=10)
        if response.status_code == 200:
            bs = BeautifulSoup(response.content, "html.parser")
            return parse_twitchtracker_duration_data(bs)

        # Method 2: Using Selenium
        print("Opening Twitchtracker with browser...")
        source = handle_selenium(twitchtracker_url)

        bs = BeautifulSoup(source, "html.parser")
        return parse_twitchtracker_duration_data(bs)

    except Exception:
        pass

    if try_alternative:
        sullygnome_url = convert_url(twitchtracker_url, "sullygnome")
        if sullygnome_url:
            return parse_duration_sullygnome(sullygnome_url)
    return None


def parse_sullygnome_duration_data(bs):
    sullygnome_duration = bs.find_all("div", {"class": "MiddleSubHeaderItemValue"})[7].text.split(",")
    sullygnome_duration_in_minutes = parse_website_duration(sullygnome_duration)
    return sullygnome_duration_in_minutes


def parse_duration_sullygnome(sullygnome_url):
    try:
        # Method 1: Using requests
        response = requests.get(sullygnome_url, headers=return_user_agent(), timeout=10)
        if response.status_code == 200:
            bs = BeautifulSoup(response.content, "html.parser")
            return parse_sullygnome_duration_data(bs)

        # Method 2: Using Selenium
        print("Opening Sullygnome with browser...")
        source = handle_selenium(sullygnome_url)

        bs = BeautifulSoup(source, "html.parser")
        return parse_sullygnome_duration_data(bs)

    except Exception:
        pass

    sullygnome_url = convert_url(sullygnome_url, "twitchtracker")
    if sullygnome_url:
        return parse_duration_twitchtracker(sullygnome_url, try_alternative=False)
    return None


def parse_streamscharts_datetime_data(bs):
    stream_date = (
        bs.find_all("time", {"class": "ml-2 font-bold"})[0]
        .text.strip()
        .replace(",", "")
        + ":00"
    )
    stream_datetime = datetime.strptime(stream_date, "%d %b %Y %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")


    try:
        streamcharts_duration = bs.find_all("span", {"class": "mx-2 font-bold"})[0].text
        streamcharts_duration_in_minutes = parse_website_duration(streamcharts_duration)
    except Exception:
        streamcharts_duration_in_minutes = None

    return stream_datetime, streamcharts_duration_in_minutes


def parse_datetime_streamscharts(streamscharts_url, skip_gql=False):
    try:
        # Method 1: Using api
        if not skip_gql:
            stream_datetime = get_stream_datetime(streamscharts_url)
            if stream_datetime and stream_datetime != (None, None):
                return stream_datetime
            stream_datetime = get_datetime_from_vod_vod(streamscharts_url)
            if stream_datetime and stream_datetime != (None, None):
                return stream_datetime

        # Method 2: Using requests
        response = requests.get(
            streamscharts_url, headers=return_user_agent(), timeout=10
        )
        if response.status_code == 200:
            bs = BeautifulSoup(response.content, "html.parser")
            return parse_streamscharts_datetime_data(bs)

        # Method 3: Using Selenium
        print("\nOpening Streamscharts with browser...")

        source = handle_selenium(streamscharts_url)

        bs = BeautifulSoup(source, "html.parser")
        return parse_streamscharts_datetime_data(bs)

    except Exception:
        pass
    return None, None


def parse_twitchtracker_datetime_data(bs):
    twitchtracker_datetime = bs.find_all("div", {"class": "stream-timestamp-dt"})[0].text
    try:
        twitchtracker_duration = bs.find_all("div", {"class": "g-x-s-value"})[0].text
        twitchtracker_duration_in_minutes = parse_website_duration(twitchtracker_duration)
    except Exception:
        twitchtracker_duration_in_minutes = None

    return twitchtracker_datetime, twitchtracker_duration_in_minutes


def parse_datetime_twitchtracker(twitchtracker_url, skip_gql=False):
    try:
        # Method 1: Using api
        if not skip_gql:
            stream_datetime = get_stream_datetime(twitchtracker_url)
            if stream_datetime and stream_datetime != (None, None):
                return stream_datetime
            stream_datetime = get_datetime_from_vod_vod(twitchtracker_url)
            if stream_datetime and stream_datetime != (None, None):
                return stream_datetime

        # Method 2: Using requests
        response = requests.get(twitchtracker_url, headers=return_user_agent(), timeout=10)
        if response.status_code == 200:
            bs = BeautifulSoup(response.content, "html.parser")
            return parse_twitchtracker_datetime_data(bs)

        # Method 3: Using Selenium
        print("\nOpening Twitchtracker with browser...")

        source = handle_selenium(twitchtracker_url)

        bs = BeautifulSoup(source, "html.parser")
        description_meta = bs.find("meta", {"name": "description"})
        twitchtracker_datetime = None

        if description_meta:
            description_content = description_meta.get("content")
            match = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", description_content)
            if match:
                twitchtracker_datetime = match.group(0)

                try:
                    twitchtracker_duration = bs.find_all("div", {"class": "g-x-s-value"})[0].text
                    twitchtracker_duration_in_minutes = parse_website_duration(twitchtracker_duration)
                except Exception:
                    twitchtracker_duration_in_minutes = None

                return twitchtracker_datetime, twitchtracker_duration_in_minutes
    except Exception:
        pass
    return None, None


def parse_sullygnome_datetime_data(bs):
    stream_date = bs.find_all("div", {"class": "MiddleSubHeaderItemValue"})[6].text
    modified_stream_date = remove_chars_from_ordinal_numbers(stream_date)
    formatted_stream_date = datetime.strptime(f"{datetime.now().year} {modified_stream_date}", "%Y %A %d %B %I:%M%p").strftime("%m-%d %H:%M:%S")
    sullygnome_datetime = str(datetime.now().year) + "-" + formatted_stream_date

    sullygnome_duration = bs.find_all("div", {"class": "MiddleSubHeaderItemValue"})[7].text.split(",")
    sullygnome_duration_in_minutes = parse_website_duration(sullygnome_duration)

    return sullygnome_datetime, sullygnome_duration_in_minutes


def parse_datetime_sullygnome(sullygnome_url, skip_gql=False):
    try:
        # Method 1: Using api
        if not skip_gql:
            stream_datetime = get_stream_datetime(sullygnome_url)
            if stream_datetime and stream_datetime != (None, None):
                return stream_datetime
            stream_datetime = get_datetime_from_vod_vod(sullygnome_url)
            if stream_datetime and stream_datetime != (None, None):
                return stream_datetime
        # Method 2: Using requests
        response = requests.get(sullygnome_url, headers=return_user_agent(), timeout=10)
        if response.status_code == 200:
            bs = BeautifulSoup(response.content, "html.parser")
            return parse_sullygnome_datetime_data(bs)

        # Method 3: Using Selenium
        print("\nOpening Sullygnome with browser...")
        source = handle_selenium(sullygnome_url)

        bs = BeautifulSoup(source, "html.parser")
        return parse_sullygnome_datetime_data(bs)

    except Exception:
        pass
    return None, None


def unmute_vod(m3u8_link):
    video_filepath = get_vod_filepath(parse_streamer_from_m3u8_link(m3u8_link), parse_video_id_from_m3u8_link(m3u8_link))
    
    write_m3u8_to_file(m3u8_link, video_filepath)
    
    with open(video_filepath, "r+", encoding="utf-8") as video_file:
        file_contents = video_file.readlines()
        video_file.seek(0)

        is_muted = is_video_muted(m3u8_link)
        base_link = m3u8_link.replace("index-dvr.m3u8", "")

        for line in file_contents:
            if line.startswith("#"):
                if line.startswith("#EXT-X-MAP") and "URI=" in line:
                    try:
                        prefix, uri_part = line.split("URI=", 1)
                        if uri_part.startswith('"'):
                            end_quote = uri_part.find('"', 1)
                            raw_uri = uri_part[1:end_quote]
                            absolute_uri = ensure_absolute_uri(raw_uri, base_link)
                            line = f"{prefix}URI=\"{absolute_uri}\"\n"
                        else:
                            raw_uri = uri_part.strip().split(",")[0]
                            absolute_uri = ensure_absolute_uri(raw_uri, base_link)
                            line = f"#EXT-X-MAP:URI=\"{absolute_uri}\"\n"
                    except Exception:
                        pass
                video_file.write(line)
                continue

            segment_uri = line.strip()
            if not segment_uri:
                video_file.write(line)
                continue

            if "-unmuted" in segment_uri:
                segment_uri = segment_uri.replace("-unmuted", "-muted")
            absolute_segment = ensure_absolute_uri(segment_uri, base_link)

            video_file.write(f"{absolute_segment}\n")

        video_file.truncate()
    
    if is_muted:
        print(f"{os.path.normpath(video_filepath)} has been processed!\n")


def mark_invalid_segments_in_playlist(m3u8_link):
    print()
    unmute_vod(m3u8_link)
    vod_file_path = get_vod_filepath(parse_streamer_from_m3u8_link(m3u8_link),parse_video_id_from_m3u8_link(m3u8_link))

    with open(vod_file_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    print("Checking for invalid segments...")
    segments = asyncio.run(validate_playlist_segments(get_all_playlist_segments(m3u8_link)))

    if not segments:
        if "/highlight" not in m3u8_link:
            print("No segments are valid. Cannot generate M3U8! Returning to main menu.")
        os.remove(vod_file_path)
        return
    
    playlist_segments = [segment for segment in segments if segment in lines]
    modified_playlist = []
    for line in lines:
        if line in playlist_segments:
            modified_playlist.append(line)
        elif line.startswith("#"):
            modified_playlist.append(line)
        elif line.endswith(".ts"):
            modified_playlist.append("#" + line)
        else:
            modified_playlist.append(line)
    with open(vod_file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(modified_playlist))
    input("Press Enter to continue...")


def return_m3u8_duration(m3u8_link):
    total_duration = 0
    file_contents = requests.get(m3u8_link, stream=True, timeout=30).text.splitlines()
    for line in file_contents:
        if line.startswith("#EXTINF:"):
            segment_duration = float(line.split(":")[1].split(",")[0])
            total_duration += segment_duration
    total_minutes = int(total_duration // 60)
    return total_minutes


def check_if_unmuted_is_playable(m3u8_source):
    try:
        async def run_ffprobe():
            ffprobe_path = get_ffprobe_path()
            cmd = [
                ffprobe_path,
                '-protocol_whitelist', 'file,http,https,tcp,tls,crypto',
                '-i', m3u8_source
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=20)
                return stderr.decode('utf-8', errors='ignore')
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise subprocess.TimeoutExpired(cmd, 20)
        
        output = asyncio.run(run_ffprobe())
        
        if "Error" in output:
            print("Video is not playable after unmuting, using original m3u8 instead\n")
            return False
        else:
            return True
            
    except (asyncio.TimeoutError, subprocess.TimeoutExpired):
        print("ffprobe check timed out, using original m3u8 instead\n")
        return False
    except Exception as e:
        print(f"Error checking if unmuted is playable: {e}")
        return False


def process_m3u8_configuration(m3u8_link, skip_check=False):
    playlist_segments = get_all_playlist_segments(m3u8_link)
    check_segments = read_config_by_key("settings", "CHECK_SEGMENTS") and not skip_check

    m3u8_source = None
    if is_video_muted(m3u8_link):
        print("Video contains muted/invalid segments")
        if read_config_by_key("settings", "UNMUTE_VIDEO"):
            unmute_vod(m3u8_link)
            m3u8_source = get_vod_filepath(parse_streamer_from_m3u8_link(m3u8_link),parse_video_id_from_m3u8_link(m3u8_link),)
            is_playable = check_if_unmuted_is_playable(m3u8_source)
            if is_playable:
                return m3u8_source
            else:
                return m3u8_link
        
    else:
        m3u8_source = m3u8_link
        file_path = get_vod_filepath(parse_streamer_from_m3u8_link(m3u8_link), parse_video_id_from_m3u8_link(m3u8_link))
        if os.path.exists(file_path):
            os.remove(file_path)

    if check_segments:
        print("Checking valid segments...")
        try:
            async def validate_with_timeout():
                return await asyncio.wait_for(validate_playlist_segments(playlist_segments), timeout=60)
            asyncio.run(validate_with_timeout())
        except asyncio.TimeoutError:
            print("Segment validation timed out. Continuing without validation...")
        except Exception as e:
            print(f"Segment validation failed: {e}. Continuing without validation...")
    return m3u8_source


def get_all_playlist_segments(m3u8_link):
    video_file_path = get_vod_filepath(parse_streamer_from_m3u8_link(m3u8_link), parse_video_id_from_m3u8_link(m3u8_link))
    write_m3u8_to_file(m3u8_link, video_file_path)

    segment_list = []
    base_link = m3u8_link.replace("index-dvr.m3u8", "")
    
    with open(video_file_path, "r+", encoding="utf-8") as video_file:
        file_contents = video_file.readlines()
        video_file.seek(0)

        for line in file_contents:
            if line.startswith("#"):
                if line.startswith("#EXT-X-MAP") and "URI=" in line:
                    try:
                        prefix, uri_part = line.split("URI=", 1)
                        if uri_part.startswith('"'):
                            end_quote = uri_part.find('"', 1)
                            raw_uri = uri_part[1:end_quote]
                            absolute_uri = ensure_absolute_uri(raw_uri, base_link)
                            line = f"{prefix}URI=\"{absolute_uri}\"\n"
                        else:
                            raw_uri = uri_part.strip().split(",")[0]
                            absolute_uri = ensure_absolute_uri(raw_uri, base_link)
                            line = f"#EXT-X-MAP:URI=\"{absolute_uri}\"\n"
                    except Exception:
                        pass
                video_file.write(line)
                continue

            segment_uri = line.strip()
            if not segment_uri:
                video_file.write(line)
                continue

            absolute_segment = ensure_absolute_uri(segment_uri, base_link)
            video_file.write(f"{absolute_segment}\n")
            segment_list.append(absolute_segment)

        video_file.truncate()
    return segment_list


async def validate_playlist_segments(segments):
    valid_segments = []
    all_segments = [url.strip() for url in segments]
    available_segment_count = 0
    
    batch_size = 250
    
    connector = aiohttp.TCPConnector(
        limit=150,
        force_close=True,
        enable_cleanup_closed=True,
        ssl=False
    )
    
    timeout = aiohttp.ClientTimeout(total=20, connect=5)
    
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            for i in range(0, len(all_segments), batch_size):
                batch = all_segments[i:i + batch_size]
                tasks = []
                
                for url in batch:
                    task = asyncio.create_task(fetch_status(session, url, retries=3, timeout=30))
                    tasks.append(task)
                
                try:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for url in results:
                        if url and not isinstance(url, Exception):
                            available_segment_count += 1
                            valid_segments.append(url)
                    
                    print(f"\rChecking segments {min(i + batch_size, len(all_segments))} / {len(all_segments)}", end="", flush=True)
                
                except Exception as e:
                    print(f"\nError processing batch: {str(e)}")
                    continue
                
                await asyncio.sleep(0.5)
    
    except Exception as e:
        print(f"\nError during segment validation: {str(e)}")
    
    finally:
        if not connector.closed:
            await connector.close()
    
    print()
    if available_segment_count == len(all_segments):
        print("All Segments are Available\n")
    elif available_segment_count == 0:
        print("No Segments are Available\n")
    else:
        print(f"{available_segment_count} out of {len(all_segments)} Segments are Available. To recheck the segments select option 4 from the menu.\n")
    
    return valid_segments


def run_vod_recovery(streamer_name, video_id, timestamp):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        vod_url = loop.run_until_complete(get_vod_urls(streamer_name, video_id, timestamp))
        loop.close()
        return vod_url
    except Exception as e:
        print(f"\n✖  Error during VOD recovery: {str(e)}")
        return None


def try_alternate_timestamps(streamer_name, video_id, timestamp, alternate_websites):
    all_timestamps = [timestamp]
    asked_same_timestamps = set()

    for website in alternate_websites:
        parsed_timestamp = None
        if "streamscharts" in website:
            parsed_timestamp, _ = parse_datetime_streamscharts(website, skip_gql=True)
        elif "twitchtracker" in website:
            parsed_timestamp, _ = parse_datetime_twitchtracker(website, skip_gql=True)
        elif "sullygnome" in website:
            # If the timestamp shows a year different from the current one, skip it since SullyGnome doesn't provide the year
            if timestamp and datetime.now().year != int(timestamp.split("-")[0]):
                continue
            parsed_timestamp, _ = parse_datetime_sullygnome(website, skip_gql=True)

        if parsed_timestamp and parsed_timestamp != timestamp and parsed_timestamp not in all_timestamps:
            print(f"Found different timestamp: {parsed_timestamp}")
            all_timestamps.append(parsed_timestamp)

            vod_url = run_vod_recovery(streamer_name, video_id, parsed_timestamp)
            if vod_url:
                return vod_url
        else:
            if parsed_timestamp is not None:
                print(f"Found same timestamp: {parsed_timestamp}")
                if parsed_timestamp in asked_same_timestamps:
                    print("Already handled same timestamp, skipping...")
                else:
                    if get_yes_no_choice("Do you want to retry with the same timestamp?"):
                        asked_same_timestamps.add(parsed_timestamp)
                        vod_url = run_vod_recovery(streamer_name, video_id, parsed_timestamp)
                        if vod_url:
                            return vod_url
                    else:
                        asked_same_timestamps.add(parsed_timestamp)
                        print("Skipping same timestamp...")

    return None


def vod_recover(streamer_name, video_id, timestamp, tracker_url=None):
    print(f"\nDatetime: {timestamp}")
    try:
        vod_age = calculate_days_since_broadcast(timestamp)

        if vod_age > 60:
            print("Video is older than 60 days. Chances of recovery are very slim.")
        vod_url = None

        if timestamp:
            m3u8_url = run_vod_recovery(streamer_name, video_id, timestamp)
            vod_url = return_supported_qualities(m3u8_url)

        if vod_url is None:
            alternate_websites = generate_website_links(streamer_name, video_id, tracker_url)

            print("\nUnable to recover with provided url! Searching for different timestamps")
            vod_url = try_alternate_timestamps(streamer_name, video_id, timestamp, alternate_websites)
            
            if vod_url:
                return vod_url

            if not timestamp:
                print("\033[91m \n✖ Unable to get the stream start datetime!\033[0m")
                print("The datetime should be in the format: YYYY-MM-DD HH:MM:SS")

                input_datetime = input("\nEnter the datetime: ")

                if not input_datetime:
                    print("\033[91m \n✖  No datetime entered! \033[0m")
                    input("\nPress Enter to continue...")
                    return_to_main_menu()
                
                vod_url = run_vod_recovery(streamer_name, video_id, input_datetime)
                
                if vod_url:
                    return vod_url

            if not vod_url and tracker_url:
                print("\033[91m \n✖  Unable to recover the video! \033[0m")
                input("\nPress Enter to continue...")
                return_to_main_menu()
            else:
                return None

        return vod_url
    except ReturnToMain:
        raise
    except Exception as e:
        print(f"\n✖  Error during VOD recovery: {str(e)}")
        return None


def print_bulk_vod_options_menu(all_m3u8_links):
    while True:
        print("\nFound M3U8 Links:")
        for idx, (video_id, link) in enumerate(all_m3u8_links, 1):
            print(f"{idx}. Video {video_id}: \033[92m{link}\033[0m")
        
        print("\nOptions:")
        print("1. Download all VODs")
        print("2. Download specific VOD")
        print("3. Download or trim specific VOD")
        print("4. Return to main menu")
        
        choice = input("\nSelect Option: ")
        
        if choice in ["1", "2", "3", "4"]:
            return choice
        else:
            print("Invalid choice. Please try again.")


def print_select_vod_menu(all_m3u8_links):
    while True:
        print("\nSelect a VOD to download:")
        for idx, (video_id, link) in enumerate(all_m3u8_links, 1):
            print(f"{idx}. VOD {idx}: \033[92m{link}\033[0m")
        
        try:
            vod_num = int(input("\nEnter the number of the VOD to download: "))
            if 1 <= vod_num <= len(all_m3u8_links):
                return all_m3u8_links[vod_num - 1]
            else:
                print("Invalid VOD number. Please try again.")
        except ValueError:
            print("Please enter a valid number.")


def bulk_vod_recovery():
    csv_file_path = get_and_validate_csv_filename()
    streamer_name = parse_streamer_from_csv_filename(csv_file_path)
    csv_file = parse_vod_csv_file(csv_file_path)
    print()
    all_m3u8_links = []
    for timestamp, video_id in csv_file.items():
        print("Recovering Video:", video_id)
        m3u8_link = asyncio.run(get_vod_urls(streamer_name.lower(), video_id, timestamp))

        if m3u8_link is not None:
            process_m3u8_configuration(m3u8_link)
            all_m3u8_links.append((video_id, m3u8_link))
        else:
            print("No VODs found using the current domain list.")
    
    if all_m3u8_links:
        while True:
            choice = print_bulk_vod_options_menu(all_m3u8_links)
            
            if choice == "1":
                for video_id, link in all_m3u8_links:
                    print(f"\nDownloading VOD {video_id}...")
                    handle_vod_url_normal(link)
                break
            elif choice == "2":
                selected_vod = print_select_vod_menu(all_m3u8_links)
                if selected_vod:
                    video_id, link = selected_vod
                    print(f"\nDownloading VOD {video_id}...")
                    handle_vod_url_normal(link)
                break
            elif choice == "3":
                selected_vod = print_select_vod_menu(all_m3u8_links)
                if selected_vod:
                    video_id, link = selected_vod
                    handle_download_menu(link)
                break
            else:
                print("Invalid choice. Please try again.")
        input("\nPress Enter to continue...")


def clip_recover(streamer, video_id, duration):
    iteration_counter, valid_counter = 0, 0
    valid_url_list = []

    clip_format = print_clip_format_menu().split(" ")
    print("Searching...")
    full_url_list = get_all_clip_urls(get_clip_format(video_id, calculate_max_clip_offset(duration)), clip_format)

    request_session = requests.Session()
    max_retries = 3

    def check_url(url):
        for attempt in range(1, max_retries + 1):
            try:
                response = request_session.head(url, timeout=20)
                return url, response.status_code
            except Exception:
                if attempt < max_retries:
                    time.sleep(0.5)
                else:
                    return url, None

    with ThreadPoolExecutor(max_workers=100) as executor:
        future_to_url = {executor.submit(check_url, url): url for url in full_url_list}
        for future in as_completed(future_to_url):
            iteration_counter += 1
            url, status = future.result()
            print(f"\rSearching for clips... {iteration_counter} of {len(full_url_list)}", end=" ", flush=True)
            if status == 200:
                valid_counter += 1
                valid_url_list.append(url)
                print(f"- {valid_counter} Clip(s) Found", end=" ")
            else:
                print(f"- {valid_counter} Clip(s) Found", end=" ")

    print()

    if valid_url_list:
        for url in valid_url_list:
            write_text_file(url, get_log_filepath(streamer, video_id))
        if (read_config_by_key("settings", "AUTO_DOWNLOAD_CLIPS") or get_yes_no_choice("\nDo you want to download the recovered clips?")):
            download_clips(get_default_directory(), streamer, video_id)
        if read_config_by_key("settings", "REMOVE_LOG_FILE"):
            os.remove(get_log_filepath(streamer, video_id))
        else:
            keep_log_option = input("Do you want to remove the log file? ")
            if keep_log_option.upper() == "Y":
                os.remove(get_log_filepath(streamer, video_id))
    else:
        print("No clips found! Returning to main menu.\n")


def get_and_validate_csv_filename():
    try:
        window = tk.Tk()
        window.wm_attributes("-topmost", 1)
        window.withdraw()

        file_path = filedialog.askopenfilename(parent=window, title="Select The CSV File", filetypes=(("CSV files", "*.csv"), ("all files", "*.*")))

        if not file_path:
            print("\nNo file selected! Returning to main menu.")
            return_to_main_menu()
        window.destroy()
        csv_filename = os.path.basename(file_path)
        pattern = r"^[a-zA-Z0-9_]{4,25} - Twitch stream stats"
        if bool(re.match(pattern, csv_filename)):
            return file_path
        print("The CSV filename MUST be the original filename that was downloaded from sullygnome!")
        return_to_main_menu()
    except tk.TclError:
        file_path = input("Enter the full path to the CSV file: ").strip(' "\'')
        while True:
            if not file_path:
                print("\nNo file entered! Returning to main menu.")
                return_to_main_menu()
            if not os.path.exists(file_path):
                file_path = input("File does not exist! Enter a valid path: ").strip(' "\'')
                continue
            csv_filename = os.path.basename(file_path)
            pattern = r"^[a-zA-Z0-9_]{4,25} - Twitch stream stats"
            if bool(re.match(pattern, csv_filename)):
                return file_path
            print("The CSV filename MUST be the original filename that was downloaded from sullygnome!")
            file_path = input("Enter a valid path: ").strip(' "\'')


def parse_clip_csv_file(file_path):
    vod_info_dict = {}
    lines = read_csv_file(file_path)[1:]
    for line in lines:
        if line:
            stream_date = remove_chars_from_ordinal_numbers(line[1].replace('"', ""))
            modified_stream_date = datetime.strptime(stream_date, "%A %d %B %Y %H:%M").strftime("%d-%B-%Y")
            video_id = line[2].partition("stream/")[2].replace('"', "")
            duration = line[3]
            if video_id != "0":
                max_clip_offset = calculate_max_clip_offset(int(duration))
                vod_info_dict.update({video_id: (modified_stream_date, max_clip_offset)})
    return vod_info_dict


def parse_vod_csv_file(file_path):
    vod_info_dict = {}
    lines = read_csv_file(file_path)[1:]
    for line in lines:
        if line:
            stream_date = remove_chars_from_ordinal_numbers(line[1].replace('"', ""))
            modified_stream_date = datetime.strptime(stream_date, "%A %d %B %Y %H:%M").strftime("%Y-%m-%d %H:%M:%S")
            video_id = line[2].partition("stream/")[2].split(",")[0].replace('"', "")
            vod_info_dict.update({modified_stream_date: video_id})
    return vod_info_dict


def merge_csv_files(csv_filename, directory_path):
    csv_list = [file for file in os.listdir(directory_path) if file.endswith(".csv")]
    header_saved = False
    with open(os.path.join(directory_path, f"{csv_filename.title()}_MERGED.csv"), "w", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file)
        for file in csv_list:
            reader = read_csv_file(os.path.join(directory_path, file))
            header = reader[0]
            if not header_saved:
                writer.writerow(header)
                header_saved = True
            for row in reader[1:]:
                writer.writerow(row)
    print("CSV files merged successfully!")


def random_clip_recovery(video_id, hours, minutes):
    max_retries = 3
    display_count = 3

    clip_format = print_clip_format_menu().split(" ")
    duration = calculate_broadcast_duration_in_minutes(hours, minutes)
    full_url_list = get_all_clip_urls(get_clip_format(video_id, calculate_max_clip_offset(duration)), clip_format)
    random.shuffle(full_url_list)

    request_session = requests.Session()

    def check_url(url):
        for _ in range(max_retries):
            try:
                response = request_session.head(url, timeout=20)
                if response.status_code == 200:
                    return url
            except Exception:
                time.sleep(0.5)
        return None

    print("Searching...")

    counter = 0
    should_continue = True
    url_iter = iter(full_url_list)

    with ThreadPoolExecutor() as executor:
        while should_continue:
            batch_futures = []
            try:
                for _ in range(display_count * 2):
                    url = next(url_iter)
                    batch_futures.append(executor.submit(check_url, url))
            except StopIteration:
                pass 

            if not batch_futures:
                break 

            for future in as_completed(batch_futures):
                result = future.result()
                if result:
                    print(result)
                    counter += 1

                    if counter % display_count == 0:
                        if not get_yes_no_choice("\nDo you want to search more URLs?"):                            
                            should_continue = False
                            break

            if counter == 0 and not should_continue:
                print("No valid clips found.")
                break


def bulk_clip_recovery():
    vod_counter = 0
    streamer_name, csv_file_path = "", ""

    bulk_recovery_option = print_bulk_clip_recovery_menu()
    if bulk_recovery_option == "1":
        csv_file_path = get_and_validate_csv_filename()
        streamer_name = parse_streamer_from_csv_filename(csv_file_path).lower()
    elif bulk_recovery_option == "2":
        csv_directory = input("Enter the full path where the sullygnome csv files exist: ").replace('"', "")
        streamer_name = input("Enter the streamer's name: ").lower()
        if get_yes_no_choice("Do you want to merge the CSV files in the directory?"):
            merge_csv_files(streamer_name, csv_directory)
            csv_file_path = os.path.join(csv_directory, f"{streamer_name.title()}_MERGED.csv")
        else:
            csv_file_path = get_and_validate_csv_filename()
            csv_file_path = csv_file_path.replace('"', "")
    elif bulk_recovery_option == "3":
        return_to_main_menu()

    clip_format = print_clip_format_menu().split(" ")
    stream_info_dict = parse_clip_csv_file(csv_file_path)

    request_session = requests.Session()
    max_retries = 3

    def check_url(url):
        for attempt in range(1, max_retries + 1):
            try:
                response = request_session.head(url, timeout=20)
                return url, response.status_code
            except Exception:
                if attempt < max_retries:
                    time.sleep(0.5)
                else:
                    return url, None

    should_download = read_config_by_key("settings", "AUTO_DOWNLOAD_CLIPS")
    if not should_download:
        should_download = get_yes_no_choice("Do you want to download all clips recovered?")

    should_keep_logs = False
    if not should_download:
        remove_log_file = read_config_by_key("settings", "REMOVE_LOG_FILE")
        if remove_log_file is not None:
            should_keep_logs = not remove_log_file
        else:
            should_keep_logs = get_yes_no_choice("Would you like to keep the log files containing links to the recovered clips?")

    for video_id, values in stream_info_dict.items():
        vod_counter += 1
        iteration_counter, valid_counter = 0, 0
        
        print(f"\nProcessing Past Broadcast:\n" 
              f"Stream Date: {values[0].replace('-', ' ')}\n" 
              f"Vod ID: {video_id}\n" 
              f"Vod Number: {vod_counter} of {len(stream_info_dict)}\n")
        
        full_url_list = get_all_clip_urls(get_clip_format(video_id, values[1]), clip_format)
        print("Searching...")

        with ThreadPoolExecutor(max_workers=100) as executor:
            future_to_url = {executor.submit(check_url, url): url for url in full_url_list}
            for future in as_completed(future_to_url):
                iteration_counter += 1
                url, status = future.result()
                print(f"\rSearching for clips... {iteration_counter} of {len(full_url_list)}", end=" ", flush=True)
                if status == 200:
                    valid_counter += 1
                    write_text_file(url, get_log_filepath(streamer_name, video_id))
                    print(f"- {valid_counter} Clip(s) Found", end=" ")
                else:
                    print(f"- {valid_counter} Clip(s) Found", end=" ")

        print(f"\n\033[92m{valid_counter} Clip(s) Found\033[0m\n")

        if valid_counter != 0:
            if should_download:
                download_clips(get_default_directory(), streamer_name, video_id)
                os.remove(get_log_filepath(streamer_name, video_id))
            else:
                if not should_keep_logs:
                    os.remove(get_log_filepath(streamer_name, video_id))
                else:
                    print("\nRecovered links saved to " + get_log_filepath(streamer_name, video_id))
        else:
            if len(stream_info_dict) > vod_counter:
                print("No clips found!... Moving on to next vod.")
    
    input("\nPress Enter to continue...")


def download_clips(directory, streamer_name, video_id):
    download_directory = os.path.join(directory, f"{streamer_name.title()}_{video_id}")
    os.makedirs(download_directory, exist_ok=True)
    file_contents = read_text_file(get_log_filepath(streamer_name, video_id))
    if not file_contents:
        print("File is empty!")
        return
    mp4_links = [link for link in file_contents if os.path.basename(link).endswith(".mp4")]
    for link in mp4_links:
        try:
            response = requests.get(link, stream=False, timeout=30)
            if response.status_code == 200:
                offset = extract_offset(response.url)
                file_name = f"{streamer_name.title()}_{video_id}_{offset}{get_default_video_format()}"
                try:
                    with open(os.path.join(download_directory, file_name), "wb") as x:
                        print(f"Downloaded: {file_name}")
                        x.write(response.content)
                except ValueError:
                    print(f"Failed to download... {response.url}")
            else:
                print(f"Failed to download.... {response.url}")
        except Exception:
            print(f"Failed to download.... {link}")
            continue

    print(f"\n\033[92m\u2713 Clips downloaded to {download_directory}\033[0m")


def get_ffmpeg_path():
    try:
        try:

            if subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True).returncode == 0:
                return "ffmpeg"
        except Exception:
            pass 
        
        if os.path.exists(ffdl.ffmpeg_path):
            return ffdl.ffmpeg_path

        raise Exception
    except Exception:
        sys.exit("FFmpeg not found! Please install FFmpeg correctly and try again.")


def get_ffprobe_path():
    try:
        try:
            if subprocess.run(["ffprobe", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True).returncode == 0:
                return "ffprobe"
        except Exception:
            pass

        if os.path.exists(ffdl.ffprobe_path):
            return ffdl.ffprobe_path

        raise Exception
    except Exception:
        sys.exit("FFprobe not found! Please install FFmpeg with FFprobe correctly and try again.")


def get_yt_dlp_path():
    try:
        if (subprocess.run(["yt-dlp", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True).returncode == 0):
            return "yt-dlp"
    except Exception:
        command = [sys.executable, "-m", "pip", "install", "yt-dlp", "--upgrade", "-q", "--disable-pip-version-check"]

        try:
            subprocess.run(command, check=True)
            return "yt-dlp"
        except Exception:
            sys.exit("yt-dlp not installed! Please install yt-dlp and try again.")


def update_yt_dlp():
    print("\nUpdating yt-dlp to nightly version...")
    command = [sys.executable, "-m", "pip", "install", "-U", "--pre", "yt-dlp[default]"]
    try:
        subprocess.run(command, check=True)
    except Exception as e:
        print(f"\n✖  Could not update yt-dlp to nightly: {e}")
        print("\nAttempting to update to stable version...\n")
        try:
            command_stable = [sys.executable, "-m", "pip", "install", "-U", "yt-dlp[default]"]
            subprocess.run(command_stable, check=True)
        except Exception as e_stable:
            print(f"\n✖  Could not update yt-dlp: {e_stable}")
    input("\nPress Enter to continue...")


def get_short_filename(filename):
    base_name = os.path.splitext(os.path.basename(filename))[0]
    
    if " - " in base_name:
        parts = base_name.split(" - ")
        if len(parts) >= 2:
            return f"{parts[0]} - {parts[1]}"
        else:
            return parts[0]
    
    return base_name[:30] + "..." if len(base_name) > 30 else base_name


def format_file_size(n):
    try:
        n = float(n)
    except Exception:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024.0
        i += 1
    return f"{n:.1f} {units[i]}"


def get_m3u8_duration(m3u8_source):
    try:
        total_duration = 0.0
        
        if m3u8_source.startswith(('http://', 'https://')):
            response = requests.get(m3u8_source, timeout=30)
            response.raise_for_status()
            content = response.text
            lines = content.splitlines()
        else:
            with open(m3u8_source, 'r', encoding='utf-8', errors='ignore') as file:
                lines = file.readlines()
        
        for line in lines:
            line = line.strip()
            if line.startswith('#EXTINF:'):
                # Extract duration from #EXTINF:duration,title
                duration_str = line.split('#EXTINF:')[1].split(',')[0]
                try:
                    duration = float(duration_str)
                    total_duration += duration
                except ValueError:
                    continue
                    
        return total_duration if total_duration > 0 else None
    except Exception:
        return None


def seconds_to_time_str(seconds):
    try:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    except Exception:
        return "00:00:00"


def calculate_slice_duration(start_time, end_time):
    try:
        def time_to_seconds(time_str):
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        
        start_seconds = time_to_seconds(start_time)
        end_seconds = time_to_seconds(end_time)
        
        return end_seconds - start_seconds if end_seconds > start_seconds else None
    except Exception:
        return None


def handle_progress_bar(command, output_filename, m3u8_source, start_time=None, end_time=None):
    try:
        short_title = get_short_filename(output_filename)
        
        if start_time and end_time:
            duration_override = calculate_slice_duration(start_time, end_time)
        else:
            duration_override = get_m3u8_duration(m3u8_source)
        
        with FfmpegProgress(command) as ff:
            with tqdm(total=100, position=0, desc=short_title, leave=None, colour="blue", unit="%", bar_format="{l_bar}{bar}| {percentage:.1f}/100%{postfix}") as pbar:
                # Extract output file path from the ffmpeg command
                try:
                    if "-y" in command:
                        out_idx = command.index("-y") + 1
                        output_path_cmd = command[out_idx]
                    else:
                        output_path_cmd = output_filename
                except (ValueError, IndexError):
                    output_path_cmd = output_filename

                if duration_override:
                    progress_iterator = ff.run_command_with_progress(duration_override=duration_override)
                else:
                    progress_iterator = ff.run_command_with_progress()
                
                for progress in progress_iterator:
                    if progress is not None:
                        pbar.update(progress - pbar.n)

                    current_time_str = "00:00:00"
                    total_time_str = "00:00:00"
                    
                    if duration_override and progress is not None:
                        current_seconds = (progress / 100.0) * duration_override
                        current_time_str = seconds_to_time_str(current_seconds)
                        total_time_str = seconds_to_time_str(duration_override)
                    
                    size_str = "0 B"
                    try:
                        file_path = os.path.normpath(output_path_cmd)
                        if os.path.exists(file_path):
                            size_str = format_file_size(os.path.getsize(file_path))
                    except Exception:
                        pass
                    
                    if duration_override:
                        postfix_str = f"[{current_time_str} / {total_time_str}] • {size_str}"
                    else:
                        postfix_str = size_str
                    
                    pbar.set_postfix_str(postfix_str, refresh=True)

                pbar.close()
        return True
    except Exception as e:
        print(f"Error: {str(e).strip()}")
        raise Exception from e


def handle_file_already_exists(output_path):
    if os.path.exists(output_path):
        if CLI_MODE:
            return True
        if not get_yes_no_choice(f'File already exists at "{output_path}". Do you want to redownload it?'):
            print("\n\033[94m\u2713 Skipping download!\033[0m\n")
            input("Press Enter to continue...")
            return_to_main_menu()
    return True


def handle_retry_command(command):
    try:
        retry_command = ' '.join(f'"{part}"' if ' ' in part else part for part in command)
        print("Retrying command: " + retry_command)
        subprocess.run(retry_command, shell=True, check=True)
        return True
    except Exception:
        return False


def is_m3u8_live(m3u8_link):
    try:
        parsed_url = urlparse(m3u8_link)
        if parsed_url.scheme in ("http", "https"):
            try:
                response = requests.get(m3u8_link, timeout=15)
                response.raise_for_status()
                return all('#EXT-X-ENDLIST' not in line for line in response.text.splitlines())
            except Exception:
                return True
        else:
            with open(m3u8_link, 'r', encoding='utf-8', errors='ignore') as file:
                for line in file:
                    if '#EXT-X-ENDLIST' in line:
                        return False
    except Exception:
        return True
    return True


def download_m3u8_video_url(m3u8_link, output_filename, from_start=False):
    if os.name != 'nt':
        output_filename = quote_filename(output_filename)

    output_path = os.path.normpath(os.path.join(get_default_directory(), output_filename))
    handle_file_already_exists(output_path)

    downloader = get_default_downloader()


    if downloader == "ffmpeg":
        command = [
            get_ffmpeg_path(),
            "-hide_banner",
            "-loglevel", "warning",
            "-stats",
        ]

        is_live = is_m3u8_live(m3u8_link)

        if CLI_MODE and CLI_DOWNLOAD_FROM_START:
            from_start = True

        if is_live:
            if from_start:
                command += ["-live_start_index", "0"]
            elif not CLI_MODE and get_yes_no_choice("Do you want to download the stream from the start?"):
                command += ["-live_start_index", "0"]

        command += [
            "-i", m3u8_link,
            "-c", "copy",
            "-f", get_ffmpeg_format(get_default_video_format()),
            "-y", output_path
        ]

    else:
        command = [
            get_yt_dlp_path(),
            m3u8_link,
            "-o", output_path,
        ]
        custom_options = get_yt_dlp_custom_options()
        if custom_options:
            command.extend(custom_options)

    print("\nCommand: " + " ".join(command) + "\n")

    try:
        if downloader == "ffmpeg" and get_use_progress_bar():
            handle_progress_bar(command, output_filename, m3u8_link)
        else:
            subprocess.run(command, check=True)
        return True
    except Exception as e:
        if downloader == "ffmpeg" and get_use_progress_bar():
            try:
                retry_cmd = ' '.join(f'"{part}"' if ' ' in part else part for part in command)
                subprocess.run(retry_cmd, shell=True, check=True)
                if os.path.exists(output_path):
                    return True
            except Exception:
                pass
        retry_success = handle_retry_command(command)
        if retry_success and os.path.exists(output_path):
            return True
        return False


def download_m3u8_video_url_slice(m3u8_link, output_filename, video_start_time, video_end_time):
    if os.name != 'nt':
        output_filename = quote_filename(output_filename)

    output_path = os.path.normpath(os.path.join(get_default_directory(), output_filename))
    handle_file_already_exists(output_path)

    downloader = get_default_downloader()

    if downloader == "ffmpeg":
        
        command = [
            get_ffmpeg_path(),
            "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
            "-hide_banner",
            "-loglevel", "warning",
            "-stats",
            "-live_start_index", "0",
            "-ss", video_start_time,
            "-to", video_end_time, 
            "-i", m3u8_link,
            "-c", "copy",
            "-f", get_ffmpeg_format(get_default_video_format()),
            "-y", output_path,
        ]
    elif downloader == "yt-dlp":
        command = [
            get_yt_dlp_path(),
            m3u8_link,
            "-o", output_path,
            "--download-sections", f"*{video_start_time}-{video_end_time}",
        ]
        custom_options = get_yt_dlp_custom_options()
        if custom_options:
            command.extend(custom_options)

    print("\nCommand: " + " ".join(command) + "\n")

    try:
        if downloader == "ffmpeg" and get_use_progress_bar():
            handle_progress_bar(command, output_filename, m3u8_link, video_start_time, video_end_time)
        else:
            subprocess.run(command, check=True)
        return True
    except Exception as e:
        if downloader == "ffmpeg" and get_use_progress_bar():
            try:
                retry_cmd = ' '.join(f'"{part}"' if ' ' in part else part for part in command)
                subprocess.run(retry_cmd, shell=True, check=True)
                if os.path.exists(output_path):
                    return True
            except Exception:
                pass
        retry_success = handle_retry_command(command)
        if retry_success and os.path.exists(output_path):
            return True
        return False


def download_m3u8_video_file(m3u8_file_path, output_filename):    
    output_path = os.path.normpath(os.path.join(get_default_directory(), output_filename))
    handle_file_already_exists(output_path)

    downloader = get_default_downloader()
    
    if downloader == "yt-dlp":
        if os.name == 'nt' and m3u8_file_path.startswith('\\\\'):
            m3u8_file_path = 'file://' + m3u8_file_path.replace('\\', '/')
        else:
            m3u8_file_path = Path(m3u8_file_path).resolve().as_uri()

    if downloader == "ffmpeg":
        command = [
            get_ffmpeg_path(),
            "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
            "-hide_banner",
            "-loglevel", "warning",
            "-stats",
            "-ignore_unknown",
            "-i", m3u8_file_path,
            "-c", "copy",
            "-f", get_ffmpeg_format(get_default_video_format()),
            "-y", output_path,
        ]
    elif downloader == "yt-dlp":
        command = [
            get_yt_dlp_path(),
            "--enable-file-urls",
            m3u8_file_path,
            "-o", output_path,
        ]
        custom_options = get_yt_dlp_custom_options()
        if custom_options:
            command.extend(custom_options)

    print("\nCommand: " + " ".join(command) + "\n")

    try:
        if downloader == "ffmpeg" and get_use_progress_bar():
            handle_progress_bar(command, output_filename, m3u8_file_path)
        else:
            subprocess.run(command, check=True)
        return True
    except Exception as e:
        if downloader == "ffmpeg" and get_use_progress_bar():
            try:
                retry_cmd = ' '.join(f'"{part}"' if ' ' in part else part for part in command)
                subprocess.run(retry_cmd, shell=True, check=True)
                if os.path.exists(output_path):
                    return True
            except Exception:
                pass
        retry_success = handle_retry_command(command)
        if retry_success and os.path.exists(output_path):
            return True
        return False


def download_m3u8_video_file_slice(m3u8_file_path, output_filename, video_start_time, video_end_time):
    output_path = os.path.normpath(os.path.join(get_default_directory(), output_filename))
    handle_file_already_exists(output_path)

    if not os.path.exists(m3u8_file_path):
        print(f"Error: The m3u8 file does not exist at {m3u8_file_path}")
        return False

    downloader = get_default_downloader()

    if downloader == "yt-dlp":
        print("Using ffmpeg, because yt-dlp doesn't natively support trimming before downloading")

    command = [
        get_ffmpeg_path(),
        "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
        "-hide_banner",
        "-loglevel", "warning",
        "-stats",
        "-ignore_unknown",
        "-ss", video_start_time,
        "-to", video_end_time, 
        "-i", m3u8_file_path,
        "-c", "copy",
        "-f", get_ffmpeg_format(get_default_video_format()),
        "-y", output_path,
    ]

    print("\nCommand: " + " ".join(command) + "\n")

    try:
        if get_use_progress_bar():
            handle_progress_bar(command, output_filename, m3u8_file_path, video_start_time, video_end_time)
        else:
            subprocess.run(command, check=True)
        return True
    except Exception as e:
        if get_use_progress_bar():
            try:
                retry_cmd = ' '.join(f'"{part}"' if ' ' in part else part for part in command)
                subprocess.run(retry_cmd, shell=True, check=True)
                if os.path.exists(output_path):
                    return True
            except Exception:
                pass
        retry_success = handle_retry_command(command)
        if retry_success and os.path.exists(output_path):
            return True
        return False


def get_twitch_channel_from_url(twitch_url):
    try:
        parsed = urlparse(twitch_url)
        path_parts = [p for p in parsed.path.split("/") if p]
        if path_parts:
            return path_parts[0]
        return twitch_url.strip().split("?")[0]
    except Exception:
        return twitch_url


def handle_live_recording_fallback(channel_name, command, output_path):
    print("\033[94m\nVod Storage for this stream is likely disabled, searching for stream M3U8...\033[0m")
    
    vod_id, created_at_iso, started_at_iso = fetch_stream_data(channel_name)
    datetime_iso = created_at_iso or started_at_iso
    
    if not datetime_iso:
        return False
        
    formatted = format_iso_datetime(datetime_iso)
    if not formatted:
        return False
        
    m3u8_source = vod_recover(channel_name, vod_id, formatted)
    if m3u8_source:
        vod_filename = get_filename_for_url_source(m3u8_source, title=None, stream_date=formatted)
        success = download_m3u8_video_url(m3u8_source, vod_filename, from_start=True)
        if success:
            print(f"\n\033[92m\u2713 Live recording saved to {os.path.join(get_default_directory(), vod_filename)}\033[0m\n")
            input("Press Enter to continue...")
            return True
    
    print("\033[91m \n✖  Unable to record stream from the beginning! \033[0m")
    
    if get_yes_no_choice("Try to record from the current point?"):
        if "--live-from-start" in command:
            command.remove("--live-from-start")
        
        try:
            subprocess.run(command, check=True)
            print(f"\n\033[92m\u2713 Live recording saved to {output_path}\033[0m\n")
            input("Press Enter to continue...")
            return True
        except Exception as e:
            print(f"\n\033[94m\nError: {e}\033[0m")
            return False
    else:
        return_to_main_menu()


def record_live_from_start(twitch_url=None):
    if not twitch_url:
        twitch_url = print_get_twitch_url_or_name_menu()
    
    if not is_twitch_livestream_url(twitch_url):
        return twitch_recover(twitch_url)
    
    channel_name = get_twitch_channel_from_url(twitch_url)
    from_start = get_yes_no_choice("Download from the start?")
    
    output_filename = f"{channel_name} - Live - {datetime.now().strftime('%Y-%m-%d %H-%M-%S')}{get_default_video_format()}"
    if os.name != 'nt':
        output_filename = quote_filename(output_filename)
    
    output_path = os.path.normpath(os.path.join(get_default_directory(), output_filename))
    handle_file_already_exists(output_path)
    
    yt_dlp_bin = get_yt_dlp_path()
    command = [yt_dlp_bin, twitch_url, "-o", output_path]
    
    if from_start:
        command.insert(1, "--live-from-start")
    
    custom_options = get_yt_dlp_custom_options()
    if custom_options:
        command.extend(custom_options)
    
    print("\nCommand: " + " ".join(command) + "\n")
    
    try:
        subprocess.run(command, check=True)
        print(f"\n\033[92m✓ Live recording saved to {output_path}\033[0m\n")
        input("Press Enter to continue...")
        return True
    except Exception:
        return handle_live_recording_fallback(channel_name, command, output_path)


def wait_and_record_stream(twitch_url=None):
    if not twitch_url:
        twitch_url = print_get_twitch_url_or_name_menu()
    channel_name = get_twitch_channel_from_url(twitch_url)

    output_filename = f"{channel_name} - Live - {datetime.now().strftime('%Y-%m-%d %H-%M-%S')}{get_default_video_format()}"
    if os.name != 'nt':
        output_filename = quote_filename(output_filename)

    output_path = os.path.normpath(os.path.join(get_default_directory(), output_filename))
    handle_file_already_exists(output_path)

    yt_dlp_bin = get_yt_dlp_path()
    command = [yt_dlp_bin, "--wait-for-video", "30", twitch_url, "-o", output_path]

    custom_options = get_yt_dlp_custom_options()
    if custom_options:
        command.extend(custom_options)

    print("\nCommand: " + " ".join(command) + "\n")
    try:
        subprocess.run(command, check=True)
        print(f"\n\033[92m✓ Recording saved to {output_path}\033[0m\n")
        input("Press Enter to continue...")
        return True
    except Exception as e:
        print(f"\n\033[91m✖ Failed to record: {e}\033[0m\n")
        return False


def record_live_menu(twitch_url=None):
    print("\n1) Record Stream\n2) Wait and record when stream starts\n3) Return")
    while True:
        choice = input("\nChoose an option: ").strip()
        if choice == "1":
            return record_live_from_start(twitch_url)
        if choice == "2":
            return wait_and_record_stream(twitch_url)
        if choice == "3":
            return
        print("\n✖  Invalid option! Please Try Again.")


def record_live_cli(twitch_url, from_start=False):
    channel_name = get_twitch_channel_from_url(twitch_url)

    output_filename = f"{channel_name} - Live - {datetime.now().strftime('%Y-%m-%d %H-%M-%S')}{get_default_video_format()}"
    if os.name != 'nt':
        output_filename = quote_filename(output_filename)

    output_path = os.path.normpath(os.path.join(get_default_directory(), output_filename))
    handle_file_already_exists(output_path)

    yt_dlp_bin = get_yt_dlp_path()
    command = [yt_dlp_bin, twitch_url, "-o", output_path]

    if from_start:
        command.insert(1, "--live-from-start")

    custom_options = get_yt_dlp_custom_options()
    if custom_options:
        command.extend(custom_options)

    print("\nCommand: " + " ".join(command) + "\n")

    try:
        subprocess.run(command, check=True)
        print(f"\n\033[92m Live recording saved to {output_path}\033[0m\n")
    except Exception as exc:
        raise SystemExit(f"Error: Live recording failed ({exc}).") from exc


def get_VLC_Location():
    try:
        vlc_location = read_config_by_key("settings", "VLC_LOCATION")
        if vlc_location and os.path.isfile(vlc_location):
            return vlc_location

        possible_locations = (
            [f"{chr(i)}:/Program Files/VideoLAN/VLC/vlc.exe" for i in range(65, 91)] + [
             f"{chr(i)}:/Program Files (x86)/VideoLAN/VLC/vlc.exe" for i in range(65, 91)]
            + [
                "/Applications/VLC.app/Contents/MacOS/VLC",  # macOS default
                # Linux locations
                "/usr/bin/vlc",  
                "/usr/local/bin/vlc",
                # Extra locations of other players
                "C:/Program Files/MPC-HC/mpc-hc64.exe",
                "C:/Program Files (x86)/MPC-HC/mpc-hc.exe",
                "C:/Program Files/mpv/mpv.exe",
                "/usr/bin/mpv",
                "/usr/local/bin/mpv",
                "/Applications/mpv.app/Contents/MacOS/mpv"
            ]
        )

        for location in possible_locations:
            if os.path.isfile(location):
                script_dir = get_script_directory()
                config_file_path = os.path.join(script_dir, "config", "settings.json")
                try:
                    with open(config_file_path, "r", encoding="utf-8") as config_file:
                        config_data = json.load(config_file)

                    config_data["VLC_LOCATION"] = location
                    with open(config_file_path, "w", encoding="utf-8") as config_file:
                        json.dump(config_data, config_file, indent=4)
                except (FileNotFoundError, json.JSONDecodeError) as error:
                    print(f"Error: {error}")
                return location

        return None
    except Exception:
        return None


def handle_vod_url_normal(m3u8_source, title=None, stream_date=None):
    is_file = os.path.isfile(m3u8_source)

    if is_file:
        vod_filename = get_filename_for_file_source(m3u8_source, title=title, stream_date=stream_date)

        success = download_m3u8_video_file(m3u8_source, vod_filename)
        if not success:
            print(f"\n\033[91m\u2717 Failed to download Vod: {vod_filename}\033[0m\n")
            return False
        os.remove(m3u8_source)
    else:
        vod_filename = get_filename_for_url_source(m3u8_source, title=title, stream_date=stream_date)

        success = download_m3u8_video_url(m3u8_source, vod_filename)
        if not success:
            print(f"\n\033[91m\u2717 Failed to download Vod: {vod_filename}\033[0m\n")
            return False

    print(f"\n\033[92m\u2713 Vod downloaded to {os.path.join(get_default_directory(), vod_filename)}\033[0m\n")
    return True


def format_date(date_string):
    try:
        return datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
    except ValueError:
        return None


def get_filename_for_file_source(m3u8_source, title, stream_date):
    streamer_name, video_id = parse_vod_filename(m3u8_source)
    formatted_date = format_date(stream_date) if stream_date else None

    filename_parts = [streamer_name]

    if formatted_date:
        filename_parts.append(formatted_date)

    if title:
        filename_parts.append(sanitize_filename(title))

    filename_parts.append(f"[{video_id}]")
    filename = " - ".join(filename_parts) + get_default_video_format()

    return filename


def get_filename_for_url_source(m3u8_source, title, stream_date):
    streamer = parse_streamer_from_m3u8_link(m3u8_source)
    vod_id = parse_video_id_from_m3u8_link(m3u8_source)
    formatted_date = format_date(stream_date) if stream_date else None

    filename_parts = [streamer]

    if formatted_date:
        filename_parts.append(formatted_date)

    if title:
        filename_parts.append(sanitize_filename(title))

    filename_parts.append(f"[{vod_id}]")
    filename = " - ".join(filename_parts) + get_default_video_format()

    return filename


def handle_vod_url_trim(m3u8_source, title=None, stream_date=None, start_time=None, end_time=None):
    vod_start_time = start_time or get_time_input_HH_MM_SS("Enter start time (HH:MM:SS): ")
    vod_end_time = end_time or get_time_input_HH_MM_SS("Enter end time (HH:MM:SS): ")

    raw_start_time = vod_start_time.replace(":", ".")
    raw_end_time = vod_end_time.replace(":", ".")

    is_file = os.path.isfile(m3u8_source)
    if is_file:
        vod_filename = get_filename_for_file_trim(m3u8_source, title, stream_date, raw_start_time, raw_end_time)
        success = download_m3u8_video_file_slice(m3u8_source, vod_filename, vod_start_time, vod_end_time)
        if not success:
            print(f"\n\033[91m\u2717 Failed to download Vod: {vod_filename}\033[0m\n")
            return False

        if os.path.isfile(m3u8_source):
            os.remove(m3u8_source)
    else:
        vod_filename = get_filename_for_url_trim(m3u8_source, title, stream_date, raw_start_time, raw_end_time)
        success = download_m3u8_video_url_slice(m3u8_source, vod_filename, vod_start_time, vod_end_time)
        if not success:
            print(f"\n\033[91m\u2717 Failed to download Vod: {vod_filename}\033[0m\n")
            return False

    print(f"\n\033[92m\u2713 Vod downloaded to {os.path.join(get_default_directory(), vod_filename)}\033[0m\n")
    return True


def get_filename_for_file_trim(m3u8_source, title, stream_date, raw_start_time, raw_end_time):
    streamer_name, video_id = parse_vod_filename(m3u8_source)
    formatted_date = format_date(stream_date) if stream_date else None

    filename_parts = [streamer_name]

    if formatted_date:
        filename_parts.append(formatted_date)

    if title:
        filename_parts.append(sanitize_filename(title))

    filename_parts.append(f"[{video_id}]")
    filename_parts.extend([raw_start_time, raw_end_time])

    filename = " - ".join(filename_parts) + get_default_video_format()

    return filename


def get_filename_for_url_trim(m3u8_source, title, stream_date, raw_start_time, raw_end_time):
    streamer = parse_streamer_from_m3u8_link(m3u8_source)
    vod_id = parse_video_id_from_m3u8_link(m3u8_source)
    formatted_date = format_date(stream_date) if stream_date else None

    filename_parts = [streamer]

    if formatted_date:
        filename_parts.append(formatted_date)

    if title:
        filename_parts.append(sanitize_filename(title))

    filename_parts.append(f"[{vod_id}]")
    filename_parts.extend([raw_start_time, raw_end_time])
    filename = " - ".join(filename_parts) + get_default_video_format()

    return filename


def get_time_input_HH_MM_SS(prompt):
    while True:
        time_input = input(prompt).strip().replace("'", "").replace('"', "")
        if re.match(r"^(\d+):([0-5]\d):([0-5]\d)$", time_input):
            return time_input

        print("\nInvalid input format! Please enter the time in HH:MM:SS format.\n")


def get_time_input_HH_MM(prompt):
    while True:
        time_input = input(prompt).strip().replace("'", "").replace('"', "")

        if re.match(r"^(\d+):([0-5]\d)$", time_input):
            return time_input

        print("\nInvalid input format! Please enter the time in HH:MM format.\n")


def get_time_input_YYYY_MM_DD_HH_MM_SS(prompt):
    while True:
        time_input = input(prompt).strip().replace("'", "").replace('"', "")

        if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", time_input):
            return time_input

        print("\nInvalid input format! Please enter the time in YYYY-MM-DD HH:MM:SS format.\n")


def handle_download_menu(link, title=None, stream_datetime=None):
    vlc_location = get_VLC_Location()
    exit_option = 3 if not vlc_location else 4

    while True:
        start_download = print_confirm_download_menu()
        if start_download == 1:
            handle_vod_url_normal(link, title, stream_datetime)
            input("Press Enter to continue...")
            return_to_main_menu()
        elif start_download == 2:
            handle_vod_url_trim(link, title, stream_datetime)
            input("Press Enter to continue...")
            return_to_main_menu()
        elif start_download == 3 and vlc_location:
            if os.path.isfile(link):
                link = link.replace("/", "\\") if os.name == "nt" else link

            if sys.platform.startswith("darwin"):
                subprocess.Popen(["open", "-a", vlc_location, link])
            elif os.name == "posix":
                subprocess.Popen([vlc_location, link])
            else:
                subprocess.Popen([vlc_location, link])
        elif start_download == exit_option:
            return_to_main_menu()
        else:
            print("\n✖  Invalid option! Please Try Again.\n")


def play_m3u8_with_vlc(m3u8_source):
    vlc_location = get_VLC_Location()
    if not vlc_location:
        raise SystemExit("Error: VLC player not found. Configure VLC_LOCATION in settings.json.")

    playable_path = m3u8_source
    if os.path.isfile(playable_path) and os.name == "nt":
        playable_path = playable_path.replace("/", "\\")

    try:
        if sys.platform.startswith("darwin"):
            subprocess.Popen(["open", "-a", vlc_location, playable_path])
        elif os.name == "posix":
            subprocess.Popen([vlc_location, playable_path])
        else:
            subprocess.Popen([vlc_location, playable_path])
    except Exception as exc:
        raise SystemExit(f"Error: Unable to launch VLC ({exc}).")
    return True


def get_datetime_from_m3u8(m3u8_file):
    try:
        date = None
        total_seconds = 0
        date_pattern = re.compile(r"#ID3-EQUIV-TDTG:(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")

        with open(m3u8_file, "r", encoding="utf-8") as f:
            for line in f:
                date_match = date_pattern.match(line)
                if date_match:
                    date = date_match.group(1)
                if line.startswith("#EXT-X-TWITCH-TOTAL-SECS:"):
                    total_seconds = int(float(line.split(":")[-1].strip()))
        if date is not None:
            date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")
            adjusted_date = date - timedelta(seconds=total_seconds)
            adjusted_date_str = adjusted_date.strftime("%Y-%m-%d")
            return adjusted_date_str
    except Exception:
        pass


def handle_file_download_menu(m3u8_file_path):
    stream_date = get_datetime_from_m3u8(m3u8_file_path)

    vlc_location = get_VLC_Location()
    exit_option = 3 if not vlc_location else 4

    while True:
        start_download = print_confirm_download_menu()
        if start_download == 1:

            streamer_name, video_id = parse_vod_filename(m3u8_file_path)
            if stream_date:
                output_filename = f"{streamer_name} - {stream_date} - [{video_id}]{get_default_video_format()}"
            else:
                output_filename = (f"{streamer_name} - [{video_id}]{get_default_video_format()}")

            success = download_m3u8_video_file(m3u8_file_path, output_filename)
            if not success:
                return print(f"\n\033[91m\u2717 Failed to download Vod: {output_filename}\033[0m\n")

            print(f"\n\033[92m\u2713 Vod downloaded to {os.path.join(get_default_directory(), output_filename)}\033[0m\n")
            break

        elif start_download == 2:
            vod_start_time = get_time_input_HH_MM_SS("Enter start time (HH:MM:SS): ")
            vod_end_time = get_time_input_HH_MM_SS("Enter end time (HH:MM:SS): ")

            raw_start_time = vod_start_time.replace(":", ".")
            raw_end_time = vod_end_time.replace(":", ".")

            streamer_name, video_id = parse_vod_filename(m3u8_file_path)
            if stream_date:
                vod_filename = f"{streamer_name} - {stream_date} - [{video_id}] - {raw_start_time} - {raw_end_time}{get_default_video_format()}"
            else:
                vod_filename = f"{streamer_name} - [{video_id}] - {raw_start_time} - {raw_end_time}{get_default_video_format()}"

            success = download_m3u8_video_file_slice(m3u8_file_path, vod_filename, vod_start_time, vod_end_time)
            if not success:
                return print(f"\n\033[91m\u2717 Failed to download Vod: {vod_filename}\033[0m\n")

            print(f"\n\033[92m\u2713 Vod downloaded to {os.path.join(get_default_directory(), vod_filename)}\033[0m\n")
            break

        elif start_download == 3 and vlc_location:
            if os.path.isfile(m3u8_file_path):
                m3u8_file_path = m3u8_file_path.replace("/", "\\") if os.name == "nt" else m3u8_file_path

            if sys.platform.startswith("darwin"):
                subprocess.Popen(["open", "-a", vlc_location, m3u8_file_path])
            elif os.name == "posix":
                subprocess.Popen([vlc_location, m3u8_file_path])
            else:
                subprocess.Popen([vlc_location, m3u8_file_path])
        elif start_download == exit_option:
            return_to_main_menu()
        else:
            print("\n✖  Invalid option! Please Try Again.\n")


def print_confirm_download_menu():
    vlc_location = get_VLC_Location()
    menu_options = ["1) Start Downloading", "2) Trim and Download"]
    if vlc_location:
        menu_options.append("3) Play with VLC")
    menu_options.append(f"{3 if not vlc_location else 4}) Return")

    print("\n".join(menu_options))
    try:
        return int(input("\nChoose an option: "))
    except ValueError:
        print("\n✖  Invalid option! Please Try Again.\n")
        return print_confirm_download_menu()


def extract_id_from_url(url: str):
    pattern1 = r"twitch\.tv/(?:[^\/]+/)?(\d+)"
    pattern2 = r"twitch\.tv/.+?/video/(\d+)"

    match = re.search(pattern1, url) or re.search(pattern2, url)
    if match:
        return match.group(1)

    if CLI_MODE:
        raise SystemExit("Error: Invalid Twitch VOD or Highlight URL.")
    print("\n✖  Invalid Twitch VOD or Highlight URL! Please Try Again.\n")
    url = print_get_twitch_url_menu()
    return extract_id_from_url(url)


def fetch_twitch_data(vod_id, retries=3, delay=5):
    attempt = 0
    while attempt < retries:
        try:
            res = requests.post(
                "https://gql.twitch.tv/gql",
                json={
                    "query": f'query {{ video(id: "{vod_id}") {{ title, broadcastType, createdAt, seekPreviewsURL, owner {{ login }} }} }}'
                },
                headers={
                    "Client-Id": "ue6666qo983tsx6so1t0vnawi233wa",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            if res.status_code == 200:
                return res.json()
        except Exception:
            pass

        attempt += 1
        time.sleep(delay)

    return None


def get_vod_or_highlight_url(vod_id):
    print(f"\nSearching URL for Vod {vod_id}...")
    url = f"https://usher.ttvnw.net/vod/{vod_id}.m3u8"
    response = requests.get(url, timeout=30)
    if response.status_code != 200:
        data = fetch_twitch_data(vod_id)
        vod_data = data["data"]["video"]

        if data is None or vod_data is None:
            return None, None, None

        current_url = urlparse(vod_data["seekPreviewsURL"])

        domain = current_url.netloc
        paths = current_url.path.split("/")
        vod_special_id = paths[paths.index([i for i in paths if "storyboards" in i][0]) - 1]
        old_vods_date = datetime.strptime("2023-02-10", "%Y-%m-%d")
        created_date = datetime.strptime(vod_data["createdAt"], "%Y-%m-%dT%H:%M:%SZ")

        time_diff = (old_vods_date - created_date).total_seconds()
        days_diff = time_diff / (60 * 60 * 24)

        broadcast_type = vod_data["broadcastType"].lower()

        url = None
        if broadcast_type == "highlight":
            url = f"https://{domain}/{vod_special_id}/chunked/highlight-{vod_id}.m3u8"
        elif broadcast_type == "upload" and days_diff > 7:
            url = f"https://{domain}/{vod_data['owner']['login']}/{vod_id}/{vod_special_id}/chunked/index-dvr.m3u8"
        else:
            url = f"https://{domain}/{vod_special_id}/chunked/index-dvr.m3u8"

        if url is not None:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                return url, vod_data["title"], vod_data["createdAt"]
    return response.url, None, None


def twitch_recover(link=None):
    url = link if link else print_get_twitch_url_menu()

    if is_twitch_livestream_url(url):
        if CLI_MODE:
            return record_live_cli(url, CLI_DOWNLOAD_FROM_START)
        return record_live_menu(url)
    
    vod_id = extract_id_from_url(url)
    url, title, stream_datetime = get_vod_or_highlight_url(vod_id)

    if url is None:
        print("\n✖  Unable to find it! Try using one of the other websites.\n")
        input("Press Enter to continue...")
        return_to_main_menu()

    try:
        format_datetime = datetime.strptime(stream_datetime, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        format_datetime = None

    m3u8_url = return_supported_qualities(url)
    print(f"\n\033[92m\u2713 Found URL: {m3u8_url}\n\033[0m")

    m3u8_source = process_m3u8_configuration(m3u8_url, skip_check=True)
    return handle_download_menu(m3u8_source, title=title, stream_datetime=format_datetime)


def get_twitch_clip(clip_slug, retries=3):
    url_endpoint = "https://gql.twitch.tv/gql"
    data = [
        {
            "operationName": "ShareClipRenderStatus",
            "variables": {
                "slug": clip_slug,
            },
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "1844261bb449fa51e6167040311da4a7a5f1c34fe71c71a3e0c4f551bc30c698",
                }
            },
        }
    ]
    headers = {"Client-Id": "ue6666qo983tsx6so1t0vnawi233wa"}
    
    for attempt in range(retries):
        try:
            response_endpoint = requests.post(url_endpoint, json=data, headers=headers, timeout=30)
            response_endpoint.raise_for_status()
            response = response_endpoint.json()

            if "error" in response or "errors" in response:
                raise ValueError(response.get("message", "Unable to get clip!"))

            playback_access_token = response[0]["data"]["clip"]["playbackAccessToken"]
            url = (
                response[0]["data"]["clip"]["videoQualities"][0]["sourceURL"]
                + "?sig=" + playback_access_token["signature"]
                + "&token=" + requests.utils.quote(playback_access_token["value"])
            )
            return url

        except (requests.exceptions.RequestException, ValueError):
            print("\nRetrying...")
            if attempt < retries - 1:
                time.sleep(3) 

    print("\n✖  Unable to get clip! Check the URL and try again.\n")
    if CLI_MODE:
        raise RuntimeError("Unable to get clip")
    input("Press Enter to continue...")
    return_to_main_menu()


def twitch_clip_downloader(clip_url, slug, streamer):
    print("\nDownloading Clip...")
    try:
        response = requests.get(clip_url, stream=True, timeout=30)
        if response.status_code != 200:
            raise Exception("Unable to download clip!")
        download_location = os.path.join(get_default_directory(), f"{streamer}-{slug}{get_default_video_format()}")

        with open(os.path.join(download_location), "wb") as file:
            shutil.copyfileobj(response.raw, file)

        print(f"\n\033[92m\u2713 Clip downloaded to {download_location}\033[0m\n")

        if not CLI_MODE:
            input("Press Enter to continue...")
        return True
    except Exception:
        raise Exception("Unable to download clip!")


def handle_twitch_clip(clip_url):
    streamer, slug = extract_slug_and_streamer_from_clip_url(clip_url)
    url = get_twitch_clip(slug)
    return twitch_clip_downloader(url, slug, streamer)


def _validate_cli_time(value, label):
    if value and not re.match(r"^\d{2}:\d{2}:\d{2}$", value):
        raise SystemExit(f"Error: {label} must be in HH:MM:SS format.")


def download_url_cli(args):
    global CLI_DOWNLOAD_FROM_START
    url = (args.url or "").strip()
    if not url:
        raise SystemExit("Error: --url requires a valid URL.")

    if args.clip_url:
        raise SystemExit("Error: --url cannot be combined with --clip.")

    start_time = args.start_time.strip() if args.start_time else None
    end_time = args.end_time.strip() if args.end_time else None
    watch_mode = bool(getattr(args, "watch", False))
    from_start_flag = bool(getattr(args, "from_start", False))

    if (start_time and not end_time) or (end_time and not start_time):
        raise SystemExit("Error: --start and --end must be provided together.")

    if watch_mode and (start_time or end_time):
        raise SystemExit("Error: --watch cannot be combined with --start/--end.")

    _validate_cli_time(start_time, "--start")
    _validate_cli_time(end_time, "--end")

    if not url.startswith("https://"):
        url = "https://" + url

    try:
        title = None
        stream_datetime = None
        m3u8_source = None

        if "streamscharts" in url:
            m3u8_source, stream_datetime = handle_vod_recover(url, parse_streamscharts_url, parse_datetime_streamscharts, "Streamscharts")
        elif "twitchtracker" in url:
            m3u8_source, stream_datetime = handle_vod_recover(url, parse_twitchtracker_url, parse_datetime_twitchtracker, "Twitchtracker")
        elif "sullygnome" in url:
            new_tracker_url = re.sub(r"/\d+/", "/", url)
            m3u8_source, stream_datetime = handle_vod_recover(new_tracker_url, parse_sullygnome_url, parse_datetime_sullygnome, "Sullygnome")
        elif "twitch.tv" in url:
            if is_twitch_livestream_url(url):
                record_live_cli(url, from_start_flag)
                return

            vod_id = extract_id_from_url(url)
            if not vod_id:
                raise SystemExit("Error: Unable to parse VOD ID from URL.")

            resolved_url, title, stream_datetime_iso = get_vod_or_highlight_url(vod_id)
            if not resolved_url:
                raise SystemExit("Error: Unable to resolve VOD URL.")

            m3u8_url = return_supported_qualities(resolved_url)
            if not m3u8_url:
                raise SystemExit("Error: Unable to determine playable quality.")

            m3u8_source = process_m3u8_configuration(m3u8_url, skip_check=True)
            if stream_datetime_iso:
                try:
                    stream_datetime = datetime.strptime(stream_datetime_iso, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    stream_datetime = None
        else:
            raise SystemExit("Error: URL not supported. Please provide a Twitch/TwitchTracker/Streamscharts/SullyGnome URL.")

        if not m3u8_source:
            raise SystemExit("Error: Unable to prepare download source.")

        if watch_mode:
            play_m3u8_with_vlc(m3u8_source)
            return

        if start_time and end_time:
            previous_flag = CLI_DOWNLOAD_FROM_START
            CLI_DOWNLOAD_FROM_START = from_start_flag
            try:
                success = handle_vod_url_trim(m3u8_source, title=title, stream_date=stream_datetime, start_time=start_time, end_time=end_time)
            finally:
                CLI_DOWNLOAD_FROM_START = previous_flag
        else:
            previous_flag = CLI_DOWNLOAD_FROM_START
            CLI_DOWNLOAD_FROM_START = from_start_flag
            try:
                success = handle_vod_url_normal(m3u8_source, title=title, stream_date=stream_datetime)
            finally:
                CLI_DOWNLOAD_FROM_START = previous_flag

        if not success:
            raise SystemExit("Error: Download failed.")

    except ReturnToMain:
        raise SystemExit("Error: Unable to process URL.")


def download_m3u8_cli(args):

    m3u8_url = (getattr(args, "m3u8", None) or "").strip()
    if not m3u8_url:
        raise SystemExit("Error: --m3u8 requires a valid M3U8 URL.")

    if args.url or args.clip_url:
        raise SystemExit("Error: --m3u8 cannot be combined with --url or --clip.")

    start_time = args.start_time.strip() if args.start_time else None
    end_time = args.end_time.strip() if args.end_time else None
    watch_mode = bool(getattr(args, "watch", False))

    if (start_time and not end_time) or (end_time and not start_time):
        raise SystemExit("Error: --start and --end must be provided together.")

    if watch_mode and (start_time or end_time):
        raise SystemExit("Error: --watch cannot be combined with --start/--end.")

    _validate_cli_time(start_time, "--start")
    _validate_cli_time(end_time, "--end")

    if not (m3u8_url.startswith("http://") or m3u8_url.startswith("https://")):
        m3u8_url = "https://" + m3u8_url

    print("Processing URL...")
    m3u8_source = process_m3u8_configuration(m3u8_url)
    if not m3u8_source:
        raise SystemExit("Error: Unable to prepare M3U8 source.")

    if watch_mode:
        play_m3u8_with_vlc(m3u8_source)
        return

    title = None
    stream_datetime = None

    if start_time and end_time:
        success = handle_vod_url_trim(m3u8_source, title=title, stream_date=stream_datetime, start_time=start_time, end_time=end_time)
    else:
        success = handle_vod_url_normal(m3u8_source, title=title, stream_date=stream_datetime)

    if not success:
        raise SystemExit("Error: Download failed.")


def fetch_stream_data(channel_name: str, vod_id: str = None):
    try:
        if vod_id:
            query = """
                query($login:String!, $videoId:ID){
                user(login:$login){
                    lastBroadcast{ id startedAt }
                    stream{ id createdAt }
                    videos(first:100){ edges{ node{ id createdAt publishedAt title previewThumbnailURL animatedPreviewURL} } }
                }
                video(id:$videoId){ id createdAt}
                }
            """
            variables = {"login": channel_name, "videoId": vod_id}
        else:
            query = (
                "query($login:String!){\n"
                "  user(login:$login){\n"
                "    lastBroadcast{ id startedAt }\n"
                "    stream{ id createdAt }\n"
                "    videos(first:5){ edges{ node{ id createdAt publishedAt title previewThumbnailURL animatedPreviewURL } } }\n"
                "  }\n"
                "}"
            )
            variables = {"login": channel_name}

        payload = {"query": query, "variables": variables}

        res = requests.post(
            "https://gql.twitch.tv/gql",
            json=payload,
            headers={
                "Client-ID": "ue6666qo983tsx6so1t0vnawi233wa",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0",
            },
            timeout=30,
        )
        if res.status_code != 200:
            return None, None, None

        data = (res.json() or {}).get("data") or {}

        user = data.get("user") or {}
        last_broadcast = user.get("lastBroadcast") or {}
        current_stream = user.get("stream") or {}
        latest_videos_edges = ((user.get("videos") or {}).get("edges") or [])
        targeted_video = data.get("video") or {}

        last_broadcast_id = last_broadcast.get("id")
        last_broadcast_started_at = last_broadcast.get("startedAt")
        stream_id = current_stream.get("id")
        stream_created_at = current_stream.get("createdAt")
        # latest_vod_node = latest_videos_edges[0].get("node") if latest_videos_edges else {}


        if vod_id:
            # 1) Direct VOD Id lookup
            if (targeted_video.get("id") or None) == vod_id:
                return vod_id, targeted_video.get("createdAt"), targeted_video.get("publishedAt")
            # 2) Live stream Id match
            if stream_id and str(stream_id) == str(vod_id):
                return vod_id, stream_created_at, stream_created_at
            # 3) Search among recent videos
            for edge in latest_videos_edges:
                vod_node = (edge or {}).get("node") or {}
                if (vod_node.get("id") or None) == vod_id:
                    return vod_id, vod_node.get("createdAt"), vod_node.get("publishedAt")
                
                preview_url = vod_node.get("previewThumbnailURL") or ""
                animated_url = vod_node.get("animatedPreviewURL") or ""
                if (preview_url and vod_id in preview_url) or (animated_url and vod_id in animated_url):
                    return vod_node.get("id"), vod_node.get("createdAt"), vod_node.get("publishedAt")

            return None, None, None


        if stream_id and stream_created_at:
            return stream_id, stream_created_at, None
        if last_broadcast_id and last_broadcast_started_at:
            return last_broadcast_id, None, last_broadcast_started_at
        
        return None, None, None
    except Exception as e:
        print(f"Error fetching stream data: {e}")
        return None, None, None


def get_stream_datetime(url: str):
    try:    
        channel_name = None
        vod_id = None
        if "twitchtracker.com" not in url:
            converted_url = convert_url(url, "twitchtracker")
        else:
            converted_url = url

        url_match = re.search(r"twitchtracker\.com/([^/\s]+)/streams(?:/(\d+))?", converted_url, re.IGNORECASE)
        if url_match:
            channel_name = url_match.group(1)
            vod_id = url_match.group(2) if url_match.lastindex and url_match.lastindex >= 2 else None

        if not channel_name:
            return None, None

        broadcast_id, created_at_iso, started_at_iso = fetch_stream_data(channel_name, vod_id)
        
        if not broadcast_id and not created_at_iso:
            return None, None

        datetime_iso = created_at_iso or started_at_iso
        if datetime_iso:
            formatted = format_iso_datetime(datetime_iso)
            return formatted, None

        return None, None
    except Exception as e:
        print(f"Error fetching stream data: {e}")
        return None, None

def run_vod_recover():
    print("\nWELCOME TO VOD RECOVERY!")
    
    menu = 0
    while menu < 50:
        print()
        menu = print_main_menu()
        try:
            if menu == 1:
                vod_mode = print_video_mode_menu()
                if vod_mode == 1:
                    link, stream_datetime = website_vod_recover()
                    handle_download_menu(link, stream_datetime=stream_datetime)
                elif vod_mode == 2:
                    manual_vod_recover()
                elif vod_mode == 3:
                    bulk_vod_recovery()
                elif vod_mode == 4:
                    continue
            elif menu == 2:
                clip_type = print_clip_type_menu()
                if clip_type == 1:
                    clip_recovery_method = print_clip_recovery_menu()
                    if clip_recovery_method == 1:
                        website_clip_recover()
                    elif clip_recovery_method == 2:
                        manual_clip_recover()
                    elif clip_recovery_method == 3:
                        continue
                elif clip_type == 2:
                    video_id, hour, minute = get_random_clip_information()
                    random_clip_recovery(video_id, hour, minute)
                elif clip_type == 3:
                    clip_url = print_get_twitch_clip_url_menu()
                    handle_twitch_clip(clip_url)
                elif clip_type == 4:
                    bulk_clip_recovery()
                elif clip_type == 5:
                    continue
            elif menu == 3:
                download_type = print_download_type_menu()
                if download_type == 1:
                    vod_url = print_get_m3u8_link_menu()
                    print()
                    m3u8_source = process_m3u8_configuration(vod_url)
                    handle_download_menu(m3u8_source)
                elif download_type == 2:
                    file_path = get_m3u8_file_dialog()
                    if not file_path:
                        print("\nNo file selected! Returning to main menu.")
                        continue
                    print(f"\n{file_path}\n")
                    m3u8_file_path = file_path.strip()

                    handle_file_download_menu(m3u8_file_path)
                    input("Press Enter to continue...")

                elif download_type == 3:
                    twitch_recover()

                elif download_type == 4:
                    continue
            elif menu == 4:
                record_live_menu()
            elif menu == 5:
                get_latest_streams()
            elif menu == 6:
                mode = print_handle_m3u8_availability_menu()
                if mode == 1:
                    url = print_get_m3u8_link_menu()
                    is_muted = is_video_muted(url)
                    if is_muted:
                        print("\nVideo contains muted/invalid segments")
                        if get_yes_no_choice("Do you want to unmute the video so it can be played in media players?"):
                            print()
                            unmute_vod(url)
                            input("Press Enter to continue...")
                        else:
                            print("\nReturning to main menu...")
                            continue
                    else:
                        print("\n\033[92mVideo is not muted! \033[0m")
                elif mode == 2:
                    url = print_get_m3u8_link_menu()
                    mark_invalid_segments_in_playlist(url)
                elif mode == 3:
                    url = print_get_m3u8_link_menu()
                    unmute_vod(url)
                    print(f'File saved to "{get_default_directory()}"')
                    input("\nPress Enter to continue...")
                elif mode == 4:
                    continue
            elif menu == 7:
                while True:
                    print()
                    options_choice = print_options_menu()
                    if options_choice == 1:
                        set_default_video_format()
                    elif options_choice == 2:
                        set_default_directory()
                    elif options_choice == 3:
                        set_default_downloader()
                    elif options_choice == 4:
                        check_for_updates()
                    elif options_choice == 5:
                        update_yt_dlp()
                    elif options_choice == 6:
                        script_dir = get_script_directory()
                        config_file_path = os.path.join(script_dir, "config", "settings.json")
                        if os.path.exists(config_file_path):
                            print(f"Opening {config_file_path}...")
                            open_file(config_file_path)
                            input("\nPress Enter to continue...")
                        else:
                            print("File not found!")
                    elif options_choice == 7:
                        print_help()
                        input("Press Enter to continue...")
                    elif options_choice == 8:
                        break
            elif menu == 8:
                print("\nExiting...\n")
                sys.exit()
            else:
                continue
        except ReturnToMain:
            continue


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VodRecovery CLI")
    parser.add_argument("--url", dest="url", help="Download VOD from Twitch/TwitchTracker/Streamscharts/SullyGnome URL")
    parser.add_argument("--m3u8", dest="m3u8", help="Download VOD directly from an M3U8 URL")
    parser.add_argument("--clip", dest="clip_url", help="Download Twitch clip by URL")
    parser.add_argument("--start", dest="start_time", help="Trim start time HH:MM:SS for VOD download")
    parser.add_argument("--end", dest="end_time", help="Trim end time HH:MM:SS for VOD download")
    parser.add_argument("--watch", dest="watch", action="store_true", help="Open the stream in VLC instead of downloading")
    parser.add_argument("--from-start", dest="from_start", action="store_true", help="Attempt to record live channel from the beginning")

    args = parser.parse_args()

    if any([args.url, args.clip_url, getattr(args, "m3u8", None)]):
        try:
            CLI_MODE = True
            if args.clip_url:
                handle_twitch_clip(args.clip_url)
            elif getattr(args, "m3u8", None):
                download_m3u8_cli(args)
            elif args.url:
                download_url_cli(args)
        except KeyboardInterrupt:
            print("\n\nExiting...")
            os._exit(0)
    else:
        try:
            run_vod_recover()
        except KeyboardInterrupt:
            print("\n\nExiting...")
            os._exit(0)
