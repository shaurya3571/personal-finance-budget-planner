# Viva preparation - FinTrack (Personal Finance & Budget Planner)

## 30-second pitch
FinTrack is a desktop app in Python/Tkinter that tracks income and expenses, enforces monthly
budgets, follows savings goals and produces reports. Data lives in a local SQLite file. The code is
split into UI (`pages/`, `widgets.py`), logic (`services.py`) and storage (`db.py`) so each part can be
tested on its own.

## Likely questions

1. **Why Tkinter?** It ships with Python, needs no installs, and is enough for a desktop form-and-table app.
2. **Why SQLite instead of a text file?** Queries (`SUM`, `GROUP BY`, filters), constraints (`CHECK amount > 0`) and safe writes; still just one file, no server.
3. **Explain the structure.** `App` owns the window, sidebar and month; every screen is a `Page` subclass with `build()` (create widgets once) and `refresh()` (reload data). Pages are registered in `pages/__init__.py`.
4. **Which layout managers did you use?** `grid` for card layouts (weights make columns resize), `pack` for rows and forms, `place` to stack the pages on top of each other and raise the active one.
5. **How does navigation work?** All pages are created once and stacked with `place`; `show(key)` calls `tkraise()` and `refresh()`.
6. **How does the month selector update everything?** `App.month` holds `YYYY-MM`; changing it calls `refresh()` on the visible page, which re-queries the database for that month.
7. **How are the charts drawn without matplotlib?** `Canvas` primitives: rectangles for bars, thick `arc`s for the donut, lines and text for axes. They redraw on `<Configure>` so they resize with the window.
8. **How is input validated?** `parse_amount` and `parse_date` in `services.py` raise `ValueError` with a friendly message; the page shows it with `messagebox.showerror` and nothing is saved.
9. **SQL injection?** All queries use `?` placeholders, never string-formatted user input.
10. **How does the budget colour logic work?** `budget_status`: below 80% green, 80-100% amber, above 100% red.
11. **How is dark mode done?** Colours live in one dict `C` (`theme.py`). Toggling replaces the palette, re-applies the ttk style and rebuilds the UI; the choice is stored in the `settings` table.
12. **What are keyboard shortcuts and how are they bound?** `bind_all("<Control-n>", ...)` in `App.bind_shortcuts`; the menu items show the same accelerators.
13. **What happens when the user closes the window?** `protocol("WM_DELETE_WINDOW", on_close)` asks for confirmation, closes the DB, then destroys the window.
14. **How is the projected month-end spend computed?** Spent so far divided by days elapsed, times days in the month (`projected_spend`).
15. **How did you test it?** Unit tests for helpers, database and CSV export, plus headless GUI tests that drive the real widgets (add/edit/delete, both themes, empty database).
16. **How does login work?** `AuthService.login` looks the user up, hashes the typed password with the stored salt and compares in constant time (`hmac.compare_digest`). On success `App.enter_app(user)` sets `db.uid`, builds the main window and every query is then filtered by that user id.
17. **How are passwords stored?** Only as `pbkdf2_sha256$iterations$salt$hash`. A random 16-byte salt per user stops rainbow-table and same-password matching; 600,000 iterations make brute force slow. Passwords are not recoverable, only resettable.
18. **What is the rate limiting?** 5 failed logins for a username -> 60-second lock (`MAX_ATTEMPTS`, `LOCKOUT_SECONDS`). Counters live in the `login_attempts` table, so restarting the app does not bypass them. Unknown usernames are counted too and get the same message, so an attacker cannot learn which users exist.
19. **JDBC vs Python?** Same idea, different names: `DriverManager.getConnection` -> `sqlite3.connect`; `PreparedStatement` with `?` -> `conn.execute(sql, params)`; `ResultSet` -> cursor rows (`sqlite3.Row`); `commit()`/`rollback()` -> `with conn:`; `Connection.close()` -> `conn.close()`.
20. **How do you stop one user reading another's data?** Every data table has `user_id`; every SELECT/UPDATE/DELETE includes `AND user_id = ?`. A unit test logs in as two users and checks isolation.
21. **What happens to data created before accounts?** `_migrate` adds the `user_id` column (default 0); when the first account registers, `adopt_legacy` assigns those rows to it.
22. **Limitations / future work.** Single user, no login, no recurring transactions, no multi-currency conversion, no cloud sync.

## Demo order (3 minutes)
0. Create an account (show the validation message, then a wrong-password lockout). 1. Data -> Load demo data. 2. Dashboard: point at cards, charts, budget bars. 3. Add a transaction
(show validation error first). 4. Budgets: push one over the limit. 5. Goals: Add funds. 6. Reports:
export CSV. 7. Toggle dark mode (`Ctrl+T`), quit (shows confirmation).
