import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
from auth import AuthError, AuthService, hash_password, verify_password
from db import Database

auth.ITERATIONS = 1000  # keep the tests fast; production value is 600,000


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class PasswordTests(unittest.TestCase):
    def test_hash_is_salted_and_verifiable(self):
        a, b = hash_password("Secret123"), hash_password("Secret123")
        self.assertNotEqual(a, b)                      # random salt
        self.assertNotIn("Secret123", a)               # plaintext never stored
        self.assertTrue(verify_password("Secret123", a))
        self.assertFalse(verify_password("secret123", a))
        self.assertFalse(verify_password("x", "garbage"))

    def test_validation_rules(self):
        for bad in ("ab", "has space", "x" * 21, "bad!char"):
            with self.assertRaises(AuthError):
                auth.validate_username(bad)
        for bad in ("short1", "onlyletters", "12345678", "x" * 129):
            with self.assertRaises(AuthError):
                auth.validate_password(bad)
        auth.validate_password("goodpass1")


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.clock = FakeClock()
        self.svc = AuthService(self.db, self.clock)

    def test_register_and_login(self):
        user = self.svc.register("Shaurya", "Passw0rd1", "Passw0rd1")
        self.assertEqual(self.svc.login("shaurya", "Passw0rd1")["id"], user["id"])  # case-insensitive username
        with self.assertRaises(AuthError):
            self.svc.register("SHAURYA", "Passw0rd1")                              # duplicate
        with self.assertRaises(AuthError):
            self.svc.register("other", "Passw0rd1", "Different1")                  # confirm mismatch

    def test_wrong_password_and_unknown_user_share_one_message(self):
        self.svc.register("alice", "Passw0rd1")
        with self.assertRaises(AuthError) as a:
            self.svc.login("alice", "wrong")
        with self.assertRaises(AuthError) as b:
            self.svc.login("nobody", "wrong")
        self.assertEqual(str(a.exception).split(".")[0], str(b.exception).split(".")[0])

    def test_lockout_after_five_failures_then_recovers(self):
        self.svc.register("alice", "Passw0rd1")
        for _ in range(auth.MAX_ATTEMPTS - 1):
            with self.assertRaises(AuthError):
                self.svc.login("alice", "bad")
        with self.assertRaises(AuthError) as locked:
            self.svc.login("alice", "bad")
        self.assertIn("Locked", str(locked.exception))
        with self.assertRaises(AuthError) as still:                      # even the right password is refused
            self.svc.login("alice", "Passw0rd1")
        self.assertIn("Try again in", str(still.exception))
        self.clock.now += auth.LOCKOUT_SECONDS + 1                       # lock expires
        self.assertEqual(self.svc.login("alice", "Passw0rd1")["username"], "alice")
        self.assertEqual(self.db.get_attempts("alice"), (0, 0.0))        # counter cleared on success

    def test_lockout_survives_restart(self):
        path = os.path.join(tempfile.mkdtemp(), "t.db")
        db1 = Database(path)
        AuthService(db1, self.clock).register("bob", "Passw0rd1")
        for _ in range(auth.MAX_ATTEMPTS):
            with self.assertRaises(AuthError):
                AuthService(db1, self.clock).login("bob", "bad")
        db1.close()
        with self.assertRaises(AuthError) as err:                        # "restart": new connection, same file
            AuthService(Database(path), self.clock).login("bob", "Passw0rd1")
        self.assertIn("Try again in", str(err.exception))


class UserIsolationTests(unittest.TestCase):
    def test_users_only_see_their_own_data(self):
        db = Database(":memory:")
        svc = AuthService(db)
        a, b = svc.register("alice", "Passw0rd1"), svc.register("bob", "Passw0rd1")
        db.set_user(a["id"])
        tid = db.add_transaction("expense", 100, "Rent", "2026-11-01")
        db.set_budget("Rent", 500)
        db.add_goal("Bike", 1000)
        db.set_user(b["id"])
        self.assertEqual(db.get_transactions(), [])
        self.assertEqual(db.get_budgets(), {})
        self.assertEqual(db.list_goals(), [])
        db.delete_transaction(tid)                                       # bob cannot delete alice's row
        db.update_transaction(tid, "expense", 1, "Rent", "2026-11-01")
        db.clear_all()
        db.set_user(a["id"])
        self.assertEqual(db.get_transactions()[0]["amount"], 100)
        self.assertEqual(db.get_budgets(), {"Rent": 500})

    def test_legacy_database_is_upgraded_and_adopted_by_first_user(self):
        path = os.path.join(tempfile.mkdtemp(), "old.db")
        old = sqlite3.connect(path)                                       # schema from before accounts existed
        old.executescript("""
            CREATE TABLE transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, amount REAL NOT NULL,
                                       category TEXT NOT NULL, tx_date TEXT NOT NULL, note TEXT NOT NULL DEFAULT '');
            CREATE TABLE budgets (category TEXT PRIMARY KEY, monthly_limit REAL NOT NULL);
            CREATE TABLE goals (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, target REAL NOT NULL,
                                saved REAL NOT NULL DEFAULT 0, deadline TEXT);
            INSERT INTO transactions (kind, amount, category, tx_date) VALUES ('expense', 50, 'Transport', '2026-10-01');
            INSERT INTO budgets VALUES ('Transport', 900);
            INSERT INTO goals (name, target) VALUES ('Old goal', 100);
        """)
        old.commit()
        old.close()
        db = Database(path)
        user = AuthService(db).register("first", "Passw0rd1")
        db.set_user(user["id"])
        self.assertEqual(len(db.get_transactions()), 1)
        self.assertEqual(db.get_budgets(), {"Transport": 900})
        self.assertEqual(db.list_goals()[0]["name"], "Old goal")
        second = AuthService(db).register("second", "Passw0rd1")
        db.set_user(second["id"])
        self.assertEqual(db.get_transactions(), [])


if __name__ == "__main__":
    unittest.main()
