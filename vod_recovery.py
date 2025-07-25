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
from time import sleep, time
from shutil import rmtree, copyfileobj
from datetime import datetime, timedelta
from tkinter import filedialog
from urllib.parse import urlparse
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

logging.getLogger('asyncio').setLevel(logging.CRITICAL)
logging.getLogger('aiohttp').setLevel(logging.CRITICAL)

CURRENT_VERSION = "1.3.19"
SUPPORTED_FORMATS = [".mp4", ".mkv", ".mov", ".avi", ".ts"]
RESOLUTIONS = ["chunked", "1440p60", "1440p30", "1080p60", "1080p30", "720p60", "720p30", "480p60", "480p30", "360p60", "360p30", "160p60", "160p30"]

if sys.platform == 'win32':
	asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def read_config_by_key(config_file, key):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(script_dir, "config", f"{config_file}.json")

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
        "4) Search Recent Streams",
        "5) Extra M3U8 Options",
        "6) Options",
        "7) Exit",
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


def print_video_recovery_menu():
    vod_recovery_options = [
        "1) Website Video Recovery",
        "2) Manual Recovery",
        "3) Return",
    ]
    while True:
        print("\n".join(vod_recovery_options))
        try:
            choice = int(input("\nSelect VOD Recovery Method: "))
            if choice not in range(1, len(vod_recovery_options) + 1):
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
                return run_vod_recover()
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
        "3) From Twitch URL (Only for VODs or Highlights still up on Twitch)",
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
        "3) Return",
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
        "5) Open settings.json File",
        "6) Help",
        "7) Return",
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
    m3u8_url = input("Enter M3U8 Link: ").strip(" \"'")
    if m3u8_url.endswith(".m3u8"):
        return m3u8_url
    print("\n✖  Invalid M3U8 link! Please try again:\n")
    return print_get_m3u8_link_menu()


def quote_filename(filename):
    if not filename.startswith("'") and not filename.endswith("'"):
        filename = filename.replace("'", "'\"'\"'")
        filename = f"'{filename}'"
    return filename


def ask_to_redownload(output_path):
    while True:
        choice = input(f"\nFile already exists at {output_path}. Do you want to redownload it? (Y/N): ").strip().lower()
        if choice in ['y', 'n']:
            return choice == 'y'
        print("Invalid input! Please enter 'Y' for Yes or 'N' for No.")


def get_websites_tracker_url():
    while True:
        tracker_url = input("Enter Twitchtracker/Streamscharts/Sullygnome url: ").strip()
        if re.match(r"^(https?:\/\/)?(www\.)?(twitchtracker\.com|streamscharts\.com|sullygnome\.com)\/.*", tracker_url):
            return tracker_url

        print("\n✖  Invalid URL! Please enter a URL from Twitchtracker, Streamscharts, or Sullygnome.\n")


def print_get_twitch_url_menu():
    twitch_url = input("Enter Twitch URL: ").strip(" \"'")
    if "twitch.tv" in twitch_url:
        return twitch_url
    print("\n✖  Invalid Twitch URL! Please try again:\n")
    return print_get_twitch_url_menu()


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
                sleep(3)  
                continue 
            else:
                return None


