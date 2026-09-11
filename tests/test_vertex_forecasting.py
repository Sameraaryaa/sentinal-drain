"""
Unit Tests for Vertex AI Outbreak Forecasting Model
Verifies PRD requirements:
- FR-11: Surge probability with calibrated lead-time window (3-7 days)
- Multi-modal prediction combining sensor signal + OPD baseline + seasonal prior
- Feature importance SHAP explainability
"""

import pytest
from backend.app.forecasting.vertex_predictor import VertexAIForecaster

def test_vertex_forecaster_training_and_calibration():
    forecaster = VertexAIForecaster()
    assert forecaster.classifier is not None
    assert forecaster.lead_time_regressor is not None

def test_outbreak_prediction_with_positive_assay():
    forecaster = VertexAIForecaster()

    stage1_anomaly = {"anomaly_score": 4.5, "conductivity": 1320.0, "orp": 45.0}
    stage2_positive = {"result": "POSITIVE", "optical_absorbance_ratio": 2.45}

    result = forecaster.predict(
        catchment_id="CAT-RAMPUR",
        stage1_data=stage1_anomaly,
        stage2_data=stage2_positive,
        opd_baseline=85,
        seasonal_index=0.82
    )

    # Surge probability should be high
    assert result["surge_probability"] >= 0.70
    # PRD Target: 3-7 days lead time
    assert 3.0 <= result["lead_time_days"] <= 7.0
    # OPD multiplier should show surge
    assert result["predicted_footfall_multiplier"] > 1.5
    assert result["predicted_opd_footfall"] > 85
    # Primary drivers should explain prediction
    assert len(result["primary_drivers"]) >= 3
    # Top driver should be assay or ORP shift
    top_feature = result["primary_drivers"][0]["feature"]
    assert "Assay" in top_feature or "ORP" in top_feature

def test_baseline_prediction_no_surge():
    forecaster = VertexAIForecaster()

    stage1_normal = {"anomaly_score": 0.35, "conductivity": 840.0, "orp": 185.0}
    stage2_negative = {"result": "NEGATIVE", "optical_absorbance_ratio": 0.45}

    result = forecaster.predict(
        catchment_id="CAT-BILASPUR",
        stage1_data=stage1_normal,
        stage2_data=stage2_negative,
        opd_baseline=110,
        seasonal_index=0.25
    )

    assert result["surge_probability"] < 0.35
    assert result["lead_time_days"] == 0.0
    assert result["predicted_footfall_multiplier"] == 1.0
