"""
Sentinel Drain - Seed Data Generator
Populates initial pilot district nodes, PHC inventory baselines,
and initial sensor readings for Gorakhpur Health District.
"""

import time
import random
from .database import get_db_connection, init_database

def seed_all_data():
    init_database()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing seed data if any
    cursor.execute("DELETE FROM nodes")
    cursor.execute("DELETE FROM phc_ops")
    cursor.execute("DELETE FROM readings_stage1")
    cursor.execute("DELETE FROM readings_stage2")
    cursor.execute("DELETE FROM forecasts")
    cursor.execute("DELETE FROM alerts")
    cursor.execute("DELETE FROM agent_incidents")
    cursor.execute("DELETE FROM agent_evidence")
    cursor.execute("DELETE FROM agent_actions")
    cursor.execute("DELETE FROM redistribution_plans")
    cursor.execute("DELETE FROM human_approvals")

    # 1. Seed 5 PHCs in Gorakhpur District
    phcs = [
        {
            "phc_id": "PHC-RAMPUR",
            "phc_name": "Rampur Primary Health Centre",
            "district": "Gorakhpur",
            "catchment_id": "CAT-RAMPUR",
            "lat": 26.7588,
            "lon": 83.3697,
            "opd_footfall_daily": 85,
            "normal_capacity": 120,
            "stock_ors": 450,           # Vulnerable deficit in outbreak
            "stock_iv_fluids": 80,       # Very low reserve
            "stock_antibiotics": 210,
            "stock_zinc": 600,
            "stock_rdt_kits": 40
        },
        {
            "phc_id": "PHC-SITAPUR",
            "phc_name": "Sitapur Community Health Centre",
            "district": "Gorakhpur",
            "catchment_id": "CAT-SITAPUR",
            "lat": 26.7820,
            "lon": 83.4100,
            "opd_footfall_daily": 65,
            "normal_capacity": 100,
            "stock_ors": 1800,
            "stock_iv_fluids": 320,
            "stock_antibiotics": 450,
            "stock_zinc": 1400,
            "stock_rdt_kits": 120
        },
        {
            "phc_id": "PHC-BILASPUR",
            "phc_name": "Bilaspur Block Hospital & Hub PHC",
            "district": "Gorakhpur",
            "catchment_id": "CAT-BILASPUR",
            "lat": 26.7350,
            "lon": 83.3320,
            "opd_footfall_daily": 110,
            "normal_capacity": 200,
            "stock_ors": 5200,          # Substantial surplus available for redistribution
            "stock_iv_fluids": 980,      # High surplus
            "stock_antibiotics": 1200,
            "stock_zinc": 3500,
            "stock_rdt_kits": 400
        },
        {
            "phc_id": "PHC-MAHARAJ",
            "phc_name": "Maharajganj Border PHC",
            "district": "Gorakhpur",
            "catchment_id": "CAT-MAHARAJ",
            "lat": 26.8150,
            "lon": 83.3900,
            "opd_footfall_daily": 55,
            "normal_capacity": 90,
            "stock_ors": 1400,
            "stock_iv_fluids": 260,
            "stock_antibiotics": 350,
            "stock_zinc": 1100,
            "stock_rdt_kits": 95
        },
        {
            "phc_id": "PHC-CHAURI",
            "phc_name": "Chauri Chaura Sub-District PHC",
            "district": "Gorakhpur",
            "catchment_id": "CAT-CHAURI",
            "lat": 26.6850,
            "lon": 83.5850,
            "opd_footfall_daily": 95,
            "normal_capacity": 150,
            "stock_ors": 3100,          # Healthy reserve
            "stock_iv_fluids": 540,
            "stock_antibiotics": 680,
            "stock_zinc": 2200,
            "stock_rdt_kits": 250
        }
    ]

    now = time.time()
    for p in phcs:
        cursor.execute("""
        INSERT INTO phc_ops (
            phc_id, phc_name, district, catchment_id, lat, lon,
            opd_footfall_daily, normal_capacity, stock_ors, stock_iv_fluids,
            stock_antibiotics, stock_zinc, stock_rdt_kits, last_updated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["phc_id"], p["phc_name"], p["district"], p["catchment_id"],
            p["lat"], p["lon"], p["opd_footfall_daily"], p["normal_capacity"],
            p["stock_ors"], p["stock_iv_fluids"], p["stock_antibiotics"],
            p["stock_zinc"], p["stock_rdt_kits"], now
        ))

    # 2. Seed 11 Drain Biosurveillance Nodes
    nodes = [
        # Catchment Rampur (3 nodes)
        ("ND-RAM-01", "CAT-RAMPUR", "PHC-RAMPUR", 26.7588, 83.3697, "2026-01-15", "ONLINE", 96, 26),
        ("ND-RAM-02", "CAT-RAMPUR", "PHC-RAMPUR", 26.7610, 83.3750, "2026-01-15", "ONLINE", 92, 28),
        ("ND-RAM-03", "CAT-RAMPUR", "PHC-RAMPUR", 26.7545, 83.3640, "2026-01-16", "ONLINE", 94, 25),

        # Catchment Sitapur (2 nodes)
        ("ND-SIT-01", "CAT-SITAPUR", "PHC-SITAPUR", 26.7820, 83.4100, "2026-02-01", "ONLINE", 89, 29),
        ("ND-SIT-02", "CAT-SITAPUR", "PHC-SITAPUR", 26.7865, 83.4150, "2026-02-01", "ONLINE", 97, 30),

        # Catchment Bilaspur (2 nodes)
        ("ND-BIL-01", "CAT-BILASPUR", "PHC-BILASPUR", 26.7350, 83.3320, "2026-01-20", "ONLINE", 99, 30),
        ("ND-BIL-02", "CAT-BILASPUR", "PHC-BILASPUR", 26.7390, 83.3380, "2026-01-20", "ONLINE", 95, 27),

        # Catchment Maharajganj (2 nodes)
        ("ND-MAH-01", "CAT-MAHARAJ", "PHC-MAHARAJ", 26.8150, 83.3900, "2026-02-10", "ONLINE", 91, 24),
        ("ND-MAH-02", "CAT-MAHARAJ", "PHC-MAHARAJ", 26.8190, 83.3950, "2026-02-10", "ONLINE", 88, 23),

        # Catchment Chauri Chaura (2 nodes)
        ("ND-CHA-01", "CAT-CHAURI", "PHC-CHAURI", 26.6850, 83.5850, "2026-02-15", "ONLINE", 93, 28),
        ("ND-CHA-02", "CAT-CHAURI", "PHC-CHAURI", 26.6890, 83.5910, "2026-02-15", "ONLINE", 98, 29),
    ]

    for n in nodes:
        cursor.execute("""
        INSERT INTO nodes (
            node_id, catchment_id, phc_id, lat, lon, install_date,
            status, battery_pct, reagents_remaining, last_seen
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (n[0], n[1], n[2], n[3], n[4], n[5], n[6], n[7], n[8], now))

    # 3. Seed historical Stage-1 telemetry (last 24 hours of normal baselines)
    for n in nodes:
        node_id, catchment_id = n[0], n[1]
        for step in range(24):
            t_sample = now - (24 - step) * 3600
            ph = 7.18 + random.uniform(-0.12, 0.12)
            cond = 835.0 + random.uniform(-25.0, 25.0)
            orp = 182.0 + random.uniform(-10.0, 10.0)
            turb = 44.0 + random.uniform(-5.0, 5.0)
            temp = 28.2 + random.uniform(-0.6, 0.6)
            score = round(random.uniform(0.15, 0.75), 2)

            cursor.execute("""
            INSERT INTO readings_stage1 (
                node_id, catchment_id, timestamp, ph, conductivity, orp,
                turbidity, temperature, anomaly_score, is_dilution_event, probe_fouling
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
            """, (node_id, catchment_id, t_sample, ph, cond, orp, turb, temp, score))

    conn.commit()
    conn.close()
    print("Database successfully seeded with 5 PHCs, 11 Nodes, and 24-hr historical telemetry.")

if __name__ == "__main__":
    seed_all_data()
