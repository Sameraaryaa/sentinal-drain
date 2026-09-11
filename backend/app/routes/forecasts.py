"""
Sentinel Drain - Vertex AI Forecasting API Routes
Provides surge probabilities, 3-7 day lead time estimates, and feature attribution.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any

from ..database import get_db_connection
from ..forecasting.vertex_predictor import vertex_forecaster

router = APIRouter(prefix="/api/forecasts", tags=["forecasts"])

@router.get("/catchment/{catchment_id}")
def get_catchment_forecast(catchment_id: str):
    """Computes or retrieves calibrated Vertex AI outbreak surge forecast for a catchment."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get PHC info
    cursor.execute("SELECT * FROM phc_ops WHERE catchment_id = ?", (catchment_id,))
    phc_row = cursor.fetchone()
    if not phc_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Catchment {catchment_id} not found.")

    phc = dict(phc_row)

    # Get latest Stage-1 reading
    cursor.execute("""
    SELECT * FROM readings_stage1
    WHERE catchment_id = ?
    ORDER BY timestamp DESC
    LIMIT 1
    """, (catchment_id,))
    s1_row = cursor.fetchone()
    stage1_data = dict(s1_row) if s1_row else {"anomaly_score": 0.4, "conductivity": 840.0, "orp": 185.0}

    # Get latest Stage-2 assay
    cursor.execute("""
    SELECT * FROM readings_stage2
    WHERE catchment_id = ?
    ORDER BY timestamp DESC
    LIMIT 1
    """, (catchment_id,))
    s2_row = cursor.fetchone()
    stage2_data = dict(s2_row) if s2_row else None

    conn.close()

    forecast = vertex_forecaster.predict(
        catchment_id=catchment_id,
        stage1_data=stage1_data,
        stage2_data=stage2_data,
        opd_baseline=phc.get("opd_footfall_daily", 85),
        rainfall_mm=0.0,
        seasonal_index=0.74
    )

    return {
        "phc_id": phc["phc_id"],
        "phc_name": phc["phc_name"],
        "district": phc["district"],
        **forecast
    }

@router.get("/all")
def get_all_catchment_forecasts():
    """Returns outbreak surge forecast for all 5 catchments in the pilot district."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT catchment_id FROM phc_ops")
    catchment_rows = cursor.fetchall()
    conn.close()

    results = []
    for row in catchment_rows:
        cid = row["catchment_id"]
        results.append(get_catchment_forecast(cid))

    return results
