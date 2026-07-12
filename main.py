import os
from threading import Thread

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window

from downloader import YouTubeDownloader
from utils import download_thumbnail


from kivy.utils import platform
from kivy.core.window import Window

import traceback


if platform != "android":
    Window.size = (420, 760)


class MainLayout(BoxLayout):

    downloader = ObjectProperty(None)

    def __init__(self, **kwargs):
        self.is_downloading = False
        super().__init__(**kwargs)

        self.downloader = YouTubeDownloader()

        self.video_info = None
        self.video_formats = []

        self.selected_format = None

    # --------------------------------------------------------
    # UI EVENTS
    # --------------------------------------------------------

    def get_information(self):

        url = self.ids.url_input.text.strip()

        if not url:
            self.ids.progress_label.text = "Please enter a URL."
            return

        self.ids.progress_label.text = "Loading video information..."

        Thread(
            target=self._load_video_information,
            args=(url,),
            daemon=True
        ).start()

    def download_type_changed(self, value):

        if value == "Audio":
            self.ids.quality_box.disabled = True
            self.ids.quality_box.opacity = 0

        else:
            self.ids.quality_box.disabled = False
            self.ids.quality_box.opacity = 1

    #FOLDER

    def _folder_changed(self):
        self.ids.progress_label.text = "Download folder changed."            

    def change_download_folder(self):

        if platform != "android":
            return

        from android_storage import AndroidStorage

        storage = AndroidStorage()

        storage.choose_folder(
            lambda uri: Clock.schedule_once(
                lambda dt: (
                    self._folder_changed(),
                    self.update_folder_label()
                )
            )
        )

    def update_folder_label(self):
        if platform != "android":
            return

        from android_storage import AndroidStorage

        storage = AndroidStorage()

        uri = storage.get_saved_uri()

        if uri:
            self.ids.folder_label.text = f"Current folder:\n{uri}"
        else:
            self.ids.folder_label.text = "Current folder: Not selected"        
            
              

    # --------------------------------------------------------
    # LOAD VIDEO INFO
    # --------------------------------------------------------

    def _set_loading_state(self):
        self.ids.progress_label.text = "Fetching video info..."

    def _load_video_information(self, url):

        try:
            Clock.schedule_once(lambda dt: self._set_loading_state())

            print(f"Fetching video info for URL: {url}")
            info = self.downloader.get_video_info(url)
            print(f"Video info fetched: {info['title']}")

            formats = self.downloader.get_video_formats(url)

            thumbnail = download_thumbnail(
                info["thumbnail"],
                "thumbnail.jpg"
            )

            Clock.schedule_once(
                lambda dt:
                self._update_video_information(
                    info,
                    formats,
                    thumbnail
                )
            )


        except Exception as e:
            traceback.print_exc()

            Clock.schedule_once(
                lambda dt, error=str(e):
                    self._show_error(error)
            )

    def _update_video_information(
        self,
        info,
        formats,
        thumbnail
    ):

        self.video_info = info
        self.video_formats = formats

        self.ids.thumbnail.source = thumbnail
        self.ids.thumbnail.reload()

        self.ids.title_label.text = info["title"]
        self.ids.channel_label.text = info["channel"]

        values = ["Best"]

        for f in formats:
            values.append(f["label"])

        self.ids.quality_spinner.values = values
        self.ids.quality_spinner.text = "Best"

        self.ids.progress_bar.value = 0
        self.ids.progress_label.text = "Ready."

    # --------------------------------------------------------
    # HELPERS
    # --------------------------------------------------------

    def _show_error(self, message):

        self.ids.progress_label.text = f"Error: {message}"
        self.ids.progress_bar.value = 0

    def get_selected_format(self):

        quality = self.ids.quality_spinner.text

        if quality == "Best":
            return None

        for f in self.video_formats:

            if f["label"] == quality:
                return f["format"]

        return None
    

    # --------------------------------------------------------
    # DOWNLOAD
    # --------------------------------------------------------

    def download(self):

        url = self.ids.url_input.text.strip()

        if not url:
            self.ids.progress_label.text = "Please enter a URL."
            return

        if not self.video_info:
            self.ids.progress_label.text = "Load video info first."
            return

        if self.is_downloading:
            return

        # ---------- SOLO ANDROID ----------
        if platform == "android":

            storage = self.downloader.storage

            if not storage.has_folder():

                self.ids.progress_label.text = "Choose download folder..."

                storage.choose_folder(
                    lambda uri: Clock.schedule_once(
                        lambda dt: self.download(), 0
                    )
                )

                return
        # ----------------------------------

        self.ids.progress_label.text = "Starting download..."
        self.ids.progress_bar.value = 0

        Thread(
            target=self._start_download,
            args=(url,),
            daemon=True
        ).start()


    def _start_download(self, url):

        try:
            self.is_downloading = True

            download_type = self.ids.download_type.text

            if download_type == "Video":

                format_code = self.get_selected_format()

                self.downloader.download_video(
                    url=url,
                    format_code=format_code,
                    progress_hook=self._on_progress
                )

            else:

                self.downloader.download_audio(
                    url=url,
                    progress_hook=self._on_progress
                )

            Clock.schedule_once(
                lambda dt: self._on_download_complete()
            )

        except Exception as e:
            traceback.print_exc()

            Clock.schedule_once(
                lambda dt, error=str(e):
                    self._show_error(error)
            )

    # --------------------------------------------------------
    # PROGRESS CALLBACK
    # --------------------------------------------------------

    def _on_progress(self, d):

        if not isinstance(d, dict):
            return

        status = d.get("status")

        if status == "downloading":

            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate")

            percent = (downloaded / total * 100) if total else 0

            def update(dt):
                self.ids.progress_bar.value = percent
                self.ids.progress_label.text = f"Downloading {percent:.0f}%"

            Clock.schedule_once(update)

        elif status == "finished":

            def update(dt):
                self.ids.progress_bar.value = 100
                self.ids.progress_label.text = "Processing file..."

            Clock.schedule_once(update)

    # --------------------------------------------------------
    # COMPLETION
    # --------------------------------------------------------

    def _on_download_complete(self):
        self.is_downloading = False

        self.ids.progress_bar.value = 100
        self.ids.progress_label.text = "Download completed successfully!"


    # --------------------------------------------------------
    # STATE RESET / CLEANUP
    # --------------------------------------------------------
    def reset_ui(self):

        if not hasattr(self, "ids"):
            return

        if "progress_bar" not in self.ids:
            return

        self.ids.progress_bar.value = 0
        self.ids.progress_label.text = "Ready"

        self.video_info = None
        self.video_formats = []
        self.selected_format = None

    def on_kv_post(self, base_widget):
        Clock.schedule_once(lambda dt: self.reset_ui(), 0)

        if platform == "android":
            Clock.schedule_once(
                lambda dt: self.update_folder_label(),
                0
            )


class DownloaderApp(App):

    def build(self):
        self.title = "YouTube Downloader"

        Builder.load_file("ui.kv")
        return MainLayout()

    # def on_start(self):
    #     from android_storage import AndroidStorage

    #     storage = AndroidStorage()

    #     storage.choose_folder(
    #         lambda uri: print("Carpeta:", uri)
    #     )



if __name__ == "__main__":
    print("Downloader created")
    DownloaderApp().run()
        