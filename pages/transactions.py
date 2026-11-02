import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from db import EXPENSE_CATEGORIES, INCOME_CATEGORIES
from pages.base import Page
from services import parse_amount, parse_date
from theme import C, F
from widgets import heading, Card, label

ALL_CATEGORIES = sorted(set(EXPENSE_CATEGORIES + INCOME_CATEGORIES))


class TransactionsPage(Page):
    title = "Transactions"

    def build(self):
        self.editing_id = None
        body = self.body
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        self._build_form(body)
        self._build_list(body)

    # ---- form ----------------------------------------------------------
    def _build_form(self, parent):
        card = Card(parent)
        card.grid(row=0, column=0, sticky="ns", padx=(0, 16))
        f = card.body
        self.form_title = heading(f, "New transaction")
        self.form_title.pack(anchor="w", pady=(0, 12))

        self.kind = tk.StringVar(value="expense")
        row = tk.Frame(f, bg=C["surface"])
        row.pack(fill="x", pady=(0, 10))
        for text, value in (("Expense", "expense"), ("Income", "income")):
            ttk.Radiobutton(row, text=text, value=value, variable=self.kind,
                            command=self._sync_categories).pack(side="left", padx=(0, 18))

        self.amount = tk.StringVar()
        self.category = tk.StringVar()
        self.tx_date = tk.StringVar(value=date.today().isoformat())
        self.note = tk.StringVar()
        self.amount_entry = ttk.Entry(f, textvariable=self.amount, width=26)
        self._field(f, "Amount (₹)", self.amount_entry)
        self.category_box = ttk.Combobox(f, textvariable=self.category, state="readonly", width=24)
        self._field(f, "Category", self.category_box)
        self._field(f, "Date (YYYY-MM-DD)", ttk.Entry(f, textvariable=self.tx_date, width=26))
        self._field(f, "Note (optional)", ttk.Entry(f, textvariable=self.note, width=26))
        self._sync_categories()

        buttons = tk.Frame(f, bg=C["surface"])
        buttons.pack(fill="x", pady=(14, 0))
        self.save_btn = ttk.Button(buttons, text="Add transaction", style="Primary.TButton", command=self.save)
        self.save_btn.pack(fill="x")
        self.clear_btn = ttk.Button(buttons, text="Clear form", style="Ghost.TButton", command=self.clear_form)
        self.clear_btn.pack(fill="x", pady=(8, 0))
        self.status = label(f, "", 9, "bold", C["income"])
        self.status.pack(anchor="w", pady=(10, 0))
        for widget in f.winfo_children():
            if isinstance(widget, ttk.Entry):
                widget.bind("<Return>", lambda e: self.save())

    def _field(self, parent, text, widget):
        label(parent, text, 9, "bold", C["muted"]).pack(anchor="w", pady=(8, 3))
        widget.pack(fill="x")

    def _sync_categories(self):
        cats = EXPENSE_CATEGORIES if self.kind.get() == "expense" else INCOME_CATEGORIES
        self.category_box["values"] = cats
        if self.category.get() not in cats:
            self.category.set(cats[0])

    # ---- list ----------------------------------------------------------
    def _build_list(self, parent):
        card = Card(parent, padding=16)
        card.grid(row=0, column=1, sticky="nsew")
        f = card.body

        bar = tk.Frame(f, bg=C["surface"])
        bar.pack(fill="x", pady=(0, 10))
        self.search = tk.StringVar()
        self.f_kind = tk.StringVar(value="All types")
        self.f_cat = tk.StringVar(value="All categories")
        self.month_only = tk.BooleanVar(value=True)
        label(bar, "Search", 9, "bold", C["muted"]).pack(side="left", padx=(0, 6))
        ttk.Entry(bar, textvariable=self.search, width=14).pack(side="left")
        ttk.Combobox(bar, textvariable=self.f_kind, state="readonly", width=9,
                     values=["All types", "Income", "Expense"]).pack(side="left", padx=(10, 4))
        ttk.Combobox(bar, textvariable=self.f_cat, state="readonly", width=13,
                     values=["All categories"] + ALL_CATEGORIES).pack(side="left", padx=4)
        ttk.Checkbutton(bar, text="This month only", variable=self.month_only,
                        command=self.refresh).pack(side="left", padx=10)
        self.search.trace_add("write", lambda *_: self.refresh())
        for var in (self.f_kind, self.f_cat):
            var.trace_add("write", lambda *_: self.refresh())

        wrap = tk.Frame(f, bg=C["surface"])
        wrap.pack(fill="both", expand=True)
        cols = ("date", "type", "category", "note", "amount")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", selectmode="browse")
        for col, text, width, anchor in (("date", "Date", 92, "w"), ("type", "Type", 70, "w"),
                                         ("category", "Category", 120, "w"), ("note", "Note", 120, "w"),
                                         ("amount", "Amount", 100, "e")):
            self.tree.heading(col, text=text, anchor=anchor)
            self.tree.column(col, width=width, minwidth=width, anchor=anchor, stretch=col == "note")
        scroll = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda e: self.edit_selected())
        self.tree.bind("<Delete>", lambda e: self.delete_selected())

        foot = tk.Frame(f, bg=C["surface"])
        foot.pack(fill="x", pady=(10, 0))
        self.summary = label(foot, "", 9, color=C["muted"])
        self.summary.pack(side="left")
        ttk.Button(foot, text="Delete", style="Danger.TButton", command=self.delete_selected).pack(side="right")
        ttk.Button(foot, text="Edit", style="Ghost.TButton", command=self.edit_selected).pack(side="right", padx=8)

    def refresh(self):
        self.tree.tag_configure("income", foreground=C["income"])
        self.tree.tag_configure("expense", foreground=C["expense"])
        self.tree.tag_configure("odd", background=C["row_alt"])
        kind = {"Income": "income", "Expense": "expense"}.get(self.f_kind.get())
        cat = None if self.f_cat.get() == "All categories" else self.f_cat.get()
        month = self.app.month if self.month_only.get() else None
        rows = self.db.get_transactions(month, kind, cat, self.search.get().strip() or None)
        self.tree.delete(*self.tree.get_children())
        net = 0.0
        for i, r in enumerate(rows):
            sign = "+" if r["kind"] == "income" else "-"
            net += r["amount"] if r["kind"] == "income" else -r["amount"]
            tags = (r["kind"], "odd") if i % 2 else (r["kind"],)
            self.tree.insert("", "end", iid=str(r["id"]), tags=tags, values=(
                r["tx_date"], r["kind"].title(), r["category"], r["note"],
                f"{sign}{self.app.money(r['amount'], 2)}"))
        self.summary.config(text=f"{len(rows)} transactions, net {self.app.money(net)}")

    # ---- actions -------------------------------------------------------
    def save(self):
        try:
            amount = parse_amount(self.amount.get())
            tx_date = parse_date(self.tx_date.get()).isoformat()
            if not self.category.get():
                raise ValueError("Please choose a category.")
        except ValueError as err:
            messagebox.showerror("Check your entry", str(err), parent=self)
            return
        args = (self.kind.get(), amount, self.category.get(), tx_date, self.note.get())
        if self.editing_id:
            self.db.update_transaction(self.editing_id, *args)
            message = "Transaction updated"
        else:
            self.db.add_transaction(*args)
            message = "Transaction added"
        self.clear_form()
        self.status.config(text=message)
        self.after(2500, lambda: self.status.config(text=""))
        self.app.refresh()

    def clear_form(self):
        self.editing_id = None
        self.amount.set("")
        self.note.set("")
        self.tx_date.set(date.today().isoformat())
        self.form_title.config(text="New transaction")
        self.save_btn.config(text="Add transaction")
        self.clear_btn.config(text="Clear form")

    def edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select a row", "Click a transaction first, then press Edit.", parent=self)
            return
        row = next(r for r in self.db.get_transactions() if str(r["id"]) == sel[0])
        self.editing_id = row["id"]
        self.kind.set(row["kind"])
        self._sync_categories()
        self.category.set(row["category"])
        self.amount.set(f"{row['amount']:g}")
        self.tx_date.set(row["tx_date"])
        self.note.set(row["note"])
        self.form_title.config(text="Edit transaction")
        self.save_btn.config(text="Save changes")
        self.clear_btn.config(text="Cancel edit")

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        if messagebox.askyesno("Delete transaction", "Delete the selected transaction permanently?", parent=self):
            self.db.delete_transaction(int(sel[0]))
            if self.editing_id == int(sel[0]):
                self.clear_form()
            self.app.refresh()

    def focus_new(self):
        """Called by the Ctrl+N shortcut."""
        self.clear_form()
        self.amount_entry.focus_set()