def get_latest_streams_from_twitchtracker():
    streamer_name = input("\nEnter streamer name: ").strip().lower()
    url = f"https://twitchtracker.com/{streamer_name}/streams"
    
    current_page = 1
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print("\nOpening TwitchTracker with browser...")
            streams = selenium_get_latest_streams_from_twitchtracker(url)

            if not streams:
                if attempt < max_retries - 1:
                    print("Retrying...")
                    continue
                else:
                    print("Unable to get streams from TwitchTracker!")
                    return

            # Show 10 vods per page
            rows_per_page = 10
            total_rows = len(streams)
            total_pages = (total_rows + rows_per_page - 1) // rows_per_page
            
            def display_streams(page_num):
                start_idx = (page_num - 1) * 10
                end_idx = min(start_idx + 10, total_rows)
                rows_to_display = streams[start_idx:end_idx]
                print(f"\nLatest streams for {streamer_name}:")
                print("\n#   Date                Duration    Title")
                print("-" * 80)
                stream_info = []
                valid_streams = []
                for idx, row in enumerate(rows_to_display, start_idx + 1):
                    try:
                        date_utc = row['dt_utc']
                        idx_str = str(idx).ljust(3)
                        date_str = row['dt_local'].ljust(20)
                        duration_str = (str(round(row['duration'], 1)) + " hrs").ljust(10)
                        title = row['title']
                        if len(title) > 75:
                            title = title[:72] + "..."
                        video_id = row['stream_id']
                        stream_info.append((video_id, date_str, date_utc, title))
                        valid_streams.append(idx)
                        print(f"{idx_str} {date_str} {duration_str} {title}")
                    except Exception as e:
                        print(f"\n✖  Error processing stream {idx}: {str(e)}")
                        continue
                return stream_info, valid_streams
            
            stream_info, valid_streams = display_streams(current_page)
            if not stream_info:
                print("\n✖  No valid streams found!")
                if attempt < max_retries - 1:
                    print("Retrying...")
                    continue
                else:
                    print("Max retries reached!")
                    return
            break
        except Exception as e:
            print(f"\n✖  Error occurred: {str(e)}")
            if attempt < max_retries - 1:
                print("Retrying...")
                continue
            else:
                print("Max retries reached!")
                return
    while True:
        print("\nOptions:")
        print("1. Recover specific stream")
        print("2. Recover all streams")
        if current_page < total_pages:
            print("3. Show next 10 streams")
            print("4. Return")
        else:
            print("3. Return")
        choice = input("\nSelect Option: ")
        if choice == "1":
            try:
                stream_num = int(input("\nEnter the number of the stream: "))
                try:
                    list_index = valid_streams.index(stream_num)
                    video_id, date_str, date_utc, title = stream_info[list_index]
                    print(f"\nRecovering VOD: {date_str.strip()} - {title}") 
                    timestamp = datetime.strptime(date_utc, "%Y-%m-%d %H:%M").strftime("%Y-%m-%d %H:%M:%S")  # Use UTC for recovery
                    m3u8_source = vod_recover(streamer_name, video_id, timestamp, url)
                    if m3u8_source:
                        handle_download_menu(m3u8_source, title=title, stream_datetime=timestamp)
                    else:
                        print(f"\n✖  Could not recover VOD {video_id}!")
                except ValueError:
                    print("Invalid stream number. Please try again.")
                    continue
            except ValueError:
                print("Please enter a valid number.")
                continue
            break
        elif choice == "2":
            print("\nRecovering all streams...")
            for video_id, date_str, date_utc, title in stream_info:
                print(f"\nRecovering Video: {date_str} - {title}")  # Show local time
                timestamp = datetime.strptime(date_utc, "%Y-%m-%d %H:%M").strftime("%Y-%m-%d %H:%M:%S")  # Use UTC for recovery
                m3u8_source = vod_recover(streamer_name, video_id, timestamp, url)
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
                break
        elif choice == "4" and current_page == 1:
            break
        else:
            print("\nInvalid option. Please try again.")


def check_for_updates():
    latest_version = version.parse(get_latest_version())
    current_version = version.parse(CURRENT_VERSION)
    if latest_version and current_version:
        if latest_version != current_version:
            print(f"\n\033[34mNew version ({latest_version}) - Download at: https://github.com/MacielG1/VodRecovery/releases/latest\033[0m")
            input("\nPress Enter to continue...")
            return run_vod_recover()
        else:
            print(f"\n\033[92m\u2713 Vod Recovery is updated to {CURRENT_VERSION}!\033[0m")
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
            response = requests.get(m3u8_link, timeout=10)
            response.raise_for_status()

            with open(destination_path, "w", encoding="utf-8") as m3u8_file:
                m3u8_file.write(response.text)

            return m3u8_file

        except Exception:
            attempt += 1
            sleep(1)
    raise Exception(f"Failed to write M3U8 after {max_retries} attempts.")


def read_csv_file(csv_file_path):
    with open(csv_file_path, "r", encoding="utf-8") as csv_file:
        return list(csv.reader(csv_file))

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
    response = requests.get(m3u8_link, timeout=10).text
    return bool("unmuted" in response)


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
        return run_vod_recover()


def parse_twitchtracker_url(twitchtracker_url):
    try:
        streamer_name = twitchtracker_url.split(".com/", 1)[1].split("/streams/")[0]
        video_id = twitchtracker_url.split("/streams/", 1)[1]
        return streamer_name, video_id
    except IndexError:
        print("\033[91m \n✖  Invalid Twitchtracker URL! Please try again:\n \033[0m")
        input("Press Enter to continue...")
        return run_vod_recover()


def parse_sullygnome_url(sullygnome_url):
    try:
        streamer_name = sullygnome_url.split("/channel/", 1)[1].split("/")[0]
        video_id = sullygnome_url.split("/stream/", 1)[1]
        return streamer_name, video_id
    except IndexError:
        print("\033[91m \n✖  Invalid SullyGnome URL! Please try again:\n \033[0m")
        input("Press Enter to continue...")
        return run_vod_recover()


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
            parent=window, initialdir=dir, title="Select A Default Directory"
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
        return run_vod_recover()


def manual_vod_recover():
    while True:
        streamer_name = input("Enter the Streamer Name: ")
        if streamer_name.lower().strip():
            break
        else:
            print("\n✖  No streamer name! Please try again:\n")
        
    while True:
        video_id = input("Enter the Video ID (from: Twitchtracker/Streamscharts/Sullygnome): ")
        if video_id.strip():
            break
        else:
            print("\n✖  No video ID! Please try again:\n")

    timestamp = get_time_input_YYYY_MM_DD_HH_MM_SS("Enter VOD Datetime YYYY-MM-DD HH:MM:SS (24-hour format, UTC): ")

    streamer_name = streamer_name.lower().strip()
    print(f"\nRecovering VOD for {streamer_name} with ID {video_id} at {timestamp}")
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
        input(f"\nNo M3U8 link found from {website_name}! Press Enter to return...")
        return run_vod_recover()

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

    twitch_recover(url)

    print("\n✖  Link not supported! Returning to main menu...")
    return run_vod_recover()


