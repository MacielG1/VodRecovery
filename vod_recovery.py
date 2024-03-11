import hashlib
import json
import csv
import os
import random
import re
import subprocess
import time
import shutil
import tkinter as tk
import sys
from datetime import datetime, timedelta
from collections.abc import Iterable
from tkinter import filedialog
from urllib.parse import urlparse
import concurrent.futures
import grequests
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from seleniumbase import SB
import requests

supported_formats = [".mp4", ".mkv", ".mov", ".avi", ".ts"]

def read_config_by_key(config_file, key):
    with open(f"config/{config_file}.json", 'r', encoding="utf-8") as input_config_file:
        config = json.load(input_config_file)
    return config.get(key, None)


def get_default_video_format():
    default_video_format = read_config_by_key('settings', 'DEFAULT_VIDEO_FORMAT')
    
    if default_video_format in supported_formats:
        return default_video_format
    return ".mp4"


def print_main_menu():
    default_video_format = get_default_video_format() or ".mp4"
    menu_options = [
        "1) VOD Recovery",
        "2) Clip Recovery",
        f"3) Download VOD ({default_video_format})",
        "4) Unmute & Check M3U8 Availability",
        "5) Set Default Video Format",
        "6) Set Download Directory",
        "7) Help",
        "8) Exit"
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
        "3) Bulk Video Recovery from SullyGnome CSV Export",
        "4) Return"
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
        "3) Return"
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
    clip_type_options = ["1) Recover All Clips from a VOD","2) Find Random Clips from a VOD",
                         "3) Donwload Clip from Twitch URL", "4) Bulk Recover Clips from SullyGnome CSV Export", "5) Return"]
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
    clip_recovery_options = ["1) Website Clip Recovery", "2) Manual Clip Recovery",  "3) Return"]
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
        "3) Return"
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
        "4) Return"
    ]
    print()
    while True:
        print("\n".join(clip_format_options))
        try:
            choice = int(input("\nSelect Clip URL Format: "))
            if choice == 4:
                return run_vod_recover()
            elif choice not in range(1, len(clip_format_options) + 1):
                raise ValueError("Invalid option")
            else:
                return str(choice)
        except ValueError:
            print("\n✖  Invalid option! Please try again:\n")
            

