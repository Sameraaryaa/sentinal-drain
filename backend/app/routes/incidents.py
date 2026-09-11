"""
Sentinel Drain - Incident Management & Multi-Agent Trace API Routes
Provides endpoints to trigger incidents, inspect agent reasoning traces,
and view evidence cards.
"""

import json
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any, Optional

from ..database import get_db_connection
from ..agents.orchestrator_agent import sentinel_orchestrator
from ..firmware_emulator.simulator_service import fleet_simulator

router = APIRouter(prefix="/api/incidents", tags=["incidents"])

@router.post("/trigger")
def trigger_incident(node_id: str = "ND-RAM-01", force_positive_assay: bool = True):
    """
    Triggers an end-to-end multi-agent evaluation starting from a drain node anomaly.
    """
    if node_id not in fleet_simulator.nodes:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found in simulator fleet.")

    node = fleet_simulator.nodes[node_id]

    # Generate current reading
    primary_reading = node.evaluate_sample(
        ph=6.45 if force_positive_assay else 7.15,
        cond=1320.0 if force_positive_assay else 840.0,
        orp=45.0 if force_positive_assay else 185.0,
        turb=95.0 if force_positive_assay else 42.0,
        temp=28.8
    )

    # Gather neighbor readings in same catchment
    neighbor_readings = [
        n.evaluate_sample(ph=6.55, cond=1280.0, orp=60.0, turb=85.0, temp=28.7)
        for nid, n in fleet_simulator.nodes.items()
        if n.catchment_id == node.catchment_id and nid != node_id
    ]

    # Run isothermal LAMP bioassay if forced
    assay_result = None
    if force_positive_assay:
        assay_result = node.run_isothermal_lamp_assay(
            target_pathogen="Vibrio cholerae O1/O139",
            force_result="POSITIVE"
        )

    incident_result = sentinel_orchestrator.process_incident(
        primary_reading=primary_reading,
        neighbor_readings=neighbor_readings,
        stage2_assay=assay_result
    )

    return incident_result

@router.get("/active")
def get_active_incidents():
    """Returns list of all active or pending incidents."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM agent_incidents
    ORDER BY created_at DESC
    LIMIT 20
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/{incident_id}")
def get_incident_details(incident_id: str):
    """Retrieves full incident dossier with evidence cards and action history."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM agent_incidents WHERE incident_id = ?", (incident_id,))
    inc_row = cursor.fetchone()
    if not inc_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Incident not found")

    incident = dict(inc_row)

    # Evidence
    cursor.execute("""
    SELECT * FROM agent_evidence
    WHERE incident_id = ?
    ORDER BY timestamp ASC
    """, (incident_id,))
    evidence_rows = [dict(r) for r in cursor.fetchall()]
    for ev in evidence_rows:
        if ev.get("data_json"):
            try:
                ev["data"] = json.loads(ev["data_json"])
            except:
                pass

    # Actions
    cursor.execute("""
    SELECT * FROM agent_actions
    WHERE incident_id = ?
    ORDER BY timestamp ASC
    """, (incident_id,))
    action_rows = [dict(r) for r in cursor.fetchall()]

    # Redistribution plans
    cursor.execute("""
    SELECT * FROM redistribution_plans
    WHERE incident_id = ?
    """, (incident_id,))
    plan_rows = [dict(r) for r in cursor.fetchall()]

    # Alerts
    cursor.execute("""
    SELECT * FROM alerts
    WHERE incident_id = ?
    """, (incident_id,))
    alert_rows = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "incident": incident,
        "evidence": evidence_rows,
        "actions": action_rows,
        "redistribution_plans": plan_rows,
        "alerts": alert_rows
    }
