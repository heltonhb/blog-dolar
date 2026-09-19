# -*- coding: utf-8 -*-
"""Pipeline API routes."""
from flask import Blueprint, jsonify, request

from dashboard.services.helpers import login_required
from dashboard.services.pipeline import (
    _clear_checkpoint,
    _load_checkpoints,
    _run_pipeline_logic,
)
from db import delete_pipeline_history_by_index, get_pipeline_history

pipeline_bp = Blueprint("pipeline", __name__, url_prefix="/api/pipeline")


@pipeline_bp.route("", methods=["POST"])
@pipeline_bp.route("/", methods=["POST"])
@login_required
def api_pipeline():
    """Trigger an end-to-end automated pipeline run."""
    try:
        data = request.json or {}
        keyword = data.get("keyword", "").strip()
        if not keyword:
            return jsonify({"success": False, "error": "Palavra-chave obrigatória"}), 400

        result = _run_pipeline_logic(
            keyword=keyword,
            pin_prompt=data.get("pin_prompt", ""),
            skip_publish=data.get("skip_publish", False),
            skip_pinterest=data.get("skip_pinterest", False),
            article_filename=data.get("article_filename", ""),
            force_restart=data.get("force_restart", False),
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@pipeline_bp.route("/history")
@login_required
def api_pipeline_history():
    """Return pipeline execution history ordered by completion date descending."""
    history = get_pipeline_history()
    if not isinstance(history, list):
        history = []
    history.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
    return jsonify(history)


@pipeline_bp.route("/history/delete/<int:index>", methods=["DELETE"])
@login_required
def api_delete_pipeline_history(index):
    """Delete a pipeline execution history entry by index."""
    try:
        deleted = delete_pipeline_history_by_index(index)
        if not deleted:
            return jsonify({"success": False, "error": f"Índice inválido: {index}"}), 404
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@pipeline_bp.route("/checkpoints")
@login_required
def api_pipeline_checkpoints():
    """Return all active pipeline checkpoints."""
    return jsonify(_load_checkpoints())


@pipeline_bp.route("/checkpoints/clear/<slug>", methods=["DELETE"])
@login_required
def api_clear_checkpoint(slug):
    """Clear checkpoints for a specific article slug."""
    try:
        _clear_checkpoint(slug)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
