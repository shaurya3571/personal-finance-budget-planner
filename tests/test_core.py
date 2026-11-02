import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import services as s
from db import Database


class ServicesTests(unittest.TestCase):
    def test_indian_grouping(self):
        self.assertEqual(s.fmt_money(1234567), "₹12,34,567")
        self.assertEqual(s.fmt_money(950), "₹950")
        self.assertEqual(s.fmt_money(-4500.5, decimals=2), "-₹4,500.50")

    def test_parse_amount(self):
        self.assertEqual(s.parse_amount(" 1,250.456 "), 1250.46)
        for bad in ("", "abc", "0", "-5", "nan", "inf", "9999999999"):
            with self.assertRaises(ValueError):
                s.parse_amount(bad)

    def test_parse_date(self):
        self.assertEqual(s.parse_date("2026-11-03"), date(2026, 11, 3))
        with self.assertRaises(ValueError):
            s.parse_date("03/11/2026")

    def test_shift_month_wraps_years(self):
        self.assertEqual(s.shift_month("2026-01", -1), "2025-12")
        self.assertEqual(s.shift_month("2026-11", 3), "2027-02")

    def test_budget_status(self):
        self.assertEqual(s.budget_status(50, 100)[0], "ok")
        self.assertEqual(s.budget_status(80, 100)[0], "warn")
        self.assertEqual(s.budget_status(101, 100)[0], "over")

    def test_savings_rate_and_projection(self):
        self.assertEqual(s.savings_rate(0, 100), 0.0)
        self.assertAlmostEqual(s.savings_rate(1000, 400), 60.0)
        self.assertAlmostEqual(s.projected_spend(1000, "2026-11", date(2026, 11, 10)), 3000.0)
        self.assertAlmostEqual(s.projected_spend(900, "2026-09", date(2026, 11, 10)), 900.0)


class ChartDataTests(unittest.TestCase):
    ROWS = [
        {"kind": "expense", "amount": 100, "tx_date": "2026-11-02"},   # Monday
        {"kind": "expense", "amount": 50, "tx_date": "2026-11-02"},
        {"kind": "expense", "amount": 30, "tx_date": "2026-11-04"},    # Wednesday
        {"kind": "income", "amount": 999, "tx_date": "2026-11-02"},    # ignored
        {"kind": "expense", "amount": 70, "tx_date": "2026-10-31"},    # other month
    ]

    def test_daily_totals_and_cumulative(self):
        days = s.daily_expense_totals(self.ROWS, "2026-11")
        self.assertEqual(len(days), 30)
        self.assertEqual((days[1], days[3], days[0]), (150, 30, 0))
        run = s.cumulative(days, upto=4)
        self.assertEqual(run[3], 180)
        self.assertIsNone(run[4])                       # stops after "today"
        self.assertEqual(s.cumulative([1, 2, 3])[-1], 6)

    def test_weekday_totals(self):
        totals = s.weekday_totals(self.ROWS, {"2026-11"})
        self.assertEqual((totals[0], totals[2]), (150, 30))
        self.assertEqual(sum(totals), 180)

    def test_compact_money(self):
        self.assertEqual(s.compact_money(950), "₹950")
        self.assertEqual(s.compact_money(12400), "₹12.4k")
        self.assertEqual(s.compact_money(250000), "₹2.5L")
        self.assertEqual(s.compact_money(-1500), "-₹1.5k")


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")

    def test_crud_and_totals(self):
        a = self.db.add_transaction("income", 1000, "Salary", "2026-11-01")
        b = self.db.add_transaction("expense", 300, "Food & Dining", "2026-11-02", "lunch")
        self.assertEqual(self.db.totals("2026-11"), (1000, 300))
        self.assertEqual(self.db.balance(), 700)
        self.db.update_transaction(b, "expense", 400, "Food & Dining", "2026-11-02", "lunch+tea")
        self.assertEqual(self.db.totals("2026-11")[1], 400)
        self.db.delete_transaction(a)
        self.assertEqual(len(self.db.get_transactions()), 1)

    def test_filters(self):
        self.db.add_transaction("expense", 50, "Transport", "2026-10-30", "metro")
        self.db.add_transaction("expense", 90, "Food & Dining", "2026-11-02", "pizza")
        self.assertEqual(len(self.db.get_transactions(month="2026-11")), 1)
        self.assertEqual(len(self.db.get_transactions(search="pizza")), 1)
        self.assertEqual(len(self.db.get_transactions(kind="income")), 0)

    def test_category_and_series(self):
        self.db.add_transaction("expense", 100, "Transport", "2026-11-02")
        self.db.add_transaction("expense", 300, "Rent", "2026-11-03")
        self.db.add_transaction("income", 500, "Salary", "2026-10-01")
        self.assertEqual(self.db.spending_by_category("2026-11")[0], ("Rent", 300))
        series = self.db.monthly_series("2026-11", 3)
        self.assertEqual([m for m, *_ in series], ["2026-09", "2026-10", "2026-11"])
        self.assertEqual(series[1][1], 500)
        self.assertEqual(series[2][2], 400)

    def test_budgets_goals_settings(self):
        self.db.set_budget("Food & Dining", 3000)
        self.db.set_budget("Food & Dining", 3500)  # upsert
        self.assertEqual(self.db.get_budgets(), {"Food & Dining": 3500})
        gid = self.db.add_goal("Bike", 10000, 1000, "2027-01-01")
        self.db.add_to_goal(gid, 500)
        self.assertEqual(self.db.list_goals()[0]["saved"], 1500)
        self.db.set_setting("theme", "dark")
        self.assertEqual(self.db.get_setting("theme"), "dark")

    def test_seed_demo(self):
        self.db.seed_demo(date(2026, 11, 3))
        self.assertFalse(self.db.is_empty())
        self.assertTrue(self.db.get_budgets())
        self.db.clear_all()
        self.assertTrue(self.db.is_empty())


if __name__ == "__main__":
    unittest.main()
