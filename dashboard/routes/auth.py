# -*- coding: utf-8 -*-
"""Authentication routes."""
import hmac

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

    # Fail closed with an explanation instead of a misleading "wrong password".
    if not _get_dashboard_password():
        return render_template(
            "login.html",
            error="DASHBOARD_PASSWORD não configurado — o dashboard está desabilitado.",
        ), 503

    if request.method == "POST":
        if is_locked(ip):
            return render_template(
                "login.html",
                error=f"Muitas tentativas. Tente novamente em {seconds_left(ip)}s.",
            ), 429

        password = request.form.get("password", "")
        # Constant-time comparison: a plain == leaks the password length/prefix
        # through response timing.
        expected = _get_dashboard_password().encode("utf-8")
        if hmac.compare_digest(password.encode("utf-8", "replace"), expected):
            reset_failures(ip)
            session["authenticated"] = True
            session.permanent = True  # honours PERMANENT_SESSION_LIFETIME
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
