"""Authentication: password hashing, input validation and login rate limiting.

* Passwords are never stored - only a salted PBKDF2-HMAC-SHA256 hash (stdlib, works on every Python).
* Failed logins are counted per username in the database, so restarting the app does not reset the
  lockout. After MAX_ATTEMPTS wrong passwords the account is locked for LOCKOUT_SECONDS.
* Error messages are generic ("incorrect username or password") so an attacker cannot tell which
  usernames exist.
"""
import hashlib
import hmac
import math
import os
import re
import sqlite3
import time

ITERATIONS = 600_000      # OWASP-recommended work factor for PBKDF2-HMAC-SHA256
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 60

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.]{3,20}$")
_dummy_hash = None


class AuthError(Exception):
    """Raised with a message that is safe to show to the user."""


def hash_password(password: str, salt: bytes | None = None, iterations: int | None = None) -> str:
    iterations = iterations or ITERATIONS
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), hash_hex)


def validate_username(username: str) -> str:
    username = username.strip()
    if not _USERNAME_RE.match(username):
        raise AuthError("Username must be 3-20 characters: letters, digits, _ or . only.")
    return username


def validate_password(password: str):
    if len(password) < 8:
        raise AuthError("Password must be at least 8 characters.")
    if len(password) > 128:
        raise AuthError("Password is too long (max 128 characters).")
    if not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
        raise AuthError("Password must contain at least one letter and one digit.")


class AuthService:
    def __init__(self, db, clock=time.time):
        self.db = db
        self.clock = clock

    def register(self, username: str, password: str, confirm: str | None = None) -> dict:
        username = validate_username(username)
        validate_password(password)
        if confirm is not None and confirm != password:
            raise AuthError("Passwords do not match.")
        try:
            uid = self.db.create_user(username, hash_password(password))
        except sqlite3.IntegrityError:
            raise AuthError("That username is already taken.") from None
        if self.db.user_count() == 1:
            self.db.adopt_legacy(uid)  # data created before accounts existed goes to the first user
        return {"id": uid, "username": username}

    def login(self, username: str, password: str) -> dict:
        global _dummy_hash
        key = username.strip().lower()
        now = self.clock()
        failed, locked_until = self.db.get_attempts(key)
        if locked_until > now:
            raise AuthError(f"Too many failed attempts. Try again in {math.ceil(locked_until - now)} seconds.")
        if locked_until:          # a previous lock has expired -> start counting again
            failed = 0

        user = self.db.get_user(key)
        if user is None:          # still do the expensive hash so timing does not reveal valid usernames
            _dummy_hash = _dummy_hash or hash_password("not-a-real-password")
            verify_password(password, _dummy_hash)
        elif verify_password(password, user["pw_hash"]):
            self.db.clear_attempts(key)
            return {"id": user["id"], "username": user["username"]}

        failed += 1
        if failed >= MAX_ATTEMPTS:
            self.db.set_attempts(key, 0, now + LOCKOUT_SECONDS)
            raise AuthError(f"Too many failed attempts. Locked for {LOCKOUT_SECONDS} seconds.")
        self.db.set_attempts(key, failed, 0)
        left = MAX_ATTEMPTS - failed
        raise AuthError(f"Incorrect username or password. {left} attempt{'s' if left != 1 else ''} left.")
