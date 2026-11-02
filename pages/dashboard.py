import tkinter as tk
from tkinter import ttk

from pages.base import Page
from services import budget_status, month_label, savings_rate, shift_month
from theme import C, F
from widgets import BarChart, Card, DonutChart, ProgressBar, StatCard, label

STATUS_COLOR = {"ok": "income", "warn": "warn", "over": "expense"}


class DashboardPage(Page):
    title = "Dashboard"
    subtitle = "Your money at a glance"

    def build(self):
        ttk.Button(self.actions, text="+  Add transaction", style="Primary.TButton",
                   command=lambda: self.app.show("transactions")).pack()
        body = self.body
        for col in range(4):
            body.columnconfigure(col, weight=1, uniform="col")
        body.rowconfigure(1, weight=3)
        body.rowconfigure(2, weight=2)

        self.cards = {}
        for col, (key, title, accent) in enumerate((
                ("balance", "Net balance", C["primary"]), ("income", "Income", C["income"]),
                ("expense", "Expenses", C["expense"]), ("rate", "Savings rate", C["warn"]))):
            card = StatCard(body, title, accent)
            card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 0 if col == 3 else 8))
            self.cards[key] = card

        trend = Card(body)
        trend.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=(0, 8), pady=16)
        label(trend.body, "Income vs expenses", 12, "bold").pack(anchor="w")
        label(trend.body, "Last 6 months", 9, color=C["muted"]).pack(anchor="w", pady=(0, 6))
        self.bars = BarChart(trend.body)
        self.bars.pack(fill="both", expand=True)

        split = Card(body)
        split.grid(row=1, column=2, columnspan=2, sticky="nsew", padx=(8, 0), pady=16)
        label(split.body, "Spending by category", 12, "bold").pack(anchor="w")
        self.split_sub = label(split.body, "", 9, color=C["muted"])
        self.split_sub.pack(anchor="w", pady=(0, 6))
        self.donut = DonutChart(split.body)
        self.donut.pack(fill="both", expand=True)

        recent = Card(body)
        recent.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=(0, 8))
        head = tk.Frame(recent.body, bg=C["surface"])
        head.pack(fill="x")
        label(head, "Recent transactions", 12, "bold").pack(side="left")
        link = label(head, "View all →", 9, "bold", C["primary"], cursor="hand2")
        link.pack(side="right")
        link.bind("<Button-1>", lambda e: self.app.show("transactions"))
        self.recent_list = tk.Frame(recent.body, bg=C["surface"])
        self.recent_list.pack(fill="both", expand=True, pady=(8, 0))

        budgets = Card(body)
        budgets.grid(row=2, column=2, columnspan=2, sticky="nsew", padx=(8, 0))
        head = tk.Frame(budgets.body, bg=C["surface"])
        head.pack(fill="x")
        label(head, "Budget status", 12, "bold").pack(side="left")
        link = label(head, "Manage →", 9, "bold", C["primary"], cursor="hand2")
        link.pack(side="right")
        link.bind("<Button-1>", lambda e: self.app.show("budgets"))
        self.budget_list = tk.Frame(budgets.body, bg=C["surface"])
        self.budget_list.pack(fill="both", expand=True, pady=(8, 0))

    def refresh(self):
        db, m = self.db, self.app.month
        income, expense = db.totals(m)
        prev_inc, prev_exp = db.totals(shift_month(m, -1))
        prev = month_label(shift_month(m, -1), short=True)

        def delta(cur, old):
            return "" if old == 0 else f"{(cur - old) / old * 100:+.0f}% vs {prev}"

        net = db.balance()
        self.cards["balance"].set(self.app.money(net), "All-time income minus expenses",
                                  C["income"] if net >= 0 else C["expense"])
        self.cards["income"].set(self.app.money(income), delta(income, prev_inc) or "This month")
        self.cards["expense"].set(self.app.money(expense), delta(expense, prev_exp) or "This month")
        self.cards["rate"].set(f"{savings_rate(income, expense):.0f}%",
                               f"Saved {self.app.money(income - expense)} this month")

        self.bars.set(db.monthly_series(m, 6))
        spend = db.spending_by_category(m)
        self.split_sub.config(text=month_label(m))
        self.donut.set(spend, "spent")
        self._fill_recent()
        self._fill_budgets(dict(spend))

    def _fill_recent(self):
        for w in self.recent_list.winfo_children():
            w.destroy()
        rows = self.db.get_transactions(limit=3)
        if not rows:
            label(self.recent_list, "No transactions yet. Add your first one!", 10, color=C["muted"]).pack(pady=20)
        for r in rows:
            line = tk.Frame(self.recent_list, bg=C["surface"])
            line.pack(fill="x", pady=4)
            sign, color = ("+", C["income"]) if r["kind"] == "income" else ("-", C["expense"])
            dot = tk.Canvas(line, width=34, height=34, bg=C["surface"], highlightthickness=0)
            dot.create_oval(2, 2, 32, 32, fill=C["row_alt"], outline=C["border"])
            dot.create_text(17, 17, text=r["category"][0], font=F(11, "bold"), fill=color)
            dot.pack(side="left")
            info = tk.Frame(line, bg=C["surface"])
            info.pack(side="left", padx=10)
            label(info, r["note"] or r["category"], 10, "bold").pack(anchor="w")
            label(info, f'{r["category"]}  ·  {r["tx_date"]}', 8, color=C["muted"]).pack(anchor="w")
            label(line, f"{sign}{self.app.money(r['amount'])}", 11, "bold", color).pack(side="right")

    def _fill_budgets(self, spent_by_cat):
        for w in self.budget_list.winfo_children():
            w.destroy()
        budgets = self.db.get_budgets()
        if not budgets:
            label(self.budget_list, "No budgets yet. Set limits in the Budgets tab.", 10, color=C["muted"]).pack(pady=20)
            return
        rows = sorted(((c, spent_by_cat.get(c, 0.0), lim) for c, lim in budgets.items()),
                      key=lambda t: t[1] / t[2], reverse=True)[:4]
        for cat, spent, limit in rows:
            status, frac = budget_status(spent, limit)
            item = tk.Frame(self.budget_list, bg=C["surface"])
            item.pack(fill="x", pady=5)
            top = tk.Frame(item, bg=C["surface"])
            top.pack(fill="x")
            label(top, cat, 10, "bold").pack(side="left")
            label(top, f"{self.app.money(spent)} / {self.app.money(limit)}", 9, color=C["muted"]).pack(side="right")
            bar = ProgressBar(item, 8)
            bar.pack(fill="x", pady=(4, 0))
            bar.set(frac, C[STATUS_COLOR[status]])
