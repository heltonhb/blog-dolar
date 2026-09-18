# -*- coding: utf-8 -*-
"""Main page routes."""
from flask import Blueprint, render_template, jsonify, request
from datetime import datetime

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Main dashboard page."""
    return render_template("index.html")


@main_bp.route("/ideas")
def ideas():
    """Ideas management page."""
    return render_template("ideas.html")


@main_bp.route("/generate")
def generate():
    """Article generation page."""
    return render_template("generate.html")


@main_bp.route("/articles")
def articles():
    """Articles list page."""
    return render_template("articles.html")


@main_bp.route("/images")
def images():
    """Images gallery page."""
    return render_template("images.html")


@main_bp.route("/publish")
def publish():
    """Publish article page."""
    return render_template("publish.html")


@main_bp.route("/pinterest")
def pinterest():
    """Pinterest management page."""
    return render_template("pinterest.html")


@main_bp.route("/verify")
def verify():
    """SEO verification page."""
    return render_template("verify.html")


@main_bp.route("/adcash")
def adcash():
    """AdCash stats page."""
    return render_template("adcash.html")


@main_bp.route("/pipeline")
def pipeline():
    """Pipeline page."""
    return render_template("pipeline.html")


@main_bp.route("/settings")
def settings():
    """Settings page."""
    return render_template("settings.html")


@main_bp.route("/scheduler")
def scheduler():
    """Scheduler page."""
    return render_template("scheduler.html")