def get_all_clip_urls(clip_format_dict, clip_format_list):
    combined_clip_format_list = []
    for key, value in clip_format_dict.items():
        if key in clip_format_list:
            combined_clip_format_list += value
    return combined_clip_format_list


async def fetch_status(session, url, retries=3, timeout=10):
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    # For m3u8 files, check for the header
                    if url.endswith('.m3u8'):
                        data = await response.text()
                        if data and "#EXTM3U" in data:
                            return url
                    # For TS files, just check status code
                    elif url.endswith('.ts'):
                        return url
                    # For other files, at least check if there's content
                    else:
                        data = await response.read()
                        if data:
                            return url
                return None
        except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionResetError) as e:
            if attempt == retries - 1:
                continue
            await asyncio.sleep(1)
            continue
        except Exception as e:
            if attempt == retries - 1:
                continue
            await asyncio.sleep(1)
            continue
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
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return resolution
        except Exception:
            pass
        return None

    with ThreadPoolExecutor() as executor:
        results = executor.map(check_quality, RESOLUTIONS)

    valid_resolutions = [res for res in results if res]

    if not valid_resolutions:
        return None

    valid_resolutions.sort(key=RESOLUTIONS.index)

    if always_best_quality:
        return m3u8_link.replace(f"/{found_quality}/", f"/{valid_resolutions[0]}/")

    print("\nQuality Options:")
    for idx, resolution in enumerate(valid_resolutions, 1):
        if "chunked" in resolution:
            print(f"{idx}. {resolution.replace('chunked', 'Chunked (Best Quality)')}")
        else:
            print(f"{idx}. {resolution}")
    print()
    user_option = get_user_resolution_choice(m3u8_link, valid_resolutions, found_quality)
    return user_option

def get_user_resolution_choice(m3u8_link, valid_resolutions, found_quality):
    try:
        choice = int(input("Choose a quality: "))
        if 1 <= choice <= len(valid_resolutions):
            quality = valid_resolutions[choice - 1]
            user_option = m3u8_link.replace(f"/{found_quality}/", f"/{quality}/")
            return user_option

        print("\n✖  Invalid option! Please try again:\n")
        return get_user_resolution_choice(m3u8_link, valid_resolutions, found_quality)
    except ValueError:
        print("\n✖  Invalid option! Please try again:\n")
        return get_user_resolution_choice(m3u8_link, valid_resolutions, found_quality)


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
                sb.sleep(3)
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
                    sb.sleep(5)
                    source = sb.cdp.get_page_source()
                    return source
                except Exception as e:
                    print(e)
            finally:
                selenium_cleanup()
    except Exception as e:
        print(e)


