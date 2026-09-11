"""
Sentinel Drain - Epidemiology Specialist Agent
Specialist Agent synthesizing Stage-2 LAMP bioassay readouts, Vertex AI surge forecasts,
historical OPD footfall, and seasonal epidemiological priors into a clinical outbreak assessment.
"""

from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent
from ..forecasting.vertex_predictor import vertex_forecaster

class EpidemiologyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="EpidemiologyAgent",
            role_description="Combines Stage-2 LAMP assay, Vertex AI forecasting, and OPD baselines into an explainable outbreak-risk assessment."
        )

    def evaluate_outbreak_risk(
        self,
        incident_id: str,
        catchment_id: str,
        stage1_summary: Dict[str, Any],
        stage2_assay: Optional[Dict[str, Any]],
        phc_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executes epidemiological risk synthesis.
        """
        opd_baseline = phc_info.get("opd_footfall_daily", 85)
        phc_name = phc_info.get("phc_name", "Local PHC")

        # 1. Extract Stage-1 Telemetry Data
        stage1_data = stage1_summary
        if isinstance(stage1_summary, dict) and "evidence" in stage1_summary:
            ev_data = stage1_summary["evidence"].get("data_json")
            if isinstance(ev_data, str):
                import json
                try:
                    stage1_data = json.loads(ev_data)
                except Exception:
                    stage1_data = {}
            elif isinstance(ev_data, dict):
                stage1_data = ev_data

        # Invoke Vertex AI Forecasting Model Tool
        forecast = vertex_forecaster.predict(
            catchment_id=catchment_id,
            stage1_data=stage1_data,
            stage2_data=stage2_assay,
            opd_baseline=opd_baseline,
            rainfall_mm=0.0,
            seasonal_index=0.76  # Post-monsoon enteric pathogen season
        )

        surge_prob = forecast["surge_probability"]
        lead_time = forecast["lead_time_days"]
        multiplier = forecast["predicted_footfall_multiplier"]
        predicted_opd = forecast["predicted_opd_footfall"]

        # 2. Pathogen and Clinical Severity Analysis
        if stage2_assay and stage2_assay.get("result") == "POSITIVE":
            pathogen = stage2_assay.get("target_pathogen", "Vibrio cholerae O1")
            assay_conf = stage2_assay.get("confidence", 0.95)
            is_confirmed_bioassay = True
        else:
            pathogen = "Unconfirmed Enteric Pathogen"
            assay_conf = 0.50
            is_confirmed_bioassay = False

        if "cholerae" in pathogen.lower():
            clinical_risk = "HIGH_ACUTE_DEHYDRATION"
            presentation = "Profuse watery diarrhea, severe electrolyte loss, rapid hypovolemic shock if untreated."
            required_countermeasures = ["ORS pre-positioning", "IV Ringer's Lactate buffer", "Zinc supplementation", "Chlorination drive"]
        elif "rotavirus" in pathogen.lower():
            clinical_risk = "PEDIATRIC_GASTROENTERITIS"
            presentation = "Severe acute watery diarrhea in infants and under-5 children, high vomiting frequency."
            required_countermeasures = ["Pediatric ORS", "Zinc dispersible tablets", "IV fluid pediatric lines"]
        else:
            clinical_risk = "MODERATE_ENTERIC_SYNDROME"
            presentation = "Acute diarrheal illness cluster."
            required_countermeasures = ["Oral Rehydration Salts", "Broad-spectrum oral antimicrobials"]

        # 3. Overall Risk Tier
        if surge_prob >= 0.70 and is_confirmed_bioassay:
            risk_tier = "CRITICAL_EARLY_WARNING"
            lead_window = f"{lead_time} days before clinical OPD surge"
        elif surge_prob >= 0.40:
            risk_tier = "ELEVATED_WATCH"
            lead_window = f"{lead_time} days early warning"
        else:
            risk_tier = "LOW_RISK"
            lead_window = "No immediate surge expected"

        summary_text = (
            f"{risk_tier}: {round(surge_prob * 100, 1)}% probability of localized {pathogen} outbreak surge "
            f"in {catchment_id} ({phc_name}). Estimated lead time: {lead_time} days ahead of clinical presentation. "
            f"OPD footfall projected to surge from normal {opd_baseline}/day to {predicted_opd}/day ({multiplier:.1f}x)."
        )

        evidence = self.create_evidence(
            incident_id=incident_id,
            evidence_type="EPIDEMIOLOGICAL_SURGE_FORECAST",
            source="VertexAI/EpidemiologyEngine",
            summary=summary_text,
            data={
                "pathogen": pathogen,
                "surge_probability": surge_prob,
                "lead_time_days": lead_time,
                "predicted_footfall_multiplier": multiplier,
                "opd_baseline": opd_baseline,
                "predicted_opd": predicted_opd,
                "clinical_risk": clinical_risk,
                "primary_drivers": forecast["primary_drivers"]
            },
            confidence=round(0.85 * assay_conf + 0.15 * forecast["confidence"], 2)
        )

        action = self.log_action(
            incident_id=incident_id,
            action_type="VERTEX_AI_PREDICTION",
            tool_called="VertexAI.predict_catchment_surge",
            input_params={"catchment_id": catchment_id, "opd_baseline": opd_baseline},
            output_result={"surge_prob": surge_prob, "lead_time": lead_time, "predicted_opd": predicted_opd}
        )

        return {
            "risk_tier": risk_tier,
            "pathogen": pathogen,
            "surge_probability": surge_prob,
            "lead_time_days": lead_time,
            "predicted_footfall_multiplier": multiplier,
            "opd_baseline": opd_baseline,
            "predicted_opd_footfall": predicted_opd,
            "clinical_presentation": presentation,
            "countermeasures": required_countermeasures,
            "forecast_drivers": forecast["primary_drivers"],
            "summary_text": summary_text,
            "evidence": evidence,
            "action": action
        }
