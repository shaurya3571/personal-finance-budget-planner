"""Reusable custom widgets: cards, stat tiles, progress bars and canvas-drawn charts."""
import math
import tkinter as tk

import theme
from services import fmt_money, month_label
from theme import C, F


def label(parent, text="", size=10, weight="normal", color=None, bg=None, **kw):
    return tk.Label(parent, text=text, font=F(size, weight), fg=color or C["text"],
                    bg=bg or parent["bg"], **kw)


class Card(tk.Frame):
    """White rounded-looking panel with a hairline border."""

    def __init__(self, parent, padding=18, **kw):
        super().__init__(parent, bg=C["surface"], highlightthickness=1,
                         highlightbackground=C["border"], **kw)
        self.body = tk.Frame(self, bg=C["surface"])
        self.body.pack(fill="both", expand=True, padx=padding, pady=padding)


class StatCard(Card):
    def __init__(self, parent, title, accent):
        super().__init__(parent, padding=16)
        tk.Frame(self, bg=accent, height=3).place(x=0, y=0, relwidth=1)
        label(self.body, title.upper(), 8, "bold", C["muted"]).pack(anchor="w")
        self.value = label(self.body, "-", 20, "bold")
        self.value.pack(anchor="w", pady=(4, 0))
        self.sub = label(self.body, "", 9, color=C["muted"])
        self.sub.pack(anchor="w")

    def set(self, value, sub="", color=None):
        self.value.config(text=value, fg=color or C["text"])
        self.sub.config(text=sub)


class ProgressBar(tk.Canvas):
    def __init__(self, parent, height=10, bg=None):
        super().__init__(parent, height=height, bg=bg or parent["bg"], highlightthickness=0)
        self._fraction, self._color = 0.0, C["primary"]
        self.bind("<Configure>", lambda e: self._draw())

    def set(self, fraction, color):
        self._fraction, self._color = max(0.0, fraction), color
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), int(self["height"])
        if w <= 1:
            return
        r = h / 2
        self._pill(0, w, h, r, C["track"])
        fill = min(self._fraction, 1.0) * w
        if fill > 0:
            self._pill(0, max(fill, h), h, r, self._color)

    def _pill(self, x0, x1, h, r, color):
        self.create_oval(x0, 0, x0 + h, h, fill=color, outline=color)
        self.create_oval(x1 - h, 0, x1, h, fill=color, outline=color)
        self.create_rectangle(x0 + r, 0, x1 - r, h, fill=color, outline=color)


class BarChart(tk.Canvas):
    """Grouped income/expense bars per month."""

    def __init__(self, parent, height=170):
        super().__init__(parent, height=height, bg=C["surface"], highlightthickness=0)
        self.data = []
        self.bind("<Configure>", lambda e: self._draw())

    def set(self, data):
        self.data = data
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 50 or not self.data:
            return
        left, right, top, bottom = 56, 10, 14, 44
        peak = max((max(i, e) for _, i, e in self.data), default=0) or 1
        step = 10 ** math.floor(math.log10(peak))
        top_value = math.ceil(peak / step) * step
        plot_h = h - top - bottom
        for i in range(5):
            y = top + plot_h * i / 4
            self.create_line(left, y, w - right, y, fill=C["border"])
            self.create_text(left - 8, y, text=fmt_money(top_value * (1 - i / 4)).replace("₹", ""),
                             anchor="e", fill=C["muted"], font=F(8))
        slot = (w - left - right) / len(self.data)
        bar_w = min(26, slot / 3)
        for idx, (ym, inc, exp) in enumerate(self.data):
            cx = left + slot * (idx + 0.5)
            for off, value, color in ((-bar_w / 2 - 2, inc, C["income"]), (bar_w / 2 + 2, exp, C["expense"])):
                bar_h = plot_h * value / top_value
                if bar_h < 1:
                    continue
                self.create_rectangle(cx + off - bar_w / 2, top + plot_h - bar_h,
                                      cx + off + bar_w / 2, top + plot_h, fill=color, outline=color)
            self.create_text(cx, h - bottom + 16, text=month_label(ym, short=True),
                             fill=C["muted"], font=F(9))
        # legend
        for x, text, color in ((left, "Income", C["income"]), (left + 80, "Expenses", C["expense"])):
            self.create_rectangle(x, h - 14, x + 10, h - 4, fill=color, outline=color)
            self.create_text(x + 16, h - 9, text=text, anchor="w", fill=C["muted"], font=F(9))


class DonutChart(tk.Canvas):
    """Category spending donut with a legend."""

    def __init__(self, parent, height=170):
        super().__init__(parent, height=height, bg=C["surface"], highlightthickness=0)
        self.items, self.center_text = [], ""
        self.bind("<Configure>", lambda e: self._draw())

    def set(self, items, center_text=""):
        self.items, self.center_text = items, center_text
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 50:
            return
        total = sum(v for _, v in self.items)
        if total <= 0:
            self.create_text(w / 2, h / 2, text="No spending this month", fill=C["muted"], font=F(10))
            return
        size = min(h - 20, w * 0.5)
        x0, y0 = 14, (h - size) / 2
        thick = size * 0.2
        box = (x0 + thick / 2, y0 + thick / 2, x0 + size - thick / 2, y0 + size - thick / 2)
        start = 90.0
        for i, (_, value) in enumerate(self.items):
            extent = min(-value / total * 360, -0.5)
            self.create_arc(*box, start=start, extent=max(extent, -359.99), style="arc",
                            outline=theme.CATEGORY_COLORS[i % len(theme.CATEGORY_COLORS)], width=thick)
            start += extent
        cx, cy = x0 + size / 2, y0 + size / 2
        self.create_text(cx, cy - 8, text=fmt_money(total), fill=C["text"], font=F(14, "bold"))
        self.create_text(cx, cy + 12, text=self.center_text, fill=C["muted"], font=F(8))
        lx, ly = x0 + size + 24, max(12, (h - min(len(self.items), 6) * 26) / 2)
        for i, (name, value) in enumerate(self.items[:6]):
            y = ly + i * 26
            color = theme.CATEGORY_COLORS[i % len(theme.CATEGORY_COLORS)]
            self.create_oval(lx, y + 3, lx + 10, y + 13, fill=color, outline=color)
            self.create_text(lx + 18, y + 8, text=name, anchor="w", fill=C["text"], font=F(9))
            self.create_text(w - 10, y + 8, text=f"{value / total * 100:.0f}%", anchor="e",
                             fill=C["muted"], font=F(9))


class ScrollFrame(tk.Frame):
    """Vertically scrollable container; put children into `.inner`."""

    def __init__(self, parent, bg=None):
        super().__init__(parent, bg=bg or parent["bg"])
        self.canvas = tk.Canvas(self, bg=self["bg"], highlightthickness=0)
        bar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=self["bg"])
        win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(win, width=e.width))
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.canvas.bind("<Enter>", lambda e: self._bind_wheel())
        self.canvas.bind("<Leave>", lambda e: self._unbind_wheel())

    def _bind_wheel(self):
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-e.delta / 120), "units"))
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

    def _unbind_wheel(self):
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.unbind_all(seq)
