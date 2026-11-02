"""Pure helper functions (no Tkinter, no database) so they are easy to unit-test."""
import calendar
import math
from datetime import date, datetime


def _indian_group(digits: str) -> str:
    """12345678 -> 1,23,45,678 (Indian digit grouping)."""
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def fmt_money(value: float, symbol: str = "₹", decimals: int = 0) -> str:
    negative = value < 0
    whole, _, frac = f"{abs(value):.{decimals}f}".partition(".")
    text = symbol + _indian_group(whole) + (f".{frac}" if frac else "")
    return f"-{text}" if negative else text


def parse_amount(text: str) -> float:
    """Validate a money field. Raises ValueError with a user-friendly message."""
    cleaned = text.replace(",", "").replace("₹", "").strip()
    if not cleaned:
        raise ValueError("Please enter an amount.")
    try:
        value = float(cleaned)
    except ValueError:
        raise ValueError("Amount must be a number, e.g. 450 or 1250.50.") from None
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Amount must be greater than zero.")
    if value > 1_000_000_000:
        raise ValueError("Amount is unrealistically large.")
    return round(value, 2)


def parse_date(text: str) -> date:
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Date must look like YYYY-MM-DD, e.g. 2026-11-03.") from None


def current_month(today: date | None = None) -> str:
    return (today or date.today()).strftime("%Y-%m")


def shift_month(ym: str, delta: int) -> str:
    year, month = int(ym[:4]), int(ym[5:7])
    index = year * 12 + (month - 1) + delta
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def month_label(ym: str, short: bool = False) -> str:
    year, month = int(ym[:4]), int(ym[5:7])
    name = calendar.month_abbr[month] if short else calendar.month_name[month]
    return name if short else f"{name} {year}"


def savings_rate(income: float, expense: float) -> float:
    return 0.0 if income <= 0 else (income - expense) / income * 100


def budget_status(spent: float, limit: float) -> tuple[str, float]:
    """Return ('ok'|'warn'|'over', fraction_used)."""
    fraction = spent / limit if limit > 0 else 0.0
    if fraction > 1:
        return "over", fraction
    if fraction >= 0.8:
        return "warn", fraction
    return "ok", fraction


def projected_spend(spent: float, ym: str, today: date | None = None) -> float:
    """Linear projection of month-end spending from spending so far."""
    today = today or date.today()
    year, month = int(ym[:4]), int(ym[5:7])
    days_in_month = calendar.monthrange(year, month)[1]
    if ym == current_month(today):
        elapsed = max(today.day, 1)
    elif ym < current_month(today):
        elapsed = days_in_month
    else:
        return 0.0
    return spent / elapsed * days_in_month


def days_left(deadline: str | None, today: date | None = None) -> int | None:
    if not deadline:
        return None
    return (parse_date(deadline) - (today or date.today())).days


def compact_money(value: float, symbol: str = "₹") -> str:
    """Short label for chart axes: 950 -> ₹950, 12400 -> ₹12.4k, 250000 -> ₹2.5L."""
    sign, v = ("-" if value < 0 else ""), abs(value)
    if v >= 100_000:
        return f"{sign}{symbol}{f'{v / 100_000:.1f}'.removesuffix('.0')}L"
    if v >= 1_000:
        return f"{sign}{symbol}{f'{v / 1_000:.1f}'.removesuffix('.0')}k"
    return f"{sign}{symbol}{v:.0f}"


def daily_expense_totals(rows, ym: str) -> list[float]:
    """Expense per day of a month (index 0 = day 1)."""
    out = [0.0] * calendar.monthrange(int(ym[:4]), int(ym[5:7]))[1]
    for r in rows:
        if r["kind"] == "expense" and r["tx_date"][:7] == ym:
            out[int(r["tx_date"][8:10]) - 1] += r["amount"]
    return out


def cumulative(values, upto: int | None = None):
    """Running total. Days after `upto` (1-based) become None so a line stops at today."""
    total, out = 0.0, []
    for day, v in enumerate(values, start=1):
        total += v
        out.append(total if upto is None or day <= upto else None)
    return out


def weekday_totals(rows, months) -> list[float]:
    """Expense totals Monday..Sunday over the given set of 'YYYY-MM' months."""
    out = [0.0] * 7
    for r in rows:
        if r["kind"] == "expense" and r["tx_date"][:7] in months:
            out[date.fromisoformat(r["tx_date"]).weekday()] += r["amount"]
    return out
