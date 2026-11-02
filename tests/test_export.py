import csv
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import exporter
from db import Database


class ExportTests(unittest.TestCase):
    def test_transactions_and_month_report(self):
        db = Database(":memory:")
        db.add_transaction("expense", 120.5, "Transport", "2026-11-02", "cab, airport")
        db.add_transaction("income", 5000, "Allowance", "2026-11-01")
        folder = tempfile.mkdtemp()

        path = os.path.join(folder, "all.csv")
        exporter.export_transactions(db.get_transactions(), path)
        rows = list(csv.reader(open(path, encoding="utf-8-sig")))
        self.assertEqual(rows[0], ["Date", "Type", "Category", "Note", "Amount"])
        self.assertEqual(rows[1][3], "cab, airport")  # comma survives CSV quoting

        report = os.path.join(folder, "month.csv")
        exporter.export_month_report(report, "November 2026", 5000, 120.5,
                                     db.spending_by_category("2026-11"), {"Transport": 100})
        rows = list(csv.reader(open(report, encoding="utf-8-sig")))
        self.assertEqual(rows[3], ["Net savings", "4879.50"])
        self.assertEqual(rows[6], ["Transport", "120.50", "100.0", "100.00", "-20.50"])


if __name__ == "__main__":
    unittest.main()
