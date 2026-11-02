import tkinter as tk
from datetime import date

from pages.base import Page
from services import (budget_status, cumulative, current_month, daily_expense_totals, month_label,
                      savings_rate, shift_month, weekday_totals)
from theme import C
from widgets import (CalendarHeatmap, Card, ColumnChart, HBarChart, LineChart, RingGauge, ScrollFrame,
                     heading, label)

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
STATUS_COLOR = {"ok": "income", "warn": "warn", "over": "expense"}


class AnalyticsPage(Page):
    title = "Analytics"

    def build(self):
        scroll = ScrollFrame(self.body)
        scroll.pack(fill="both", expand=True)
        grid = scroll.inner
        for col in range(6):
            grid.columnconfigure(col, weight=1, uniform="a")

        self.pace_sub = self._panel(grid, "Spending pace", 0, 0, 4)
        self.pace = LineChart(self.pace_sub[0], 200)
        self.pace.pack(fill="x")

        rings = self._panel(grid, "Month health", 0, 4, 2)
        row = tk.Frame(rings[0], bg=C["surface"])
        row.pack()
        self.ring_save = RingGauge(row, "Savings rate", 130)
        self.ring_save.pack(side="left", padx=6)
        self.ring_budget = RingGauge(row, "Budget used", 130)
        self.ring_budget.pack(side="left", padx=6)
        rings[1].config(text="Share of income kept, and share of budgets spent")

        self.cal_sub = self._panel(grid, "Spending calendar", 1, 0, 3)
        self.calendar = CalendarHeatmap(self.cal_sub[0], 250)
        self.calendar.pack(fill="x")

        self.week_sub = self._panel(grid, "Spending by weekday", 1, 3, 3)
        self.weekdays = ColumnChart(self.week_sub[0], 250)
        self.weekdays.pack(fill="x")

        self.top_sub = self._panel(grid, "Top categories", 2, 0, 3)
        self.top = HBarChart(self.top_sub[0], 220)
        self.top.pack(fill="x")

        self.net_sub = self._panel(grid, "Net savings by month", 2, 3, 3)
        self.net = ColumnChart(self.net_sub[0], 220)
        self.net.pack(fill="x")

    def _panel(self, grid, title, row, col, span):
        """Card with a title and a muted caption; returns (container, caption_label)."""
        card = Card(grid)
        card.grid(row=row, column=col, columnspan=span, sticky="nsew",
                  padx=(0 if col == 0 else 8, 0 if col + span == 6 else 8), pady=(0, 16))
        heading(card.body, title).pack(anchor="w")
        caption = label(card.body, "", 9, color=C["muted"])
        caption.pack(anchor="w", pady=(0, 8))
        return card.body, caption

    def refresh(self):
        m, db = self.app.month, self.db
        rows = db.get_transactions()
        prev = shift_month(m, -1)

        this_days, prev_days = daily_expense_totals(rows, m), daily_expense_totals(rows, prev)
        today = date.today()
        upto = today.day if m == current_month() else (None if m < current_month() else 0)
        count = max(len(this_days), len(prev_days))
        pad = lambda vals: vals + [None] * (count - len(vals))
        self.pace.set([(month_label(prev, short=True), C["muted"], pad(cumulative(prev_days))),
                       (month_label(m, short=True), C["primary"], pad(cumulative(this_days, upto)))], count)
        gap = sum(this_days[:upto or len(this_days)]) - sum(prev_days[:upto or len(prev_days)])
        self.pace_sub[1].config(text=f"Cumulative spend, day by day. {self.app.money(abs(gap))} "
                                     f"{'more' if gap > 0 else 'less'} than {month_label(prev)} at this point")

        income, expense = db.totals(m)
        rate = max(savings_rate(income, expense), 0) / 100
        self.ring_save.set(rate, C["income"] if rate >= 0.2 else C["warn"])
        budgets = db.get_budgets()
        spent = dict(db.spending_by_category(m))
        total_budget = sum(budgets.values())
        used = sum(spent.get(c, 0.0) for c in budgets) / total_budget if total_budget else 0.0
        self.ring_budget.set(used, C[STATUS_COLOR[budget_status(used, 1.0)[0]]])

        self.cal_sub[1].config(text=f"{month_label(m)}, darker means more spent")
        self.calendar.set(m, this_days)

        months = {shift_month(m, -i) for i in range(6)}
        totals = weekday_totals(rows, months)
        peak = max(totals) if totals else 0
        self.week_sub[1].config(text="Last 6 months, busiest day highlighted")
        self.weekdays.set(list(zip(DAYS, totals)),
                          lambda i, v: C["expense"] if v == peak and v > 0 else C["primary"])

        self.top_sub[1].config(text=month_label(m))
        self.top.set(db.spending_by_category(m)[:6])

        series = db.monthly_series(m, 6)
        self.net_sub[1].config(text="Income minus expenses, last 6 months")
        self.net.set([(month_label(ym, short=True), inc - exp) for ym, inc, exp in series],
                     lambda i, v: C["income"] if v >= 0 else C["expense"])
