# -*- coding: utf-8 -*-
"""Scheduler service.

The scheduler is started lazily and guarded by a PostgreSQL advisory lock so
that only ONE process ever runs the cron jobs. Under gunicorn (or any
multi-process server) each worker imports this module, and an unguarded
BackgroundScheduler meant every worker fired the same pipeline job: duplicate
Gemini calls, duplicate posts, duplicate pins.

The lock is session-scoped: the winning process holds an open connection with
``pg_try_advisory_lock``. If that process dies the lock is released by Postgres
and another worker picks the jobs up, so there is no stale-leader problem.
"""
import logging
import os

log = logging.getLogger("dashboard.scheduler")

# Arbitrary but fixed key: only our own app contends on it.
_LOCK_KEY = 0x0B106D0A  # "blogdolar"
_ENABLED_ENV = "ENABLE_SCHEDULER"

_scheduler = None
_scheduler_owns_lock = False
_SCHEDULER_AVAILABLE = False


def scheduler_enabled() -> bool:
    """Scheduler runs only when explicitly enabled (default: off).

    A web dyno should not run cron jobs by default: Render may spin up several
    instances, and a job firing twice costs API quota and creates duplicate
    published posts.
    """
    return os.environ.get(_ENABLED_ENV, "").strip().lower() in ("1", "true", "yes", "on")


def _try_acquire_instance_lock() -> bool:
    """Attempt to become the single scheduler instance. Never raises."""
    try:
        import psycopg2

        from dashboard.services.helpers import _env

        url = _env("DATABASE_URL", "")
        if not url:
            # No database configured: allow a single process to run jobs, which
            # is the right default for a local dev box.
            return True

        conn = psycopg2.connect(url.replace("postgres://", "postgresql://"), sslmode="require")
        cur = conn.cursor()
        cur.execute("SELECT pg_try_advisory_lock(%s)", (_LOCK_KEY,))
        acquired = cur.fetchone()[0]
        cur.close()
        if acquired:
            # Deliberately not closed: the session must stay open to hold the lock.
            globals()["_lock_conn"] = conn
            log.info("scheduler: advisory lock acquired (single instance)")
        else:
            conn.close()
            log.info("scheduler: another instance holds the lock; running idle")
        return acquired
    except Exception as e:  # unreachable DB must not crash the web worker
        log.warning("scheduler: could not acquire instance lock (%s); staying idle", e)
        return False


def get_scheduler():
    """Return the scheduler instance for THIS process, or None.

    Starts it lazily so importing the module never spawns a thread, and only
    when this process actually won the single-instance election.
    """
    global _scheduler, _SCHEDULER_AVAILABLE, _scheduler_owns_lock

    if _scheduler is not None:
        return _scheduler
    if not scheduler_enabled():
        return None

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        return None

    if not _try_acquire_instance_lock():
        return None

    _scheduler = BackgroundScheduler(
        daemon=True,
        # Never let two firings of the same job overlap: a pipeline run that
        # takes longer than the interval would otherwise stack up.
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 3600},
    )
    _scheduler.start()
    _SCHEDULER_AVAILABLE = True
    _scheduler_owns_lock = True
    log.info("scheduler: started (pid=%s)", os.getpid())
    return _scheduler


def is_scheduler_available() -> bool:
    """True only in the process that owns the scheduler."""
    return get_scheduler() is not None


def owns_scheduler_lock() -> bool:
    """True when this process is the single scheduler instance."""
    return _scheduler_owns_lock


def get_scheduler_status():
    """Return dict with scheduler running state and active jobs."""
    info = {"running": False, "jobs": [], "enabled": scheduler_enabled()}
    sched = get_scheduler()
    if sched is not None:
        info["running"] = sched.running
        info["jobs"] = [
            {"id": j.id, "next_run": str(j.next_run_time)} for j in sched.get_jobs()
        ]
    return info


def _restore_scheduler_jobs():
    """Re-register persisted jobs from scheduler_jobs.json after a restart."""
    sched = get_scheduler()
    if sched is None:
        return
    from dashboard.services.helpers import _load_json
    from dashboard.services.pipeline import _scheduled_pipeline_job
    sched_data = _load_json("scheduler_jobs.json", [])
    for job_cfg in sched_data:
        try:
            from apscheduler.triggers.cron import CronTrigger

            sched.add_job(
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
        except Exception as e:
            log.warning("scheduler: could not restore job %s (%s)", job_cfg.get("id"), e)
