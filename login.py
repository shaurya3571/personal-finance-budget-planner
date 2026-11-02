"""Sign-in / create-account screen shown before the main window content."""
import tkinter as tk
from tkinter import ttk

from auth import AuthError, AuthService
from theme import C, F
from widgets import Card, label


class LoginView(tk.Frame):
    def __init__(self, parent, auth: AuthService, on_success):
        super().__init__(parent, bg=C["bg"])
        self.auth, self.on_success, self.mode = auth, on_success, "login"
        self.username, self.password, self.confirm = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.show_pw = tk.BooleanVar(value=False)
        self._build_brand_panel()
        self._build_form()
        self._set_mode("login")

    def _build_brand_panel(self):
        panel = tk.Frame(self, bg=C["sidebar"], width=430)
        panel.pack(side="left", fill="y")
        panel.pack_propagate(False)
        inner = tk.Frame(panel, bg=C["sidebar"])
        inner.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(inner, text="◆", font=F(34, "bold"), fg=C["primary"], bg=C["sidebar"]).pack(anchor="w")
        tk.Label(inner, text="FinTrack", font=F(28, "bold"), fg="#FFFFFF", bg=C["sidebar"]).pack(anchor="w")
        tk.Label(inner, text="Know where every rupee goes.", font=F(12), fg=C["sidebar_text"],
                 bg=C["sidebar"]).pack(anchor="w", pady=(4, 28))
        for text in ("Track income and expenses", "Stay inside monthly budgets",
                     "Reach your savings goals", "Private - every account has its own data"):
            row = tk.Frame(inner, bg=C["sidebar"])
            row.pack(anchor="w", pady=5)
            tk.Label(row, text="✓", font=F(11, "bold"), fg=C["income"], bg=C["sidebar"]).pack(side="left")
            tk.Label(row, text=f"  {text}", font=F(11), fg="#E5E7EB", bg=C["sidebar"]).pack(side="left")

    def _build_form(self):
        side = tk.Frame(self, bg=C["bg"])
        side.pack(side="left", fill="both", expand=True)
        card = Card(side, padding=34)
        card.place(relx=0.5, rely=0.5, anchor="center")
        f = card.body
        self.title = label(f, "", 20, "bold")
        self.title.grid(row=0, column=0, sticky="w")
        self.subtitle = label(f, "", 10, color=C["muted"])
        self.subtitle.grid(row=1, column=0, sticky="w", pady=(2, 14))

        label(f, "Username", 9, "bold", C["muted"]).grid(row=2, column=0, sticky="w", pady=(6, 3))
        self.user_entry = ttk.Entry(f, textvariable=self.username, width=34)
        self.user_entry.grid(row=3, column=0, sticky="ew")
        label(f, "Password", 9, "bold", C["muted"]).grid(row=4, column=0, sticky="w", pady=(10, 3))
        self.pw_entry = ttk.Entry(f, textvariable=self.password, show="•", width=34)
        self.pw_entry.grid(row=5, column=0, sticky="ew")
        self.confirm_label = label(f, "Confirm password", 9, "bold", C["muted"])
        self.confirm_label.grid(row=6, column=0, sticky="w", pady=(10, 3))
        self.confirm_entry = ttk.Entry(f, textvariable=self.confirm, show="•", width=34)
        self.confirm_entry.grid(row=7, column=0, sticky="ew")
        self.hint = label(f, "At least 8 characters with a letter and a digit.", 8, color=C["muted"])
        self.hint.grid(row=8, column=0, sticky="w", pady=(4, 0))
        ttk.Checkbutton(f, text="Show password", variable=self.show_pw,
                        command=self._toggle_show).grid(row=9, column=0, sticky="w", pady=(10, 0))

        self.error = tk.Label(f, text="", font=F(9, "bold"), fg=C["expense"], bg=C["surface"],
                              wraplength=300, justify="left")
        self.error.grid(row=10, column=0, sticky="w", pady=(10, 0))
        self.submit_btn = ttk.Button(f, style="Primary.TButton", command=self.submit)
        self.submit_btn.grid(row=11, column=0, sticky="ew", pady=(10, 0))
        self.switch = label(f, "", 9, "bold", C["primary"], cursor="hand2")
        self.switch.grid(row=12, column=0, pady=(14, 0))
        self.switch.bind("<Button-1>", lambda e: self._set_mode("register" if self.mode == "login" else "login"))
        for entry in (self.user_entry, self.pw_entry, self.confirm_entry):
            entry.bind("<Return>", lambda e: self.submit())
        self.user_entry.focus_set()

    def _toggle_show(self):
        char = "" if self.show_pw.get() else "•"
        self.pw_entry.config(show=char)
        self.confirm_entry.config(show=char)

    def _set_mode(self, mode):
        self.mode = mode
        register = mode == "register"
        self.title.config(text="Create your account" if register else "Welcome back")
        self.subtitle.config(text="Your data stays private to this account." if register
                             else "Sign in to open your planner.")
        self.submit_btn.config(text="Create account" if register else "Sign in")
        self.switch.config(text="Already have an account? Sign in" if register else "New here? Create an account")
        for widget in (self.confirm_label, self.confirm_entry, self.hint):
            widget.grid() if register else widget.grid_remove()
        self.password.set("")
        self.confirm.set("")
        self.error.config(text="")
        self.user_entry.focus_set()

    def submit(self):
        self.error.config(text="")
        try:
            if self.mode == "register":
                user = self.auth.register(self.username.get(), self.password.get(), self.confirm.get())
            else:
                user = self.auth.login(self.username.get(), self.password.get())
        except AuthError as err:
            self.error.config(text=str(err))
            self.password.set("")
            self.confirm.set("")
            self.pw_entry.focus_set()
            return
        self.password.set("")
        self.confirm.set("")
        self.on_success(user)
