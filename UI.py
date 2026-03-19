import warnings
warnings.filterwarnings("ignore")

import asyncio
import os
import flet as ft

from changer_theme import ThemeManager
from theme_controller import ThemeController
from utils import is_valid_url, get_video_data, download_video


class DownloaderApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Downloader"
        self.page.vertical_alignment = ft.MainAxisAlignment.CENTER
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        self.is_cancelled = False
        self.current_video_url = None
        self.last_requested_url = None
        self.request_id = 0

        self.manager = ThemeManager()
        self.page.theme_mode = self.manager.load_state()

        icon = ft.Icons.LIGHT_MODE if self.page.theme_mode == "dark" else ft.Icons.DARK_MODE

        self.COLOR_WHITE = ft.Colors.WHITE
        self.COLOR_DARK_FIELD = ft.Colors.BLACK_87
        self.TEXT_BLACK = ft.Colors.BLACK
        self.TEXT_WHITE = ft.Colors.WHITE

        self.loader = ft.ProgressRing(
            width=40,
            height=40,
            visible=False
        )

        self.video_image = ft.Image(
            src="",
            width=320,
            height=180,
            border_radius=15,
            visible=False,
            gapless_playback=True
        )

        self.video_title = ft.Text(
            value="",
            weight=ft.FontWeight.BOLD,
            size=16,
            text_align=ft.TextAlign.CENTER
        )

        self.quality_dropdown = ft.Dropdown(
            label="Quality",
            width=220,
            visible=False,
            on_select=self.quality_changed
        )

        self.progress_bar = ft.ProgressBar(
            width=300,
            value=0,
            visible=False,
            color=ft.Colors.GREEN
        )

        self.progress_text = ft.Text("0%", visible=False)
        self.status_text = ft.Text("", size=16, visible=False)

        self.info_container = ft.Column(
            controls=[
                self.video_image,
                self.video_title,
                self.quality_dropdown
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            visible=False
        )

        self.download_btn = ft.ElevatedButton(
            content=ft.Text("Download"),
            icon=ft.Icons.DOWNLOAD,
            bgcolor=ft.Colors.GREEN_700,
            color=ft.Colors.WHITE,
            visible=False,
            on_click=self.start_download
        )

        self.cancel_btn = ft.ElevatedButton(
            content=ft.Text("Cancel"),
            icon=ft.Icons.CANCEL,
            bgcolor=ft.Colors.RED_600,
            color=ft.Colors.WHITE,
            visible=False,
            on_click=self.cancel_download
        )

        self.url_field = ft.TextField(
            hint_text="Insert a link to the video",
            border_radius=30,
            bgcolor=self.COLOR_DARK_FIELD if self.page.theme_mode == "light" else self.COLOR_WHITE,
            color=self.TEXT_WHITE if self.page.theme_mode == "light" else self.TEXT_BLACK,
            border_color=ft.Colors.TRANSPARENT,
            border_width=1,
            height=75,
            on_change=self.validate,
            content_padding=ft.Padding.only(left=20, right=20),
            suffix=ft.Container(
                content=ft.Icon(
                    icon=ft.Icons.CLOSE,
                    color=ft.Colors.RED_600,
                    size=16
                ),
                on_click=self.clear_field,
                padding=0,
                margin=0,
                ink=True
            )
        )

        self.theme_controller = ThemeController(
            self.page,
            self.url_field,
            self.manager
        )

        self.page.appbar = ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.FOLDER_OPEN,
                tooltip="Open downloads folder",
                on_click=self.open_downloads_folder
            ),
            actions=[
                ft.IconButton(
                    icon=icon,
                    on_click=self.theme_controller.toggle
                )
            ]
        )

        self.page.add(
            ft.Column(
                controls=[
                    ft.Container(
                        content=self.url_field,
                        margin=ft.Margin.only(bottom=20, top=40),
                        padding=ft.Padding.symmetric(horizontal=20)
                    ),
                    ft.Row(
                        controls=[self.loader],
                        alignment=ft.MainAxisAlignment.CENTER
                    ),
                    self.info_container,
                    ft.Row(
                        controls=[self.download_btn, self.cancel_btn],
                        alignment=ft.MainAxisAlignment.CENTER
                    ),
                    ft.Column(
                        controls=[
                            self.progress_bar,
                            self.progress_text,
                            self.status_text
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                expand=True
            )
        )

    def open_downloads_folder(self, e):
        path = os.path.join(os.path.expanduser("~"), "Downloads", "VideoDownloader")
        os.makedirs(path, exist_ok=True)

        try:
            os.startfile(path)
        except AttributeError:
            self.status_text.visible = True
            self.status_text.value = f"Open this folder manually: {path}"
            self.page.update()

    def check_is_cancelled(self):
        return self.is_cancelled

    def clear_field(self, e):
        self.url_field.value = ""
        self.current_video_url = None
        self.last_requested_url = None
        self.reset_video_info()
        self.validate()
        self.page.update()

    def reset_video_info(self):
        self.video_image.src = ""
        self.video_title.value = ""
        self.quality_dropdown.options = []
        self.quality_dropdown.value = None

        self.video_image.visible = False
        self.quality_dropdown.visible = False
        self.info_container.visible = False
        self.download_btn.visible = False
        self.cancel_btn.visible = False

        self.progress_bar.visible = False
        self.progress_bar.value = 0
        self.progress_text.visible = False
        self.progress_text.value = "0%"
        self.status_text.visible = False
        self.status_text.value = ""
        self.loader.visible = False

    def quality_changed(self, e):
        self.download_btn.visible = self.quality_dropdown.value is not None
        self.page.update()

    def validate(self, e=None):
        url = self.url_field.value.strip() if self.url_field.value else ""

        if not url:
            self.url_field.border_color = ft.Colors.TRANSPARENT
            self.url_field.border_width = 1
            self.reset_video_info()
            self.page.update()
            return

        if is_valid_url(url):
            self.url_field.border_color = ft.Colors.GREEN_600
            self.url_field.border_width = 2

            if url != self.last_requested_url:
                self.last_requested_url = url
                self.request_id += 1
                self.page.run_task(self.process_video, url, self.request_id)
        else:
            self.url_field.border_color = ft.Colors.RED_600
            self.url_field.border_width = 2
            self.reset_video_info()

        self.page.update()

    async def process_video(self, url, request_id):
        self.loader.visible = True
        self.info_container.visible = False
        self.download_btn.visible = False
        self.status_text.visible = False
        self.page.update()

        try:
            data = await asyncio.to_thread(get_video_data, url)
        except Exception as ex:
            if request_id != self.request_id:
                return

            self.loader.visible = False
            self.info_container.visible = False
            self.status_text.visible = True
            self.status_text.value = f"Failed to get video info: {ex}"
            self.page.update()
            return

        if request_id != self.request_id:
            return

        self.loader.visible = False

        if data:
            self.current_video_url = url
            self.video_image.src = data.get("thumbnail", "")
            self.video_title.value = data.get("title", "Unknown title")

            formats = data.get("formats", [])
            self.quality_dropdown.options = [ft.dropdown.Option(q) for q in formats]
            self.quality_dropdown.value = None

            self.video_image.visible = True
            self.quality_dropdown.visible = True
            self.info_container.visible = True
            self.status_text.visible = False
        else:
            self.info_container.visible = False
            self.status_text.visible = True
            self.status_text.value = "Failed to get video info."

        self.page.update()

    async def start_download(self, e):
        if not self.url_field.value or not self.quality_dropdown.value:
            self.status_text.visible = True
            self.status_text.value = "Choose a video and quality first."
            self.page.update()
            return

        self.is_cancelled = False

        self.url_field.disabled = True
        self.quality_dropdown.disabled = True
        self.download_btn.disabled = True

        self.download_btn.visible = False
        self.cancel_btn.visible = True
        self.cancel_btn.disabled = False

        self.progress_bar.visible = True
        self.progress_bar.value = 0
        self.progress_text.visible = True
        self.progress_text.value = "0%"

        self.status_text.visible = True
        self.status_text.value = "Downloading and processing. Please wait..."
        self.page.update()

        try:
            success = await asyncio.to_thread(
                download_video,
                self.url_field.value.strip(),
                self.quality_dropdown.value,
                self.update_progress,
                self.check_is_cancelled
            )
        except Exception:
            success = False

        await self.on_download_complete(success)

    def cancel_download(self, e):
        self.is_cancelled = True
        self.status_text.visible = True
        self.status_text.value = "Cancelling... deleting files."
        self.cancel_btn.disabled = True
        self.page.update()

    def update_progress(self, value):
        if self.is_cancelled:
            raise Exception("CancelledByUser")

        async def ui_update():
            self.progress_bar.value = value
            self.progress_text.value = f"{int(value * 100)}%"
            self.page.update()

        self.page.run_task(ui_update)

    async def on_download_complete(self, success):
        self.url_field.disabled = False
        self.quality_dropdown.disabled = False
        self.download_btn.disabled = False
        self.cancel_btn.disabled = False

        self.cancel_btn.visible = False
        self.progress_bar.visible = False
        self.progress_text.visible = False

        if success and not self.is_cancelled:
            self.download_btn.visible = True
            self.status_text.visible = True
            self.status_text.value = "Download finished ✅"
        elif self.is_cancelled:
            self.download_btn.visible = True
            self.status_text.visible = True
            self.status_text.value = "Download cancelled 🚫"
        else:
            self.download_btn.visible = True
            self.status_text.visible = True
            self.status_text.value = "Download failed ❌"

        self.page.update()


def main(page: ft.Page):
    DownloaderApp(page)


ft.run(main)