# -*- coding: utf-8 -*-
"""Tests for Scheduler API.

The scheduler is opt-in (``ENABLE_SCHEDULER=1``) so that only one process among
many ever runs the cron jobs. Tests that exercise scheduling therefore enable it
explicitly and must reset the singleton between cases.
"""
import pytest


@pytest.fixture
def scheduler_on(monkeypatch):
    """Enable the scheduler for the duration of a test."""
    from dashboard.services import scheduler as scheduler_mod

    monkeypatch.setenv("ENABLE_SCHEDULER", "1")
    # No DATABASE_URL in the sandbox => _try_acquire_instance_lock() returns True
    # (single local process), which is the path we want to test here.
    monkeypatch.setattr(scheduler_mod, "_scheduler", None, raising=False)
    monkeypatch.setattr(scheduler_mod, "_scheduler_owns_lock", False, raising=False)
    yield scheduler_mod
    sched = scheduler_mod._scheduler
    if sched is not None:
        sched.shutdown(wait=False)
    monkeypatch.setattr(scheduler_mod, "_scheduler", None, raising=False)
    monkeypatch.setattr(scheduler_mod, "_scheduler_owns_lock", False, raising=False)


def test_scheduler_disabled_by_default(client):
    """Cron must be opt-in: a multi-process deploy must not fire jobs twice."""
    resp = client.get("/api/scheduler/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["enabled"] is False
    assert data["running"] is False


def test_scheduler_add_is_refused_while_disabled(client):
    """Adding a job must 503 with an actionable message, not silently no-op."""
    resp = client.post("/api/scheduler/add", json={
        "keyword": "test topic", "hour": 9, "minute": 30,
    })
    assert resp.status_code == 503
    body = resp.get_json()
    assert body["success"] is False
    assert "ENABLE_SCHEDULER" in body["error"]


def test_scheduler_status(client):
    """Test retrieving scheduler status."""
    resp = client.get("/api/scheduler/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "available" in data
    assert "running" in data
    assert "jobs" in data


def test_scheduler_add_and_remove(client, scheduler_on):
    """Test scheduling a pipeline job and removing it."""
    add_resp = client.post("/api/scheduler/add", json={
        "keyword": "test scheduled topic",
        "hour": 9,
        "minute": 30,
        "days_of_week": "mon-fri",
    })
    assert add_resp.status_code == 200
    add_data = add_resp.get_json()
    assert add_data["success"] is True
    job_id = add_data["job_id"]

    # Trigger run now
    run_resp = client.post(f"/api/scheduler/run_now/{job_id}")
    assert run_resp.status_code == 200
    assert run_resp.get_json()["success"] is True

    # Remove scheduled job
    del_resp = client.delete(f"/api/scheduler/remove/{job_id}")
    assert del_resp.status_code == 200
    assert del_resp.get_json()["success"] is True


def test_scheduler_only_one_instance_runs(scheduler_on):
    """The advisory lock must stop a second process from starting a scheduler.

    Without this, every gunicorn worker would fire the same pipeline job.
    """
    from dashboard.services import scheduler as scheduler_mod

    # Worker #1 wins the election and runs the jobs.
    scheduler_on._try_acquire_instance_lock = lambda: True
    assert scheduler_on.get_scheduler() is not None
    assert scheduler_mod.owns_scheduler_lock() is True

    # Worker #2 loses: it must not get a scheduler, and must not claim ownership.
    first = scheduler_mod._scheduler
    scheduler_mod._scheduler = None
    scheduler_mod._scheduler_owns_lock = False
    scheduler_on._try_acquire_instance_lock = lambda: False
    assert scheduler_on.get_scheduler() is None, "loser must not start jobs"
    assert scheduler_mod.owns_scheduler_lock() is False
    # restore for teardown
    scheduler_mod._scheduler = first


def test_scheduler_single_instance_acquired(scheduler_on):
    """The process that wins the lock reports ownership."""
    from dashboard.services import scheduler as scheduler_mod

    scheduler_on._try_acquire_instance_lock = lambda: True
    sched = scheduler_on.get_scheduler()
    assert sched is not None
    assert scheduler_mod.owns_scheduler_lock() is True


def test_remove_job_clears_persisted_entry(client, scheduler_on):
    """Removing a job must clear the JSON even if this process owns nothing.

    Otherwise the next restart (by whichever instance holds the lock) would
    resurrect the job.
    """
    from dashboard.services.helpers import _load_json, _save_json

    _save_json("scheduler_jobs.json", [
        {"id": "pipeline_ghost_0900", "keyword": "ghost", "hour": 9, "minute": 0}
    ])
    resp = client.delete("/api/scheduler/remove/pipeline_ghost_0900")
    assert resp.status_code == 200
    assert _load_json("scheduler_jobs.json", []) == []
