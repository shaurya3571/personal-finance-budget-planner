import tkinter as tk
from tkinter import messagebox, ttk

from db import EXPENSE_CATEGORIES
from pages.base import Page
from services import budget_status, month_label, parse_amount
from theme import C, F
from widgets import Card, ProgressBar, ScrollFrame, label

STATUS = {"ok": ("On track", "income"), "warn": ("Close to limit", "warn"), "over": ("Over budget", "expense")}


class BudgetsPage(Page):
    title = "Budgets"
    subtitle = "Monthly spending limits per category"

    def build(self):
        body = self.body
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        self.summary = Card(body, padding=16)
        self.summary.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        self.tiles = {}
        for col, (key, title) in enumerate((("limit", "TOTAL BUDGET"), ("spent", "SPENT"), ("left", "REMAINING"))):
            tile = tk.Frame(self.summary.body, bg=C["surface"])
            tile.pack(side="left", expand=True, fill="x")
            label(tile, title, 8, "bold", C["muted"]).pack(anchor="w")
            self.tiles[key] = label(tile, "-", 18, "bold")
            self.tiles[key].pack(anchor="w")

        form = Card(body)
        form.grid(row=1, column=0, sticky="ns", padx=(0, 16))
        f = form.body
        label(f, "Set a budget", 13, "bold").pack(anchor="w", pady=(0, 6))
        label(f, "Saving a category again updates its limit.", 9, color=C["muted"]).pack(anchor="w")
        self.category = tk.StringVar(value=EXPENSE_CATEGORIES[0])
        self.limit = tk.StringVar()
        label(f, "Category", 9, "bold", C["muted"]).pack(anchor="w", pady=(14, 3))
        ttk.Combobox(f, textvariable=self.category, values=EXPENSE_CATEGORIES, state="readonly", width=24).pack(fill="x")
        label(f, "Monthly limit (₹)", 9, "bold", C["muted"]).pack(anchor="w", pady=(10, 3))
        entry = ttk.Entry(f, textvariable=self.limit, width=26)
        entry.pack(fill="x")
        entry.bind("<Return>", lambda e: self.save())
        ttk.Button(f, text="Save budget", style="Primary.TButton", command=self.save).pack(fill="x", pady=(16, 0))

        right = tk.Frame(body, bg=C["bg"])
        right.grid(row=1, column=1, sticky="nsew")
        self.scroll = ScrollFrame(right)
        self.scroll.pack(fill="both", expand=True)

    def refresh(self):
        month = self.app.month
        spent = dict(self.db.spending_by_category(month))
        budgets = self.db.get_budgets()
        total_limit = sum(budgets.values())
        total_spent = sum(spent.get(c, 0.0) for c in budgets)
        self.tiles["limit"].config(text=self.app.money(total_limit))
        self.tiles["spent"].config(text=self.app.money(total_spent))
        left = total_limit - total_spent
        self.tiles["left"].config(text=self.app.money(left), fg=C["income"] if left >= 0 else C["expense"])

        inner = self.scroll.inner
        for w in inner.winfo_children():
            w.destroy()
        if not budgets:
            label(inner, f"No budgets for {month_label(month)} yet.\nPick a category and set a limit on the left.",
                  11, color=C["muted"], justify="center").pack(pady=60)
            return
        ordered = sorted(budgets.items(), key=lambda kv: spent.get(kv[0], 0) / kv[1], reverse=True)
        for cat, limit in ordered:
            self._row(inner, cat, spent.get(cat, 0.0), limit)

    def _row(self, parent, cat, spent, limit):
        status, frac = budget_status(spent, limit)
        text, color_key = STATUS[status]
        card = Card(parent, padding=14)
        card.pack(fill="x", pady=(0, 10), padx=(0, 6))
        f = card.body
        top = tk.Frame(f, bg=C["surface"])
        top.pack(fill="x")
        label(top, cat, 11, "bold").pack(side="left")
        label(top, f"  {text}", 9, "bold", C[color_key]).pack(side="left")
        remove = label(top, "Remove", 9, "bold", C["muted"], cursor="hand2")
        remove.pack(side="right")
        remove.bind("<Button-1>", lambda e, c=cat: self.remove(c))
        edit = label(top, "Edit", 9, "bold", C["primary"], cursor="hand2")
        edit.pack(side="right", padx=12)
        edit.bind("<Button-1>", lambda e, c=cat, l=limit: self._load(c, l))
        bar = ProgressBar(f, 10, C["surface"])
        bar.pack(fill="x", pady=8)
        bar.set(frac, C[color_key])
        bottom = tk.Frame(f, bg=C["surface"])
        bottom.pack(fill="x")
        label(bottom, f"{self.app.money(spent)} of {self.app.money(limit)}  ({frac * 100:.0f}%)", 9, color=C["muted"]).pack(side="left")
        remaining = limit - spent
        msg = f"{self.app.money(remaining)} left" if remaining >= 0 else f"Over by {self.app.money(-remaining)}"
        label(bottom, msg, 9, "bold", C[color_key]).pack(side="right")

    def _load(self, cat, limit):
        self.category.set(cat)
        self.limit.set(f"{limit:g}")

    def save(self):
        try:
            limit = parse_amount(self.limit.get())
        except ValueError as err:
            messagebox.showerror("Check your entry", str(err), parent=self)
            return
        self.db.set_budget(self.category.get(), limit)
        self.limit.set("")
        self.app.refresh()

    def remove(self, cat):
        if messagebox.askyesno("Remove budget", f"Remove the budget for {cat}?", parent=self):
            self.db.delete_budget(cat)
            self.app.refresh()
