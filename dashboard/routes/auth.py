# -*- coding: utf-8 -*-
"""Authentication routes."""
import secrets

from flask import Blueprint, redirect, render_template, request, session, url_for

from dashboard.services.helpers import _get_dashboard_password

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login_page():
    error = ""
    if request.method == "POST":
        # CSRF validation
        if request.form.get("csrf_token") != session.get("csrf_token") or not session.get("csrf_token"):
            return "CSRF token missing or invalid", 403
        password = request.form.get("password", "")
        if password == _get_dashboard_password():
            session["authenticated"] = True
            return redirect(url_for("main.index"))
        error = "Senha incorreta."

    token = secrets.token_hex(32)
    session["csrf_token"] = token
    return render_template("login.html", error=error, csrf_token=token)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))
