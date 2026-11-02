"""SQLite persistence layer for the Personal Finance & Budget Planner.

Every row of user data carries a `user_id`; all queries are filtered by `self.uid`
(set with set_user() after login) so one account can never see or change another's data.
"""
import calendar
import os
import random
import sqlite3
from datetime import date, timedelta

from services import shift_month

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "finance.db")

EXPENSE_CATEGORIES = [
    "Food & Dining", "Transport", "Rent", "Shopping", "Utilities",
    "Entertainment", "Health", "Education", "Subscriptions", "Other",
]
INCOME_CATEGORIES = ["Allowance", "Salary", "Business", "Freelance", "Investments", "Other"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username  TEXT NOT NULL UNIQUE COLLATE NOCASE,
    pw_hash   TEXT NOT NULL,
    created   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS login_attempts (
    username      TEXT PRIMARY KEY,
    failed        INTEGER NOT NULL DEFAULT 0,
    locked_until  REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS transactions (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL DEFAULT 0,
    kind      TEXT NOT NULL CHECK (kind IN ('income', 'expense')),
    amount    REAL NOT NULL CHECK (amount > 0),
    category  TEXT NOT NULL,
    tx_date   TEXT NOT NULL,
    note      TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_tx_user_date ON transactions(user_id, tx_date);
CREATE TABLE IF NOT EXISTS budgets (
    user_id       INTEGER NOT NULL DEFAULT 0,
    category      TEXT NOT NULL,
    monthly_limit REAL NOT NULL CHECK (monthly_limit > 0),
    PRIMARY KEY (user_id, category)
);
CREATE TABLE IF NOT EXISTS goals (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL DEFAULT 0,
    name      TEXT NOT NULL,
    target    REAL NOT NULL CHECK (target > 0),
    saved     REAL NOT NULL DEFAULT 0,
    deadline  TEXT
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
"""


class Database:
    def __init__(self, path: str = DB_PATH):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.uid = 0                       # 0 = nobody logged in (also used by unit tests)
        self._migrate()
        self.conn.executescript(SCHEMA)
        self._finish_migration()
        self.conn.commit()

    def close(self):
        self.conn.close()

    def set_user(self, uid: int):
        self.uid = uid

    # ---- upgrade databases created before user accounts existed ----------
    def _columns(self, table):
        return {r[1] for r in self.conn.execute(f"PRAGMA table_info({table})")}

    def _migrate(self):
        for table in ("transactions", "goals"):
            cols = self._columns(table)
            if cols and "user_id" not in cols:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0")
        cols = self._columns("budgets")
        if cols and "user_id" not in cols:
            self.conn.execute("ALTER TABLE budgets RENAME TO budgets_legacy")

    def _finish_migration(self):
        if self._columns("budgets_legacy"):
            self.conn.execute("INSERT OR IGNORE INTO budgets (user_id, category, monthly_limit) "
                              "SELECT 0, category, monthly_limit FROM budgets_legacy")
            self.conn.execute("DROP TABLE budgets_legacy")

    # ---- users & login attempts -----------------------------------------
    def create_user(self, username, pw_hash) -> int:
        with self.conn:
            cur = self.conn.execute("INSERT INTO users (username, pw_hash) VALUES (?, ?)", (username, pw_hash))
        return cur.lastrowid

    def get_user(self, username):
        return self.conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    def user_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def adopt_legacy(self, uid):
        """Give rows created before accounts existed (user_id 0) to the first registered user."""
        with self.conn:
            for table in ("transactions", "goals", "budgets"):
                self.conn.execute(f"UPDATE {table} SET user_id = ? WHERE user_id = 0", (uid,))

    def get_attempts(self, key):
        row = self.conn.execute("SELECT failed, locked_until FROM login_attempts WHERE username = ?", (key,)).fetchone()
        return (row["failed"], row["locked_until"]) if row else (0, 0.0)

    def set_attempts(self, key, failed, locked_until):
        with self.conn:
            self.conn.execute(
                "INSERT INTO login_attempts (username, failed, locked_until) VALUES (?, ?, ?) "
                "ON CONFLICT(username) DO UPDATE SET failed=excluded.failed, locked_until=excluded.locked_until",
                (key, failed, locked_until))

    def clear_attempts(self, key):
        with self.conn:
            self.conn.execute("DELETE FROM login_attempts WHERE username = ?", (key,))

    # ---- transactions -------------------------------------------------
    def add_transaction(self, kind, amount, category, tx_date, note="") -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO transactions (user_id, kind, amount, category, tx_date, note) VALUES (?,?,?,?,?,?)",
                (self.uid, kind, amount, category, tx_date, note.strip()),
            )
        return cur.lastrowid

    def update_transaction(self, tid, kind, amount, category, tx_date, note=""):
        with self.conn:
            self.conn.execute(
                "UPDATE transactions SET kind=?, amount=?, category=?, tx_date=?, note=? WHERE id=? AND user_id=?",
                (kind, amount, category, tx_date, note.strip(), tid, self.uid),
            )

    def delete_transaction(self, tid):
        with self.conn:
            self.conn.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (tid, self.uid))

    def get_transactions(self, month=None, kind=None, category=None, search=None, limit=None):
        sql, args = "SELECT * FROM transactions WHERE user_id = ?", [self.uid]
        if month:
            sql += " AND substr(tx_date, 1, 7) = ?"
            args.append(month)
        if kind:
            sql += " AND kind = ?"
            args.append(kind)
        if category:
            sql += " AND category = ?"
            args.append(category)
        if search:
            sql += " AND (note LIKE ? OR category LIKE ?)"
            args += [f"%{search}%", f"%{search}%"]
        sql += " ORDER BY tx_date DESC, id DESC"
        if limit:
            sql += f" LIMIT {int(limit)}"
        return self.conn.execute(sql, args).fetchall()

    def totals(self, month=None):
        """Return (income, expense) for a month, or all time when month is None."""
        sql = "SELECT kind, COALESCE(SUM(amount), 0) FROM transactions WHERE user_id = ?"
        args = [self.uid]
        if month:
            sql += " AND substr(tx_date, 1, 7) = ?"
            args.append(month)
        sql += " GROUP BY kind"
        sums = {k: v for k, v in self.conn.execute(sql, args)}
        return sums.get("income", 0.0), sums.get("expense", 0.0)

    def balance(self) -> float:
        income, expense = self.totals()
        return income - expense

    def spending_by_category(self, month):
        rows = self.conn.execute(
            "SELECT category, SUM(amount) AS total FROM transactions "
            "WHERE user_id = ? AND kind='expense' AND substr(tx_date,1,7)=? GROUP BY category ORDER BY total DESC",
            (self.uid, month),
        ).fetchall()
        return [(r["category"], r["total"]) for r in rows]

    def monthly_series(self, end_month, n=6):
        """[(ym, income, expense)] for the n months ending at end_month (oldest first)."""
        months = [shift_month(end_month, -i) for i in range(n - 1, -1, -1)]
        data = {m: [0.0, 0.0] for m in months}
        rows = self.conn.execute(
            "SELECT substr(tx_date,1,7) AS ym, kind, SUM(amount) AS total FROM transactions "
            "WHERE user_id = ? AND substr(tx_date,1,7) BETWEEN ? AND ? GROUP BY ym, kind",
            (self.uid, months[0], months[-1]),
        )
        for r in rows:
            data[r["ym"]][0 if r["kind"] == "income" else 1] = r["total"]
        return [(m, *data[m]) for m in months]

    # ---- budgets ------------------------------------------------------
    def set_budget(self, category, limit):
        with self.conn:
            self.conn.execute(
                "INSERT INTO budgets (user_id, category, monthly_limit) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id, category) DO UPDATE SET monthly_limit=excluded.monthly_limit",
                (self.uid, category, limit),
            )

    def delete_budget(self, category):
        with self.conn:
            self.conn.execute("DELETE FROM budgets WHERE user_id=? AND category=?", (self.uid, category))

    def get_budgets(self) -> dict:
        return {r["category"]: r["monthly_limit"] for r in self.conn.execute(
            "SELECT category, monthly_limit FROM budgets WHERE user_id=? ORDER BY category", (self.uid,))}

    # ---- goals --------------------------------------------------------
    def add_goal(self, name, target, saved=0.0, deadline=None) -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO goals (user_id, name, target, saved, deadline) VALUES (?,?,?,?,?)",
                (self.uid, name.strip(), target, saved, deadline or None),
            )
        return cur.lastrowid

    def list_goals(self):
        return self.conn.execute("SELECT * FROM goals WHERE user_id=? ORDER BY id", (self.uid,)).fetchall()

    def add_to_goal(self, gid, amount):
        with self.conn:
            self.conn.execute("UPDATE goals SET saved = saved + ? WHERE id=? AND user_id=?", (amount, gid, self.uid))

    def delete_goal(self, gid):
        with self.conn:
            self.conn.execute("DELETE FROM goals WHERE id=? AND user_id=?", (gid, self.uid))

    # ---- settings & housekeeping --------------------------------------
    def get_setting(self, key, default=None):
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        with self.conn:
            self.conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))

    def is_empty(self) -> bool:
        return self.conn.execute("SELECT COUNT(*) FROM transactions WHERE user_id=?", (self.uid,)).fetchone()[0] == 0

    def clear_all(self):
        """Delete the current user's transactions, budgets and goals (other accounts are untouched)."""
        with self.conn:
            for table in ("transactions", "budgets", "goals"):
                self.conn.execute(f"DELETE FROM {table} WHERE user_id=?", (self.uid,))

    def seed_demo(self, today: date | None = None):
        """Fill the current user's account with believable sample data for the last 5 months."""
        today = today or date.today()
        rng = random.Random(7)
        this_month = today.strftime("%Y-%m")

        def add(kind, ym, day, amount, cat, note):
            y, m = int(ym[:4]), int(ym[5:])
            d = date(y, m, min(day, calendar.monthrange(y, m)[1]))
            if d <= today:
                self.add_transaction(kind, round(amount, 2), cat, d.isoformat(), note)

        for back in range(4, -1, -1):
            ym = shift_month(this_month, -back)
            add("income", ym, 1, 12000, "Allowance", "Monthly allowance")
            add("income", ym, 10, rng.randint(17000, 26000), "Business", "Electronics sales profit")
            add("expense", ym, 3, 7000, "Rent", "PG rent")
            add("expense", ym, 5, 199, "Subscriptions", "Music streaming")
            add("expense", ym, 6, 149, "Subscriptions", "Cloud storage")
            add("expense", ym, 8, rng.randint(350, 900), "Utilities", "Mobile + internet")
            for _ in range(rng.randint(9, 13)):
                add("expense", ym, rng.randint(1, 28), rng.randint(80, 460), "Food & Dining",
                    rng.choice(["Mess extra", "Cafe", "Groceries", "Snacks", "Dinner out"]))
            for _ in range(rng.randint(5, 8)):
                add("expense", ym, rng.randint(1, 28), rng.randint(40, 260), "Transport",
                    rng.choice(["Auto", "Metro", "Cab", "Fuel"]))
            for _ in range(rng.randint(1, 3)):
                add("expense", ym, rng.randint(1, 28), rng.randint(600, 2600), "Shopping",
                    rng.choice(["Clothes", "Headphones", "Shoes", "Desk lamp"]))
            for _ in range(rng.randint(2, 4)):
                add("expense", ym, rng.randint(1, 28), rng.randint(150, 700), "Entertainment",
                    rng.choice(["Movie", "Gaming", "Concert", "Outing"]))
            if rng.random() < 0.6:
                add("expense", ym, rng.randint(1, 28), rng.randint(500, 1500), "Education", "Books / course")
            if rng.random() < 0.4:
                add("expense", ym, rng.randint(1, 28), rng.randint(200, 900), "Health", "Pharmacy")

        for cat, limit in [("Food & Dining", 4500), ("Transport", 1500), ("Shopping", 3000),
                           ("Entertainment", 1800), ("Rent", 7000), ("Utilities", 900)]:
            self.set_budget(cat, limit)
        self.add_goal("Laptop upgrade", 80000, 32000, (today + timedelta(days=120)).isoformat())
        self.add_goal("Emergency fund", 50000, 18500, (today + timedelta(days=240)).isoformat())
        self.add_goal("Goa trip", 15000, 15000, (today + timedelta(days=45)).isoformat())
