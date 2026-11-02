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
7. **How are the charts drawn without matplotlib?** `Canvas` primitives: rectangles for bars and heatmap cells, thick `arc`s for the donut and rings, polylines for the line chart, text for axes. Each chart is a `tk.Canvas` subclass in `widgets.py` that redraws on `<Configure>`, so it resizes with the window. The numbers behind them (daily totals, running totals, weekday totals) are pure functions in `services.py` with unit tests.
8. **How is input validated?** `parse_amount` and `parse_date` in `services.py` raise `ValueError` with a friendly message; the page shows it with `messagebox.showerror` and nothing is saved.
9. **SQL injection?** All queries use `?` placeholders, never string-formatted user input.
10. **How does the budget colour logic work?** `budget_status`: below 80% green, 80-100% amber, above 100% red.
11. **How is dark mode done?** Colours live in one dict `C` (`theme.py`). Toggling replaces the palette, re-applies the ttk style and rebuilds the UI; the choice is stored in the `settings` table.
12. **What are keyboard shortcuts and how are they bound?** `bind_all("<Control-n>", ...)` in `App.bind_shortcuts`; the menu items show the same accelerators.
13. **What happens when the user closes the window?** `protocol("WM_DELETE_WINDOW", on_close)` asks for confirmation, closes the DB, then destroys the window.
14. **How is the projected month-end spend computed?** Spent so far divided by days elapsed, times days in the month (`projected_spend`).
15. **How did you test it?** Unit tests for helpers, database and CSV export, plus headless GUI tests that drive the real widgets (add/edit/delete, both themes, empty database).
16. **Limitations / future work.** Single user, no login, no recurring transactions, no multi-currency conversion, no cloud sync.

## Demo order (3 minutes)
1. Data -> Load demo data. 2. Dashboard: point at cards, charts, budget bars. 3. Add a transaction
(show validation error first). 4. Budgets: push one over the limit. 5. Goals: Add funds. 6. Reports:
export CSV. 7. Toggle dark mode (`Ctrl+T`), quit (shows confirmation).
