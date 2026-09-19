# -*- coding: utf-8 -*-
"""Tests for Scheduler API."""


def test_scheduler_status(client):
    """Test retrieving scheduler status."""
    resp = client.get("/api/scheduler/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "available" in data
    assert "running" in data
    assert "jobs" in data


def test_scheduler_add_and_remove(client):
    """Test scheduling a pipeline job and removing it."""
    # Add scheduled job
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
