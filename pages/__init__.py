"""Registry of screens shown in the sidebar: (key, label, icon, Page subclass)."""
from pages.dashboard import DashboardPage
from pages.transactions import TransactionsPage

REGISTRY = [
    ("dashboard", "Dashboard", "▦", DashboardPage),
    ("transactions", "Transactions", "⇅", TransactionsPage),
]
