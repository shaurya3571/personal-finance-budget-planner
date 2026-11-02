"""Registry of screens shown in the sidebar: (key, label, Page subclass)."""
from pages.analytics import AnalyticsPage
from pages.budgets import BudgetsPage
from pages.dashboard import DashboardPage
from pages.goals import GoalsPage
from pages.reports import ReportsPage
from pages.transactions import TransactionsPage

REGISTRY = [
    ("dashboard", "Dashboard", DashboardPage),
    ("analytics", "Analytics", AnalyticsPage),
    ("transactions", "Transactions", TransactionsPage),
    ("budgets", "Budgets", BudgetsPage),
    ("goals", "Goals", GoalsPage),
    ("reports", "Reports", ReportsPage),
]
