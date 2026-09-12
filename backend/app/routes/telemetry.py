"""
Sentinel Drain - Telemetry Ingestion API Routes
Handles live packet ingestion from drain nodes and queries for time-series charts.
"""

import time
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any, Optional

from ..database import get_db_connection
from ..models import Stage1ReadingModel, Stage2AssayModel
from ..firmware_emulator.simulator_service import fleet_simulator

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])

@router.post("/stage1")
def ingest_stage1(reading: Stage1ReadingModel):
    """Ingests Stage-1 physicochemical telemetry packet."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO readings_stage1 (
        node_id, catchment_id, timestamp, ph, conductivity, orp,
        turbidity, temperature, anomaly_score, is_dilution_event, probe_fouling
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        reading.node_id, reading.catchment_id, reading.timestamp,
        reading.ph, reading.conductivity, reading.orp, reading.turbidity,
        reading.temperature, reading.anomaly_score,
        1 if reading.is_dilution_event else 0,
        1 if reading.probe_fouling else 0
    ))

    # Update node last seen and battery
    cursor.execute("""
    UPDATE nodes SET
        battery_pct = ?,
        reagents_remaining = ?,
        last_seen = ?,
        status = CASE WHEN ? = 1 THEN 'FOULING_ALERT' ELSE 'ONLINE' END
    WHERE node_id = ?
    """, (
        reading.battery_pct, reading.reagents_remaining,
        reading.timestamp, 1 if reading.probe_fouling else 0,
        reading.node_id
    ))

    conn.commit()
    conn.close()

    return {"status": "INGESTED", "node_id": reading.node_id, "timestamp": reading.timestamp}

@router.post("/stage2")
def ingest_stage2(assay: Stage2AssayModel):
    """Ingests Stage-2 isothermal LAMP bioassay result."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO readings_stage2 (
        node_id, catchment_id, timestamp, target_pathogen,
        assay_temperature_c, optical_absorbance_ratio, result, confidence
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        assay.node_id, assay.catchment_id, assay.timestamp,
        assay.target_pathogen, assay.assay_temperature_c,
        assay.optical_absorbance_ratio, assay.result, assay.confidence
    ))

    cursor.execute("""
    UPDATE nodes SET
        reagents_remaining = ?,
        last_seen = ?
    WHERE node_id = ?
    """, (assay.cartridge_remaining, assay.timestamp, assay.node_id))

    conn.commit()
    conn.close()

    return {"status": "ASSAY_LOGGED", "node_id": assay.node_id, "result": assay.result}

@router.get("/nodes")
def list_nodes():
    """Returns real-time status, health, and GPS coordinates for all nodes."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM nodes ORDER BY node_id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/history/{node_id}")
def get_node_history(node_id: str, limit: int = 48):
    """Retrieves recent telemetry history for time-series charts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM readings_stage1
    WHERE node_id = ?
    ORDER BY timestamp DESC
    LIMIT ?
    """, (node_id, limit))
    rows = cursor.fetchall()
    conn.close()
    # Return chronologically ascending
    return [dict(r) for r in reversed(rows)]

@router.post("/trigger-stage2/{node_id}")
def trigger_manual_stage2(node_id: str):
    """Triggers an on-demand Stage-2 LAMP bioassay on a specific edge node."""
    if node_id not in fleet_simulator.nodes:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found in fleet.")
    
    node = fleet_simulator.nodes[node_id]
    target_pathogen = "Vibrio cholerae O1/O139" if "RAM" in node_id or "BIL" in node_id else "Rotavirus Group A"
    assay = node.run_isothermal_lamp_assay(target_pathogen=target_pathogen, force_result="POSITIVE")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO readings_stage2 (
        node_id, catchment_id, timestamp, target_pathogen,
        assay_temperature_c, optical_absorbance_ratio, result, confidence
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        assay.node_id, assay.catchment_id, assay.timestamp,
        assay.target_pathogen, assay.assay_temperature_c,
        assay.optical_absorbance_ratio, assay.result, assay.confidence
    ))
    cursor.execute("""
    UPDATE nodes SET reagents_remaining = ?, last_seen = ? WHERE node_id = ?
    """, (assay.cartridge_remaining, assay.timestamp, assay.node_id))
    conn.commit()
    conn.close()
    
    return {"status": "TRIGGERED", "node_id": node_id, "assay": assay.__dict__}

@router.post("/clean/{node_id}")
def clean_sensor_probe(node_id: str):
    """Performs manual/ultrasonic sensor cleaning and clears fouling flags."""
    if node_id not in fleet_simulator.nodes:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found in fleet.")
    
    node = fleet_simulator.nodes[node_id]
    node.probe_fouling = False
    node.status = "ONLINE"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE nodes SET status = 'ONLINE' WHERE node_id = ?", (node_id,))
    conn.commit()
    conn.close()
    
    return {"status": "CLEANED", "node_id": node_id, "message": f"Electrode surfaces for {node_id} cleaned. Calibration restored to 100%."}

