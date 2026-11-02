import calendar
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk

import exporter
from pages.base import Page
from services import current_month, month_label, projected_spend
from theme import C
from widgets import Card, label


class ReportsPage(Page):
    title = "Reports"

    def build(self):
        ttk.Button(self.actions, text="Export month (CSV)", style="Primary.TButton",
                   command=self.export_month).pack(side="left", padx=(0, 8))
        ttk.Button(self.actions, text="Export all transactions", style="Ghost.TButton",
                   command=self.export_all).pack(side="left")

        body = self.body
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)

        strip = Card(body, padding=16)
        strip.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        self.insights = {}
        for key, title in (("top", "TOP CATEGORY"), ("big", "BIGGEST EXPENSE"),
                           ("avg", "AVG DAILY SPEND"), ("proj", "PROJECTED MONTH-END")):
            tile = tk.Frame(strip.body, bg=C["surface"])
            tile.pack(side="left", expand=True, fill="x")
            label(tile, title, 8, "bold", C["muted"]).pack(anchor="w")
            self.insights[key] = label(tile, "-", 14, "bold")
            self.insights[key].pack(anchor="w")
            self.insights[key + "_sub"] = label(tile, "", 9, color=C["muted"])
            self.insights[key + "_sub"].pack(anchor="w")

        table = Card(body, padding=16)
        table.grid(row=1, column=0, sticky="nsew")
        label(table.body, "Category breakdown", 12, "bold").pack(anchor="w", pady=(0, 8))
        cols = ("category", "spent", "share", "budget", "remaining")
        self.tree = ttk.Treeview(table.body, columns=cols, show="headings", selectmode="none")
        for col, text, width, anchor in (("category", "Category", 200, "w"), ("spent", "Spent", 120, "e"),
                                         ("share", "Share", 90, "e"), ("budget", "Budget", 120, "e"),
                                         ("remaining", "Remaining", 130, "e")):
            self.tree.heading(col, text=text, anchor=anchor)
            self.tree.column(col, width=width, anchor=anchor, stretch=True)
        self.tree.pack(fill="both", expand=True)

    def refresh(self):
        m, db = self.app.month, self.db
        spend = db.spending_by_category(m)
        budgets = db.get_budgets()
        income, expense = db.totals(m)
        total = sum(v for _, v in spend)

        self.insights["top"].config(text=spend[0][0] if spend else "-")
        self.insights["top_sub"].config(text=f"{spend[0][1] / total * 100:.0f}% of spending" if spend else "No data")
        expenses = db.get_transactions(m, "expense")
        if expenses:
            big = max(expenses, key=lambda r: r["amount"])
            self.insights["big"].config(text=self.app.money(big["amount"]))
            self.insights["big_sub"].config(text=f'{big["note"] or big["category"]}, {big["tx_date"]}')
        else:
            self.insights["big"].config(text="-")
            self.insights["big_sub"].config(text="No data")
        today = date.today()
        elapsed = today.day if m == current_month(today) else calendar.monthrange(int(m[:4]), int(m[5:]))[1]
        self.insights["avg"].config(text=self.app.money(expense / max(elapsed, 1)))
        self.insights["avg_sub"].config(text="per day so far")
        self.insights["proj"].config(text=self.app.money(projected_spend(expense, m)))
        self.insights["proj_sub"].config(text="at the current pace")

        self.tree.tag_configure("over", foreground=C["expense"])
        self.tree.delete(*self.tree.get_children())
        for cat, spent in spend:
            limit = budgets.get(cat)
            tags = ("over",) if limit is not None and spent > limit else ()
            self.tree.insert("", "end", tags=tags, values=(
                cat, self.app.money(spent), f"{spent / total * 100:.1f}%",
                "-" if limit is None else self.app.money(limit),
                "-" if limit is None else self.app.money(limit - spent)))

    def export_month(self):
        m = self.app.month
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", initialfile=f"report-{m}.csv",
                                            filetypes=[("CSV file", "*.csv")], title="Save month report")
        if not path:
            return
        income, expense = self.db.totals(m)
        exporter.export_month_report(path, month_label(m), income, expense,
                                     self.db.spending_by_category(m), self.db.get_budgets())
        messagebox.showinfo("Export complete", f"Saved report to:\n{path}", parent=self)

    def export_all(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", initialfile="transactions.csv",
                                            filetypes=[("CSV file", "*.csv")], title="Save all transactions")
        if not path:
            return
        exporter.export_transactions(self.db.get_transactions(), path)
        messagebox.showinfo("Export complete", f"Saved transactions to:\n{path}", parent=self)
