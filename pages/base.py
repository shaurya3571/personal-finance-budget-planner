import tkinter as tk

from theme import C
from widgets import label


class Page(tk.Frame):
    """Base class for every screen. Subclasses implement build() once and refresh() on every show."""

    title = ""
    subtitle = ""

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app, self.db = app, app.db
        self.header = tk.Frame(self, bg=C["bg"])
        self.header.pack(fill="x", padx=28, pady=(24, 12))
        text = tk.Frame(self.header, bg=C["bg"])
        text.pack(side="left")
        label(text, self.title, 20, "bold").pack(anchor="w")
        if self.subtitle:
            label(text, self.subtitle, 10, color=C["muted"]).pack(anchor="w")
        self.actions = tk.Frame(self.header, bg=C["bg"])
        self.actions.pack(side="right")
        self.body = tk.Frame(self, bg=C["bg"])
        self.body.pack(fill="both", expand=True, padx=28, pady=(0, 24))
        self.build()

    def build(self):
        pass

    def refresh(self):
        pass
