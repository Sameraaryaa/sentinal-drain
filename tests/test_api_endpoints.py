"""
Unit and Integration Tests for Sentinel Drain API Endpoints
Verifies:
- Telemetry ingestion routes (/api/telemetry)
- Incident management and audit trace routes (/api/incidents)
- Vertex AI forecasting routes (/api/forecasts)
- Supply chain and human approval routes (/api/supply-chain)
- Multilingual alerts routes (/api/alerts)
- Simulation controller routes (/api/simulation)
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.seed_data import seed_all_data

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_clean_db():
    seed_all_data()

def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert data["version"] == "1.1.0"

def test_telemetry_nodes_endpoint():
    res = client.get("/api/telemetry/nodes")
    assert res.status_code == 200
    nodes = res.json()
    assert len(nodes) == 11
    assert any(n["node_id"] == "ND-RAM-01" for n in nodes)

def test_stage1_ingestion():
    payload = {
        "node_id": "ND-RAM-01",
        "catchment_id": "CAT-RAMPUR",
        "phc_id": "PHC-RAMPUR",
        "timestamp": 1700000000.0,
        "ph": 7.18,
        "conductivity": 845.0,
        "orp": 182.0,
        "turbidity": 43.0,
        "temperature": 28.3,
        "anomaly_score": 0.45,
        "is_dilution_event": False,
        "probe_fouling": False,
        "battery_pct": 98,
        "battery_voltage": 12.8,
        "solar_voltage": 18.2,
        "reagents_remaining": 26,
        "trigger_assay_recommended": False,
        "is_assay_active": False
    }
    res = client.post("/api/telemetry/stage1", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "INGESTED"

def test_forecast_endpoints():
    res = client.get("/api/forecasts/catchment/CAT-RAMPUR")
    assert res.status_code == 200
    data = res.json()
    assert "surge_probability" in data
    assert "lead_time_days" in data
    assert "primary_drivers" in data

    res_all = client.get("/api/forecasts/all")
    assert res_all.status_code == 200
    assert len(res_all.json()) >= 5

def test_supply_chain_inventory_and_human_approval():
    # 1. Fetch inventory
    res_inv = client.get("/api/supply-chain/inventory")
    assert res_inv.status_code == 200
    inv = res_inv.json()
    assert len(inv) == 5

    # 2. Trigger incident to generate a plan
    res_trig = client.post("/api/incidents/trigger", params={"node_id": "ND-RAM-01", "force_positive_assay": True})
    assert res_trig.status_code == 200
    inc_data = res_trig.json()
    assert len(inc_data["plan_ids"]) > 0
    plan_id = inc_data["plan_ids"][0]

    # 3. Test Human-in-the-loop Approval Action Gate
    approval_payload = {
        "plan_id": plan_id,
        "incident_id": inc_data["incident_id"],
        "officer_name": "Dr. Arvind Saxena",
        "officer_role": "District Health Supply Coordinator",
        "action": "APPROVED",
        "comments": "Approved emergency pre-positioning based on Sentinel Drain early warning."
    }
    res_app = client.post("/api/supply-chain/approve", json=approval_payload)
    assert res_app.status_code == 200
    app_data = res_app.json()
    assert app_data["status"] == "PROCESSED"
    assert app_data["action"] == "APPROVED"

    # 4. Verify inventory was updated
    res_plans = client.get("/api/supply-chain/plans", params={"status": "APPROVED"})
    assert res_plans.status_code == 200
    approved_plans = res_plans.json()
    assert any(p["plan_id"] == plan_id for p in approved_plans)

def test_alerts_dispatch():
    res_alerts = client.get("/api/alerts/latest")
    assert res_alerts.status_code == 200
    alerts = res_alerts.json()
    if len(alerts) > 0:
        alert_id = alerts[0]["alert_id"]
        res_disp = client.post(f"/api/alerts/dispatch/{alert_id}")
        assert res_disp.status_code == 200
        assert res_disp.json()["status"] == "DISPATCH_CONFIRMED"

def test_simulation_scenarios_and_tick():
    # Test setting scenario
    res_scen = client.post("/api/simulation/scenario", json={"scenario": "MONSOON_DILUTION"})
    assert res_scen.status_code == 200
    assert res_scen.json()["scenario"] == "MONSOON_DILUTION"

    # Test tick execution
    res_tick = client.post("/api/simulation/tick")
    assert res_tick.status_code == 200
    assert res_tick.json()["status"] == "TICK_COMPLETED"
    assert res_tick.json()["packets_generated"] == 11
