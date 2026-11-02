"""CSV export helpers (no Tkinter, so they can be unit-tested)."""
import csv


def export_transactions(rows, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Date", "Type", "Category", "Note", "Amount"])
        for r in rows:
            writer.writerow([r["tx_date"], r["kind"], r["category"], r["note"], f"{r['amount']:.2f}"])


def export_month_report(path, month, income, expense, breakdown, budgets):
    """breakdown: [(category, spent)], budgets: {category: limit}."""
    total = sum(v for _, v in breakdown) or 1
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Month", month])
        writer.writerow(["Income", f"{income:.2f}"])
        writer.writerow(["Expenses", f"{expense:.2f}"])
        writer.writerow(["Net savings", f"{income - expense:.2f}"])
        writer.writerow([])
        writer.writerow(["Category", "Spent", "Share %", "Budget", "Remaining"])
        for cat, spent in breakdown:
            limit = budgets.get(cat)
            writer.writerow([cat, f"{spent:.2f}", f"{spent / total * 100:.1f}",
                             "" if limit is None else f"{limit:.2f}",
                             "" if limit is None else f"{limit - spent:.2f}"])
