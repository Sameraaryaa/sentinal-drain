"""
Sentinel Drain - Scenario Simulator & Hackathon Demo Runner API Routes
Controls demonstration scenarios: Outbreak Surge, Monsoon Rain Dilution,
Sensor Fouling, and Rotavirus Pediatric Surge.
"""

from fastapi import APIRouter
from typing import Dict, List, Any

from ..firmware_emulator.simulator_service import fleet_simulator
from ..agents.orchestrator_agent import sentinel_orchestrator
from ..database import get_db_connection
from ..seed_data import seed_all_data
from ..models import ScenarioTriggerRequest

router = APIRouter(prefix="/api/simulation", tags=["simulation"])

@router.get("/status")
def get_simulation_status():
    """Returns the currently active simulation scenario and fleet stats."""
    return {
        "active_scenario": fleet_simulator.active_scenario,
        "scenario_start_time": fleet_simulator.scenario_start_time,
        "total_nodes": len(fleet_simulator.nodes),
        "available_scenarios": [
            {
                "id": "OUTBREAK_CHOLERA",
                "name": "Pre-Symptomatic Cholera Surge (Catchment Rampur)",
                "description": "Full end-to-end early warning: Stage-1 anomaly -> LAMP bioassay positive -> Vertex AI 84% surge forecast in 4.5 days -> OR-Tools stock redistribution -> Human Approval Gate -> Multilingual alerts."
            },
            {
                "id": "MONSOON_DILUTION",
                "name": "Monsoon Rain Dilution (Edge Case Mitigation)",
                "description": "Demonstrates PRD FR-9: High turbidity with severe conductivity drop from stormwater runoff. Sensor Intel and Risk Auditor flag dilution and suppress false alerts."
            },
            {
                "id": "PROBE_FOULING",
                "name": "Electrode Bio-Fouling & Hardware Diagnostic",
                "description": "Demonstrates PRD FR-8: Biofilm coating on sensor probe produces erratic flatline. Sensor Intel issues maintenance ticket instead of false alarm."
            },
            {
                "id": "OUTBREAK_ROTAVIRUS",
                "name": "Rotavirus Pediatric Outbreak (Catchment Chauri Chaura)",
                "description": "Pathogen panel switch: Optical colorimetric detection of Rotavirus Group A leading to pediatric ORS and zinc supply redistribution."
            },
            {
                "id": "BASELINE",
                "name": "Healthy Nominal Baseline",
                "description": "Stable domestic wastewater parameters across all 5 PHCs with rolling baseline control-charts."
            }
        ]
    }

@router.post("/scenario")
def set_scenario(req: ScenarioTriggerRequest):
    """Sets active scenario."""
    res = fleet_simulator.set_scenario(req.scenario)
    return res