def selenium_get_latest_streams_from_twitchtracker(url):
    try:
        check_seleniumbase_version()
        with SB(uc=True) as sb:
            try:
                sb.activate_cdp_mode(url)
                sb.sleep(3)
                sb.uc_gui_click_captcha()
                sb.sleep(5)
            except Exception as e:
                print(e)
            finally:
                selenium_cleanup()

            timezone_offset_hours = 0
            timezone_offset_mins = 0
            try:
                try:
                    offset_minutes = sb.execute_script("return (new Date()).getTimezoneOffset();")
                    offset_hours = -offset_minutes // 60
                    offset_mins = abs(offset_minutes) % 60
                    timezone_offset_hours = offset_hours
                    timezone_offset_mins = offset_mins
                except Exception:
                    try:
                        timezone_text = sb.execute_script("document.querySelector('#timezone-switch > span')?.textContent || null")
                        if timezone_text is not None:
                            timezone_match = re.match(r'UTC([+-]\\d+):?[+-]?(\\d+)?', timezone_text)
                            timezone_offset_hours = int(timezone_match.group(1) if timezone_match else 0)
                            timezone_offset_mins = int(timezone_match.group(2) if timezone_match and timezone_match.group(2) else 0)
                        else:
                            raise ValueError("No timezone text found")
                    except Exception as e2:
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
                data = sb.execute_script("$('#streams').DataTable().data()")
                compl = sb.execute_script("Y.complicator")
                if compl is None or data is None:
                    raise Exception("Could not find stream data with DataTable JS")
                for key in data:
                    if not key.isdigit():
                        continue
                    row = data[key]
                    dt_utc = row[0]['@data-order']
                    dt = datetime.strptime(dt_utc, "%Y-%m-%d %H:%M")
                    dt_local = datetime.strftime(dt + timedelta(hours=timezone_offset_hours, minutes=timezone_offset_mins), "%d/%b/%Y %H:%M")
                    title = row[6]
                    dur_raw = float(row[1]['@data-order'])
                    duration = dur_raw // 60 + (dur_raw % 60 / 60)
                    local_date = datetime.strptime(dt_local, "%d/%b/%Y %H:%M")
                    current_date = datetime.now()
                    old_date = current_date - timedelta(days=60)
                    if local_date < old_date:
                        continue
                    if not dt_utc in compl:
                        continue
                    assist = compl[dt_utc]
                    stream_id = assist['id']
                    stream = {
                        'dt_utc': dt_utc,
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
                            dt_utc = dt_utc_obj.strftime("%Y-%m-%d %H:%M")
                            dt_local = dt_local_obj.strftime("%d/%b/%Y %H:%M")
                        except Exception:
                            dt_utc = row['dt_utc']
                            dt_local = row['dt_local']
                        try:
                            duration = float(row['duration'].split()[0])
                        except Exception:
                            duration = 0
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
            rmtree("downloaded_files")
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


def parse_datetime_streamscharts(streamscharts_url):
    try:
        # Method 1: Using requests
        response = requests.get(
            streamscharts_url, headers=return_user_agent(), timeout=10
        )
        if response.status_code == 200:
            bs = BeautifulSoup(response.content, "html.parser")
            return parse_streamscharts_datetime_data(bs)

        # Method 2: Using Selenium
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


def parse_datetime_twitchtracker(twitchtracker_url):
    try:
        # Method 1: Using requests
        response = requests.get(twitchtracker_url, headers=return_user_agent(), timeout=10)
        if response.status_code == 200:
            bs = BeautifulSoup(response.content, "html.parser")
            return parse_twitchtracker_datetime_data(bs)

        # Method 2: Using Selenium
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


def parse_datetime_sullygnome(sullygnome_url):
    try:
        # Method 1: Using requests
        response = requests.get(sullygnome_url, headers=return_user_agent(), timeout=10)
        if response.status_code == 200:
            bs = BeautifulSoup(response.content, "html.parser")
            return parse_sullygnome_datetime_data(bs)

        # Method 2: Using Selenium
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
        counter = 0
        
        for segment in file_contents:
            if segment.startswith("#"):
                video_file.write(segment)
            else:
                if is_muted:
                    if "-unmuted" in segment:
                        video_file.write(f"{base_link}{counter}-muted.ts\n")
                    else:
                        video_file.write(f"{base_link}{counter}.ts\n")
                else:
                    video_file.write(f"{base_link}{counter}.ts\n")
                counter += 1
        
        video_file.truncate()
    
    if is_muted:
        print(f"{os.path.normpath(video_filepath)} has been unmuted!\n")


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
    ffprobe_command = f"ffprobe -protocol_whitelist file,http,https,tcp,tls,crypto -i {m3u8_source}"
    result = subprocess.run(ffprobe_command, shell=True, check=False, capture_output=True, text=True)
    output = result.stderr
    if "Error" in output:
        # print("Video is not playable after unmuting, using original m3u8 instead\n")
        return False
    else:
        return True
    

def process_m3u8_configuration(m3u8_link, skip_check=False):
    playlist_segments = get_all_playlist_segments(m3u8_link)

    check_segments = read_config_by_key("settings", "CHECK_SEGMENTS") and not skip_check

    m3u8_source = None
    if is_video_muted(m3u8_link):
        print("Video contains muted segments")
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
        os.remove(get_vod_filepath(parse_streamer_from_m3u8_link(m3u8_link), parse_video_id_from_m3u8_link(m3u8_link)))
    if check_segments:
        print("Checking valid segments...")
        asyncio.run(validate_playlist_segments(playlist_segments))
    return m3u8_source


def get_all_playlist_segments(m3u8_link):
    video_file_path = get_vod_filepath(parse_streamer_from_m3u8_link(m3u8_link), parse_video_id_from_m3u8_link(m3u8_link))
    write_m3u8_to_file(m3u8_link, video_file_path)

    segment_list = []
    base_link = m3u8_link.replace("index-dvr.m3u8", "")
    counter = 0
    
    with open(video_file_path, "r+", encoding="utf-8") as video_file:
        file_contents = video_file.readlines()
        video_file.seek(0)
        
        for segment in file_contents:
            if segment.startswith("#"):
                video_file.write(segment)
            else:
                if "-unmuted" in segment:
                    new_segment = f"{base_link}{counter}-muted.ts"
                else:
                    new_segment = f"{base_link}{counter}.ts"
                
                video_file.write(f"{new_segment}\n")
                segment_list.append(new_segment)
                counter += 1
        
        video_file.truncate()
    return segment_list


async def validate_playlist_segments(segments):
    valid_segments = []
    all_segments = [url.strip() for url in segments]
    available_segment_count = 0
    
    batch_size = 200
    
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
                    task = asyncio.create_task(fetch_status(session, url, retries=1, timeout=15))
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
                
                await asyncio.sleep(0.1)
    
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


def vod_recover(streamer_name, video_id, timestamp, tracker_url=None):
    print(f"\nDatetime: {timestamp}")
    try:
        vod_age = calculate_days_since_broadcast(timestamp)

        if vod_age > 60:
            print("Video is older than 60 days. Chances of recovery are very slim.")
        vod_url = None

        if timestamp:

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            vod_url = loop.run_until_complete(get_vod_urls(streamer_name, video_id, timestamp))
            loop.close()
            vod_url = return_supported_qualities(vod_url)

        if vod_url is None:
            alternate_websites = generate_website_links(streamer_name, video_id, tracker_url)

            print("\nUnable to recover with provided url! Searching for different timestamps")
            all_timestamps = [timestamp]

            # Check if any alternate websites have a different timestamp
            for website in alternate_websites:
                parsed_timestamp = None
                if "streamscharts" in website:                                                                                                              
                    parsed_timestamp, _ = parse_datetime_streamscharts(website)
                elif "twitchtracker" in website:
                    parsed_timestamp, _ = parse_datetime_twitchtracker(website)
                elif "sullygnome" in website:
                    # If the timestamp shows a year different from the current one, skip it since SullyGnome doesn't provide the year
                    if timestamp and datetime.now().year != int(timestamp.split("-")[0]):
                        continue
                    parsed_timestamp, _ = parse_datetime_sullygnome(website)

                if (parsed_timestamp and parsed_timestamp != timestamp and parsed_timestamp not in all_timestamps):
                    print(f"Found different timestamp: {parsed_timestamp}")
                    all_timestamps.append(parsed_timestamp)

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    vod_url = loop.run_until_complete(get_vod_urls(streamer_name, video_id, parsed_timestamp))
                    loop.close()
                    
                    if vod_url:
                        return vod_url
                else:
                    if parsed_timestamp is not None:
                        print("Found same timestamp, skipping...")

            if not any(all_timestamps):
                print("\033[91m \n✖ Unable to get the stream start datetime!\033[0m")
                print(f'\nOpen the Twitch Tracker page source \033[94mview-source:{tracker_url}\033[0m and search for <meta name=\"description\"')
                print("The datetime will be in the content, like for example: 2025-01-01 12:00:00")

                input_datetime = input("\nEnter the datetime: ")

                if not input_datetime:
                    print("\033[91m \n✖  No datetime entered! \033[0m")
                    input("\nPress Enter to continue...")
                    run_vod_recover()
                
                # Get the VOD URLs using asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                vod_url = loop.run_until_complete(get_vod_urls(streamer_name, video_id, input_datetime))
                loop.close()
                
                if vod_url:
                    return vod_url

            if not vod_url:
                print("\033[91m \n✖  Unable to recover the video! \033[0m")
                input("\nPress Enter to continue...")
                run_vod_recover()

        return vod_url
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
                response = request_session.head(url, timeout=10)
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
        if (read_config_by_key("settings", "AUTO_DOWNLOAD_CLIPS") or input("\nDo you want to download the recovered clips (Y/N): ").upper() == "Y"):
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
            return run_vod_recover()
        window.destroy()
        csv_filename = os.path.basename(file_path)
        pattern = r"^[a-zA-Z0-9_]{4,25} - Twitch stream stats"
        if bool(re.match(pattern, csv_filename)):
            return file_path
        print("The CSV filename MUST be the original filename that was downloaded from sullygnome!")
    except tk.TclError:
        file_path = input("Enter the full path to the CSV file: ").strip(' "\'')
        while True:
            if not file_path:
                print("\nNo file entered! Returning to main menu.")
                return run_vod_recover()
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
                response = request_session.head(url, timeout=10)
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
                        user_input = input("\nDo you want to search more URLs (Y/N): ").strip().upper()
                        if user_input != "Y":                            
                            should_continue = False
                            break

            if counter == 0 and not should_continue:
                print("No valid clips found.")
                break


async def validate_clip(session, url, streamer_name, video_id):
    try:
        async with session.head(url, timeout=30) as response:
            if response.status == 200:
                write_text_file(response.url, get_log_filepath(streamer_name, video_id))
                return response.url
    except Exception:
        return None


async def bulk_clip_recovery():
    vod_counter, total_counter, valid_counter, iteration_counter = 0, 0, 0, 0
    streamer_name, csv_file_path = "", ""

    bulk_recovery_option = print_bulk_clip_recovery_menu()
    if bulk_recovery_option == "1":
        csv_file_path = get_and_validate_csv_filename()
        streamer_name = parse_streamer_from_csv_filename(csv_file_path)
    elif bulk_recovery_option == "2":
        csv_directory = input("Enter the full path where the sullygnome csv files exist: ").replace('"', "")
        streamer_name = input("Enter the streamer's name: ")
        merge_files = input("Do you want to merge the CSV files in the directory? (Y/N): ")
        if merge_files.upper() == "Y":
            merge_csv_files(streamer_name, csv_directory)
            csv_file_path = os.path.join(csv_directory, f"{streamer_name.title()}_MERGED.csv")
        else:
            csv_file_path = get_and_validate_csv_filename()
            csv_file_path = csv_file_path.replace('"', "")
    elif bulk_recovery_option == "3":
        return run_vod_recover()

    clip_format = print_clip_format_menu().split(" ")
    stream_info_dict = parse_clip_csv_file(csv_file_path)

    connector = aiohttp.TCPConnector(limit=200, force_close=True, enable_cleanup_closed=True)
    timeout = aiohttp.ClientTimeout(total=15, connect=10)
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                for video_id, values in stream_info_dict.items():
                    vod_counter += 1
                    print(f"\nProcessing Past Broadcast:\n" 
                          f"Stream Date: {values[0].replace('-', ' ')}\n" 
                          f"Vod ID: {video_id}\n" 
                          f"Vod Number: {vod_counter} of {len(stream_info_dict)}\n")
                    original_vod_url_list = get_all_clip_urls(get_clip_format(video_id, values[1]), clip_format)
                    print("Searching...")

                    batch_size = 500
                    for i in range(0, len(original_vod_url_list), batch_size):
                        batch = original_vod_url_list[i:i + batch_size]
                        tasks = []
                        for url in batch:
                            try:
                                tasks.append(validate_clip(session, url, streamer_name, video_id))
                            except Exception:
                                continue
                        
                        if not tasks:
                            continue

                        try:
                            results = await asyncio.gather(*tasks, return_exceptions=True)
                            for result in results:
                                total_counter += 1
                                iteration_counter += 1
                                if iteration_counter % 100 == 0:
                                    print(f"\rSearching for clips... {iteration_counter} of {len(original_vod_url_list)}", end=" ", flush=True)
                                if result and not isinstance(result, Exception):
                                    valid_counter += 1
                        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
                            print(f"\nError in batch (continuing anyway): {str(e)}")
                            continue

                    print(f"\n\033[92m{valid_counter} Clip(s) Found\033[0m\n")

                    if valid_counter != 0:
                        user_option = input("Do you want to download all clips recovered (Y/N)? ")

                        if user_option.upper() == "Y":
                            download_clips(get_default_directory(), streamer_name, video_id)
                            os.remove(get_log_filepath(streamer_name, video_id))
                        else:
                            choice = input("\nWould you like to keep the log file containing links to the recovered clips (Y/N)? ")
                            if choice.upper() == "N":
                                os.remove(get_log_filepath(streamer_name, video_id))
                            else:
                                print("\nRecovered links saved to " + get_log_filepath(streamer_name, video_id))
                    else:
                        print("No clips found!... Moving on to next vod." + "\n")
                    total_counter, valid_counter, iteration_counter = 0, 0, 0
                return 
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            retry_count += 1
            if retry_count >= max_retries:
                print(f"\nFailed after {max_retries} attempts. Please restart the program.")
                break
            print(f"\nError occurred (attempt {retry_count}/{max_retries}): {str(e)}")
            await asyncio.sleep(1)

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
        command = ["pip", "install", "yt-dlp", "--upgrade", "--quiet"]
        try:
            subprocess.run(command, check=True)
            print("yt-dlp installed successfully!")
            return "yt-dlp"
        except Exception:
            sys.exit("yt-dlp not installed! Please install yt-dlp and try again.")


def get_m3u8_duration(m3u8_link):
    command = [
        get_ffprobe_path(),
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        m3u8_link
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

        if result.returncode != 0:
            return None

        duration = result.stdout.strip()
        if duration:
            return float(duration)

    except Exception:
        return None


def handle_progress_bar(command, output_filename, total_duration):
    try:
        ff = FfmpegProgress(command)
        with tqdm(total=100, position=0, desc=output_filename, leave=None, colour="green", unit="%", bar_format="{l_bar}{bar}| {percentage:.1f}/100% [{elapsed}]{postfix}") as pbar:
            for progress in ff.run_command_with_progress():
                pbar.update(progress - pbar.n)
                
                if total_duration is not None:
                    total_duration_seconds = total_duration
                    current_duration_seconds = (progress / 100) * total_duration_seconds
                    current_duration_str = str(timedelta(seconds=int(current_duration_seconds)))
                    total_duration_str = str(timedelta(seconds=int(total_duration_seconds)))
                    pbar.set_postfix_str(f"{current_duration_str}/{total_duration_str}")

            pbar.close()
        return True
    except Exception as e:
        print(f"Error: {str(e).strip()}")
        raise Exception


def handle_file_already_exists(output_path):
    if os.path.exists(output_path):
        if not ask_to_redownload(output_path):
            print("\n\033[94m\u2713 Skipping download!\033[0m\n")
            input("Press Enter to continue...")
            return run_vod_recover()
        

def handle_retry_command(command):
    try:
        retry_command = ' '.join(f'"{part}"' if ' ' in part else part for part in command)
        print("Retrying command: " + retry_command)
        subprocess.run(retry_command, shell=True, check=True)
        return True
    except Exception:
        return False


def download_m3u8_video_url(m3u8_link, output_filename):
    if os.name != 'nt':
        output_filename = quote_filename(output_filename)

    output_path = os.path.normpath(os.path.join(get_default_directory(), output_filename))
    handle_file_already_exists(output_path)

    downloader = get_default_downloader()

    if downloader == "ffmpeg":
        command = [
            get_ffmpeg_path(), 
            "-i", m3u8_link, 
            "-hide_banner",
            "-c", "copy", 
            "-f", get_ffmpeg_format(get_default_video_format()),
            "-y", output_path
        ]

    else:
        command = [
            "yt-dlp",
            m3u8_link,
            "-o", output_path,
        ]
        custom_options = get_yt_dlp_custom_options()
        if custom_options:
            command.extend(custom_options)

    print("\nCommand: " + " ".join(command) + "\n")

    try:
        if downloader == "ffmpeg" and get_use_progress_bar():
            total_duration = get_m3u8_duration(m3u8_link)
            handle_progress_bar(command, output_filename, total_duration)
        else:
            subprocess.run(command, shell=True, check=True)
        return True
    except Exception:
        handle_retry_command(command)


def download_m3u8_video_url_slice(m3u8_link, output_filename, video_start_time, video_end_time):
    if os.name != 'nt':
        output_filename = quote_filename(output_filename)

    output_path = os.path.normpath(os.path.join(get_default_directory(), output_filename))
    handle_file_already_exists(output_path)

    downloader = get_default_downloader()

    if downloader == "ffmpeg":
        
        command = [
            get_ffmpeg_path(),
            "-protocol_whitelist", "file,http,https,tcp,tls",
            "-hide_banner",
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
            total_duration = get_m3u8_duration(m3u8_link)
            handle_progress_bar(command, output_filename, total_duration)

        else:
            subprocess.run(command, shell=True, check=True)
        return True
    except Exception:
        handle_retry_command(command)


def download_m3u8_video_file(m3u8_file_path, output_filename):    
    output_path = os.path.normpath(os.path.join(get_default_directory(), output_filename))
    handle_file_already_exists(output_path)

    downloader = get_default_downloader()

    
    if downloader == "ffmpeg":
        command = [
            get_ffmpeg_path(),
            "-protocol_whitelist", "file,http,https,tcp,tls",
            "-hide_banner",
            "-ignore_unknown",
            "-i", m3u8_file_path,
            "-c", "copy",
            "-f", get_ffmpeg_format(get_default_video_format()),
            "-y", output_path,
        ]
    elif downloader == "yt-dlp":
        if os.name == 'nt':  # For Windows
            m3u8_file_path = f"file:\\\\{m3u8_file_path}"
        else:  # For Linux and macOS
            m3u8_file_path = f"file://{m3u8_file_path}"
        command = [
            "yt-dlp",
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
            total_duration = get_m3u8_duration(m3u8_file_path)
            handle_progress_bar(command, output_filename, total_duration)

        else:
            subprocess.run(command, shell=True, check=True)
        return True
    except Exception:
        handle_retry_command(command)


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
        "-protocol_whitelist", "file,http,https,tcp,tls",
        "-hide_banner",
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
        if downloader == "ffmpeg" and get_use_progress_bar():
            total_duration = get_m3u8_duration(m3u8_file_path)
            handle_progress_bar(command, output_filename, total_duration)
        else:
            subprocess.run(command, shell=True, check=True)
        return True
    except Exception:
        handle_retry_command(command)


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
            return print(f"\n\033[91m\u2717 Failed to download Vod: {vod_filename}\033[0m\n")
        os.remove(m3u8_source)
    else:
        vod_filename = get_filename_for_url_source(m3u8_source, title=title, stream_date=stream_date)

        success = download_m3u8_video_url(m3u8_source, vod_filename)
        if not success:
            print(f"\n\033[91m\u2717 Failed to download Vod: {vod_filename}\033[0m\n")
            return

    print(f"\n\033[92m\u2713 Vod downloaded to {os.path.join(get_default_directory(), vod_filename)}\033[0m\n")


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


def handle_vod_url_trim(m3u8_source, title=None, stream_date=None):
    vod_start_time = get_time_input_HH_MM_SS("Enter start time (HH:MM:SS): ")
    vod_end_time = get_time_input_HH_MM_SS("Enter end time (HH:MM:SS): ")

    raw_start_time = vod_start_time.replace(":", ".")
    raw_end_time = vod_end_time.replace(":", ".")

    is_file = os.path.isfile(m3u8_source)
    if is_file:
        vod_filename = get_filename_for_file_trim(m3u8_source, title, stream_date, raw_start_time, raw_end_time)
        success = download_m3u8_video_file_slice(m3u8_source, vod_filename, vod_start_time, vod_end_time)
        if not success:
            return print(f"\n\033[91m\u2717 Failed to download Vod: {vod_filename}\033[0m\n")

        if os.path.isfile(m3u8_source):
            os.remove(m3u8_source)
    else:
        vod_filename = get_filename_for_url_trim(m3u8_source, title, stream_date, raw_start_time, raw_end_time)
        success = download_m3u8_video_url_slice(m3u8_source, vod_filename, vod_start_time, vod_end_time)
        if not success:
            return print(f"\n\033[91m\u2717 Failed to download Vod: {vod_filename}\033[0m\n")

    print(f"\n\033[92m\u2713 Vod downloaded to {os.path.join(get_default_directory(), vod_filename)}\033[0m\n")


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
            return run_vod_recover()
        elif start_download == 2:
            handle_vod_url_trim(link, title, stream_datetime)
            input("Press Enter to continue...")
            return run_vod_recover()
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
            return run_vod_recover()
        else:
            print("\n✖  Invalid option! Please Try Again.\n")


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
            return run_vod_recover()
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

    print("\n✖  Invalid Twitch VOD or Highlight URL! Please Try Again.\n")
    url = print_get_twitch_url_menu()
    return extract_id_from_url(url)


def extract_slug_and_streamer_from_clip_url(url):
    try:
        pattern = r"twitch\.tv/([^\/]+)/clip/([^\/?]+)"
        match = re.search(pattern, url)
        if match:
            return match.group(1), match.group(2)
        sys.exit("\n✖  Invalid Twitch Clip URL! Please Try Again.\n")
    except Exception:
        sys.exit("\n✖  Invalid Twitch Clip URL! Please Try Again.\n")


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
                    "Client-Id": "kimne78kx3ncx6brgo4mv6wki5h1ko",
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
        sleep(delay)

    return None

def get_vod_or_highlight_url(vod_id):
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
    vod_id = extract_id_from_url(url)
    url, title, stream_datetime = get_vod_or_highlight_url(vod_id)

    if url is None:
        print("\n✖  Unable to find it! Try using one of the other websites.\n")
        input("Press Enter to continue...")
        return run_vod_recover()

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
            "operationName": "ClipsDownloadButton",
            "variables": {
                "slug": clip_slug,
            },
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "6e465bb8446e2391644cf079851c0cb1b96928435a240f07ed4b240f0acc6f1b",
                }
            },
        }
    ]
    headers = {"Client-Id": "kimne78kx3ncx6brgo4mv6wki5h1ko"}
    
    for attempt in range(retries):
        try:
            response_endpoint = requests.post(url_endpoint, json=data, headers=headers, timeout=30)
            response_endpoint.raise_for_status()  # Raise an error for bad responses
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
            print(f"\nRetrying...")
            if attempt < retries - 1:
                sleep(3) 

    print("\n✖  Unable to get clip! Check the URL and try again.\n")
    input("Press Enter to continue...")
    return run_vod_recover()


