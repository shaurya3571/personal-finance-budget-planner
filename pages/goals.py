import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from pages.base import Page
from services import days_left, parse_amount, parse_date
from theme import C
from widgets import heading, Card, ProgressBar, ScrollFrame, label


class GoalsPage(Page):
    title = "Savings goals"

    def build(self):
        body = self.body
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        form = Card(body)
        form.grid(row=0, column=0, sticky="ns", padx=(0, 16))
        f = form.body
        heading(f, "New goal").pack(anchor="w", pady=(0, 6))
        self.vars = {k: tk.StringVar() for k in ("name", "target", "saved", "deadline")}
        for key, text in (("name", "Goal name"), ("target", "Target amount (₹)"),
                          ("saved", "Already saved (₹, optional)"), ("deadline", "Deadline (YYYY-MM-DD, optional)")):
            label(f, text, 9, "bold", C["muted"]).pack(anchor="w", pady=(10, 3))
            entry = ttk.Entry(f, textvariable=self.vars[key], width=26)
            entry.pack(fill="x")
            entry.bind("<Return>", lambda e: self.add())
        ttk.Button(f, text="Create goal", style="Primary.TButton", command=self.add).pack(fill="x", pady=(16, 0))

        self.scroll = ScrollFrame(body)
        self.scroll.grid(row=0, column=1, sticky="nsew")

    def refresh(self):
        inner = self.scroll.inner
        for w in inner.winfo_children():
            w.destroy()
        goals = self.db.list_goals()
        if not goals:
            label(inner, "No goals yet.", 11,
                  color=C["muted"], justify="center").pack(pady=60)
            return
        for g in goals:
            self._card(inner, g)

    def _card(self, parent, g):
        target, saved = g["target"], g["saved"]
        frac = saved / target
        done = saved >= target
        card = Card(parent, padding=16)
        card.pack(fill="x", pady=(0, 12), padx=(0, 6))
        f = card.body
        top = tk.Frame(f, bg=C["surface"])
        top.pack(fill="x")
        heading(top, g["name"]).pack(side="left")
        left = days_left(g["deadline"])
        if done:
            note, color = "Goal reached", C["income"]
        elif left is None:
            note, color = "No deadline", C["muted"]
        elif left < 0:
            note, color = f"{-left} days overdue", C["expense"]
        else:
            note, color = f"{left} days left", C["muted"]
        label(top, note, 9, "bold", color).pack(side="right")

        bar = ProgressBar(f, 12, C["surface"])
        bar.pack(fill="x", pady=10)
        bar.set(frac, C["income"] if done else C["primary"])

        mid = tk.Frame(f, bg=C["surface"])
        mid.pack(fill="x")
        label(mid, f"{self.app.money(saved)} of {self.app.money(target)}  ({min(frac, 1) * 100:.0f}%)",
              10, "bold").pack(side="left")
        if not done and left and left > 0:
            monthly = (target - saved) / max(left / 30, 1)
            label(mid, f"Save about {self.app.money(monthly)}/month", 9, color=C["muted"]).pack(side="right")

        actions = tk.Frame(f, bg=C["surface"])
        actions.pack(fill="x", pady=(12, 0))
        ttk.Button(actions, text="Add funds", style="Ghost.TButton",
                   command=lambda gid=g["id"]: self.add_funds(gid)).pack(side="left")
        ttk.Button(actions, text="Delete", style="Danger.TButton",
                   command=lambda gid=g["id"], n=g["name"]: self.delete(gid, n)).pack(side="left", padx=8)

    def add(self):
        v = {k: var.get().strip() for k, var in self.vars.items()}
        try:
            if not v["name"]:
                raise ValueError("Please give your goal a name.")
            target = parse_amount(v["target"])
            saved = parse_amount(v["saved"]) if v["saved"] else 0.0
            deadline = parse_date(v["deadline"]).isoformat() if v["deadline"] else None
        except ValueError as err:
            messagebox.showerror("Check your entry", str(err), parent=self)
            return
        self.db.add_goal(v["name"], target, saved, deadline)
        for var in self.vars.values():
            var.set("")
        self.refresh()

    def add_funds(self, gid):
        text = simpledialog.askstring("Add funds", "How much do you want to add (₹)?", parent=self)
        if text is None:
            return
        try:
            amount = parse_amount(text)
        except ValueError as err:
            messagebox.showerror("Check your entry", str(err), parent=self)
            return
        self.db.add_to_goal(gid, amount)
        self.refresh()

    def delete(self, gid, name):
        if messagebox.askyesno("Delete goal", f'Delete the goal "{name}"?', parent=self):
            self.db.delete_goal(gid)
            self.refresh()
