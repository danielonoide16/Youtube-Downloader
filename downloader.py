from pprint import pprint
import stat
from kivy.utils import platform
import sys

import yt_dlp
import mimetypes

_original_report_error = yt_dlp.YoutubeDL.report_error

def patched_report_error(self, message, *args, **kwargs):
    print("\n========== REAL ERROR ==========")
    print(repr(message))
    raise RuntimeError(message)

yt_dlp.YoutubeDL.report_error = patched_report_error


from utils import ensure_directory
import os


DOWNLOAD_FOLDER = "downloads"
TEMP_DOWNLOAD_FOLDER = DOWNLOAD_FOLDER

print("yt-dlp version:", yt_dlp.version.__version__)


from kivy.utils import platform
from kivy.app import App
import os, shutil, sys

def prepare_ffmpeg():
    if platform != "android":
        return None

    from jnius import autoclass
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    context = PythonActivity.mActivity
    native_lib_dir = context.getApplicationInfo().nativeLibraryDir

    app_files_dir = context.getFilesDir().getAbsolutePath()
    bin_dir = os.path.join(app_files_dir, "bin")
    os.makedirs(bin_dir, exist_ok=True)

    for so_name, real_name in [("libffmpeg.so", "ffmpeg"), ("libffprobe.so", "ffprobe")]:
        src = os.path.join(native_lib_dir, so_name)
        dst = os.path.join(bin_dir, real_name)

        if not os.path.exists(src):
            print(f"ADVERTENCIA: no se encontró {src}")
            continue

        if os.path.islink(dst) or os.path.exists(dst):
            os.remove(dst)  # por si quedó una copia vieja de un build anterior

        os.symlink(src, dst)

    return bin_dir


class YouTubeDownloader:

    def __init__(self):
        print("INSIDE downloader __INIT__")
        self._last_downloaded_file = None

        if platform == "android":
            self.FFMPEG_DIR = prepare_ffmpeg()

            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            context = PythonActivity.mActivity
            native_lib_dir = context.getApplicationInfo().nativeLibraryDir

            TEMP_DOWNLOAD_FOLDER = context.getCacheDir().getAbsolutePath()


            os.environ["LD_LIBRARY_PATH"] = native_lib_dir
            print("LD_LIBRARY_PATH seteado a:", native_lib_dir)

            ffmpeg_path = os.path.join(self.FFMPEG_DIR, "ffmpeg")

            import subprocess

            try:
                r = subprocess.run(
                    [ffmpeg_path, "-version"],
                    capture_output=True,
                    text=True
                )
                print("Return code:", r.returncode)
                print(r.stdout[:300])
                print(r.stderr[:300])
            except Exception as e:
                print("FAILED:", repr(e))

            from android_storage import AndroidStorage
            self.storage = AndroidStorage()

        else:
            self.FFMPEG_DIR = None
            self.storage = None

            TEMP_DOWNLOAD_FOLDER = DOWNLOAD_FOLDER
            ensure_directory(TEMP_DOWNLOAD_FOLDER)

        self.temp_folder = TEMP_DOWNLOAD_FOLDER

    def _get_final_filename(self, d):

        if d.get("status") == "finished":
            self._last_downloaded_file = d["filename"]

    def get_video_info(self, url: str):

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 10,
            "retries": 2,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return {
            "title": info.get("title"),
            "channel": info.get("uploader"),
            "thumbnail": info.get("thumbnail"),
            "formats": info.get("formats", [])
        }

    def get_video_formats(self, url: str):
        """
        Returns one format per resolution.
        The UI will display resolutions instead of yt-dlp format IDs.
        """

        info = self.get_video_info(url)

        formats = {}
        audio_format = None

        # Find the best M4A audio stream
        for f in info["formats"]:
            if (
                f.get("vcodec") == "none"
                and f.get("acodec") != "none"
                and f.get("ext") == "m4a"
            ):
                audio_format = f["format_id"]

        # Keep only one format per resolution
        for f in info["formats"]:

            if f.get("vcodec") == "none":
                continue

            resolution = f.get("height")

            if resolution is None:
                continue

            if resolution not in formats:

                formats[resolution] = {
                    "label": f"{resolution}p",
                    "format": f"{f['format_id']}+{audio_format}" if audio_format else f["format_id"],
                    "resolution": resolution,
                    "fps": f.get("fps"),
                    "ext": f.get("ext"),
                    "filesize": f.get("filesize"),
                }

        return sorted(
            formats.values(),
            key=lambda x: x["resolution"],
            reverse=True
        )
    
    def _mime_from_filename(self, filename):

        mime, _ = mimetypes.guess_type(filename)

        return mime or "application/octet-stream"

    def download_video(
            self,
            url,
            format_code=None,
            progress_hook=None
    ):

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,

            "format": format_code if format_code else "bestvideo+bestaudio/best",

            "merge_output_format": "mp4",

            "outtmpl": os.path.join(
                self.temp_folder,
                "%(title)s.%(ext)s"
            ),

            "progress_hooks": [progress_hook] if progress_hook else [],
        }

        if self.FFMPEG_DIR:
            ydl_opts["ffmpeg_location"] = self.FFMPEG_DIR

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=True)

            filename = ydl.prepare_filename(info)

            # si hubo merge, el archivo final es mp4
            if info.get("requested_downloads") and len(info["requested_downloads"]) > 1:
                filename = os.path.splitext(filename)[0] + ".mp4"

            print("Archivo final:", filename)
            print("Existe:", os.path.exists(filename))

            if platform == "android":

                self.storage.save_and_delete(
                    filename,
                    self._mime_from_filename(filename)
                )

            return filename

    def download_audio(
            self,
            url,
            progress_hook=None
    ):
        
        hooks = [self._get_final_filename]

        if progress_hook:
            hooks.append(progress_hook)     

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,

            "format": "bestaudio[ext=m4a]",

            "outtmpl": os.path.join(
                self.temp_folder,
                "%(title)s.%(ext)s"
            ),

            "writethumbnail": True,

            "progress_hooks": hooks,

            "postprocessors": [
                {
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                    "add_chapters": False,
                },
                {
                    "key": "EmbedThumbnail",
                    "already_have_thumbnail": False,
                },
            ]
        }
   

        if self.FFMPEG_DIR:
            ydl_opts["ffmpeg_location"] = self.FFMPEG_DIR

        # import pprint

        # pprint.pprint(ydl_opts)

        # print(type(sys.stdout))
        # print(type(sys.stderr))
        # print(sys.stdout)
        # print(sys.stderr)
        # print(hasattr(sys.stderr, "write"))

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            print("error =", ydl._out_files.error)
            print("screen =", ydl._out_files.screen)
            print(type(ydl._out_files.error))
            print(type(ydl._out_files.screen))

            info = ydl.extract_info(url, download=True)


            if platform == "android":

                #filename = info["_filename"]
                filename = self._last_downloaded_file

                if filename is None:
                    raise RuntimeError("No se pudo determinar el archivo descargado")                

                if filename.endswith(".webm"):
                    filename = filename[:-5] + ".m4a"

                elif filename.endswith(".m4a"):
                    pass

                self.storage.save_and_delete(
                    filename,
                    self._mime_from_filename(filename)
                )

            return info["requested_downloads"][0]["filepath"]