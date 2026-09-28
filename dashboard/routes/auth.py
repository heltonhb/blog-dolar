# -*- coding: utf-8 -*-
"""Authentication routes."""
from flask import Blueprint, redirect, render_template, request, session, url_for

from dashboard.services.helpers import _get_dashboard_password
from dashboard.services.login_throttle import (
    client_ip,
    is_locked,
    register_failure,
    reset as reset_failures,
    seconds_left,
)
from dashboard.services.security import rotate_csrf_token

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login_page():
    error = ""
    ip = client_ip(request)

    if request.method == "POST":
        if is_locked(ip):
            return render_template(
                "login.html",
                error=f"Muitas tentativas. Tente novamente em {seconds_left(ip)}s.",
            ), 429

        password = request.form.get("password", "")
        if password == _get_dashboard_password():
            reset_failures(ip)
            session["authenticated"] = True
            rotate_csrf_token()  # fresh token after privilege change
            return redirect(url_for("main.index"))
        register_failure(ip)
        error = "Senha incorreta."

    # CSRF is enforced globally (dashboard.services.security.install_csrf);
    # the token is injected into templates by the context processor.
    return render_template("login.html", error=error)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))
