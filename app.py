"""Main window: sidebar navigation, month selector and the page stack."""
import tkinter as tk

import theme
from db import Database
from pages import REGISTRY
from services import current_month, fmt_money, month_label, shift_month
from theme import C, F
from widgets import label


class App(tk.Tk):
    def __init__(self, db=None):
        super().__init__()
        self.db = db or Database()
        theme.pick_font_family(self)
        theme.set_mode(self.db.get_setting("theme", "light"))
        self.title("Personal Finance & Budget Planner")
        self.geometry("1240x800")
        self.minsize(1080, 700)
        self.month = current_month()
        self.pages, self.nav_items, self.current = {}, {}, None
        self.build_ui()
        self.show(REGISTRY[0][0] if REGISTRY else None)

    # ---- helpers shared by pages --------------------------------------
    def money(self, value, decimals=0):
        return fmt_money(value, self.db.get_setting("currency", "₹"), decimals)

    def set_month(self, ym):
        self.month = ym
        self.month_text.config(text=month_label(ym))
        self.refresh()

    # ---- layout --------------------------------------------------------
    def build_ui(self):
        for child in self.winfo_children():
            if not isinstance(child, tk.Menu):
                child.destroy()
        theme.apply_style(self)
        self.pages, self.nav_items = {}, {}

        sidebar = tk.Frame(self, bg=C["sidebar"], width=232)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        brand = tk.Frame(sidebar, bg=C["sidebar"])
        brand.pack(fill="x", padx=22, pady=(26, 28))
        tk.Label(brand, text="◆", font=F(18, "bold"), fg=C["primary"], bg=C["sidebar"]).pack(side="left")
        names = tk.Frame(brand, bg=C["sidebar"])
        names.pack(side="left", padx=10)
        tk.Label(names, text="FinTrack", font=F(14, "bold"), fg="#FFFFFF", bg=C["sidebar"]).pack(anchor="w")
        tk.Label(names, text="Budget Planner", font=F(8), fg=C["sidebar_text"], bg=C["sidebar"]).pack(anchor="w")

        for key, text, icon, _ in REGISTRY:
            item = tk.Label(sidebar, text=f"  {icon}   {text}", anchor="w", font=F(11),
                            fg=C["sidebar_text"], bg=C["sidebar"], padx=18, pady=11, cursor="hand2")
            item.pack(fill="x", padx=12, pady=2)
            item.bind("<Button-1>", lambda e, k=key: self.show(k))
            item.bind("<Enter>", lambda e, k=key: self._hover(k, True))
            item.bind("<Leave>", lambda e, k=key: self._hover(k, False))
            self.nav_items[key] = item
        self.sidebar_footer = tk.Frame(sidebar, bg=C["sidebar"])
        self.sidebar_footer.pack(side="bottom", fill="x", padx=12, pady=16)

        main = tk.Frame(self, bg=C["bg"])
        main.pack(side="left", fill="both", expand=True)
        topbar = tk.Frame(main, bg=C["surface"], highlightthickness=1, highlightbackground=C["border"])
        topbar.pack(fill="x")
        label(topbar, "Viewing month", 9, color=C["muted"]).pack(side="left", padx=(28, 10), pady=14)
        for text, delta in (("‹", -1), ("›", 1)):
            b = tk.Label(topbar, text=text, font=F(14, "bold"), fg=C["text"], bg=C["surface"],
                         cursor="hand2", padx=8)
            b.pack(side="left")
            b.bind("<Button-1>", lambda e, d=delta: self.set_month(shift_month(self.month, d)))
            if delta == -1:
                self.month_text = label(topbar, month_label(self.month), 11, "bold", width=16)
                self.month_text.pack(side="left")
        today = tk.Label(topbar, text="Today", font=F(9, "bold"), fg=C["primary"], bg=C["surface"], cursor="hand2")
        today.pack(side="left", padx=14)
        today.bind("<Button-1>", lambda e: self.set_month(current_month()))

        self.stack = tk.Frame(main, bg=C["bg"])
        self.stack.pack(fill="both", expand=True)
        for key, _, _, page_cls in REGISTRY:
            page = page_cls(self.stack, self)
            page.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.pages[key] = page
        if not REGISTRY:
            label(self.stack, "No screens registered yet.", 12, color=C["muted"]).pack(pady=80)

    def _hover(self, key, inside):
        if key != self.current:
            self.nav_items[key].config(bg=C["sidebar_active"] if inside else C["sidebar"])

    def show(self, key):
        if key is None or key not in self.pages:
            return
        self.current = key
        for k, item in self.nav_items.items():
            active = k == key
            item.config(bg=C["sidebar_active"] if active else C["sidebar"],
                        fg="#FFFFFF" if active else C["sidebar_text"],
                        font=F(11, "bold" if active else "normal"))
        self.pages[key].tkraise()
        self.pages[key].refresh()

    def refresh(self):
        if self.current:
            self.pages[self.current].refresh()
