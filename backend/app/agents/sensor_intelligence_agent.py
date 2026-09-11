"""
Sentinel Drain - Sensor Intelligence Agent
Specialist Agent responsible for validating Stage-1 physicochemical telemetry,
cross-checking neighboring drain nodes, evaluating dilution vs biological loading,
and assessing node hardware health.
"""

from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent

class SensorIntelligenceAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="SensorIntelligenceAgent",
            role_description="Validates Stage-1 physicochemical anomalies, checks neighbor nodes, detects dilution/fouling, and decides Stage-2 assay trigger."
        )

    def assess_telemetry(
        self,
        incident_id: str,
        primary_reading: Dict[str, Any],
        neighbor_readings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validates Stage-1 anomaly and creates auditable evidence.
        """
        node_id = primary_reading.get("node_id", "UNKNOWN")
        catchment_id = primary_reading.get("catchment_id", "UNKNOWN")
        anomaly_score = primary_reading.get("anomaly_score", 0.0)
        ph = primary_reading.get("ph", 7.2)
        cond = primary_reading.get("conductivity", 800.0)
        orp = primary_reading.get("orp", 180.0)
        turb = primary_reading.get("turbidity", 40.0)
        is_dilution = primary_reading.get("is_dilution_event", False)
        probe_fouling = primary_reading.get("probe_fouling", False)

        # 1. Neighbor consistency check
        neighbor_anomalies = [r.get("anomaly_score", 0.0) for r in neighbor_readings if r.get("node_id") != node_id]
        neighbor_agreement = False
        if neighbor_anomalies:
            avg_neighbor_score = sum(neighbor_anomalies) / len(neighbor_anomalies)
            neighbor_agreement = (avg_neighbor_score >= 1.8)
        else:
            avg_neighbor_score = 0.0

        # 2. Decision Logic
        if probe_fouling:
            verdict = "HARDWARE_MAINTENANCE_REQUIRED"
            recommendation = "SUSPEND_ALERTS"
            trigger_stage2 = False
            confidence = 0.94
            explanation = (
                f"Node {node_id} exhibits physical electrode fouling or out-of-range sensor drift "
                f"(pH={ph}, ORP={orp} mV). Telemetry anomaly is an instrument artifact, not a biosignal. "
                "Dispatched maintenance ticket; Stage-2 assay suspended to conserve reagents."
            )
        elif is_dilution:
            verdict = "STORMWATER_DILUTION_DETECTED"
            recommendation = "DOWNGRADE_CONFIDENCE"
            trigger_stage2 = False
            confidence = 0.91
            explanation = (
                f"Catchment {catchment_id} exhibits high turbidity ({turb} NTU) but severe conductivity depression "
                f"({cond} uS/cm), characteristic of monsoon stormwater runoff. Pathogen load signal is masked/diluted. "
                "Flagged as weather artifact; suppressed false alarm per PRD FR-9."
            )
        elif anomaly_score >= 2.2:
            verdict = "VALIDATED_BIOLOGICAL_ANOMALY"
            recommendation = "TRIGGER_STAGE2_ASSAY"
            trigger_stage2 = True
            confidence = 0.89 if neighbor_agreement else 0.78
            explanation = (
                f"Node {node_id} reports a statistically significant Stage-1 anomaly (Z-score: {anomaly_score:.2f}). "
                f"Marked by reducing ORP ({orp:.1f} mV) and elevated conductivity ({cond:.1f} uS/cm), consistent with "
                f"pre-symptomatic pathogen shedding in community wastewater. "
                f"{'Confirmed by neighbor nodes in catchment.' if neighbor_agreement else 'Localized to single drain sector; neighbor confirmation pending.'} "
                "Recommended immediate isothermal LAMP Stage-2 assay."
            )
        else:
            verdict = "NORMAL_BASELINE"
            recommendation = "CONTINUE_MONITORING"
            trigger_stage2 = False
            confidence = 0.95
            explanation = f"Sensor parameters for Node {node_id} conform to historical baseline control charts."

        evidence = self.create_evidence(
            incident_id=incident_id,
            evidence_type="STAGE1_PHYSICOCHEMICAL_VALIDATION",
            source=f"EdgeDrainNode/{node_id}",
            summary=verdict,
            data={
                "anomaly_score": anomaly_score,
                "ph": ph,
                "conductivity": cond,
                "orp": orp,
                "turbidity": turb,
                "is_dilution": is_dilution,
                "probe_fouling": probe_fouling,
                "neighbor_agreement": neighbor_agreement,
                "avg_neighbor_score": round(avg_neighbor_score, 2)
            },
            confidence=confidence
        )

        action = self.log_action(
            incident_id=incident_id,
            action_type="TELEMETRY_EVALUATION",
            tool_called="SensorIntelligence.evaluate_physicochemical",
            input_params={"primary_reading": primary_reading, "neighbor_count": len(neighbor_readings)},
            output_result={"verdict": verdict, "trigger_stage2": trigger_stage2, "confidence": confidence}
        )

        return {
            "verdict": verdict,
            "recommendation": recommendation,
            "trigger_stage2": trigger_stage2,
            "confidence": confidence,
            "explanation": explanation,
            "evidence": evidence,
            "action": action
        }
