import os
import re
import subprocess
import sys

try:
    from packaging.version import Version, InvalidVersion
except ImportError:
    from pip._vendor.packaging.version import Version, InvalidVersion

from importlib.metadata import version as get_installed_distribution_version, PackageNotFoundError


def install_requirements(requirements_path):
    with open(requirements_path, encoding='utf-8') as f:
        requirement_lines = f.read().splitlines()

    for raw_line in requirement_lines:
        requirement = normalize_requirement_line(raw_line)
        if requirement is None:
            continue

        full_spec_for_pip = requirement["full_spec_for_pip"]
        dist_name = requirement["distribution_name"]
        operator = requirement["operator"]
        version_str = requirement["version"]

        if is_requirement_satisfied(dist_name, operator, version_str):
            continue

        try:
            spec_to_install = full_spec_for_pip if operator in ('==', '>=') else requirement["name_for_pip"]
            print(f"Installing {spec_to_install}...")
            subprocess.run([sys.executable, "-m", "pip", "install", spec_to_install, "-q", "--no-warn-conflicts"], check=True)
        except subprocess.CalledProcessError:
            base_name_for_pip = requirement["name_for_pip"]
            print(f"\n\033[34mFailed to install {full_spec_for_pip}. Trying again...\033[0m")
            print(f"Installing {base_name_for_pip}...")
            subprocess.run([sys.executable, "-m", "pip", "install", base_name_for_pip, "-q", "--no-warn-conflicts"], check=True)


def normalize_requirement_line(line):
    if not line:
        return None

    no_comment = line.split('#', 1)[0].strip()
    if not no_comment:
        return None

    before_marker, _, _ = no_comment.partition(';')
    spec_without_marker = before_marker.strip()

    name_for_pip = spec_without_marker

    operator = None
    version_str = None
    for op in ("==", ">="):
        if op in spec_without_marker:
            parts = spec_without_marker.split(op, 1)
            name_part = parts[0]
            version_str = parts[1].strip()
            operator = op
            break
    else:
        name_part = spec_without_marker

    distribution_name = re.split(r"\[", name_part.strip(), maxsplit=1)[0].strip()

    return {
        "name_for_pip": name_for_pip,
        "distribution_name": distribution_name,
        "operator": operator,
        "version": version_str,
        "full_spec_for_pip": no_comment,
    }


def is_requirement_satisfied(distribution_name, operator, version_str):
    try:
        installed_version_str = get_installed_distribution_version(distribution_name)
    except PackageNotFoundError:
        return False

    if operator == '==':
        try:
            return Version(installed_version_str) >= Version(version_str)
        except (InvalidVersion, ValueError, TypeError):
            return installed_version_str == version_str

    if operator == '>=' and version_str:
        try:
            return Version(installed_version_str) >= Version(version_str)
        except (InvalidVersion, ValueError, TypeError):
            return True

    return True


def update_pip():
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "-q"],
                       capture_output=True, check=False)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"Error updating pip: {str(e)}")


if __name__ == "__main__":
    try:
        print("Installing dependencies...")
        update_pip()

        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        requirements_file = os.path.join(script_dir, 'lib', 'requirements.txt')
        install_ffmpeg_script = os.path.join(script_dir, 'lib', 'install_ffmpeg.py')
        vod_recovery_script = os.path.join(script_dir, 'vod_recovery.py')

        install_requirements(requirements_file)
        subprocess.run([sys.executable, install_ffmpeg_script], check=False)
        subprocess.run([sys.executable, vod_recovery_script], check=False)

    except (OSError, subprocess.SubprocessError) as e:
        print(f"An error occurred: {str(e)}")
        input("\nPress Enter to continue...")

