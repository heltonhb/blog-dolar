# -*- coding: utf-8 -*-
"""Scheduler API routes."""
import re
from datetime import datetime

from apscheduler.triggers.cron import CronTrigger
from flask import Blueprint, jsonify, request

from dashboard.services.helpers import _load_json, _save_json, login_required
from dashboard.services.pipeline import _scheduled_pipeline_job
from dashboard.services.scheduler import get_scheduler


scheduler_bp = Blueprint("scheduler", __name__, url_prefix="/api/scheduler")

_DISABLED_MSG = (
    "Agendador desativado. Defina ENABLE_SCHEDULER=1 no ambiente e reinicie. "
    "Sem isso apenas uma instância do Render pode rodar os jobs, evitando duplicatas."
)


@scheduler_bp.route("/status")
@login_required
def api_scheduler_status():
    """Return scheduler status and scheduled jobs list."""
    from dashboard.services.scheduler import get_scheduler_status

    status = get_scheduler_status()
    return jsonify({
        "available": status["running"],
        "enabled": status["enabled"],
        "running": status["running"],
        "jobs": status["jobs"],
    })


@scheduler_bp.route("/add", methods=["POST"])
@login_required
def api_scheduler_add():
    """Add a scheduled cron pipeline job."""
    sched = get_scheduler()
    if sched is None:
        return jsonify({"success": False, "error": _DISABLED_MSG}), 503

    try:
        data = request.json or {}
        keyword = data.get("keyword", "").strip()
        hour = int(data.get("hour", 8))
        minute = int(data.get("minute", 0))
        days = data.get("days_of_week", "mon-sun")

        if not keyword:
            return jsonify({"success": False, "error": "Palavra-chave obrigatória"}), 400

        job_id = f"pipeline_{re.sub(r'[^a-z0-9]', '_', keyword.lower()[:30])}_{hour:02d}{minute:02d}"

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
    """Remove a job from the scheduler and from the persisted list.

    Works even when this process does not run the scheduler: the JSON entry
    must be cleared regardless, otherwise the job would be restored on the next
    restart by whichever instance holds the lock.
    """
    sched = get_scheduler()
    if sched is not None:
        try:
            sched.remove_job(job_id)
        except Exception:
            pass

    sched_data = _load_json("scheduler_jobs.json", [])
    remaining = [j for j in sched_data if j.get("id") != job_id]
    _save_json("scheduler_jobs.json", remaining)
    return jsonify({"success": True, "removed": len(sched_data) - len(remaining)})


