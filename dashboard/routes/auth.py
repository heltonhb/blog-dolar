# -*- coding: utf-8 -*-
"""Authentication routes."""
from flask import Blueprint, request, redirect, url_for, session, render_template
from pathlib import Path

auth_bp = Blueprint("auth", __name__)


def _get_dashboard_password():
    """Get dashboard password from environment."""
    pwd = os.environ.get("DASHBOARD_PASSWORD", "")
    if not pwd:
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    if k.strip() == "DASHBOARD_PASSWORD":
                        pwd = v.strip()
                        break
    return pwd


@auth_bp.route("/login", methods=["GET", "POST"])
def login_page():
    error = ""
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == _get_dashboard_password():
            session["authenticated"] = True
            return redirect(url_for("main.index"))
        error = "Senha incorreta."
    return render_template("login.html", error=error)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))
