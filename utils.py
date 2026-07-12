import os
import re
import requests


def sanitize_filename(filename: str) -> str:
    """
    Removes invalid filename characters.
    """

    return re.sub(r'[<>:"/\\|?*]', "", filename)


def seconds_to_time(seconds: int) -> str:
    """
    Converts seconds to HH:MM:SS.
    """

    if not seconds:
        return "00:00"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    if hours:
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    return f"{minutes:02}:{seconds:02}"


def bytes_to_mb(size: int) -> str:
    """
    Converts bytes to MB.
    """

    if not size:
        return "Unknown"

    return f"{size / (1024 * 1024):.2f} MB"


def download_thumbnail(url: str, output_file: str) -> str:
    """
    Downloads the video thumbnail.
    Returns the saved filename.
    """

    response = requests.get(url, timeout=20)
    response.raise_for_status()

    with open(output_file, "wb") as file:
        file.write(response.content)

    return output_file


def ensure_directory(path: str):
    """
    Creates a directory if it doesn't exist.
    """

    os.makedirs(path, exist_ok=True)