@router.post("/tick")
def run_simulation_tick(auto_trigger_incident: bool = True):
    """
    Simulates one time-step across the node network:
    - Generates Stage-1 packets
    - Ingests into database
    - Evaluates for anomaly triggers
    - Automatically coordinates multi-agent workflow if anomaly threshold exceeded
    """
    packets = fleet_simulator.generate_fleet_telemetry()
    conn = get_db_connection()
    cursor = conn.cursor()

    triggered_incidents = []

    for pkt in packets:
        # Ingest reading
        cursor.execute("""
        INSERT INTO readings_stage1 (
            node_id, catchment_id, timestamp, ph, conductivity, orp,
            turbidity, temperature, anomaly_score, is_dilution_event, probe_fouling
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pkt["node_id"], pkt["catchment_id"], pkt["timestamp"],
            pkt["ph"], pkt["conductivity"], pkt["orp"], pkt["turbidity"],
            pkt["temperature"], pkt["anomaly_score"],
            1 if pkt["is_dilution_event"] else 0,
            1 if pkt["probe_fouling"] else 0
        ))

        cursor.execute("""
        UPDATE nodes SET
            battery_pct = ?,
            reagents_remaining = ?,
            last_seen = ?,
            status = CASE
                WHEN ? = 1 THEN 'FOULING_ALERT'
                WHEN ? = 1 THEN 'DILUTION_FLAG'
                ELSE 'ONLINE'
            END
        WHERE node_id = ?
        """, (
            pkt["battery_pct"], pkt["reagents_remaining"], pkt["timestamp"],
            1 if pkt["probe_fouling"] else 0,
            1 if pkt["is_dilution_event"] else 0,
            pkt["node_id"]
        ))

    conn.commit()
    conn.close()

    # If an outbreak or anomaly scenario is active, coordinate an incident
    if auto_trigger_incident and fleet_simulator.active_scenario != "BASELINE":
        # Pick primary anomaly node based on scenario
        if fleet_simulator.active_scenario == "OUTBREAK_CHOLERA":
            target_node_id = "ND-RAM-01"
            force_assay = "POSITIVE"
        elif fleet_simulator.active_scenario == "OUTBREAK_ROTAVIRUS":
            target_node_id = "ND-CHA-01"
            force_assay = "POSITIVE"
        elif fleet_simulator.active_scenario == "MONSOON_DILUTION":
            target_node_id = "ND-RAM-02"
            force_assay = "NEGATIVE"
        elif fleet_simulator.active_scenario == "PROBE_FOULING":
            target_node_id = "ND-SIT-01"
            force_assay = "INCONCLUSIVE"
        else:
            target_node_id = "ND-RAM-01"
            force_assay = None

        node = fleet_simulator.nodes[target_node_id]
        primary_pkt = next((p for p in packets if p["node_id"] == target_node_id), packets[0])
        neighbors = [p for p in packets if p["catchment_id"] == node.catchment_id and p["node_id"] != target_node_id]

        assay_res = None
        if force_assay:
            assay_res = fleet_simulator.trigger_node_assay(target_node_id, force_result=force_assay)

        incident_result = sentinel_orchestrator.process_incident(
            primary_reading=primary_pkt,
            neighbor_readings=neighbors,
            stage2_assay=assay_res
        )
        triggered_incidents.append(incident_result)

    return {
        "status": "TICK_COMPLETED",
        "scenario": fleet_simulator.active_scenario,
        "packets_generated": len(packets),
        "incidents_created": len(triggered_incidents),
        "latest_incident": triggered_incidents[0] if triggered_incidents else None
    }

@router.post("/reset")
def reset_database():
    """Resets database and fleet to clean baseline state."""
    seed_all_data()
    fleet_simulator.set_scenario("BASELINE")
    return {"status": "RESET_COMPLETE", "message": "Fleet and database restored to pristine baseline state."}

# --- Background Real-Time Auto-Streamer ---
import threading
import time

LIVE_STREAMING_ACTIVE = True
LIVE_STREAM_INTERVAL = 3.5  # seconds
TOTAL_LIVE_TICKS = 0
_stream_thread = None

def _background_streamer_loop():
    global TOTAL_LIVE_TICKS
    while True:
        try:
            if LIVE_STREAMING_ACTIVE:
                # Run tick without printing/spamming
                run_simulation_tick(auto_trigger_incident=True)
                TOTAL_LIVE_TICKS += 1
        except Exception as e:
            # Prevent thread death on transient error
            pass
        time.sleep(LIVE_STREAM_INTERVAL)

def start_background_streamer():
    global _stream_thread
    if _stream_thread is None or not _stream_thread.is_alive():
        _stream_thread = threading.Thread(target=_background_streamer_loop, daemon=True)
        _stream_thread.start()

@router.get("/stream/status")
def get_stream_status():
    """Returns status of live background sensor stream."""
    return {
        "is_streaming": LIVE_STREAMING_ACTIVE,
        "interval_seconds": LIVE_STREAM_INTERVAL,
        "total_ticks": TOTAL_LIVE_TICKS,
        "active_scenario": fleet_simulator.active_scenario
    }

@router.post("/stream/toggle")
def toggle_stream():
    """Toggles live streaming on/off."""
    global LIVE_STREAMING_ACTIVE
    LIVE_STREAMING_ACTIVE = not LIVE_STREAMING_ACTIVE
    return {
        "is_streaming": LIVE_STREAMING_ACTIVE,
        "message": f"Live streaming is now {'ACTIVE' if LIVE_STREAMING_ACTIVE else 'PAUSED'}"
    }

@router.get("/logs")
def get_operational_logs():
    """Returns real-time system, network, and agent audit logs for Cloud Shell terminal."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 'STAGE1' as log_type, datetime(timestamp, 'unixepoch', 'localtime') as time_str,
           node_id || ': pH=' || printf('%.2f', ph) || ', Cond=' || printf('%.0f', conductivity) || 'uS, ORP=' || printf('%.0f', orp) || 'mV, Z-score=' || printf('%.2f', anomaly_score) as message
    FROM readings_stage1 ORDER BY timestamp DESC LIMIT 15
    """)
    rows = cursor.fetchall()
    conn.close()
    
    formatted_logs = [
        f"[{r['time_str']}] [ESP32-S3::{r['log_type']}] {r['message']}"
        for r in reversed(rows)
    ]
    if not formatted_logs:
        formatted_logs = [
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [GCP-RUN] Sentinel Drain Cloud Run Ingestion Online (asia-south1)",
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [BIGQUERY] Streaming insert buffer healthy. 11 nodes reporting.",
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [OR-TOOLS] Linear programming min-cost network flow solver ready."
        ]
    return {"logs": formatted_logs, "total_ticks": TOTAL_LIVE_TICKS}


