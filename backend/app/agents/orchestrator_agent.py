"""
Sentinel Drain - Sentinel Orchestrator Agent
Coordinates the incident lifecycle, delegating tasks to specialist agents:
Sensor Intelligence -> Epidemiology -> Supply Chain -> Risk Validation -> Alerting.
Enforces Human-in-the-Loop gates and manages audit logging into BigQuery/SQLite.
"""

import uuid
import time
import json
from typing import Dict, List, Any, Optional

from .base_agent import BaseAgent
from .sensor_intelligence_agent import SensorIntelligenceAgent
from .epidemiology_agent import EpidemiologyAgent
from .supply_chain_agent import SupplyChainAgent
from .risk_validation_agent import RiskValidationAgent
from ..database import get_db_connection

class SentinelOrchestratorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="SentinelOrchestratorAgent",
            role_description="Workflow coordinator managing state transitions, specialist delegation, human approval gates, and multilingual alert generation."
        )
        self.sensor_agent = SensorIntelligenceAgent()
        self.epi_agent = EpidemiologyAgent()
        self.supply_agent = SupplyChainAgent()
        self.risk_agent = RiskValidationAgent()

    def process_incident(
        self,
        primary_reading: Dict[str, Any],
        neighbor_readings: List[Dict[str, Any]],
        stage2_assay: Optional[Dict[str, Any]] = None,
        force_incident_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes full multi-agent decision lifecycle.
        """
        incident_id = force_incident_id or f"INC-{uuid.uuid4().hex[:8].upper()}"
        catchment_id = primary_reading.get("catchment_id", "CAT-RAMPUR")
        phc_id = primary_reading.get("phc_id", "PHC-RAMPUR")
        created_at = time.time()

        conn = get_db_connection()
        cursor = conn.cursor()

        # Retrieve PHC details and network status
        cursor.execute("SELECT * FROM phc_ops WHERE phc_id = ?", (phc_id,))
        target_phc_row = cursor.fetchone()
        target_phc = dict(target_phc_row) if target_phc_row else {
            "phc_id": phc_id, "phc_name": "Rampur PHC", "district": "Gorakhpur",
            "opd_footfall_daily": 85, "stock_ors": 450, "stock_iv_fluids": 80, "lat": 26.7588, "lon": 83.3697
        }

        cursor.execute("SELECT * FROM phc_ops")
        phc_network = [dict(r) for r in cursor.fetchall()]

        # STEP 1: SENSOR INTELLIGENCE VALIDATION
        sensor_res = self.sensor_agent.assess_telemetry(
            incident_id=incident_id,
            primary_reading=primary_reading,
            neighbor_readings=neighbor_readings
        )

        # STEP 2: STAGE 2 BIOASSAY CONFIRMATION
        # If trigger recommended and assay not provided, synthesize assay
        if sensor_res["trigger_stage2"] and not stage2_assay:
            from ..firmware_emulator.simulator_service import fleet_simulator
            node_id = primary_reading.get("node_id", "ND-RAM-01")
            stage2_assay = fleet_simulator.trigger_node_assay(node_id)

        # STEP 3: EPIDEMIOLOGY RISK ASSESSMENT & VERTEX AI FORECAST
        epi_res = self.epi_agent.evaluate_outbreak_risk(
            incident_id=incident_id,
            catchment_id=catchment_id,
            stage1_summary=sensor_res,
            stage2_assay=stage2_assay,
            phc_info=target_phc
        )

        # STEP 4: SUPPLY CHAIN IMPACT & OR-TOOLS DETERMINISTIC OPTIMIZATION
        supply_res = self.supply_agent.evaluate_and_optimize(
            incident_id=incident_id,
            phc_info=target_phc,
            forecast_result=epi_res,
            phc_network=phc_network
        )

        # STEP 5: ADVERSARIAL RISK & VALIDATION AUDIT
        risk_res = self.risk_agent.audit_incident(
            incident_id=incident_id,
            sensor_intel_result=sensor_res,
            epi_result=epi_res,
            supply_result=supply_res
        )

        # STEP 6: MULTILINGUAL ALERT GENERATION
        alerts = self._generate_multilingual_alerts(
            incident_id=incident_id,
            catchment_id=catchment_id,
            phc_info=target_phc,
            epi_res=epi_res,
            supply_res=supply_res,
            risk_res=risk_res
        )

        # STEP 7: DETERMINE FINAL STATUS & PERSIST RECORD
        final_confidence = risk_res["final_confidence"]
        human_approval_required = risk_res["human_approval_required"]

        if risk_res["audit_status"] == "DOWNGRADE_RECOMMENDED":
            incident_status = "DOWNGRADED"
            final_decision = f"Alert held or downgraded due to environmental/sensor audit: {'; '.join(risk_res['concerns'])}"
        elif human_approval_required:
            incident_status = "AWAITING_HUMAN_APPROVAL"
            final_decision = (
                f"Outbreak surge warning verified. Early lead-time: {epi_res['lead_time_days']} days. "
                f"OR-Tools proposed {len(supply_res['transfers'])} stock transfer(s). Awaiting District Health Officer sign-off."
            )
        else:
            incident_status = "MONITORING_ACTIVE"
            final_decision = "Surveillance continuous; risk parameters within manageable capacity."

        # Record Incident in Database
        cursor.execute("""
        INSERT OR REPLACE INTO agent_incidents (
            incident_id, catchment_id, phc_id, created_at, status, confidence,
            current_agent, anomaly_score, pathogen, surge_probability,
            lead_time_days, final_decision, human_approval_required
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            incident_id, catchment_id, phc_id, created_at, incident_status,
            final_confidence, "SentinelOrchestratorAgent", primary_reading.get("anomaly_score", 0.0),
            epi_res.get("pathogen", "None"), epi_res.get("surge_probability", 0.0),
            epi_res.get("lead_time_days", 0.0), final_decision,
            1 if human_approval_required else 0
        ))

        # Record Evidences in Database
        all_evidences = [sensor_res["evidence"], epi_res["evidence"], supply_res["evidence"], risk_res["evidence"]]
        for ev in all_evidences:
            cursor.execute("""
            INSERT INTO agent_evidence (
                incident_id, agent_name, evidence_type, source, summary, data_json, confidence, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ev["incident_id"], ev["agent_name"], ev["evidence_type"], ev["source"],
                ev["summary"], ev["data_json"], ev["confidence"], ev["timestamp"]
            ))

        # Record Actions / Tool Calls in Database
        all_actions = [sensor_res["action"], epi_res["action"], supply_res["action"], risk_res["action"]]
        for ac in all_actions:
            cursor.execute("""
            INSERT INTO agent_actions (
                incident_id, agent_name, action_type, tool_called, input_params, output_result, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ac["incident_id"], ac["agent_name"], ac["action_type"], ac["tool_called"],
                ac["input_params"], ac["output_result"], ac["timestamp"]
            ))

        # Record Redistribution Plans (calculated deterministically by OR-Tools)
        plan_ids = []
        for t in supply_res.get("transfers", []):
            plan_id = f"PLAN-{uuid.uuid4().hex[:8].upper()}"
            plan_ids.append(plan_id)
            cursor.execute("""
            INSERT INTO redistribution_plans (
                plan_id, incident_id, source_phc, destination_phc, sku, quantity,
                transit_distance_km, est_transit_hours, optimization_run_id,
                approval_status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                plan_id, incident_id, t["source_phc_id"], t["destination_phc_id"],
                t["sku"], t["quantity"], t["distance_km"], t["est_transit_hours"],
                supply_res.get("optimization_runs", [{}])[0].get("run_id", "OPT-DEFAULT"),
                "PENDING_APPROVAL",
                f"Transfer from {t['source_phc_name']} to {t['destination_phc_name']}"
            ))

        # Record Alert in Database
        alert_id = f"ALT-{uuid.uuid4().hex[:8].upper()}"
        cursor.execute("""
        INSERT INTO alerts (
            alert_id, incident_id, catchment_id, phc_id, timestamp, severity,
            title, message_en, message_hi, message_kn, message_ta, action_recommended, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert_id, incident_id, catchment_id, phc_id, time.time(),
            "HIGH" if human_approval_required else "MEDIUM",
            alerts["title"], alerts["en"], alerts["hi"], alerts["kn"], alerts["ta"],
            alerts["action_recommended"], "DISPATCHED"
        ))

        conn.commit()
        conn.close()

        return {
            "incident_id": incident_id,
            "status": incident_status,
            "confidence": final_confidence,
            "human_approval_required": human_approval_required,
            "final_decision": final_decision,
            "catchment_id": catchment_id,
            "phc_id": phc_id,
            "phc_name": target_phc["phc_name"],
            "sensor_validation": sensor_res,
            "stage2_assay": stage2_assay,
            "epidemiology": epi_res,
            "supply_chain": supply_res,
            "risk_audit": risk_res,
            "alerts": alerts,
            "plan_ids": plan_ids
        }

    def _generate_multilingual_alerts(
        self,
        incident_id: str,
        catchment_id: str,
        phc_info: Dict[str, Any],
        epi_res: Dict[str, Any],
        supply_res: Dict[str, Any],
        risk_res: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generates plain-language actionable alerts in English, Hindi, Kannada, and Tamil."""
        pathogen = epi_res.get("pathogen", "Enteric Pathogen")
        prob = int(round(epi_res.get("surge_probability", 0.8) * 100))
        lead_days = epi_res.get("lead_time_days", 4.5)
        phc_name = phc_info.get("phc_name", "Local PHC")

        title = f"EARLY WARNING: {prob}% Outbreak Surge Probability in {catchment_id}"
        action = f"Pre-position {supply_res.get('deficit_ors', 1500)} ORS sachets and {supply_res.get('deficit_iv', 200)} IV fluid units before Day {int(round(lead_days))}."

        # English
        msg_en = (
            f"URGENT HEALTH ADVISORY: Sentinel Drain node network detected pre-symptomatic {pathogen} "
            f"shedding in {catchment_id} ({phc_name}). Vertex AI forecasts {prob}% probability of acute OPD footfall surge "
            f"in {lead_days} days. Current stockout anticipated within {supply_res.get('days_to_ors_stockout', 2)} days. "
            f"Deterministic stock redistribution has been calculated from neighboring PHCs. Please verify and pre-position supplies."
        )

        # Hindi (हिन्दी)
        msg_hi = (
            f"तत्काल स्वास्थ्य चेतावनी: सेंटिनल ड्रेन नेटवर्क ने {catchment_id} ({phc_name}) के सीवेज/नाली में {pathogen} "
            f"के प्रारंभिक रोगाणु लोड की पहचान की है। वर्टेक्स एआई मॉडल {lead_days} दिनों में ओपीडी में {prob}% उछाल "
            f"की संभावना व्यक्त करता है। ओआरएस और आईवी फ्लूइड की संभावित कमी को रोकने हेतु पड़ोसी केंद्रों से पुनर्वितरण प्रस्ताव तैयार है। "
            f"कृपया तुरंत आवश्यक जीवनरक्षक दवाइयों का पूर्व-भंडारण करें।"
        )

        # Kannada (ಕನ್ನಡ)
        msg_kn = (
            f"ತುರ್ತು ಆರೋಗ್ಯ ಎಚ್ಚರಿಕೆ: ಸೆಂbpಟಿನೆಲ್ ಡ್ರೈನ್ ನೆಟ್‌ವರ್ಕ್ {catchment_id} ({phc_name}) ಒಳಚರಂಡಿಯಲ್ಲಿ {pathogen} "
            f"ರೋಗಾಣುಗಳನ್ನು ಪತ್ತೆಹಚ್ಚಿದೆ. ಮುಂದಿನ {lead_days} ದಿನಗಳಲ್ಲಿ ಒಪಿಡಿ ರೋಗಿಗಳ ಸಂಖ್ಯೆಯಲ್ಲಿ ಶೇ.{prob} ಹೆಚ್ಚಳವಾಗುವ ಸಾಧ್ಯತೆಯಿದೆ. "
            f"ಔಷಧಿ ಕೊರತೆ ತಡೆಯಲು ಹತ್ತಿರದ ಪಿಎಚ್‌ಸಿಗಳಿಂದ ದಾಸ್ತಾನು ಮರುಹಂಚಿಕೆ ಪ್ರಸ್ತಾಪಿಸಲಾಗಿದೆ. ದಯವಿಟ್ಟು ಪೂರ್ವಸಿದ್ಧತೆ ಮಾಡಿಕೊಳ್ಳಿ."
        )

        # Tamil (தமிழ்)
        msg_ta = (
            f"அவசர சுகாதார எச்சரிக்கை: சென்டினல் வடிகால் நெட்வொர்க் {catchment_id} ({phc_name}) கழிவுநீரில் {pathogen} "
            f"கிருமிகளின் இருப்பைக் கண்டறிந்துள்ளது. அடுத்த {lead_days} நாட்களில் வெளிநோயாளி வருகை {prob}% அதிகரிக்க வாய்ப்புள்ளது. "
            f"மருந்துப் பற்றாக்குறையைத் தவிர்க்க அருகிலுள்ள ஆரம்ப சுகாதார நிலையங்களிலிருந்து மருந்துகளை மறுபங்கீடு செய்யப் பரிந்துரைக்கப்பட்டுள்ளது."
        )

        return {
            "title": title,
            "action_recommended": action,
            "en": msg_en,
            "hi": msg_hi,
            "kn": msg_kn,
            "ta": msg_ta
        }

# Global orchestrator singleton
sentinel_orchestrator = SentinelOrchestratorAgent()
