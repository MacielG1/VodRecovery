from os import path
import subprocess
import sys
import ffmpeg_downloader as ffdl


def get_ffmpeg_location():
    try:
        try:
            if subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True).returncode == 0:
                return "ffmpeg"
        except FileNotFoundError:
            pass
        except subprocess.CalledProcessError:
            pass
        if path.exists(ffdl.ffmpeg_path):
            return ffdl.ffmpeg_path
    except Exception:
        return None


def download_ffmpeg():
    try:
        is_installed = get_ffmpeg_location()
        if not is_installed:
            install_command = ["ffdl", "install", "-U", "-y"]
            return subprocess.run(install_command, check=True)

        print("FFmpeg is already installed!")
    except Exception:
        sys.exit("--> Unable to download ffmpeg, try re-running this file and if the issue persists, try manually installing it from https://ffmpeg.org/download.html#get-packages")


if __name__ == "__main__":
    try:
        download_ffmpeg()
    except Exception as e:
        sys.exit(f"Error: {e}")