def twitch_clip_downloader(clip_url, slug, streamer):
    print("\nDownloading Clip...")
    try:
        response = requests.get(clip_url, stream=True, timeout=30)
        if response.status_code != 200:
            raise Exception("Unable to download clip!")
        download_location = os.path.join(get_default_directory(), f"{streamer}-{slug}{get_default_video_format()}")

        with open(os.path.join(get_default_directory(), download_location), "wb") as file:
            copyfileobj(response.raw, file)

        print(f"\n\033[92m\u2713 Clip downloaded to {download_location}\033[0m\n")

        input("Press Enter to continue...")
    except Exception:
        raise Exception("Unable to download clip!")


def handle_twitch_clip(clip_url):
    streamer, slug = extract_slug_and_streamer_from_clip_url(clip_url)
    streamer = clip_url.split("/")[3]
    url = get_twitch_clip(slug)
    return twitch_clip_downloader(url, slug, streamer)


def run_vod_recover():
    print("\nWELCOME TO VOD RECOVERY!")
    
    menu = 0
    while menu < 50:
        print()
        menu = print_main_menu()
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
                clip_url = print_get_twitch_url_menu()
                handle_twitch_clip(clip_url)
            elif clip_type == 4:
                asyncio.run(bulk_clip_recovery())
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
            get_latest_streams_from_twitchtracker()
        elif menu == 5:
            mode = print_handle_m3u8_availability_menu()
            if mode == 1:
                url = print_get_m3u8_link_menu()
                is_muted = is_video_muted(url)
                if is_muted:
                    print("\nVideo contains muted segments")
                    choice = input("Do you want to unmute the video? (Y/N): ")
                    if choice.upper() == "Y":
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
                print(f"File saved to {get_default_directory()}")
                input("\nPress Enter to continue...")
            elif menu == 3:
                continue
        elif menu == 6:
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
                    script_dir = get_script_directory()
                    config_file_path = os.path.join(script_dir, "config", "settings.json")
                    if os.path.exists(config_file_path):
                        print(f"Opening {config_file_path}...")
                        open_file(config_file_path)
                        input("\nPress Enter to continue...")
                    else:
                        print("File not found!")
                elif options_choice == 6:
                    print_help()
                    input("Press Enter to continue...")
                elif options_choice == 7:
                    break
        elif menu == 7:
            print("\nExiting...\n")
            sys.exit()
        else:
            run_vod_recover()



if __name__ == "__main__":
    try:
        run_vod_recover()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        os._exit(0)





