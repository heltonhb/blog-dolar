# -*- coding: utf-8 -*-
"""Tests for Ideas API."""
from unittest.mock import patch


def test_list_ideas(client):
    """Test listing ideas."""
    resp = client.get("/api/ideas/list")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_add_and_delete_idea(client):
    """Test adding an idea and subsequently deleting it."""
    # Add idea
    payload = {
        "title": "Test Automated Unit Testing",
        "keyword": "pytest automated testing",
        "category": "technology",
        "cpm_estimate": "$15-25",
    }
    add_resp = client.post("/api/ideas/add", json=payload)
    assert add_resp.status_code == 200
    add_data = add_resp.get_json()
    assert add_data["success"] is True
    idea_id = add_data["idea"]["idea_id"]

    # Delete idea
    del_resp = client.post(f"/api/ideas/delete/{idea_id}")
    assert del_resp.status_code == 200
    assert del_resp.get_json()["success"] is True


def test_generate_ideas_mocked(client):
    """Test generating ideas with mocked Gemini call."""
    mock_llm_output = (
        '[{"title":"Future of Quantum Computing","keyword":"quantum computing 2026",'
        '"cpm_estimate":"$20-30","category":"technology"}]'
    )
    with patch("dashboard.routes.ideas._gemini_call", return_value=mock_llm_output):
        resp = client.post("/api/ideas/generate", json={"source": "ai"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert len(data["ideas"]) >= 1
        assert data["ideas"][0]["keyword"] == "quantum computing 2026"
