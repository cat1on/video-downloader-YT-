import flet as ft

class ThemeController:
    def __init__(self, page:ft.Page, url_field:ft.TextField, manager):
        self.page = page
        self.url_field = url_field
        self.manager = manager

    def toggle(self, e):
        
        if self.page.theme_mode == "light":
            self.page.theme_mode = "dark"
            e.control.icon = ft.Icons.LIGHT_MODE
            self.url_field.bgcolor = ft.Colors.WHITE
            self.url_field.color = ft.Colors.BLACK
        else:
            self.page.theme_mode = "light"
            e.control.icon = ft.Icons.DARK_MODE
            self.url_field.bgcolor = ft.Colors.BLACK_87
            self.url_field.color = ft.Colors.WHITE

        self.manager.save_state(self.page.theme_mode)
        self.page.update()