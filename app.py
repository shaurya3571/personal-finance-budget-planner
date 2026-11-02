"""Main window: sidebar navigation, month selector and the page stack."""
import tkinter as tk
from tkinter import messagebox

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
        self.geometry("1280x840")
        self.minsize(1100, 760)
        self.month = current_month()
        self.pages, self.nav_items, self.current = {}, {}, None
        self.build_ui()
        self.build_menu()
        self.bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
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
        dark = theme.mode == "dark"
        toggle = tk.Label(self.sidebar_footer, text="☀  Light mode" if dark else "☾  Dark mode", anchor="w",
                          font=F(10), fg=C["sidebar_text"], bg=C["sidebar"], padx=18, pady=9, cursor="hand2")
        toggle.pack(fill="x")
        toggle.bind("<Button-1>", lambda e: self.toggle_theme())

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

    # ---- menu, shortcuts, theme, lifecycle ------------------------------
    def build_menu(self):
        bar = tk.Menu(self)
        file_menu = tk.Menu(bar, tearoff=0)
        file_menu.add_command(label="New transaction", accelerator="Ctrl+N", command=self.new_transaction)
        file_menu.add_command(label="Export all transactions…", accelerator="Ctrl+E",
                              command=lambda: self.pages["reports"].export_all())
        file_menu.add_separator()
        file_menu.add_command(label="Exit", accelerator="Ctrl+Q", command=self.on_close)
        bar.add_cascade(label="File", menu=file_menu)

        view = tk.Menu(bar, tearoff=0)
        for i, (key, text, _, _) in enumerate(REGISTRY, start=1):
            view.add_command(label=text, accelerator=f"Ctrl+{i}", command=lambda k=key: self.show(k))
        view.add_separator()
        view.add_command(label="Toggle dark mode", accelerator="Ctrl+T", command=self.toggle_theme)
        bar.add_cascade(label="View", menu=view)

        data = tk.Menu(bar, tearoff=0)
        data.add_command(label="Load demo data", command=self.load_demo)
        data.add_command(label="Delete all data…", command=self.clear_data)
        bar.add_cascade(label="Data", menu=data)

        help_menu = tk.Menu(bar, tearoff=0)
        help_menu.add_command(label="About", command=self.about)
        bar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=bar)

    def bind_shortcuts(self):
        self.bind_all("<Control-n>", lambda e: self.new_transaction())
        self.bind_all("<Control-e>", lambda e: self.pages["reports"].export_all())
        self.bind_all("<Control-t>", lambda e: self.toggle_theme())
        self.bind_all("<Control-q>", lambda e: self.on_close())
        self.bind_all("<F5>", lambda e: self.refresh())
        for i, (key, *_rest) in enumerate(REGISTRY, start=1):
            self.bind_all(f"<Control-Key-{i}>", lambda e, k=key: self.show(k))

    def new_transaction(self):
        self.show("transactions")
        self.pages["transactions"].focus_new()

    def toggle_theme(self):
        new_mode = "light" if theme.mode == "dark" else "dark"
        self.db.set_setting("theme", new_mode)
        theme.set_mode(new_mode)
        current = self.current
        self.build_ui()
        self.show(current)

    def load_demo(self):
        if not self.db.is_empty() and not messagebox.askyesno(
                "Load demo data", "Demo data will be added to your existing records. Continue?", parent=self):
            return
        self.db.seed_demo()
        self.refresh()

    def clear_data(self):
        if messagebox.askyesno("Delete all data", "This permanently deletes every transaction, budget and goal.\n\n"
                               "Do you want to continue?", icon="warning", parent=self):
            self.db.clear_all()
            self.refresh()

    def about(self):
        messagebox.showinfo("About FinTrack", "Personal Finance & Budget Planner\n\nBuilt with Python and Tkinter.\n"
                            "Data is stored locally in SQLite (finance.db).", parent=self)

    def on_close(self):
        if messagebox.askokcancel("Quit", "Close the Personal Finance & Budget Planner?", parent=self):
            self.db.close()
            self.destroy()
