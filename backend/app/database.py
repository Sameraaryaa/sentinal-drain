"""
Sentinel Drain - Data Store & BigQuery Emulation Layer
Stores all operational telemetry, model forecasts, agent reasoning traces,
and redistribution optimization plans.
"""

import sqlite3
import json
import os
from typing import Dict, List, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sentinel_drain.db")

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initializes BigQuery-compatible relational tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Nodes table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS nodes (
        node_id TEXT PRIMARY KEY,
        catchment_id TEXT NOT NULL,
        phc_id TEXT NOT NULL,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        install_date TEXT NOT NULL,
        status TEXT NOT NULL,
        battery_pct INTEGER DEFAULT 100,
        reagents_remaining INTEGER DEFAULT 30,
        last_seen REAL
    )
    """)

    # 2. Stage-1 Telemetry Readings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS readings_stage1 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        node_id TEXT NOT NULL,
        catchment_id TEXT NOT NULL,
        timestamp REAL NOT NULL,
        ph REAL NOT NULL,
        conductivity REAL NOT NULL,
        orp REAL NOT NULL,
        turbidity REAL NOT NULL,
        temperature REAL NOT NULL,
        anomaly_score REAL NOT NULL,
        is_dilution_event INTEGER DEFAULT 0,
        probe_fouling INTEGER DEFAULT 0,
        FOREIGN KEY (node_id) REFERENCES nodes (node_id)
    )
    """)

    # 3. Stage-2 LAMP Bioassay Readings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS readings_stage2 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        node_id TEXT NOT NULL,
        catchment_id TEXT NOT NULL,
        timestamp REAL NOT NULL,
        target_pathogen TEXT NOT NULL,
        assay_temperature_c REAL NOT NULL,
        optical_absorbance_ratio REAL NOT NULL,
        result TEXT NOT NULL,
        confidence REAL NOT NULL,
        FOREIGN KEY (node_id) REFERENCES nodes (node_id)
    )
    """)

    # 4. PHC Operational & Inventory Status
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS phc_ops (
        phc_id TEXT PRIMARY KEY,
        phc_name TEXT NOT NULL,
        district TEXT NOT NULL,
        catchment_id TEXT NOT NULL,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        opd_footfall_daily INTEGER NOT NULL,
        normal_capacity INTEGER NOT NULL,
        stock_ors INTEGER NOT NULL,
        stock_iv_fluids INTEGER NOT NULL,
        stock_antibiotics INTEGER NOT NULL,
        stock_zinc INTEGER NOT NULL,
        stock_rdt_kits INTEGER NOT NULL,
        last_updated REAL NOT NULL
    )
    """)

    # 5. Vertex AI Predictions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS forecasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        catchment_id TEXT NOT NULL,
        phc_id TEXT NOT NULL,
        timestamp REAL NOT NULL,
        surge_probability REAL NOT NULL,
        lead_time_days REAL NOT NULL,
        predicted_footfall_multiplier REAL NOT NULL,
        confidence REAL NOT NULL,
        model_version TEXT NOT NULL,
        primary_drivers TEXT
    )
    """)

    # 6. Multilingual Alerts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        alert_id TEXT PRIMARY KEY,
        incident_id TEXT,
        catchment_id TEXT NOT NULL,
        phc_id TEXT NOT NULL,
        timestamp REAL NOT NULL,
        severity TEXT NOT NULL,
        title TEXT NOT NULL,
        message_en TEXT NOT NULL,
        message_hi TEXT NOT NULL,
        message_kn TEXT NOT NULL,
        message_ta TEXT NOT NULL,
        action_recommended TEXT NOT NULL,
        status TEXT DEFAULT 'DISPATCHED'
    )
    """)

    # 7. Agent Incidents (Multi-Agent State Machine)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_incidents (
        incident_id TEXT PRIMARY KEY,
        catchment_id TEXT NOT NULL,
        phc_id TEXT NOT NULL,
        created_at REAL NOT NULL,
        status TEXT NOT NULL,
        confidence REAL NOT NULL,
        current_agent TEXT NOT NULL,
        anomaly_score REAL NOT NULL,
        pathogen TEXT,
        surge_probability REAL,
        lead_time_days REAL,
        final_decision TEXT,
        human_approval_required INTEGER DEFAULT 0
    )
    """)

    # 8. Agent Evidence Ledger (Audit Trail)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_evidence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT NOT NULL,
        agent_name TEXT NOT NULL,
        evidence_type TEXT NOT NULL,
        source TEXT NOT NULL,
        summary TEXT NOT NULL,
        data_json TEXT,
        confidence REAL NOT NULL,
        timestamp REAL NOT NULL,
        FOREIGN KEY (incident_id) REFERENCES agent_incidents (incident_id)
    )
    """)

    # 9. Agent Action / Tool Execution Log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT NOT NULL,
        agent_name TEXT NOT NULL,
        action_type TEXT NOT NULL,
        tool_called TEXT NOT NULL,
        input_params TEXT,
        output_result TEXT,
        timestamp REAL NOT NULL,
        FOREIGN KEY (incident_id) REFERENCES agent_incidents (incident_id)
    )
    """)

    # 10. Redistribution Plans (Calculated by OR-Tools)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS redistribution_plans (
        plan_id TEXT PRIMARY KEY,
        incident_id TEXT NOT NULL,
        source_phc TEXT NOT NULL,
        destination_phc TEXT NOT NULL,
        sku TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        transit_distance_km REAL NOT NULL,
        est_transit_hours REAL NOT NULL,
        optimization_run_id TEXT NOT NULL,
        approval_status TEXT NOT NULL,
        approved_by TEXT,
        approved_at REAL,
        notes TEXT,
        FOREIGN KEY (incident_id) REFERENCES agent_incidents (incident_id)
    )
    """)

    # 11. Human Approvals
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS human_approvals (
        approval_id TEXT PRIMARY KEY,
        plan_id TEXT NOT NULL,
        incident_id TEXT NOT NULL,
        officer_name TEXT NOT NULL,
        officer_role TEXT NOT NULL,
        action TEXT NOT NULL,
        comments TEXT,
        timestamp REAL NOT NULL
    )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_database()
    print("Database schema successfully initialized at:", DB_PATH)
