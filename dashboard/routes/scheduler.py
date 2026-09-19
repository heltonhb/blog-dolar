# -*- coding: utf-8 -*-
"""Scheduler API routes."""
import re
from datetime import datetime

from apscheduler.triggers.cron import CronTrigger
from flask import Blueprint, jsonify, request

from dashboard.services.helpers import _load_json, _save_json, login_required
from dashboard.services.pipeline import _scheduled_pipeline_job
from dashboard.services.scheduler import get_scheduler, is_scheduler_available

scheduler_bp = Blueprint("scheduler", __name__, url_prefix="/api/scheduler")


@scheduler_bp.route("/status")
@login_required
def api_scheduler_status():
    """Return scheduler status and scheduled jobs list."""
    if not is_scheduler_available():
        return jsonify({"available": False, "error": "APScheduler não instalado"})

    sched = get_scheduler()
    jobs = []
    for job in sched.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return jsonify({"available": True, "running": sched.running, "jobs": jobs})


@scheduler_bp.route("/add", methods=["POST"])
@login_required
def api_scheduler_add():
    """Add a scheduled cron pipeline job."""
    if not is_scheduler_available():
        return jsonify({"success": False, "error": "APScheduler não disponível"}), 503

    try:
        data = request.json or {}
        keyword = data.get("keyword", "").strip()
        hour = int(data.get("hour", 8))
        minute = int(data.get("minute", 0))
        days = data.get("days_of_week", "mon-sun")

        if not keyword:
            return jsonify({"success": False, "error": "Palavra-chave obrigatória"}), 400

        job_id = f"pipeline_{re.sub(r'[^a-z0-9]', '_', keyword.lower()[:30])}_{hour:02d}{minute:02d}"

        sched = get_scheduler()
        try:
            sched.remove_job(job_id)
        except Exception:
            pass

        sched.add_job(
            _scheduled_pipeline_job,
            trigger=CronTrigger(day_of_week=days, hour=hour, minute=minute),
            args=[keyword],
            id=job_id,
            name=f"Pipeline: {keyword[:40]}",
            replace_existing=True,
        )

        sched_data = _load_json("scheduler_jobs.json", [])
        sched_data = [j for j in sched_data if j.get("id") != job_id]
        sched_data.append({
            "id": job_id,
            "keyword": keyword,
            "hour": hour,
            "minute": minute,
            "days": days,
            "created_at": datetime.now().isoformat(),
        })
        _save_json("scheduler_jobs.json", sched_data)

        job = sched.get_job(job_id)
        return jsonify({
            "success": True,
            "job_id": job_id,
            "next_run": str(job.next_run_time) if job and job.next_run_time else None,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/remove/<job_id>", methods=["DELETE"])
@login_required
def api_scheduler_remove(job_id):
    """Remove a job from the scheduler."""
    if not is_scheduler_available():
        return jsonify({"success": False, "error": "APScheduler não disponível"}), 503

    try:
        sched = get_scheduler()
        try:
            sched.remove_job(job_id)
        except Exception:
            pass
        sched_data = _load_json("scheduler_jobs.json", [])
        sched_data = [j for j in sched_data if j.get("id") != job_id]
        _save_json("scheduler_jobs.json", sched_data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/run_now/<job_id>", methods=["POST"])
@login_required
def api_scheduler_run_now(job_id):
    """Trigger an existing scheduled job immediately."""
    if not is_scheduler_available():
        return jsonify({"success": False, "error": "APScheduler não disponível"}), 503

    try:
        sched_data = _load_json("scheduler_jobs.json", [])
        job_cfg = next((j for j in sched_data if j.get("id") == job_id), None)
        if not job_cfg:
            return jsonify({"success": False, "error": "Job não encontrado"}), 404

        sched = get_scheduler()
        sched.add_job(
            _scheduled_pipeline_job,
            args=[job_cfg["keyword"]],
            id=f"{job_id}_manual_{int(datetime.now().timestamp())}",
            name=f"Manual: {job_cfg['keyword'][:40]}",
        )
        return jsonify({"success": True, "message": f"Executando agora: {job_cfg['keyword']}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