@scheduler_bp.route("/add_drip", methods=["POST"])
@login_required
def api_scheduler_add_drip():
    """Add a scheduled Pinterest drip-feed cron job."""
    sched = get_scheduler()
    if sched is None:
        return jsonify({"success": False, "error": _DISABLED_MSG}), 503

    try:
        data = request.json or {}
        hour = int(data.get("hour", 11))
        minute = int(data.get("minute", 0))
        days = data.get("days_of_week", "mon-sun")
        board_id = data.get("board_id", "").strip()

        job_id = f"pinterest_drip_{hour:02d}{minute:02d}"

        try:
            sched.remove_job(job_id)
        except Exception:
            pass

        from dashboard.services.pipeline import _scheduled_pinterest_drip_job

        sched.add_job(
            _scheduled_pinterest_drip_job,
            trigger=CronTrigger(day_of_week=days, hour=hour, minute=minute),
            args=[board_id],
            id=job_id,
            name=f"Pinterest Drip ({hour:02d}:{minute:02d})",
            replace_existing=True,
        )

        sched_data = _load_json("scheduler_jobs.json", [])
        sched_data = [j for j in sched_data if j.get("id") != job_id]
        sched_data.append({
            "id": job_id,
            "type": "pinterest_drip",
            "hour": hour,
            "minute": minute,
            "days": days,
            "board_id": board_id,
            "name": f"Pinterest Drip ({hour:02d}:{minute:02d})",
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


@scheduler_bp.route("/autopilot", methods=["POST"])
@login_required
def api_scheduler_autopilot():
    """Execute a 1-click end-to-end monetization cycle now."""
    try:
        data = request.json or {}
        idea_id = data.get("idea_id")
        category = data.get("category", "buyer_intent")
        skip_publish = bool(data.get("skip_publish", False))
        skip_pinterest = bool(data.get("skip_pinterest", False))
        force_restart = bool(data.get("force_restart", False))
        async_run = bool(data.get("async", False))

        from dashboard.services.pipeline import run_autopilot_cycle

        if async_run:
            import threading

            thread = threading.Thread(
                target=run_autopilot_cycle,
                kwargs={
                    "idea_id": idea_id,
                    "category_filter": category,
                    "skip_publish": skip_publish,
                    "skip_pinterest": skip_pinterest,
                    "force_restart": force_restart,
                },
                daemon=True,
            )
            thread.start()
            return jsonify({
                "success": True,
                "message": "Ciclo de Piloto Automático iniciado em segundo plano.",
                "async": True,
            })

        result = run_autopilot_cycle(
            idea_id=idea_id,
            category_filter=category,
            skip_publish=skip_publish,
            skip_pinterest=skip_pinterest,
            force_restart=force_restart,
        )
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/add_autopilot", methods=["POST"])
@login_required
def api_scheduler_add_autopilot():
    """Add a recurring scheduled autopilot cron job."""
    sched = get_scheduler()
    if sched is None:
        return jsonify({"success": False, "error": _DISABLED_MSG}), 503

    try:
        data = request.json or {}
        hour = int(data.get("hour", 9))
        minute = int(data.get("minute", 0))
        days = data.get("days_of_week", "mon-sun")
        category = data.get("category", "buyer_intent").strip() or "buyer_intent"

        job_id = f"autopilot_{hour:02d}{minute:02d}"

        try:
            sched.remove_job(job_id)
        except Exception:
            pass

        from dashboard.services.pipeline import _scheduled_autopilot_job

        sched.add_job(
            _scheduled_autopilot_job,
            trigger=CronTrigger(day_of_week=days, hour=hour, minute=minute),
            args=[category],
            id=job_id,
            name=f"Piloto Automático ({hour:02d}:{minute:02d})",
            replace_existing=True,
        )

        sched_data = _load_json("scheduler_jobs.json", [])
        sched_data = [j for j in sched_data if j.get("id") != job_id]
        sched_data.append({
            "id": job_id,
            "type": "autopilot",
            "hour": hour,
            "minute": minute,
            "days": days,
            "category": category,
            "name": f"Piloto Automático ({hour:02d}:{minute:02d})",
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


@scheduler_bp.route("/run_now/<job_id>", methods=["POST"])
@login_required
def api_scheduler_run_now(job_id):
    """Trigger an existing scheduled job immediately."""
    sched = get_scheduler()
    if sched is None:
        return jsonify({"success": False, "error": _DISABLED_MSG}), 503

    try:
        sched_data = _load_json("scheduler_jobs.json", [])
        job_cfg = next((j for j in sched_data if j.get("id") == job_id), None)
        if not job_cfg:
            return jsonify({"success": False, "error": "Job não encontrado"}), 404

        job_type = job_cfg.get("type") or (
            "pinterest_drip"
            if str(job_cfg.get("id", "")).startswith("pinterest_drip")
            else (
                "autopilot"
                if str(job_cfg.get("id", "")).startswith("autopilot")
                else "pipeline"
            )
        )
        if job_type == "pinterest_drip":
            from dashboard.services.pipeline import _scheduled_pinterest_drip_job

            sched.add_job(
                _scheduled_pinterest_drip_job,
                args=[job_cfg.get("board_id", "")],
                id=f"{job_id}_manual_{int(datetime.now().timestamp())}",
                name="Manual: Pinterest Drip",
            )
            return jsonify({"success": True, "message": "Executando agora: Pinterest Drip"})

        if job_type == "autopilot":
            from dashboard.services.pipeline import _scheduled_autopilot_job

            sched.add_job(
                _scheduled_autopilot_job,
                args=[job_cfg.get("category", "buyer_intent")],
                id=f"{job_id}_manual_{int(datetime.now().timestamp())}",
                name="Manual: Piloto Automático",
            )
            return jsonify({"success": True, "message": "Executando agora: Piloto Automático"})

        sched.add_job(
            _scheduled_pipeline_job,
            args=[job_cfg.get("keyword", "")],
            id=f"{job_id}_manual_{int(datetime.now().timestamp())}",
            name=f"Manual: {job_cfg.get('keyword', '')[:40]}",
        )
        return jsonify({"success": True, "message": f"Executando agora: {job_cfg.get('keyword', '')}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

