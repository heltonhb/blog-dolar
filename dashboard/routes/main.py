# -*- coding: utf-8 -*-
"""Main page routes."""
from flask import Blueprint, render_template

from dashboard.services.helpers import login_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def index():
    """Main dashboard page."""
    return render_template("index.html")


@main_bp.route("/ideas")
@login_required
def ideas():
    """Ideas management page."""
    return render_template("ideas.html")


@main_bp.route("/generate")
@login_required
def generate():
    """Article generation page."""
    return render_template("generate.html")


@main_bp.route("/articles")
@login_required
def articles():
    """Articles list page."""
    return render_template("articles.html")


@main_bp.route("/images")
@login_required
def images():
    """Images gallery page."""
    return render_template("images.html")


@main_bp.route("/publish")
@login_required
def publish():
    """Publish article page."""
    return render_template("publish.html")


@main_bp.route("/pinterest")
@login_required
def pinterest():
    """Pinterest management page."""
    return render_template("pinterest.html")


@main_bp.route("/verify")
@login_required
def verify():
    """SEO verification page."""
    return render_template("verify.html")


@main_bp.route("/adcash")
@login_required
def adcash():
    """AdCash stats page."""
    return render_template("adcash.html")


@main_bp.route("/pipeline")
@login_required
def pipeline():
    """Pipeline page."""
    return render_template("pipeline.html")


@main_bp.route("/settings")
@login_required
def settings():
    """Settings page."""
    return render_template("settings.html")


@main_bp.route("/scheduler")
@login_required
def scheduler():
    """Scheduler page."""
    return render_template("scheduler.html")


@main_bp.route("/adsterra")
@login_required
def adsterra():
    """Adsterra ad network stats page."""
    return render_template("adsterra.html")


@main_bp.route("/traffic")
@login_required
def traffic():
    """GA4 / Pinterest traffic analytics page."""
    return render_template("traffic.html")
