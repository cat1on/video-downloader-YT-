import re
import yt_dlp
import os
import sys

DOWNLOADS_PATH = os.path.join(os.path.expanduser("~"), "Downloads", "VideoDownloader")
os.makedirs(DOWNLOADS_PATH, exist_ok=True)


def resource_path(filename):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)


def get_ffmpeg_path():
    return resource_path("ffmpeg.exe")


def is_valid_url(url: str) -> bool:
    pattern = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+"
    return re.match(pattern, url) is not None


def get_video_data(url):
    ydl_opts = {
        "format": "best",
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)

            qualities = sorted(
                {
                    f"{f['height']}p"
                    for f in info.get("formats", [])
                    if f.get("height")
                },
                key=lambda x: int(x[:-1]),
                reverse=True
            )

            qualities.append("MP3 (192 kbps)")

            return {
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "formats": qualities
            }

        except Exception as e:
            print(f"Ошибка yt-dlp: {e}")
            return None


def download_video(url, quality, on_progress_callback, check_cancel):
    current_files = set()

    def progress_hook(d):
        if "filename" in d:
            current_files.add(d["filename"])

        if check_cancel():
            raise Exception("CANCELLED")

        if d["status"] == "downloading":
            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate")

            if total and total > 0:
                progress = downloaded / total
                on_progress_callback(progress)

        elif d["status"] == "finished":
            on_progress_callback(1.0)

    ffmpeg_path = get_ffmpeg_path()

    if "MP3" in quality:
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "ffmpeg_location": ffmpeg_path,
            "outtmpl": os.path.join(DOWNLOADS_PATH, "%(title)s.%(ext)s"),
            "progress_hooks": [progress_hook],
            "quiet": False,
        }
    else:
        height = quality.replace("p", "") if "p" in quality else "720"

        ydl_opts = {
            "format": (
                f"bestvideo[ext=mp4][height<={height}][vcodec^=avc1]+"
                f"bestaudio[ext=m4a][acodec^=mp4a]/best[ext=mp4]/best"
            ),
            "merge_output_format": "mp4",
            "ffmpeg_location": ffmpeg_path,
            "outtmpl": os.path.join(DOWNLOADS_PATH, "%(title)s.%(ext)s"),
            "progress_hooks": [progress_hook],
            "quiet": True,
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True

    except Exception as e:
        if str(e) == "CANCELLED":
            for filepath in current_files:
                for ext in ["", ".part", ".ytdl"]:
                    file_to_delete = filepath + ext
                    if os.path.exists(file_to_delete):
                        try:
                            os.remove(file_to_delete)
                        except OSError:
                            pass
            return "cancelled"

        print(f"Ошибка скачивания: {e}")
        return False