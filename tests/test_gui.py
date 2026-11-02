"""Headless GUI smoke tests. Skipped automatically when no display is available
(run with:  xvfb-run -a python -m unittest discover -s tests)."""
import os
import sys
import tempfile
import unittest
from datetime import date
from tkinter import messagebox, simpledialog

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import theme
from db import Database

try:
    import tkinter as tk
    tk.Tk().destroy()
    HAS_DISPLAY = True
except Exception:  # no Tk or no display
    HAS_DISPLAY = False


@unittest.skipUnless(HAS_DISPLAY, "needs a display")
class GuiTests(unittest.TestCase):
    def setUp(self):
        for name in ("showerror", "showinfo"):
            setattr(messagebox, name, lambda *a, **k: None)
        for name in ("askyesno", "askokcancel"):
            setattr(messagebox, name, lambda *a, **k: True)
        import auth
        auth.ITERATIONS = 1000          # fast hashing for tests
        from app import App
        self.db = Database(os.path.join(tempfile.mkdtemp(), "test.db"))
        self.user = auth.AuthService(self.db).register("tester", "Passw0rd1")
        self.db.set_user(self.user["id"])
        self.db.seed_demo(date.today())
        self.app = App(self.db, user=self.user)
        self.app.update()

    def tearDown(self):
        self.app.destroy()
        theme.set_mode("light")

    def test_every_page_renders_in_both_themes(self):
        for _ in range(2):
            for key in self.app.pages:
                self.app.show(key)
                self.app.update()
            self.app.toggle_theme()

    def test_transaction_add_edit_delete(self):
        self.app.show("transactions")
        page = self.app.pages["transactions"]
        before = len(self.db.get_transactions())
        page.amount.set("250")
        page.note.set("unit test")
        page.save()
        self.assertEqual(len(self.db.get_transactions()), before + 1)
        page.tree.selection_set(page.tree.get_children()[0])
        page.edit_selected()
        page.amount.set("300")
        page.save()
        self.assertEqual(self.db.get_transactions(search="unit test")[0]["amount"], 300)
        page.tree.selection_set(page.tree.get_children()[0])
        page.delete_selected()
        self.assertEqual(len(self.db.get_transactions()), before)

    def test_invalid_input_is_rejected(self):
        self.app.show("transactions")
        page = self.app.pages["transactions"]
        before = len(self.db.get_transactions())
        page.amount.set("abc")
        page.save()
        page.amount.set("10")
        page.tx_date.set("31/12/2026")
        page.save()
        self.assertEqual(len(self.db.get_transactions()), before)

    def test_budget_and_goal_flows(self):
        budgets = self.app.pages["budgets"]
        budgets.category.set("Transport")
        budgets.limit.set("2500")
        budgets.save()
        self.assertEqual(self.db.get_budgets()["Transport"], 2500)
        goals = self.app.pages["goals"]
        goals.vars["name"].set("Bike")
        goals.vars["target"].set("20000")
        goals.add()
        gid = self.db.list_goals()[-1]["id"]
        simpledialog.askstring = lambda *a, **k: "1500"
        goals.add_funds(gid)
        self.assertEqual(self.db.list_goals()[-1]["saved"], 1500)

    def test_login_screen_flow_and_sign_out(self):
        self.app.show_login()
        self.app.update()
        from login import LoginView
        view = next(w for w in self.app.winfo_children() if isinstance(w, LoginView))
        view.username.set("tester")
        view.password.set("wrong-pass1")
        view.submit()
        self.assertIn("Incorrect username or password", view.error["text"])
        self.assertIsNone(self.app.user)
        view.password.set("Passw0rd1")
        view.submit()
        self.app.update()
        self.assertEqual(self.app.user["username"], "tester")
        self.assertEqual(self.app.current, "dashboard")
        self.app.logout()                                 # askyesno patched to True
        self.assertIsNone(self.app.user)
        self.assertEqual(self.db.uid, 0)

    def test_register_screen_creates_separate_empty_account(self):
        self.app.show_login()
        view = next(w for w in self.app.winfo_children() if w.__class__.__name__ == "LoginView")
        view._set_mode("register")
        view.username.set("newbie")
        view.password.set("Passw0rd1")
        view.confirm.set("Passw0rd1")
        view.submit()
        self.app.update()
        self.assertEqual(self.app.user["username"], "newbie")
        self.assertTrue(self.db.is_empty())               # does not see tester's demo data
        self.app.show("dashboard")
        self.app.update()

    def test_empty_database_renders(self):
        self.db.clear_all()
        for key in self.app.pages:
            self.app.show(key)
            self.app.update()


if __name__ == "__main__":
    unittest.main()
