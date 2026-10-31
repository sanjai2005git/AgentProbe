"""
Tests for FastAPI Endpoints.
"""

from fastapi.testclient import TestClient
from agentprobe.api.server import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_list_scenarios():
    response = client.get("/scenarios?limit=10")
    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) == 10
    assert scenarios[0]["id"].startswith("SCEN-")


def test_get_scenario_detail():
    response = client.get("/scenarios/SCEN-001")
    assert response.status_code == 200
    scenario = response.json()
    assert scenario["id"] == "SCEN-001"
    assert "expected_tool_sequence" in scenario


def test_run_single_eval_api():
    payload = {
        "scenario_id": "SCEN-001",
        "architecture": "barebones_react",
        "model_name": "golden",
    }
    response = client.post("/eval/run-single", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["scenario_id"] == "SCEN-001"
    assert "metrics" in data
    assert "trajectory" in data
    assert data["metrics"]["task_success"] is True


def test_run_benchmark_api():
    payload = {
        "scenario_count": 3,
        "architectures": ["barebones_react"],
        "models": ["golden"],
    }
    response = client.post("/eval/benchmark", json=payload)
    assert response.status_code == 200
    bench = response.json()
    assert bench["overall_summary"]["total_runs"] == 3

