"""Registry of screens shown in the sidebar: (key, label, icon, Page subclass)."""
from pages.dashboard import DashboardPage

REGISTRY = [
    ("dashboard", "Dashboard", "▦", DashboardPage),
]
