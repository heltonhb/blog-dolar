# -*- coding: utf-8 -*-
"""Scheduler service."""
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.start()
    _SCHEDULER_AVAILABLE = True
except ImportError:
    _scheduler = None
    _SCHEDULER_AVAILABLE = False


def get_scheduler():
    """Return the global BackgroundScheduler instance, or None if unavailable."""
    return _scheduler


def is_scheduler_available():
    """Check if APScheduler is installed and running."""
    return _SCHEDULER_AVAILABLE and _scheduler is not None


def get_scheduler_status():
    """Return dict with scheduler running state and active jobs."""
    info = {"running": False, "jobs": []}
    if is_scheduler_available() and _scheduler:
        info["running"] = _scheduler.running
        info["jobs"] = [
            {"id": j.id, "next_run": str(j.next_run_time)} for j in _scheduler.get_jobs()
        ]
    return info


def _restore_scheduler_jobs():
    """Re-register persisted jobs from scheduler_jobs.json after server restart."""
    if not is_scheduler_available():
        return
    from dashboard.services.helpers import _load_json
    from dashboard.services.pipeline import _scheduled_pipeline_job
    sched_data = _load_json("scheduler_jobs.json", [])
    for job_cfg in sched_data:
        try:
            _scheduler.add_job(
                _scheduled_pipeline_job,
                trigger=CronTrigger(
                    day_of_week=job_cfg.get("days", "mon-sun"),
                    hour=int(job_cfg.get("hour", 8)),
                    minute=int(job_cfg.get("minute", 0)),
                ),
                args=[job_cfg["keyword"]],
                id=job_cfg["id"],
                name=f"Pipeline: {job_cfg['keyword'][:40]}",
                replace_existing=True,
            )
        except Exception:
            pass