def print_download_type_menu():
    download_type_options = [
        "1) From M3U8 Link",
        "2) From M3U8 File",
        "3) From Twitch URL (Only for VODs and Highlights still up on Twitch)",
        "4) Return"
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
        "1) Check if M3U8 file is muted",
        "2) Unmute and remove invalid segments",
        "3) Return"
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


def print_get_m3u8_link_menu():
    m3u8_url = input("Enter M3U8 Link: ").strip(' "\'')
    if m3u8_url.endswith(".m3u8"):
        return m3u8_url
    print("\n✖  Invalid M3U8 link! Please try again:\n")
    return print_get_m3u8_link_menu()


def get_websites_tracker_url():
    while True:
        tracker_url = input("Enter Twitchtracker/Streamscharts/Sullygnome url: ").strip()
        if re.match(r'^(https?:\/\/)?(www\.)?(twitchtracker\.com|streamscharts\.com|sullygnome\.com)\/.*', tracker_url):
            return tracker_url
        else:
            print("\n✖  Invalid URL! Please enter a URL from Twitchtracker, Streamscharts, or Sullygnome.\n")

def print_get_twitch_url_menu():
    twitch_url = input("Enter Twitch URL: ").strip(' "\'') 
    print()
    if "twitch.tv" in twitch_url:
        return twitch_url
    print("✖  Invalid Twitch URL! Please try again:\n")
    return print_get_twitch_url_menu()


def read_config_file(config_file):
    with open(f"config/{config_file}.json", encoding="utf-8") as config_file:
        config = json.load(config_file)
    return config


def print_help():
    try:
        help_data = read_config_file('help')
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
        text_file.write(input_text + '\n')


def write_m3u8_to_file(m3u8_link, destination_path):
    with open(destination_path, "w", encoding="utf-8") as m3u8_file:
        m3u8_file.write(requests.get(m3u8_link, timeout=30).text)
    return m3u8_file


def read_csv_file(csv_file_path):
    with open(csv_file_path, "r", encoding="utf-8") as csv_file:
        return list(csv.reader(csv_file))


def get_default_directory():
    default_directory = read_config_by_key('settings', 'DEFAULT_DIRECTORY')
    return os.path.expanduser(default_directory)


def get_log_filepath(streamer_name, video_id):
    log_filename = os.path.join(get_default_directory(), f"{streamer_name}_{video_id}_log.txt")
    return log_filename


def get_vod_filepath(streamer_name, video_id):
    vod_filename = os.path.join(get_default_directory(), f"{streamer_name}_{video_id}.m3u8")
    return vod_filename


def return_user_agent():
    user_agents = read_text_file('config/user_agents.txt')
    header = {
        'user-agent': random.choice(user_agents)
    }
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
    vod_age = datetime.today() - datetime.strptime(start_timestamp, '%Y-%m-%d %H:%M:%S')
    return max(vod_age.days, 0)


def is_video_muted(m3u8_link):
    response = requests.get(m3u8_link, timeout=30).text
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
    indices = [i.start() for i in re.finditer('_', m3u8_link)]
    streamer_name = m3u8_link[indices[0] + 1:indices[-2]]
    return streamer_name


def parse_video_id_from_m3u8_link(m3u8_link):
    indices = [i.start() for i in re.finditer('_', m3u8_link)]
    video_id = m3u8_link[indices[0] + len(parse_streamer_from_m3u8_link(m3u8_link)) + 2:indices[-1]]
    return video_id


def parse_streamscharts_url(streamscharts_url):
    try:
        streamer_name = streamscharts_url.split("/channels/", 1)[1].split("/streams/")[0]
        video_id = streamscharts_url.split("/streams/", 1)[1]
        return streamer_name, video_id
    except IndexError:
        print("\n✖  Invalid Streamscharts URL! Please try again:\n")
        input("Press Enter to return to the menu...")
        print()
        return run_vod_recover()


def parse_twitchtracker_url(twitchtracker_url):
    try:
        streamer_name = twitchtracker_url.split(".com/", 1)[1].split("/streams/")[0]
        video_id = twitchtracker_url.split("/streams/", 1)[1]
        return streamer_name, video_id
    except IndexError:
        print("\n✖  Invalid Twitchtracker URL! Please try again:\n")
        input("Press Enter to return to the menu...")
        print()
        return run_vod_recover()


def parse_sullygnome_url(sullygnome_url):
    try:
        streamer_name = sullygnome_url.split("/channel/", 1)[1].split("/")[0]
        video_id = sullygnome_url.split("/stream/", 1)[1]
        return streamer_name, video_id
    except IndexError:
        print("\n✖  Invalid SullyGnome URL! Please try again:\n")
        input("Press Enter to return to the menu...")
        print()
        return run_vod_recover()


def set_default_video_format():
    print("\nSelect the default video format")

    for i, format_option in enumerate(supported_formats, start=1):
        print(f"{i}) {format_option}")

    user_option = str(input("\nChoose a video format: "))
    print(user_option)
    if user_option in [str(i) for i in range(1, len(supported_formats) + 1)]:
        selected_format = supported_formats[int(user_option) - 1]
        config_file_path = "config/settings.json"
        try:
            with open(config_file_path, 'r', encoding="utf-8") as config_file:
                config_data = json.load(config_file)

            if not config_data:
                print("Error: No config file found.")
                return

            config_data["DEFAULT_VIDEO_FORMAT"] = selected_format

            with open(config_file_path, 'w', encoding="utf-8") as config_file:
                json.dump(config_data, config_file, indent=4)

            print(f"\n\033[92m\u2713  Default video format set to: {selected_format}\033[0m")

        except (FileNotFoundError, json.JSONDecodeError) as error:
            print(f"Error: {error}")
    else:
        print("\n✖  Invalid option! Please try again:\n")
        return


def set_default_directory():
    print("\nSelect the default directory")
    window = tk.Tk()
    window.wm_attributes('-topmost', 1)
    window.withdraw() 
    file_path = filedialog.askdirectory(parent=window, initialdir=dir,
                                  title="Select A Default Directory")
    
    if file_path:
        if not file_path.endswith("/"):
            file_path += "/"
        config_file_path = "config/settings.json"
      
        try:
            with open(config_file_path, 'r', encoding="utf-8") as config_file:
                config_data = json.load(config_file)
            
            config_data["DEFAULT_DIRECTORY"] = file_path
            with open(config_file_path, 'w', encoding="utf-8") as config_file:
                json.dump(config_data, config_file, indent=4)
            
            print(f"\n\033[92m\u2713  Default directory set to: {file_path}\033[0m")
        
        except (FileNotFoundError, json.JSONDecodeError) as error:
            print(f"Error: {error}")
    else:
        print("\nNo folder selected! Returning to main menu...")
    window.destroy() 


def parse_vod_filename(m3u8_video_filename):
    base = os.path.basename(m3u8_video_filename)
    streamer_name, video_id = base.split('.m3u8', 1)[0].rsplit('_', 1)
    return f"{streamer_name}_{video_id}"


def remove_chars_from_ordinal_numbers(datetime_string):
    ordinal_numbers = ["th", "nd", "st", "rd"]
    for exclude_string in ordinal_numbers:
        if exclude_string in datetime_string:
            return datetime_string.replace(datetime_string.split(" ")[1], datetime_string.split(" ")[1][:-len(exclude_string)])


def generate_website_links(streamer_name, video_id, tracker_url=None):
    website_list = [
        f"https://sullygnome.com/channel/{streamer_name}/stream/{video_id}",
        f"https://twitchtracker.com/{streamer_name}/streams/{video_id}",
        f"https://streamscharts.com/channels/{streamer_name}/streams/{video_id}"
    ]
    if tracker_url:
        website_list = [link for link in website_list if tracker_url not in link]
    return website_list


def convert_url(url, target):
    # converts url to the specified target
    patterns = {
        "sullygnome": "https://sullygnome.com/channel/{}/stream/{}",
        "twitchtracker": "https://twitchtracker.com/{}/streams/{}",
        "streamscharts": "https://streamscharts.com/channels/{}/streams/{}"
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
    clip_offset = re.search(r'(?:-offset|-index)-(\d+)', clip_url)
    return clip_offset.group(1)


def get_clip_format(video_id, offsets):

    default_clip_list = [f"https://clips-media-assets2.twitch.tv/{video_id}-offset-{i}.mp4" for i in range(0, offsets, 2)]
    alternate_clip_list = [f"https://clips-media-assets2.twitch.tv/vod-{video_id}-offset-{i}.mp4" for i in range(0, offsets, 2)]
    legacy_clip_list = [f"https://clips-media-assets2.twitch.tv/{video_id}-index-{i:010}.mp4" for i in range(offsets)]

    clip_format_dict = {
        "1": default_clip_list,
        "2": alternate_clip_list,
        "3": legacy_clip_list
    }

    return clip_format_dict


def get_random_clip_information():
    while True:
        url = get_websites_tracker_url()
    
        if "streamscharts" in url:
            _, video_id = parse_streamscharts_url(url)
            break
        elif "twitchtracker" in url:
            _, video_id = parse_twitchtracker_url(url)
            break
        elif "sullygnome" in url:
            _, video_id = parse_sullygnome_url(url)
            break
        else:
            print("\n✖  Link not supported! Please try again:\n")

    while True:
        duration = get_time_input_HH_MM("Enter stream duration in (HH:MM) format: ")
        hours, minutes = map(int, duration.split(':'))
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

        hours, minutes = map(int, duration.split(':'))
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

        print("Retrieving stream duration from Streamscharts")
        duration_streamscharts = parse_duration_streamscharts(tracker_url)
        # print(f"Duration: {duration_streamscharts}")

        clip_recover(streamer, video_id, int(duration_streamscharts))
    elif "twitchtracker" in tracker_url:
        streamer, video_id = parse_twitchtracker_url(tracker_url)

        print("Retrieving stream duration from Twitchtracker")
        duration_twitchtracker = parse_duration_twitchtracker(tracker_url)
        # print(f"Duration: {duration_twitchtracker}")

        clip_recover(streamer, video_id, int(duration_twitchtracker))
    elif "sullygnome" in tracker_url:
        streamer, video_id = parse_sullygnome_url(tracker_url)

        print("Retrieving stream duration from Sullygnome")
        duration_sullygnome = parse_duration_sullygnome(tracker_url)
        if duration_sullygnome is None:
            print("Could not retrieve duration from Sullygnome. Try a different URL.\n")
            return print_main_menu()
        # print(f"Duration: {duration_sullygnome}")

        clip_recover(streamer, video_id, int(duration_sullygnome))
    else:
        print("\n✖  Link not supported! Returning to main menu...")
        return run_vod_recover()


def manual_vod_recover():
    while True:
        streamer_name = input("Enter the Streamer Name: ")
        if streamer_name.lower().strip():
            break

        print("\n✖  No streamer name! Please try again:\n")

    while True:
        video_id = input("Enter the Video ID (from: Twitchtracker/Streamscharts/Sullygnome): ")
        if video_id.strip():
            break
        else:
            print("\n✖  No video ID! Please try again:\n")

    timestamp = get_time_input_YYYY_MM_DD_HH_MM_SS("Enter VOD Datetime (YYYY-MM-DD HH:MM:SS): ")

    m3u8_link = vod_recover(streamer_name, video_id, timestamp)
    if m3u8_link is None:
        sys.exit("No M3U8 link found! Exiting...")

    process_m3u8_configuration(m3u8_link)
    handle_download_menu(m3u8_link)   

def website_vod_recover():
    tracker_url = get_websites_tracker_url()

    m3u8_link = None
    if not tracker_url.startswith("https://"):
        tracker_url = "https://" + tracker_url
    if "streamscharts" in tracker_url:

        streamer, video_id = parse_streamscharts_url(tracker_url)
        print(f"Checking {streamer} VOD Id: {video_id}")
        m3u8_link = vod_recover(streamer, video_id, parse_datetime_streamscharts(tracker_url), tracker_url)
        
        if m3u8_link is None:
            input("\nNo M3U8 link found! Press Enter to return...")
            return run_vod_recover()
        if m3u8_link is not None:
            print("\nProcessing URL...")
        if m3u8_link is not None:
            process_m3u8_configuration(m3u8_link)
            m3u8_duration = return_m3u8_duration(m3u8_link)

            print("Comparing Streamscharts duration with M3U8 duration...")
            streamscharts_duration = int(parse_duration_streamscharts(tracker_url))
            if streamscharts_duration >= m3u8_duration + 10:
                print("Streamscharts is generally considered the most reliable source for this data. The discrepancy in durations is likely an anomaly.")
            return m3u8_link
        
    elif "twitchtracker" in tracker_url:

        streamer, video_id = parse_twitchtracker_url(tracker_url)
        print(f"Checking {streamer} VOD Id: {video_id}")
        m3u8_link = vod_recover(streamer, video_id, parse_datetime_twitchtracker(tracker_url), tracker_url)
       
        if m3u8_link is None:
            input("\nNo M3U8 link found! Press Enter to return...")
            return run_vod_recover()
        if m3u8_link is not None:
            print("\nProcessing URL...")

            process_m3u8_configuration(m3u8_link)
            m3u8_duration = return_m3u8_duration(m3u8_link)
            streamer = parse_streamer_from_m3u8_link(m3u8_link)
            video_id = parse_video_id_from_m3u8_link(m3u8_link)
            streamscharts_url = generate_website_links(streamer, video_id)[2]
            modified_streamscharts_url = streamscharts_url[:streamscharts_url.rfind('/')]

            print("Comparing Twitchtracker duration with M3U8 duration...")
            twitchtracker_duration = int(parse_duration_twitchtracker(tracker_url))
            if twitchtracker_duration >= m3u8_duration + 10:
                print(f"The duration from Twitchtracker exceeds the M3U8 duration by over 10 minutes. Consider checking Streamscharts for a split stream. URL: {modified_streamscharts_url}")
            return m3u8_link
    elif "sullygnome" in tracker_url:
        streamer, video_id = parse_sullygnome_url(tracker_url)
        print(f"Checking {streamer} VOD Id: {video_id}")
        new_tracker_url = re.sub(r'/\d+/', '/', tracker_url)

        m3u8_link = vod_recover(streamer, video_id, parse_datetime_sullygnome(tracker_url), new_tracker_url)
        if m3u8_link is None:
            input("\nNo M3U8 link found! Press Enter to return...")
            return run_vod_recover()
        if m3u8_link is not None:
            print("\nProcessing URL...")
            process_m3u8_configuration(m3u8_link)
            m3u8_duration = return_m3u8_duration(m3u8_link)
            streamer = parse_streamer_from_m3u8_link(m3u8_link)
            video_id = parse_video_id_from_m3u8_link(m3u8_link)
            streamscharts_url = generate_website_links(streamer, video_id)[2]
            modified_streamscharts_url = streamscharts_url[:streamscharts_url.rfind('/')]

            print("Comparing Sullygnome duration with M3U8 duration...")
            sullygnome_duration = int(parse_duration_sullygnome(tracker_url))
            if sullygnome_duration >= m3u8_duration + 10:
                print("\n" + f"The duration from Sullygnome exceeds the M3U8 duration by over 10 minutes. Consider checking Streamscharts for a split stream. URL: {modified_streamscharts_url}")
            return m3u8_link
    else:
        print("\n✖  Link not supported! Returning to main menu...")
        return run_vod_recover()


def get_all_clip_urls(clip_format_dict, clip_format_list):
    combined_clip_format_list = []
    for key, value in clip_format_dict.items():
        if key in clip_format_list:
            combined_clip_format_list += value
    return combined_clip_format_list


def get_vod_urls(streamer_name, video_id, start_timestamp):
    m3u8_link_list = []
    domains = read_text_file('config/domains.txt')
    random.shuffle(domains)
    
    print("\nSearching for M3U8 URL...")

    try:
        for seconds in range(60):
            base_url = f"{streamer_name}_{video_id}_{int(calculate_epoch_timestamp(start_timestamp, seconds))}"
            hashed_base_url = str(hashlib.sha1(base_url.encode('utf-8')).hexdigest())[:20]

            for domain in domains:
                if domain.strip(): 
                    m3u8_link_list.append(f"{domain.strip()}{hashed_base_url}_{base_url}/chunked/index-dvr.m3u8")
    except Exception:
        return None

    successful_url = None
    first_url_printed = False
    progress_message_printed = False

    def fetch_status(url):
        nonlocal successful_url, first_url_printed
        if successful_url is not None:
            return None
        try:
            response = requests.head(url, timeout=30)
            if response.status_code == 200:
                successful_url = response.url
                if not first_url_printed:
                    if progress_message_printed:
                        print()
                    first_url_printed = True
                    print(f"\n\033[92m\u2713 Found URL: {successful_url}\033[0m") 

            return response
        except Exception:
            return None
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(fetch_status, url) for url in m3u8_link_list]
        for i in enumerate(concurrent.futures.as_completed(futures)):
            if successful_url is not None:  # Stop if a successful URL has been found
                break
            index, _ = i
            if not progress_message_printed:
                progress_message_printed = True
            print(f"\rSearching {index + 1} out of {len(m3u8_link_list)} URLs", end='', flush=True)
            
    if successful_url is None:
        print("\nNo successful URL found!")
        return None
    return successful_url


def return_supported_qualities(m3u8_link):
    if m3u8_link is None:
        return None
        
    print("\nChecking for available qualities...\n")
    resolutions = ["chunked", "1080p60", "1080p30", "720p60", "720p30", "480p60", "480p30"]
    request_list = [grequests.get(m3u8_link.replace("chunked", resolution)) for resolution in resolutions]
    responses = grequests.map(request_list, size=100)
    valid_resolutions =  [resolution for resolution, response in zip(resolutions, responses) if response and response.status_code == 200]

    if not valid_resolutions:
        return None

    print("Quality Options:")
    for idx, resolution in enumerate(valid_resolutions, 1):
        if 'chunked' in resolution:
            print(f"{idx}. {resolution.replace('chunked', 'Chunked (Best Quality)')}")
        else:
            print(f"{idx}. {resolution}")

    user_option = get_user_resolution_choice(m3u8_link, valid_resolutions)
    return user_option


def get_user_resolution_choice(m3u8_link, valid_resolutions):
    try:
        choice = int(input("Choose a quality: "))
        if 1 <= choice <= len(valid_resolutions):
            quality = valid_resolutions[choice - 1]
            user_option = m3u8_link.replace("chunked", quality)
            return user_option
        else:
            print("\n✖  Invalid option! Please try again:\n")
            return get_user_resolution_choice(m3u8_link, valid_resolutions)
    except ValueError:
        print("\n✖  Invalid option! Please try again:\n")
        return get_user_resolution_choice(m3u8_link, valid_resolutions)
    

def get_user_resolution_twitch(links):
    try:
        print("Quality Options:")
        for i, link in enumerate(links):
            if "Source" in link['quality']:
                print(f"{i+1}. {link['quality']} (Best Quality)")
            elif "chunked" in link['quality']:
                print(f"{i+1}. {link['quality']} (Best Quality)")
            else:
                print(f"{i+1}. {link['quality']}")

        choice = int(input("Choose a quality: "))
        if 1 <= choice <= len(links):
            selected_link = links[choice - 1]
            print()
            return selected_link['url']
        else:
            print("\n✖  Invalid option! Please try again:\n")
            return get_user_resolution_twitch(links)
    except ValueError:
        print("\n✖  Invalid option! Please try again:\n")
        return get_user_resolution_twitch(links)


def parse_website_duration(duration_string):
    if isinstance(duration_string, list):
        duration_string = ' '.join(duration_string)
    if not isinstance(duration_string, str):
        if isinstance(duration_string, Iterable) and not isinstance(duration_string, (str, bytes)):
            duration_string = ' '.join(duration_string)
        else:
            duration_string = str(duration_string)
    pattern = r"(\d+)\s*(h(?:ou)?r?s?|m(?:in)?(?:ute)?s?)"
    matches = re.findall(pattern, duration_string, re.IGNORECASE)
    hours = 0
    minutes = 0
    for value, unit in matches:
        if 'h' in unit.lower():
            hours = int(value)
        elif 'm' in unit.lower():
            minutes = int(value)
    return calculate_broadcast_duration_in_minutes(hours, minutes)


def handle_cloudflare(sb):
    # delete folder generated by selenium browser
    if os.path.exists("downloaded_files"):
        shutil.rmtree("downloaded_files")

    iframes = sb.driver.find_elements(By.TAG_NAME, "iframe")
    filtered_iframes = [iframe for iframe in iframes if "cloudflare" in iframe.get_attribute("src")]
    if len(filtered_iframes) > 0:
        try:
            for iframe in filtered_iframes:
                src_attribute = iframe.get_attribute("src")
                if src_attribute and "cloudflare" in src_attribute:
                    sb.driver.uc_switch_to_frame(iframe)
                    sb.driver.uc_click("span.mark", reconnect_time=1)
                    break
        except Exception:
            pass 


def parse_duration_streamscharts(streamcharts_url):
    try:
        # Method 1: Using requests
        response = requests.get(streamcharts_url, headers=return_user_agent(), timeout=10)
        if response.status_code == 200:
            bs = BeautifulSoup(response.content, 'html.parser')
            streamcharts_duration = bs.find_all('div', {'class': 'text-xs font-bold'})[3].text
            streamcharts_duration_in_minutes = parse_website_duration(streamcharts_duration)
            if streamcharts_duration_in_minutes:
                return streamcharts_duration_in_minutes
        
        # Method 2: Using grequests
        retries = 10
        reqs = [grequests.get(streamcharts_url, headers=return_user_agent()) for _ in range(retries)]
        for response in grequests.imap(reqs, size=100):
            if response.status_code == 200:
                bs = BeautifulSoup(response.content, 'html.parser')
                streamcharts_duration = bs.find_all('div', {'class': 'text-xs font-bold'})[3].text
                streamcharts_duration_in_minutes = parse_website_duration(streamcharts_duration)
                if streamcharts_duration_in_minutes:
                    return streamcharts_duration_in_minutes
    except Exception:
        pass

    # Method 3: Using Selenium 
    print("Opening Streamcharts with browser...")
    with SB(uc=True, headless=True) as sb:
        
        try:
            sb.driver.uc_open_with_reconnect(streamcharts_url, reconnect_time=3)
            handle_cloudflare(sb)

            bs = BeautifulSoup(sb.driver.page_source, 'html.parser')
            streamcharts_duration = bs.find_all('div', {'class': 'text-xs font-bold'})[3].text
            streamcharts_duration_in_minutes = parse_website_duration(streamcharts_duration)
            if streamcharts_duration_in_minutes:
                return streamcharts_duration_in_minutes

        except Exception:
            pass

    sullygnome_url = convert_url(streamcharts_url, "sullygnome")
    if sullygnome_url:
        return parse_duration_sullygnome(sullygnome_url)
    return None

            
def parse_duration_twitchtracker(twitchtracker_url, try_alternative=True):
    try:
        # Method 1: Using requests
        response = requests.get(twitchtracker_url, headers=return_user_agent(), timeout=10)
        if response.status_code == 200:
            bs = BeautifulSoup(response.content, 'html.parser')
            twitchtracker_duration = bs.find_all('div', {'class': 'g-x-s-value'})[0].text
            twitchtracker_duration_in_minutes = parse_website_duration(twitchtracker_duration)
            if twitchtracker_duration_in_minutes:
                return twitchtracker_duration_in_minutes
        
        # Method 2: Using grequests
        retries = 10
        reqs = [grequests.get(twitchtracker_url, headers=return_user_agent()) for _ in range(retries)]
        for response in grequests.imap(reqs, size=100):
            if response.status_code == 200:
                bs = BeautifulSoup(response.content, 'html.parser')
                twitchtracker_duration = bs.find_all('div', {'class': 'g-x-s-value'})[0].text
                twitchtracker_duration_in_minutes = parse_website_duration(twitchtracker_duration)
                if twitchtracker_duration_in_minutes:
                    return twitchtracker_duration_in_minutes
    
    except Exception:
        pass

    # Method 3: Using Selenium
    print("Opening Twitchtracker with browser...")
    with SB(uc=True, headless=True) as sb:
        try:
            sb.driver.uc_open_with_reconnect(twitchtracker_url, reconnect_time=3)
            handle_cloudflare(sb)

            bs = BeautifulSoup(sb.driver.page_source, 'html.parser')
            twitchtracker_duration = bs.find_all('div', {'class': 'g-x-s-value'})[0].text
            twitchtracker_duration_in_minutes = parse_website_duration(twitchtracker_duration)
            if twitchtracker_duration_in_minutes:
                return twitchtracker_duration_in_minutes
        except Exception:
            pass

    if try_alternative:
        sullygnome_url = convert_url(twitchtracker_url, "sullygnome")
        if sullygnome_url:
            return parse_duration_sullygnome(sullygnome_url)
    return None


def parse_duration_sullygnome(sullygnome_url):
    try:
        # Method 1: Using requests
        response = requests.get(sullygnome_url, headers=return_user_agent(), timeout=10)
        if response.status_code == 200:
            bs = BeautifulSoup(response.content, 'html.parser')
            sullygnome_duration = bs.find_all('div', {'class': 'MiddleSubHeaderItemValue'})[7].text.split(",")
            if sullygnome_duration:
                sullygnome_duration_in_minutes = parse_website_duration(sullygnome_duration)
            if sullygnome_duration_in_minutes:
                return sullygnome_duration_in_minutes
        
        # Method 2: Using grequests
        retries = 10
        reqs = [grequests.get(sullygnome_url, headers=return_user_agent()) for _ in range(retries)]
        for response in grequests.imap(reqs, size=10):
            if response.status_code == 200:
                bs = BeautifulSoup(response.content, 'html.parser')
                sullygnome_duration = bs.find_all('div', {'class': 'MiddleSubHeaderItemValue'})[7].text.split(",")
                if sullygnome_duration:
                    sullygnome_duration_in_minutes = parse_website_duration(sullygnome_duration)
                if sullygnome_duration_in_minutes:
                    return sullygnome_duration_in_minutes
    except Exception:
        pass

    # Method 3: Using Selenium 
    print("Opening Sullygnome with browser...")
    with SB(uc=True, headless=True) as sb:

        try:    
            sb.driver.uc_open_with_reconnect(sullygnome_url, reconnect_time=3)
            handle_cloudflare(sb)

            bs = BeautifulSoup(sb.driver.page_source, 'html.parser')
            sullygnome_duration = bs.find_all('div', {'class': 'MiddleSubHeaderItemValue'})[7].text.split(",")
            if sullygnome_duration:
                sullygnome_duration_in_minutes = parse_website_duration(sullygnome_duration)
                if sullygnome_duration_in_minutes:
                    return sullygnome_duration_in_minutes
        except Exception:
            pass

    sullygnome_url = convert_url(sullygnome_url, "twitchtracker")
    if sullygnome_url:
        return parse_duration_twitchtracker(sullygnome_url, try_alternative=False)    
    return None
        

def parse_datetime_streamscharts(streamscharts_url):
    print("\nRetrieving stream datetime from Streamscharts...")
    
    try:
        # Method 1: Using requests
        response = requests.get(streamscharts_url, headers=return_user_agent(), timeout=10)
        if response.status_code == 200:

            bs = BeautifulSoup(response.content, 'html.parser')
            streamscharts_datetime = bs.find_all('time', {'class': 'ml-2 font-bold'})[0].text.strip().replace(",", "") + ":00"
            stream_datetime = datetime.strptime(streamscharts_datetime, "%d %b %Y %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
            if stream_datetime:
                print(f"Datetime: {stream_datetime}")
                return stream_datetime

        # Method 2: Using grequests
        retries = 10
        reqs = [grequests.get(streamscharts_url, headers=return_user_agent()) for _ in range(retries)]
        for response in grequests.imap(reqs, size=100):
            if response.status_code == 200:

                bs = BeautifulSoup(response.content, 'html.parser')
                streamscharts_datetime = bs.find_all('time', {'class': 'ml-2 font-bold'})[0].text.strip().replace(",", "") + ":00"
                stream_datetime = datetime.strptime(streamscharts_datetime, "%d %b %Y %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                if stream_datetime:
                    print(f"Datetime: {stream_datetime}")
                    return stream_datetime
    except Exception:
        pass

    # Method 3: Using Selenium
    print("Opening Streamscharts with browser...")
    with SB(uc=True, headless=True) as sb:

        try:
            sb.driver.uc_open_with_reconnect(streamscharts_url, reconnect_time=3)
            handle_cloudflare(sb)
        
            bs = BeautifulSoup(sb.driver.page_source, 'html.parser')
            streamscharts_datetime = bs.find_all('time', {'class': 'ml-2 font-bold'})[0].text.strip().replace(",", "") + ":00"
            stream_datetime = datetime.strptime(streamscharts_datetime, "%d %b %Y %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
            if stream_datetime:
                print(f"Datetime: {stream_datetime}",)
                return stream_datetime
        except Exception:
            pass
    return None


def parse_datetime_twitchtracker(twitchtracker_url):
    print("\nRetrieving stream datetime from Twitchtracker...")

    try:
         # Method 1: Using requests
        response = requests.get(twitchtracker_url, headers=return_user_agent(), timeout=10)
        if response.status_code == 200:
            bs = BeautifulSoup(response.content, 'html.parser')
            twitchtracker_datetime = bs.find_all('div', {'class': 'stream-timestamp-dt'})[0].text

            if twitchtracker_datetime:
                print(f"Datetime: {twitchtracker_datetime}")
                return twitchtracker_datetime
        
        # Method 2: Using grequests
        retries = 10
        reqs = [grequests.get(twitchtracker_url, headers=return_user_agent()) for _ in range(retries)]
        for response in grequests.imap(reqs, size=100):
            if response.status_code == 200:

                bs = BeautifulSoup(response.content, 'html.parser')
                twitchtracker_datetime = bs.find_all('div', {'class': 'stream-timestamp-dt'})[0].text

                if twitchtracker_datetime:
                    print(f"Datetime: {twitchtracker_datetime}")
                    return twitchtracker_datetime
    except Exception:
        pass
    # Method 3: Using Selenium     
    print("Opening Twitchtracker with browser...")
    with SB(uc=True, headless=True) as sb:
        try:
            sb.driver.uc_open_with_reconnect(twitchtracker_url, reconnect_time=3)
            handle_cloudflare(sb)

            bs = BeautifulSoup(sb.driver.page_source, 'html.parser')
            description_meta = bs.find('meta', {'name': 'description'})
            twitchtracker_datetime = None

            if description_meta:
                description_content = description_meta.get('content')
                match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', description_content)
                if match:
                    twitchtracker_datetime = match.group(0)
                    print(f"Datetime: {twitchtracker_datetime}")
                    return twitchtracker_datetime
        except Exception:
            pass
    return None
                    

def parse_datetime_sullygnome(sullygnome_url):
    print("\nRetrieving stream datetime from Sullygnome...")

    try:
        # Method 1: Using requests
        response = requests.get(sullygnome_url, headers=return_user_agent(), timeout=10)
        if response.status_code == 200:
        
            bs = BeautifulSoup(response.content, 'html.parser')
            stream_date = bs.find_all('div', {'class': 'MiddleSubHeaderItemValue'})[6].text
            modified_stream_date = remove_chars_from_ordinal_numbers(stream_date)
            formatted_stream_date = datetime.strptime(modified_stream_date, "%A %d %B %I:%M%p").strftime("%m-%d %H:%M:%S")
            sullygnome_datetime = str(datetime.now().year) + "-" + formatted_stream_date

            if sullygnome_datetime:
                print(f"Datetime: {sullygnome_datetime}")
                return sullygnome_datetime
    
    # Method 2: Using grequests
        retries = 10
        reqs = [grequests.get(sullygnome_url, headers=return_user_agent()) for _ in range(retries)]
        for response in grequests.imap(reqs, size=100):

            if response.status_code == 200:
                bs = BeautifulSoup(response.content, 'html.parser')
                sullygnome_datetime = bs.find_all('div', {'class': 'MiddleSubHeaderItemValue'})[6].text
                modified_stream_date = remove_chars_from_ordinal_numbers(sullygnome_datetime)
                formatted_stream_date = datetime.strptime(modified_stream_date, "%A %d %B %I:%M%p").strftime("%m-%d %H:%M:%S")
                sullygnome_datetime = str(datetime.now().year) + "-" + formatted_stream_date

                if sullygnome_datetime:
                    print(f"Datetime: {sullygnome_datetime}")
                    return sullygnome_datetime
    except Exception:
        pass
    # Method 3: Using Selenium
    print("Opening Sullygnome with browser...")
    with SB(uc=True, headless=True) as sb:

        try: 
            sb.driver.uc_open_with_reconnect(sullygnome_url, reconnect_time=3)
            handle_cloudflare(sb)

            sullygnome_datetime = sb.driver.find_elements(By.CLASS_NAME, "MiddleSubHeaderItemValue")[6].get_attribute("innerHTML")
            modified_stream_date = remove_chars_from_ordinal_numbers(sullygnome_datetime)
            if modified_stream_date is None:
                return None
            formatted_stream_date = datetime.strptime(modified_stream_date, "%A %d %B %I:%M%p").strftime("%m-%d %H:%M:%S")
            sullygnome_datetime = str(datetime.now().year) + "-" + formatted_stream_date

            if sullygnome_datetime:
                print(f"Datetime: {sullygnome_datetime}")
                return sullygnome_datetime
        except Exception:
            pass
    return None


def unmute_vod(m3u8_link):
    counter = 0
    video_filepath = get_vod_filepath(parse_streamer_from_m3u8_link(m3u8_link), parse_video_id_from_m3u8_link(m3u8_link))
    write_m3u8_to_file(m3u8_link, video_filepath)
    file_contents = read_text_file(video_filepath)
    if is_video_muted(m3u8_link):
        with open(video_filepath, "w", encoding="utf-8") as video_file:
            for segment in file_contents:
                m3u8_link = m3u8_link.replace("index-dvr.m3u8", "")
                if "-unmuted" in segment and not segment.startswith("#"):
                    counter += 1
                    video_file.write(f"{m3u8_link}{counter - 1}-muted.ts\n")
                elif "-unmuted" not in segment and not segment.startswith("#"):
                    counter += 1
                    video_file.write(f"{m3u8_link}{counter - 1}.ts\n")
                else:
                    video_file.write(f"{segment}\n")
        print(f"{os.path.normpath(video_filepath)} has been unmuted!\n")
    else:
        with open(video_filepath, "w", encoding="utf-8") as video_file:
            for segment in file_contents:
                m3u8_link = m3u8_link.replace("index-dvr.m3u8", "")
                if not segment.startswith("#"):
                    video_file.write(f"{m3u8_link}{counter}.ts\n")
                    counter += 1
                else:
                    video_file.write(f"{segment}\n")


def mark_invalid_segments_in_playlist(m3u8_link):
    unmute_vod(m3u8_link)
    vod_file_path = get_vod_filepath(parse_streamer_from_m3u8_link(m3u8_link), parse_video_id_from_m3u8_link(m3u8_link))
    with open(vod_file_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    print("Checking for invalid segments...")
    segments = validate_playlist_segments(get_all_playlist_segments(m3u8_link))
    if not segments:
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
    input('Press Enter to continue...')


def return_m3u8_duration(m3u8_link):
    total_duration = 0
    file_contents = requests.get(m3u8_link, stream=True, timeout=30).text.splitlines()
    for line in file_contents:
        if line.startswith("#EXTINF:"):
            segment_duration = float(line.split(":")[1].split(",")[0])
            total_duration += segment_duration
    total_minutes = int(total_duration // 60)
    return total_minutes


def process_m3u8_configuration(m3u8_link):
    playlist_segments = get_all_playlist_segments(m3u8_link)
    if is_video_muted(m3u8_link):
        print("Video contains muted segments")
        if read_config_by_key('settings', 'UNMUTE_VIDEO'):
            unmute_vod(m3u8_link)
    else:
        print("Video doesn't contain muted segments")
        os.remove(get_vod_filepath(parse_streamer_from_m3u8_link(m3u8_link), parse_video_id_from_m3u8_link(m3u8_link)))
    if read_config_by_key('settings', 'CHECK_SEGMENTS'):
        print("Checking valid segments...")
        validate_playlist_segments(playlist_segments)


def get_all_playlist_segments(m3u8_link):
    counter = 0
    segment_list = []
    video_file_path = get_vod_filepath(parse_streamer_from_m3u8_link(m3u8_link), parse_video_id_from_m3u8_link(m3u8_link))
    write_m3u8_to_file(m3u8_link, video_file_path)
    file_contents = read_text_file(video_file_path)
    with open(video_file_path, "w", encoding="utf-8") as video_file:
        for segment in file_contents:
            m3u8_link = m3u8_link.replace("index-dvr.m3u8", "")
            if "-unmuted" in segment and not segment.startswith("#"):
                counter += 1
                new_segment = f"{m3u8_link}{counter - 1}-muted.ts"
                video_file.write(f"{new_segment}\n")
                segment_list.append(new_segment)
            elif "-unmuted" not in segment and not segment.startswith("#"):
                counter += 1
                new_segment = f"{m3u8_link}{counter - 1}.ts"
                video_file.write(f"{new_segment}\n")
                segment_list.append(new_segment)
            else:
                video_file.write(f"{segment}\n")
    video_file.close()
    return segment_list


def validate_playlist_segments(segments):
    valid_segments = []
    all_segments = [url.strip() for url in segments]
    available_segment_count = 0

    def fetch_status(url):
        nonlocal available_segment_count, valid_segments
        try:
            response = requests.head(url, timeout=30)
            if response.status_code == 200:
                available_segment_count += 1
                valid_segments.append(response.url)
            return response
        except Exception:
            return None

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(fetch_status, url) for url in all_segments]
        for i in enumerate(concurrent.futures.as_completed(futures)):
            index, _ = i
            print(f"\rChecking segments {index + 1} / {len(all_segments)}", end="")

    if available_segment_count == len(all_segments) or available_segment_count == 0:
        print("\nAll Segments are Available.\n")
    elif available_segment_count < len(all_segments):
        print(f"\n{available_segment_count} out of {len(all_segments)} Segments are Available. See option 4 on the menu to recheck segments availability.\n")

    return valid_segments


def vod_recover(streamer_name, video_id, timestamp, tracker_url=None):
    vod_age = calculate_days_since_broadcast(timestamp)

    if vod_age > 60:
        print("Video is older than 60 days. Chances of recovery are very slim.")
    
    vod_url = None
    if timestamp:
        vod_url = return_supported_qualities(get_vod_urls(streamer_name, video_id, timestamp))
    if vod_url is None:
        alternate_websites = generate_website_links(streamer_name, video_id, tracker_url)

        print("Unable to recover video from original url, trying alternate sources...")
         
        all_timestamps = [timestamp]

        # check if any of the alternate websites have a different timestamp, if so try to recover the video
        for website in alternate_websites:
            parsed_timestamp = None
            if "streamscharts" in website:
                parsed_timestamp = parse_datetime_streamscharts(website)
            elif "twitchtracker" in website:
                parsed_timestamp = parse_datetime_twitchtracker(website)
            elif "sullygnome" in website:
                # if timestamp contains a year that differs from current year, skip the website
                if timestamp and datetime.now().year != int(timestamp.split("-")[0]):
                    continue
                parsed_timestamp = parse_datetime_sullygnome(website)

            if parsed_timestamp and parsed_timestamp != timestamp and parsed_timestamp not in all_timestamps:
                all_timestamps.append(parsed_timestamp)
                vod_url = return_supported_qualities(get_vod_urls(streamer_name, video_id, parsed_timestamp))
                if vod_url:
                    print("\nSuccessfully recovered video from alternate source.")
                    print(f"New URL: {vod_url}\n")
                    return vod_url
        if not vod_url:
            print("\033[91m \n--> Unable to recover the video! \033[0m")
            input("\nPress Enter to continue...")
            run_vod_recover()

    return vod_url


def bulk_vod_recovery():
    csv_file_path = get_and_validate_csv_filename()
    streamer_name = parse_streamer_from_csv_filename(csv_file_path)
    csv_file = parse_vod_csv_file(csv_file_path)
    print()
    for timestamp, video_id in csv_file.items():
        print("Recovering Video...", video_id)
        m3u8_link = get_vod_urls(streamer_name.lower(), video_id, timestamp)
        print()
        if m3u8_link is not None:
            process_m3u8_configuration(m3u8_link)
        else:
            print("No vods found using the current domain list.")
    input("Press Enter to continue...")


def clip_recover(streamer, video_id, duration):
    iteration_counter, valid_counter = 0, 0
    valid_url_list = []

    clip_format = print_clip_format_menu().split(" ")
    print("Searching...")
    full_url_list = get_all_clip_urls(get_clip_format(video_id, calculate_max_clip_offset(duration)), clip_format)

    request_session = requests.Session()
    rs = [grequests.head(u, session=request_session) for u in full_url_list]

    for response in grequests.imap(rs, size=100):
        iteration_counter += 1
        print(f'\rSearching for clips..... {iteration_counter} of {len(full_url_list)}', end=" ", flush=True)
        if response.status_code == 200:
            valid_counter += 1
            valid_url_list.append(response.url)
            print(f"- {valid_counter} Clip(s) Found", end=" ")
        else:
            print(f"- {valid_counter} Clip(s) Found", end=" ")

    print()

    if valid_url_list:
        for url in valid_url_list:
            write_text_file(url, get_log_filepath(streamer, video_id))
        if read_config_by_key('settings', 'DOWNLOAD_CLIPS') or input("Do you want to download the recovered clips (Y/N): ").upper() == "Y":
            download_clips(get_default_directory(), streamer, video_id)
        else:
            print()
        if read_config_by_key('settings', 'REMOVE_LOG_FILE'):
            os.remove(get_log_filepath(streamer, video_id))
        else:
            keep_log_option = input("Do you want to remove the log file? ")
            if keep_log_option.upper() == "Y":
                os.remove(get_log_filepath(streamer, video_id))
    else:
        print("No clips found! Returning to main menu.\n")


def get_and_validate_csv_filename():
    window = tk.Tk()
    window.wm_attributes('-topmost', 1)
    window.withdraw() 

    file_path = filedialog.askopenfilename(parent=window, title="Select The CSV File", filetypes = (("CSV files","*.csv"),("all files","*.*")))
    if not file_path:
        print("\nNo file selected! Returning to main menu.")
        return run_vod_recover()
    window.destroy()
    csv_filename = os.path.basename(file_path)
    pattern = r"^[a-zA-Z0-9_]{4,25} - Twitch stream stats"
    if bool(re.match(pattern, csv_filename)):
        return file_path
    print("The CSV filename MUST be the original filename that was downloaded from sullygnome!")


def parse_clip_csv_file(file_path):
    vod_info_dict = {}
    lines = read_csv_file(file_path)[1:]
    for line in lines:
        if line:
            stream_date = remove_chars_from_ordinal_numbers(line[1].replace('"', ""))
            modified_stream_date = datetime.strptime(stream_date, "%A %d %B %Y %H:%M").strftime("%d-%B-%Y")
            video_id = line[2].partition("stream/")[2].replace('"', "")
            duration = line[3]
            if video_id != '0':
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
    counter = 0
    display_limit = 5
    clip_format = print_clip_format_menu().split(" ")
    full_url_list = get_all_clip_urls(get_clip_format(video_id, calculate_max_clip_offset(calculate_broadcast_duration_in_minutes(hours, minutes))), clip_format)
    random.shuffle(full_url_list)
    
    request_session = requests.Session()
    print("Searching...")
    rs = (grequests.head(url, session=request_session) for url in full_url_list)
    responses = grequests.imap(rs, size=100)
    for response in responses:
        if counter < display_limit:
            if response.status_code == 200:
                counter += 1
                print(response.url)
            if counter == display_limit:
                user_option = input("Do you want to search more URLs (Y/N): ")
                if user_option.upper() == "Y":
                    display_limit += 3
        else:
            break


def bulk_clip_recovery():
    vod_counter, total_counter, valid_counter, iteration_counter = 0, 0, 0, 0
    streamer_name, csv_file_path = "", ""

    bulk_recovery_option = print_bulk_clip_recovery_menu()
    if bulk_recovery_option == "1":
        csv_file_path = get_and_validate_csv_filename()
        streamer_name = parse_streamer_from_csv_filename(csv_file_path)
    elif bulk_recovery_option == "2":
        csv_directory = input("Enter the full path where the sullygnome csv files exist: ").replace('"', '')
        streamer_name = input("Enter the streamer's name: ")
        merge_files = input("Do you want to merge the CSV files in the directory? (Y/N): ")
        if merge_files.upper() == "Y":
            merge_csv_files(streamer_name, csv_directory)
            csv_file_path = os.path.join(csv_directory, f"{streamer_name.title()}_MERGED.csv")
        else:
            csv_file_path = get_and_validate_csv_filename()
            csv_file_path = csv_file_path.replace('"', '')
    elif bulk_recovery_option == "3":
        return run_vod_recover()
    clip_format = print_clip_format_menu().split(" ")
    stream_info_dict = parse_clip_csv_file(csv_file_path)
    
    def validate_clip(url):
        try:
            response = requests.head(url, timeout=30)
            if response.status_code == 200:
                return url
        except Exception:
            return None
    
    for video_id, values in stream_info_dict.items():
        vod_counter += 1
        print(
            f"\nProcessing Past Broadcast:\n"
            f"Stream Date: {values[0].replace('-', ' ')}\n"
            f"Vod ID: {video_id}\n"
            f"Vod Number: {vod_counter} of {len(stream_info_dict)}\n")
        original_vod_url_list = get_all_clip_urls(get_clip_format(video_id, values[1]), clip_format)
        print("Searching...")
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(validate_clip, url) for url in original_vod_url_list]
            for future in concurrent.futures.as_completed(futures):
                total_counter += 1
                iteration_counter += 1
                print(f'\rSearching for clips... {iteration_counter} of {len(original_vod_url_list)}', end=" ", flush=True)
                if future.result():
                    valid_counter += 1
                    write_text_file(future.result(), get_log_filepath(streamer_name, video_id))
        
        print(f'\n{valid_counter} Clip(s) Found')

        if valid_counter != 0:
            user_option = input("Do you want to download all clips recovered (Y/N)? ")

            if user_option.upper() == "Y":
                download_clips(get_default_directory(), streamer_name, video_id)
                os.remove(get_log_filepath(streamer_name, video_id))
            else:
                print("Recovered clips logged to " + get_log_filepath(streamer_name, video_id) + "\n")
        else:
            print("No clips found!... Moving on to next vod." + "\n")
        total_counter, valid_counter, iteration_counter = 0, 0, 0
    input("Press Enter to continue...")


def download_clips(directory, streamer_name, video_id):
    download_directory = os.path.join(directory, f"{streamer_name.title()}_{video_id}")
    os.makedirs(download_directory, exist_ok=True)
    file_contents = read_text_file(get_log_filepath(streamer_name, video_id))
    if not file_contents:
        print("File is empty!")
        return
    mp4_links = [link for link in file_contents if os.path.basename(link).endswith(".mp4")]
    reqs = [grequests.get(link, stream=False) for link in mp4_links]

    print("\nDownloading clips...")
    for response in grequests.imap(reqs, size=15):
        if response.status_code == 200:
             
            offset = extract_offset(response.url)
            video_format = get_default_video_format()
            file_name = f"{streamer_name.title()}_{video_id}_{offset}{video_format}"
            try:
                with open(os.path.join(download_directory, file_name), 'wb') as x:
                    x.write(response.content)
            except ValueError:
                print(f"Failed to download... {response.url}")
        else:
            print(f"Failed to download.... {response.url}")
    
    print(f"\n\033[92m\u2713 Clips downloaded to {download_directory}\033[0m\n")
    input("Press Enter to continue...")
        

def download_m3u8_video_url(m3u8_link, output_filename):
    command = [
        'ffmpeg',
        '-i', m3u8_link,
        '-c', 'copy',
        # '-bsf:a', 'aac_adtstoasc',
        '-y',
        os.path.join(get_default_directory(), output_filename),
    ]
    subprocess.run(command, shell=True, check=True)


def download_m3u8_video_url_slice(m3u8_link, output_filename, video_start_time, video_end_time):
    command = [
        'ffmpeg',
        '-ss', video_start_time,
        '-to', video_end_time,
        '-i', m3u8_link,
        '-c', 'copy',
        # '-bsf:a', 'aac_adtstoasc',
        '-y',
        os.path.join(get_default_directory(), output_filename),

    ]
    subprocess.run(command, shell=True, check=True)


def download_m3u8_video_file(m3u8_file_path, output_filename):
    command = [
        'ffmpeg',
        '-protocol_whitelist', 'file,http,https,tcp,tls',
        '-i', m3u8_file_path,
        '-c', 'copy',
        # '-bsf:a', 'aac_adtstoasc',
        os.path.join(get_default_directory(), output_filename),
    ]
    subprocess.run(command, shell=True, check=True)

def download_m3u8_video_file_slice(m3u8_file_path, output_filename, video_start_time, video_end_time):
    command = [
        'ffmpeg',
        '-protocol_whitelist', 'file,http,https,tcp,tls',
        '-ss', video_start_time,
        '-to', video_end_time,
        '-i', m3u8_file_path,
        '-c', 'copy',
        # '-c:a', 'aac',
        '-y',
        os.path.join(get_default_directory(), output_filename),
    ]
    subprocess.run(command, shell=True, check=True)


def get_VLC_Location():
    try:
        vlc_location = read_config_by_key('settings', 'VLC_LOCATION')
        if vlc_location and os.path.isfile(vlc_location):
            return vlc_location

        possible_locations = [
            "C:/Program Files/VideoLAN/VLC/vlc.exe",  # Windows default
            "C:/Program Files (x86)/VideoLAN/VLC/vlc.exe",  # Windows x86 default
            "/Applications/VLC.app/Contents/MacOS/VLC",  # macOS default
            "/usr/bin/vlc",  # Linux default
            "/usr/local/bin/vlc"  # Additional common location for Linux
        ]
        for location in possible_locations:
            if os.path.isfile(location):
                return location

        return None
    except Exception:
        return None


def handle_vod_url_normal(vod_url):

    vod_filename = f"{parse_streamer_from_m3u8_link(vod_url)}_{parse_video_id_from_m3u8_link(vod_url)}{get_default_video_format()}"

    start = time.time()
    download_m3u8_video_url(vod_url, vod_filename)

    formatted_elapsed = f"{time.time() - start:.2f}"
    print(f"\n\033[92m\u2713 Vod downloaded to {os.path.join(get_default_directory(), vod_filename)} in {formatted_elapsed} seconds\033[0m\n")


def get_time_input_HH_MM_SS(prompt):
    while True:
        time_input = input(prompt).strip().replace("'", "").replace('"', '')
        # Check if the input follows the HH:MM:SS format and is a valid time
        if re.match(r'^(\d+):([0-5]\d):([0-5]\d)$', time_input):
            return time_input
        else:
            print("\nInvalid input format! Please enter the time in HH:MM:SS format.\n")

def get_time_input_HH_MM(prompt):
    while True:
        time_input = input(prompt).strip().replace("'", "").replace('"', '')
        # Check if the input follows the HH:MM format and is a valid time
        if re.match(r'^(\d+):([0-5]\d)$', time_input):
            return time_input
        else:
            print("\nInvalid input format! Please enter the time in HH:MM format.\n")

def get_time_input_YYYY_MM_DD_HH_MM_SS(prompt):
    while True:
        time_input = input(prompt).strip().replace("'", "").replace('"', '')
        # Check if the input follows the YYYY-MM-DD HH:MM:SS format and is a valid time

        if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', time_input):
            return time_input
        else:
            print("\nInvalid input format! Please enter the time in YYYY-MM-DD HH:MM:SS format.\n")


def handle_vod_url_trim(vod_url):

    vod_start_time = get_time_input_HH_MM_SS("Enter start time (HH:MM:SS): ")
    vod_end_time = get_time_input_HH_MM_SS("Enter end time (HH:MM:SS): ")

    raw_start_time = vod_start_time.replace(":", "")
    raw_end_time = vod_end_time.replace(":", "")

    vod_filename = f"{parse_streamer_from_m3u8_link(vod_url)}_{parse_video_id_from_m3u8_link(vod_url)}_{raw_start_time}-{raw_end_time}{get_default_video_format()}"
        
    start = time.time()
    download_m3u8_video_url_slice(vod_url, vod_filename, vod_start_time, vod_end_time)

    formatted_elapsed = f"{time.time() - start:.2f}"
    print(f"\n\033[92m\u2713 Vod downloaded to {os.path.join(get_default_directory(), vod_filename)} in {formatted_elapsed} seconds\033[0m\n")


def handle_download_menu(link):
    vlc_location = get_VLC_Location()
    exit_option = 3 if not vlc_location else 4
    
    is_live = 'video-weaver' in link
    if is_live and vlc_location:
        return handle_is_live_channel(link, vlc_location)
    
    while True:
        start_download = print_confirm_download_menu()
        if start_download == 1:
            handle_vod_url_normal(link)
            input("Press Enter to continue...")
            return run_vod_recover()
        elif start_download == 2:
            handle_vod_url_trim(link)
            input("Press Enter to continue...")
            return run_vod_recover()
        elif start_download == 3 and vlc_location:
            subprocess.Popen([vlc_location, link])
        elif start_download == exit_option:
            return run_vod_recover()
        else:
            print("\n✖  Invalid option! Please Try Again.\n")


def handle_file_download_menu(m3u8_file_path):

    vlc_location = get_VLC_Location()
    exit_option = 3 if not vlc_location else 4

    while True:
        start_download = print_confirm_download_menu()
        if start_download == 1:
            start = time.time()
            output_filename = parse_vod_filename(m3u8_file_path) + get_default_video_format()
            download_m3u8_video_file(m3u8_file_path, output_filename)

            formatted_elapsed = f"{time.time() - start:.2f}"
            print(f"\n\033[92m\u2713 Vod downloaded to {os.path.join(get_default_directory(), output_filename)} in {formatted_elapsed} seconds\033[0m\n")
            break
        elif start_download == 2:
            vod_start_time = get_time_input_HH_MM_SS("Enter start time (HH:MM:SS): ")
            vod_end_time = get_time_input_HH_MM_SS("Enter end time (HH:MM:SS): ")

            raw_start_time = vod_start_time.replace(":", "")
            raw_end_time = vod_end_time.replace(":", "")

            vod_filename = f"{parse_vod_filename(m3u8_file_path)}_{raw_start_time}-{raw_end_time}{get_default_video_format()}"
            
            start = time.time()
            download_m3u8_video_file_slice(m3u8_file_path, vod_filename, vod_start_time, vod_end_time)
    
            formatted_elapsed = f"{time.time() - start:.2f}"
            print(f"\n\033[92m\u2713 Vod downloaded to {os.path.join(get_default_directory(), vod_filename)} in {formatted_elapsed} seconds\033[0m\n")
            break
        elif start_download == 3 and vlc_location:
            subprocess.Popen([vlc_location, m3u8_file_path.replace("/", "\\")])
        elif start_download == exit_option:
            return run_vod_recover()
        else:
            print("\n✖  Invalid option! Please Try Again.\n")


def print_confirm_download_menu():
    vlc_location = get_VLC_Location()
    menu_options = ["1) Start Downloading", "2) Specify Start and End time"]
    if vlc_location:
        menu_options.append("3) Play with VLC")
    menu_options.append(f"{3 if not vlc_location else 4}) Return")
    print()
    print("\n".join(menu_options))
    try:
        return int(input("\nChoose an option: "))
    except ValueError:
        print("\n✖  Invalid option! Please Try Again.\n")
        return print_confirm_download_menu()
    

def extract_id_or_channel_from_url(url: str):
    try:
        pattern = r'twitch\.tv/(?:[^\/]+\/)?(\d+)|twitch\.tv/([^\/]+)(?!/clip)'
        match = re.search(pattern, url)
        if match:
            return match.group(1) or match.group(2)
        else:
            sys.exit("\n✖  Invalid Twitch URL! Please Try Again.\n")
    except Exception:
        sys.exit("\n✖  Invalid Twitch URL! Please Try Again.\n")


def extract_clip_slug_from_url(url):
    try:
        pattern = r'clip\/([a-zA-Z0-9\-_]+)'
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        else:
            sys.exit("\n✖  Invalid Twitch Clip URL! Please Try Again.\n")
    except Exception:
        sys.exit("\n✖  Invalid Twitch Clip URL! Please Try Again.\n")     


def handle_is_live_channel(vod_url, vlc_location):
    print("This is a live channel. Enter the Vod Url to download it or use VLC to play the stream.")
    choices = ["1) Play with VLC", "2) Enter Twitch Vod URL", "3) Return"]
    print("\n".join(choices))

    try:
        choice = int(input("\nChoose an option: "))
        if choice == 1:
            return subprocess.Popen([vlc_location, vod_url])

        elif choice == 2:
            twitch_recover()

        elif choice == 3:
            return run_vod_recover()
        else:
            print("\n✖  Invalid option! Please Try Again.\n")
            return handle_is_live_channel(vod_url, vlc_location)
    except ValueError:      
        print("\n✖  Invalid option! Please Try Again.\n")
        return handle_is_live_channel(vod_url, vlc_location)


client_id = "kimne78kx3ncx6brgo4mv6wki5h1ko"


def get_token(id: str, isVod: bool):
    try:
        headers = {
        'Client-id': client_id,
        }
    
        data = json.dumps([{
        "operationName": "PlaybackAccessToken",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "0828119ded1c13477966434e15800ff57ddacf13ba1911c129dc2200705b0712"
            }
        },
        "variables": {
            "isLive": not bool(isVod),
            "login": '' if isVod else id, 
            "isVod": bool(isVod),  
            "vodID": id if isVod else '',
            "playerType": "embed"
        }
    }])
        res = requests.post('https://gql.twitch.tv/gql',
            headers=headers,
            timeout=30,
            data=data)
        if res.status_code != 200:
            sys.exit("Request failed! Try again later.")
        
        if isVod is True:
            return res.json()[0]['data']['videoPlaybackAccessToken']
        else:
            return res.json()[0]['data']['streamPlaybackAccessToken']
    except Exception:
        return None
    

def parse_playlist(data: str):
    playlists = []
    data = data.split('\n')
    count = 0
  
    for i in data[2:]:
        count += 1
        if count % 3 == 0:
            playlists.append({
                "quality": data[count - 1].split('NAME="')[1].split('"')[0],
                "url": data[count + 1],
            })    
    return playlists


def get_playlist(id_or_url: str, isVod: bool = True):
    if id_or_url.startswith('https://www.twitch.tv/'):
        id = extract_id_or_channel_from_url(id_or_url)
        if id is None:
            sys.exit("No ID or Channel found. Exiting...")
        isVod = 'videos' in id_or_url
    else:
        id = id_or_url

    token = get_token(id, isVod)
    if token is None:
        sys.exit("\n✖  Unable to find VOD!\n")

    endpoint = 'vod' if isVod else 'api/channel/hls'
    url = f"https://usher.ttvnw.net/{endpoint}/{id}.m3u8?client_id={client_id}&token={token['value']}&sig={token['signature']}&allow_source=true&allow_audio_only=true"

    res = requests.get(url, timeout=30)   
    if res.status_code == 200:
        return parse_playlist(res.text)
    else:
        try:
            response = json.loads(res.text) 
            if response and 'error' in response[0] and response[0]['error'] == 'Manifest is restricted':
                print('\n--> Vod is Sub-Only! Try the following options:\n')
                url = website_vod_recover()
                print()
                handle_download_menu(url)
        except Exception:
            pass     
        if isVod:
            sys.exit("\n✖  Something Went Wrong! Try other Recovering Options\n")
        else:
            sys.exit('--> Stream Not Found or Not Live!\n')


def get_twitch_clip(clip_slug):
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
    try:
        response_endpoint = requests.post(url_endpoint, json=data, headers={"Client-Id": client_id}, timeout=30)
        response = response_endpoint.json()

        if 'error' in response or 'errors' in response:
            raise Exception(response.get('message', 'Unable to get clip!'))

        url = ""
        playback_access_token = response[0]['data']['clip']['playbackAccessToken']
        url = response[0]['data']['clip']['videoQualities'][0]['sourceURL'] + '?sig=' + playback_access_token['signature'] + '&token=' + requests.utils.quote(playback_access_token['value'])
    except Exception:
        raise Exception('Unable to get clip!')
    
    return url

def twitch_clip_downloader(clip_url, slug):
    print("Downloading Clip...")
    try:
        response = requests.get(clip_url, stream=True, timeout=30)
        if response.status_code != 200:
            raise Exception('Unable to download clip!')
        download_location = os.path.join(get_default_directory(), f"{slug}.mp4")
        # with open(os.path.join(get_default_directory(), f"{slug}.mp4"), "wb") as file:
        #     for chunk in response.iter_content(chunk_size=1024):
        #         if chunk:
        #             file.write(chunk)
        start = time.time()
        with open(os.path.join(get_default_directory(), download_location), 'wb') as file:
            shutil.copyfileobj(response.raw, file)

        formatted_elapsed = f"{time.time() - start:.2f}"
        print(f"\n\033[92m\u2713 Clip downloaded to {download_location} in {formatted_elapsed} seconds\033[0m\n")

        input("Press Enter to continue...")
    except Exception:
        raise Exception('Unable to download clip!')
    

def twitch_recover():
    url = print_get_twitch_url_menu()
    playlists = get_playlist(url)
    url = get_user_resolution_twitch(playlists)
    handle_download_menu(url)
    

def handle_twitch_clip(clip_url):
    slug = extract_clip_slug_from_url(clip_url)
    url = get_twitch_clip(slug)
    twitch_clip_downloader(url, slug)

  
def run_vod_recover():
    print("\nWELCOME TO VOD RECOVERY!")
    menu = 0

    while menu < 50:
        print()
        menu = print_main_menu()
        if menu == 1:
            vod_mode = print_video_mode_menu()

            if vod_mode == 1:
                link = website_vod_recover()
                print()
                handle_download_menu(link)
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
                bulk_clip_recovery()

            elif clip_type == 5:
                continue
        elif menu == 3:
            download_type = print_download_type_menu()
            if download_type == 1:
                vod_url = print_get_m3u8_link_menu()
                handle_download_menu(vod_url)
            elif download_type == 2:
                window = tk.Tk()
                window.wm_attributes('-topmost', 1)
                window.withdraw()
                directory = get_default_directory()
                file_path = filedialog.askopenfilename(parent=window,
                                  initialdir=directory,
                                  title="Select A File",
                                  filetypes = (("M3U8 files", "*.m3u8"), ("All files", "*")))
                window.destroy()
                if not file_path:
                    print("\nNo file selected! Returning to main menu.")
                    continue
                print(f"\n{file_path}")
                m3u8_file_path = file_path.strip()

                handle_file_download_menu(m3u8_file_path)
                input("Press Enter to continue...")

            elif download_type == 3:
                twitch_recover()

            elif download_type == 4:
                continue
        elif menu == 4:
            mode = print_handle_m3u8_availability_menu()
            if mode == 1:
                url = print_get_m3u8_link_menu()
                is_muted = is_video_muted(url)
                if is_muted:
                    print("Video contains muted segments")
                    choice = input("Do you want to unmute the video? (Y/N): ")
  
                    if choice.upper() == "Y":
                        print()
                        unmute_vod(url)
                        input("Press Enter to continue...")
                    else:
                        print("\nReturning to main menu...")
                        continue
                else:
                    print("Video is not muted")
            elif mode == 2:
                url = print_get_m3u8_link_menu()
                mark_invalid_segments_in_playlist(url)
                
            elif menu == 3:
                continue
        elif menu == 5:
            set_default_video_format()
        elif menu == 6:
            set_default_directory()

        elif menu == 7:
            print_help()
            input("Press Enter to return to the main menu...")
        elif menu == 8:
            print("\nExiting...\n")
            sys.exit()
        else:
            run_vod_recover()


if __name__ == '__main__':
    try:
        run_vod_recover()
    except Exception as e:
        print("An error occurred:", e)
        input("Press Enter to exit.")
