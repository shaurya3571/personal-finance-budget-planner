"""Registry of screens shown in the sidebar: (key, label, icon, Page subclass)."""
from pages.budgets import BudgetsPage
from pages.dashboard import DashboardPage
from pages.goals import GoalsPage
from pages.transactions import TransactionsPage

REGISTRY = [
    ("dashboard", "Dashboard", "▦", DashboardPage),
    ("transactions", "Transactions", "⇅", TransactionsPage),
    ("budgets", "Budgets", "◔", BudgetsPage),
    ("goals", "Goals", "★", GoalsPage),
]
