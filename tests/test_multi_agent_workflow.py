"""
Unit Tests for Google ADK Multi-Agent Architecture & Specialist Agents
Verifies PRD requirements:
- FR-12 to FR-17: Sentinel Orchestrator, Sensor Intelligence, Epidemiology,
  Supply Chain, and Risk & Validation Agents
- Multilingual alert generation (EN, HI, KN, TA)
- Adversarial auditing and Human-in-the-loop gate enforcement
"""

import pytest
from backend.app.agents.sensor_intelligence_agent import SensorIntelligenceAgent
from backend.app.agents.epidemiology_agent import EpidemiologyAgent
from backend.app.agents.supply_chain_agent import SupplyChainAgent
from backend.app.agents.risk_validation_agent import RiskValidationAgent
from backend.app.agents.orchestrator_agent import SentinelOrchestratorAgent
from backend.app.seed_data import seed_all_data

@pytest.fixture(autouse=True)
def setup_db():
    seed_all_data()

def test_sensor_intelligence_agent():
    agent = SensorIntelligenceAgent()

    # Biological anomaly
    primary = {"node_id": "ND-01", "catchment_id": "CAT-01", "anomaly_score": 3.2, "ph": 6.5, "conductivity": 1250.0, "orp": 50.0}
    neighbors = [{"node_id": "ND-02", "anomaly_score": 2.8}]

    res = agent.assess_telemetry("INC-TEST", primary, neighbors)
    assert res["verdict"] == "VALIDATED_BIOLOGICAL_ANOMALY"
    assert res["trigger_stage2"] is True
    assert res["evidence"]["confidence"] > 0.80

def test_risk_validation_agent_adversarial_downgrade_on_dilution():
    agent = RiskValidationAgent()

    sensor_res = {"verdict": "STORMWATER_DILUTION_DETECTED"}
    epi_res = {"lead_time_days": 4.0, "surge_probability": 0.65}
    supply_res = {"transfers": []}

    res = agent.audit_incident("INC-TEST-DIL", sensor_res, epi_res, supply_res)
    assert res["audit_status"] == "DOWNGRADE_RECOMMENDED"
    assert res["human_approval_required"] is False
    assert len(res["concerns"]) > 0

def test_orchestrator_full_outbreak_lifecycle():
    orchestrator = SentinelOrchestratorAgent()

    primary_reading = {
        "node_id": "ND-RAM-01",
        "catchment_id": "CAT-RAMPUR",
        "phc_id": "PHC-RAMPUR",
        "timestamp": 1700000000.0,
        "ph": 6.45,
        "conductivity": 1320.0,
        "orp": 45.0,
        "turbidity": 95.0,
        "temperature": 28.8,
        "anomaly_score": 4.2,
        "is_dilution_event": False,
        "probe_fouling": False
    }

    stage2_assay = {
        "node_id": "ND-RAM-01",
        "target_pathogen": "Vibrio cholerae O1",
        "optical_absorbance_ratio": 2.45,
        "result": "POSITIVE",
        "confidence": 0.96
    }

    res = orchestrator.process_incident(primary_reading, [], stage2_assay)

    # Incident should be awaiting human approval due to cross-district stock movement
    assert res["status"] == "AWAITING_HUMAN_APPROVAL"
    assert res["human_approval_required"] is True
    assert res["epidemiology"]["surge_probability"] > 0.70
    assert 3.0 <= res["epidemiology"]["lead_time_days"] <= 7.0
    assert len(res["supply_chain"]["transfers"]) > 0

    # Verify multilingual alerts exist
    assert "en" in res["alerts"]
    assert "hi" in res["alerts"]
    assert "kn" in res["alerts"]
    assert "ta" in res["alerts"]
    assert "Vibrio" in res["alerts"]["en"]
    assert "हैलोज़न" in res["alerts"]["hi"] or "रोगाणु" in res["alerts"]["hi"] or "ओपीडी" in res["alerts"]["hi"]
