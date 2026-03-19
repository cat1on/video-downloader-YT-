import json
import os
import flet as ft

class ThemeManager:
    def __init__(self, filename = "config.json"):
        self.filename = filename

    def load_state(self):
        if not os.path.exists(self.filename):
            return "light"
        
        with open(self.filename, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return data.get("theme", "light")
            except:
                return "light"

    def save_state(self, state):

        theme_str = state.value if isinstance(state, ft.ThemeMode) else str(state)

        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump({"theme": theme_str}, f, ensure_ascii=False, indent=2)

