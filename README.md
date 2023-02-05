# VodRecovery
* A script to retrieve/download sub-only and deleted videos/clips from Twitch.

# About
* Developed by: Shishkebaboo (formerly ItIckeYd, the original developer who is back to work on the project after a hiatus)
* Initial release: May 3rd, 2022
* The script leverages logic from the [TwitchRecover](https://github.com/TwitchRecover/TwitchRecover) repository by daylamtayari

# Features
* Supports both manual and website vod recovery
* Can recover vods individually or in bulk using a CSV downloaded from Sullygnome.com
* Can recover clips manually or in bulk using a CSV from Sullygnome.com
* Supports downloading M3U8 links/files, with the ability to specify start/end timestamps for trimmed vods using [FFmpeg](https://ffmpeg.org/download.html)
* Compatible with TwitchTracker.com, Sullygnome.com, and Streamscharts.com
* Uses UTC timezone as default for recovering vods
* Notifies if vod is older than 60 days (due to Twitch's deletion process)

# Installation
* Download/install [Python](https://www.python.org/downloads/)
* Clone the repository
* Navigate to the cloned directory
* Install required packages with `pip install -r requirements.txt` (run in terminal)
* If you make changes to installed packages locally, you can overwrite the requirements.txt file with `pipreqs <path_of_project> --force`
* Run the script

### Expected Script Output

![Script_Preview](https://user-images.githubusercontent.com/118132878/216840958-bcf84edc-7e2e-4d1f-a060-4e1aff28761a.png)

### Expected FFmpeg Ouput
* Run the `ffmpeg` command in Command Prompt

![ffmpeg_preview](https://user-images.githubusercontent.com/118132878/216841020-617b9807-3a4c-4f03-856e-854d91306880.png)

# Optional IDEs
* [PyCharm Community Edition](https://www.jetbrains.com/pycharm/download/) (recommended)
* [Visual Studio Code](https://code.visualstudio.com/download)

# Additional Notes
* Provide at least one example when creating an issue
* If the script returns no results, try vods from other streamers. If the other vods return results, it is likely that the original vods don't exist.

# Support the Project
* Donations are appreciated but not expected - [PayPal](https://paypal.me/VodRecovery)

# Latest Release
* [Release - 1.0.0.4](https://github.com/Shishkebaboo/VodRecovery/releases/tag/vodrecovery-1.0.0.4)
* For the most updated code, clone the main branch of the repository.

