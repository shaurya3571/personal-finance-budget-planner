"""Colour palettes, fonts and ttk styling. `C` is mutated in place so every module sees theme changes."""
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

PALETTES = {
    "light": dict(
        bg="#F4F6FA", surface="#FFFFFF", sidebar="#111827", sidebar_text="#9CA3AF",
        sidebar_active="#1F2937", text="#111827", muted="#6B7280", border="#E5E7EB",
        primary="#4F46E5", primary_hover="#4338CA", on_primary="#FFFFFF",
        income="#059669", expense="#DC2626", warn="#D97706", track="#E5E7EB", row_alt="#F9FAFB",
        danger_bg="#FEE2E2", select="#E0E7FF",
    ),
    "dark": dict(
        bg="#0F172A", surface="#1E293B", sidebar="#020617", sidebar_text="#94A3B8",
        sidebar_active="#1E293B", text="#F1F5F9", muted="#94A3B8", border="#334155",
        primary="#818CF8", primary_hover="#6366F1", on_primary="#0F172A",
        income="#34D399", expense="#F87171", warn="#FBBF24", track="#334155", row_alt="#243047",
        danger_bg="#451A1A", select="#312E81",
    ),
}

CATEGORY_COLORS = ["#6366F1", "#F59E0B", "#10B981", "#EC4899", "#06B6D4",
                   "#8B5CF6", "#EF4444", "#84CC16", "#F97316", "#64748B"]

C: dict = {}
_family = "TkDefaultFont"
mode = "light"


def set_mode(name: str):
    global mode
    mode = name if name in PALETTES else "light"
    C.clear()
    C.update(PALETTES[mode])


def pick_font_family(root: tk.Misc):
    global _family
    available = set(tkfont.families(root))
    for name in ("Segoe UI", "Inter", "SF Pro Text", "Helvetica Neue", "Noto Sans", "DejaVu Sans", "Arial"):
        if name in available:
            _family = name
            return


def F(size: int = 10, weight: str = "normal"):
    return (_family, size, weight)


def apply_style(root: tk.Tk):
    """Configure ttk (clam base) to match the active palette."""
    style = ttk.Style(root)
    style.theme_use("clam")
    root.configure(bg=C["bg"])

    style.configure(".", background=C["surface"], foreground=C["text"], font=F(10),
                    bordercolor=C["border"], lightcolor=C["surface"], darkcolor=C["surface"])
    style.configure("TFrame", background=C["surface"])
    style.configure("TLabel", background=C["surface"], foreground=C["text"])

    for name, bg, fg, hover in (
        ("Primary.TButton", C["primary"], C["on_primary"], C["primary_hover"]),
        ("Ghost.TButton", C["surface"], C["text"], C["row_alt"]),
        ("Danger.TButton", C["surface"], C["expense"], C["danger_bg"]),
    ):
        style.configure(name, background=bg, foreground=fg, font=F(10, "bold"), padding=(14, 8),
                        borderwidth=1 if name != "Primary.TButton" else 0, bordercolor=C["border"],
                        focuscolor=bg, relief="flat")
        style.map(name, background=[("active", hover), ("pressed", hover)])

    style.configure("TEntry", fieldbackground=C["surface"], foreground=C["text"], padding=7,
                    bordercolor=C["border"], insertcolor=C["text"])
    style.map("TEntry", bordercolor=[("focus", C["primary"])])
    style.configure("TCombobox", fieldbackground=C["surface"], background=C["surface"],
                    foreground=C["text"], padding=6, arrowcolor=C["muted"], bordercolor=C["border"])
    style.map("TCombobox", fieldbackground=[("readonly", C["surface"])],
              foreground=[("readonly", C["text"])], bordercolor=[("focus", C["primary"])])
    root.option_add("*TCombobox*Listbox.background", C["surface"])
    root.option_add("*TCombobox*Listbox.foreground", C["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", C["primary"])
    root.option_add("*TCombobox*Listbox.selectForeground", C["on_primary"])

    style.configure("TCheckbutton", background=C["surface"], foreground=C["text"], focuscolor=C["surface"])
    style.map("TCheckbutton", background=[("active", C["surface"])])
    style.configure("TRadiobutton", background=C["surface"], foreground=C["text"], focuscolor=C["surface"])
    style.map("TRadiobutton", background=[("active", C["surface"])])

    style.configure("Treeview", background=C["surface"], fieldbackground=C["surface"],
                    foreground=C["text"], rowheight=34, borderwidth=0, font=F(10))
    style.configure("Treeview.Heading", background=C["row_alt"], foreground=C["muted"],
                    font=F(9, "bold"), padding=(8, 8), borderwidth=0, relief="flat")
    style.map("Treeview", background=[("selected", C["select"])], foreground=[("selected", C["text"])])
    style.map("Treeview.Heading", background=[("active", C["row_alt"])])
    style.configure("Vertical.TScrollbar", background=C["track"], troughcolor=C["surface"],
                    bordercolor=C["surface"], arrowcolor=C["muted"], relief="flat")


set_mode("light")
