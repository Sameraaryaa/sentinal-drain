# Product Requirements Document: Sentinel Drain
**Hyperlocal Wastewater Biosurveillance Network for PHC-Level Outbreak Early-Warning**

Version 1.1 — 2026-09-10
Author: Manush Prajwal (with Claude Code)
Status: Hackathon Concept — Build with AI: Code for Communities (Google Cloud)
Track: Smart Health and Supply Chain Resilience

---

## 1. Executive Summary

Sentinel Drain is a distributed hardware sensor network that detects disease outbreaks 3-7 days before they present clinically at Primary Health Centres (PHCs), by monitoring community wastewater for pathogen signatures at PHC-catchment resolution. The signal feeds a Vertex AI forecasting model that predicts localized OPD (out-patient department) surge probability. A Google ADK-based multi-agent layer, powered primarily by Gemini, then validates the evidence, coordinates outbreak reasoning, evaluates supply impact, and produces explainable redistribution recommendations for state health departments.

The core thesis: **existing wastewater-based epidemiology (WBE) operates at sewage-treatment-plant/city scale — too coarse and too slow to inform which specific PHC needs medicine redistributed this week.** Sentinel Drain pushes the same underlying science down to the ~20-30k population catchment level with field-deployable turnaround, filling a resolution gap that currently has no product occupying it in India.

Hardware is not a UX layer bolted onto a software product — it is the product. No app, satellite feed, or citizen-report system can produce a pathogen-load signal from community wastewater. Only a physical sensor in the drain can.

---

## 2. Problem Statement

### 2.1 The stated hackathon brief
Public healthcare systems across India face persistent supply chain vulnerabilities. Medicine stock-outs, unpredictable patient footfall, and poor resource-utilisation visibility across PHC networks limit the system's ability to respond when it matters most.

### 2.2 The deeper problem (root cause, not symptom)
Most "PHC supply chain" solutions treat this as an inventory-visibility problem — track what's on the shelf in real time. That solves the wrong half of the problem. A PHC can have perfect real-time visibility into its current stock and still run out, because the actual failure mode is **unanticipated demand shock**: a localized outbreak spikes OPD footfall and depletes stock faster than any restocking cycle can react, because the *first available signal* of the outbreak is the outbreak itself (people getting sick and showing up).

By the time footfall data shows a spike, it is already too late to have pre-positioned stock. The system needs a **leading indicator**, not better tracking of a lagging one.

### 2.3 Why no existing signal solves this
| Candidate signal | Why it fails as a leading indicator |
|---|---|
| Citizen self-report / symptom apps | By definition only available after symptom onset — same lag as clinical presentation |
| Satellite / remote sensing | Cannot observe biological/epidemiological state at all |
| Historical seasonal priors | Predicts *when* outbreaks are more likely in general, not *whether one is happening right now* in a specific catchment |
| City-scale wastewater surveillance (existing programs) | Aggregates an entire city; multi-day lab turnaround; cannot attribute to a specific PHC catchment |

The one physical signal that precedes clinical presentation is pathogen shedding into community wastewater — people who are infected but pre-symptomatic or mildly symptomatic still shed pathogen material into sewage/drains. This is established science (used for COVID and polio surveillance globally) but has never been deployed at the resolution and turnaround needed to drive a PHC-level redistribution decision.

---

## 3. Goals and Non-Goals

### 3.1 Goals
- G1: Detect anomalous pathogen/fecal-load signatures in community wastewater at PHC-catchment resolution.
- G2: Convert raw sensor signal into a calibrated outbreak-probability forecast with a usable lead time (target: 3-7 days ahead of OPD surge).
- G3: Generate actionable, multilingual, plain-language alerts for PHC and state health department staff.
- G4: Recommend specific cross-district stock redistribution actions before a stockout occurs.
- G5: Operate reliably in low-connectivity, low-power-infrastructure rural/peri-urban deployment conditions.
- G6: Establish a revenue model anchored to avoided cost (emergency procurement, outbreak response, mortality/morbidity), not a speculative subscription.

### 3.2 Non-Goals (explicitly out of scope for v1 / hackathon prototype)
- NG1: This is not a diagnostic device and makes no individual-patient diagnostic claims.
- NG2: This is not a full replacement for clinical surveillance — it is a triage/prioritization signal that directs where to look, not a certainty claim.
- NG3: v1 does not attempt whole-genome sequencing or novel-pathogen discovery — it targets a small, seasonally-prioritized panel of known pathogens via LAMP assay.
- NG4: The hackathon prototype does not include a live, wet-lab-validated biosensor — Stage 2 (assay) is simulated in the demo; see Section 10.

---

## 4. Stakeholders / Personas

| Persona | Need | How Sentinel Drain serves them |
|---|---|---|
| State Health Department official | Early warning to allocate limited emergency budget before a crisis, not after | Catchment-level risk dashboard + redistribution recommendations |
| PHC Medical Officer | Plain-language, actionable alert, not raw sensor data | Gemini-generated alert in local language: what's likely happening, what to pre-position |
| District Health Supply Chain Coordinator | Concrete redistribution instructions across PHCs | AI-generated cross-district redistribution recommendation with quantities |
| NGO / multilateral funder (e.g., Gavi, Global Fund, UNICEF) | Cost-effective, scalable early-warning infrastructure to fund | Outcome-based pricing model with quantifiable avoided-cost ROI |
| Hackathon judges | Evidence of real Google AI integration, deployability, India-scale reasoning | Vertex AI forecasting + Google ADK multi-agent decision layer + Gemini, with explicit built-vs-roadmap scoping |

---

## 5. System Architecture

```
DRAIN NODE (field hardware)
 ├─ Stage 1: Continuous physicochemical sensing (pH, conductivity, ORP, turbidity, temp)
 │     → on-device rolling-baseline anomaly detection (ESP32-S3)
 ├─ Trigger logic: anomaly OR scheduled interval (e.g., every 48h)
 ├─ Stage 2: Triggered LAMP isothermal bioassay
 │     → sample draw (peristaltic pump) → reagent cartridge → heater block (~63°C)
 │     → colorimetric/optical readout
 ├─ Packaging: node ID, GPS, timestamp, Stage 1 score, Stage 2 result
 └─ Uplink: LoRa (primary) / GSM-NB-IoT (fallback), store-and-forward on outage

REGIONAL GATEWAY
 └─ Aggregates multiple node uplinks → forwards to cloud ingestion

CLOUD (Google Cloud)
 ├─ Ingestion: Pub/Sub → Cloud Run
 ├─ Storage: BigQuery (time-series sensor + historical OPD + seasonal/rainfall/mobility data)
 ├─ Forecasting: Vertex AI model → catchment-level surge probability + lead-time estimate
 ├─ Agentic decision layer: Google ADK + Gemini
 │     ├─ Sentinel Orchestrator Agent → coordinates the response workflow
 │     ├─ Sensor Intelligence Agent → validates anomalies and sensor/context evidence
 │     ├─ Epidemiology Agent → fuses assay, forecast, OPD, rainfall and spatial evidence
 │     ├─ Supply Chain Agent → evaluates stock impact and invokes deterministic allocation
 │     └─ Risk & Validation Agent → challenges conflicting/low-confidence evidence
 ├─ Optimization tool: OR-Tools → computes feasible stock allocation; agents do not invent quantities
 ├─ Human approval: high-impact redistribution actions require health-authority approval
 └─ Dashboard: State Health Department web view (risk heatmap, node health, evidence, recommendations)
```

See the accompanying PDF report for the full illustrated flow diagrams (system architecture, two-stage decision flow, deployment topology, cloud/AI pipeline, and revenue flow).

---

## 6. Functional Requirements

### 6.1 Hardware / Firmware
- FR-1: Node shall continuously sample pH, conductivity, ORP, turbidity, and temperature at a configurable interval (default 5-15 min).
- FR-2: Node shall maintain a per-node rolling baseline and compute an anomaly score on-device without requiring cloud round-trip.
- FR-3: Node shall trigger a Stage 2 LAMP assay when the anomaly score exceeds a configurable threshold, or on a fixed fallback schedule.
- FR-4: Node shall support a swappable reagent cartridge containing LAMP primer/master-mix for a seasonally-configurable pathogen panel (2-3 targets).
- FR-5: Node shall control assay temperature via PID loop to isothermal target (~63°C ± 1°C) for the LAMP reaction duration (30-45 min).
- FR-6: Node shall read assay result via colorimetric/optical sensor and classify positive/negative/inconclusive.
- FR-7: Node shall queue and store readings locally when uplink is unavailable, and flush on reconnect (store-and-forward).
- FR-8: Node shall report battery/solar charge state and flag maintenance needs (fouling, low reagent, low power).
- FR-9: Node shall flag low-confidence readings (e.g., diluted sample from rainfall) rather than silently reporting a clean result.

### 6.2 Cloud / AI
- FR-10: System shall ingest node telemetry into BigQuery with catchment, node, and timestamp dimensions.
- FR-11: System shall train/serve a Vertex AI model producing a per-catchment outbreak-surge probability and estimated lead time, using sensor signal plus historical OPD footfall, seasonal priors, and rainfall/mobility covariates.
- FR-12: System shall use a Google ADK-based multi-agent layer, powered primarily by Gemini, to coordinate evidence validation, epidemiological reasoning, supply-chain analysis, risk validation, and response planning.
- FR-13: The Sentinel Orchestrator Agent shall route an incident through the appropriate specialist agents rather than relying on a single LLM call.
- FR-14: The Sensor Intelligence Agent shall assess Stage-1 anomalies using sensor history, neighboring nodes, rainfall/context data, and node-health signals, and recommend whether Stage 2 confirmation or further investigation is warranted.
- FR-15: The Epidemiology Agent shall combine Stage-2 assay results, Vertex AI forecasts, OPD trends, seasonal priors, rainfall, and neighboring-catchment evidence into an explainable outbreak-risk assessment.
- FR-16: The Supply Chain Agent shall evaluate predicted demand impact against current PHC inventory and invoke a deterministic optimization tool (e.g., OR-Tools) to calculate feasible redistribution quantities; the LLM shall explain the resulting plan rather than inventing inventory quantities.
- FR-17: The Risk & Validation Agent shall identify contradictory evidence, low-confidence assays, rainfall dilution, sensor anomalies, or other conditions that should downgrade or delay a high-confidence alert.
- FR-18: High-impact redistribution recommendations shall support a human-approval step before execution.
- FR-19: System shall present a state-level dashboard showing catchment risk heatmap, node operational health, evidence supporting each alert, and outstanding redistribution recommendations.
- FR-20: System shall log agent decisions, tool calls, alerts, approvals, recommendations, and outcomes for audit and post-hoc accuracy evaluation.

### 6.3 Non-Functional Requirements
- NFR-1 (Reliability): Node shall operate for a minimum of 30 days without physical maintenance under normal conditions (battery/solar, reagent supply permitting).
- NFR-2 (Connectivity resilience): System shall assume intermittent connectivity as the default operating condition, not an edge case.
- NFR-3 (Power): Node shall run on solar + LiFePO4 battery, sized to survive a minimum 5-day low-sun stretch (monsoon condition).
- NFR-4 (Environmental): Node enclosure shall be IP67-rated minimum, given drain-rim humidity and splash/submersion risk.
- NFR-5 (Cost): Per-node hardware cost target under ₹15,000 at prototype scale (pre-volume-discount), to keep catchment-density deployment economically plausible.
- NFR-6 (Data integrity): All readings shall be timestamped, geotagged, and immutably logged for audit and regulatory defensibility.
- NFR-7 (Regulatory posture): System shall present outputs as probabilistic early-warning signals for investigation/pre-positioning, not as medical diagnoses, to stay outside clinical-diagnostic regulatory scope.

---

## 7. Hardware Specification (v1 prototype BOM)

| Component | Function | Notes |
|---|---|---|
| ESP32-S3 | Edge compute, anomaly detection, assay scheduling, comms | Sufficient headroom for on-device rolling-baseline model |
| pH probe (industrial grade) | Stage 1 sensing | |
| Conductivity/TDS probe | Stage 1 sensing | |
| ORP probe | Stage 1 sensing | |
| Turbidity sensor (optical) | Stage 1 sensing | |
| Temperature sensor | Stage 1 sensing + assay temp control | |
| Peristaltic micro-pump + solenoid valves | Sample draw, reagent load, flush | |
| Resistive heater block + PID control | LAMP isothermal reaction (~63°C) | Simpler and cheaper than a qPCR thermal cycler |
| Photodiode / colorimetric sensor | Assay readout | Colorimetric LAMP avoids need for a fluorometer |
| Reagent cartridge (swappable, consumable) | LAMP primers + master mix, 2-3 pathogen targets | Recurring-revenue component |
| LoRa module (+ GSM/NB-IoT fallback) | Backhaul to regional gateway | Dual-path for rural connectivity gaps |
| Solar panel + LiFePO4 battery | Power | Sized for 5-day low-sun autonomy |
| IP67 enclosure | Environmental protection | Drain-rim mounting |

Estimated per-node prototype cost: ₹10,000-15,000 in component cost at low volume; expected to fall substantially at institutional procurement volume.

---

## 8. Software / AI Pipeline Detail

### 8.1 Edge anomaly detection
A rolling seasonal-adjusted control-chart / z-score model runs on the ESP32, comparing current Stage-1 readings against the node's own learned baseline (baseline varies node-to-node and by time of day/rainfall — a fixed global threshold would produce excessive false triggers). This keeps the trigger decision local and fast, and conserves reagent by only running Stage 2 when warranted.

### 8.2 Vertex AI forecasting model
Inputs: Stage 1 anomaly trend, Stage 2 assay results (when available), historical PHC OPD footfall, seasonal disease priors, rainfall, and mobility data where available. Output: per-catchment surge probability with an estimated lead-time window. This is a genuine multi-modal predictive model, not an LLM wrapper — it is the component that earns the "AI/Technical Execution" weight in the hackathon's judging criteria.

### 8.3 Agentic AI layer (Google ADK + Gemini)
The existing Vertex AI forecasting model remains the numerical prediction layer. The agentic layer sits downstream of that model and is responsible for coordinating evidence, tools, and decisions rather than replacing the predictive model.

**Framework:** Google Agent Development Kit (ADK), using a multi-agent workflow.

**Primary LLM:** Gemini 3.5 Flash for routine agentic reasoning, routing, evidence synthesis, and response generation. A more capable Gemini reasoning model may be used selectively for unusually complex or conflicting incidents; model selection remains an implementation detail and does not change the system architecture.

**Agents:**
1. **Sentinel Orchestrator Agent** — coordinates the incident workflow and delegates work to specialist agents.
2. **Sensor Intelligence Agent** — validates Stage-1 anomalies against node history, neighboring nodes, rainfall/context, and node health; it does not diagnose disease.
3. **Epidemiology Agent** — combines Stage-2 assay results, Vertex AI forecast outputs, OPD trends, seasonal priors, rainfall, and neighboring-catchment evidence into an explainable outbreak-risk assessment.
4. **Supply Chain Agent** — translates forecasted demand into a stock-impact assessment and calls a deterministic allocation tool to calculate feasible redistribution.
5. **Risk & Validation Agent** — challenges the incident hypothesis and flags contradictory evidence, low-confidence assays, rainfall dilution, sensor faults, or other reasons to downgrade or delay an alert.

**Deterministic tools:** The agents may call BigQuery for evidence retrieval, the Vertex AI forecasting service for predictions, and an OR-Tools-based optimization service for stock allocation. LLMs explain and coordinate these results; they do not fabricate sensor measurements, inventory levels, or optimal quantities.

**Human-in-the-loop:** High-impact redistribution recommendations remain subject to health-authority approval before execution.

**Alert generation:** After evidence validation, Gemini converts the structured risk assessment into a plain-language, multilingual, actionable message for PHC staff (e.g., "64% probability of rotavirus-linked OPD surge in this catchment within 4-6 days; recommend pre-positioning ORS/IV fluids").

**Explainability:** Each incident should retain the evidence and reasoning inputs used to support the recommendation so staff can answer "why this alert?" and "why this redistribution?"

### 8.4 Data model (BigQuery, indicative)
- `nodes` (node_id, catchment_id, phc_id, lat, lon, install_date, status)
- `readings_stage1` (node_id, timestamp, ph, conductivity, orp, turbidity, temp, anomaly_score)
- `readings_stage2` (node_id, timestamp, assay_result, target_panel, confidence)
- `phc_ops` (phc_id, date, opd_footfall, stock_levels_by_sku)
- `forecasts` (catchment_id, timestamp, surge_probability, lead_time_days, model_version)
- `alerts` (alert_id, catchment_id, phc_id, timestamp, message, language, action_recommended)
- `agent_incidents` (incident_id, catchment_id, created_at, status, confidence, current_agent, final_decision)
- `agent_evidence` (incident_id, evidence_type, source, value, confidence, timestamp)
- `agent_actions` (incident_id, agent_name, action, tool_called, result, timestamp)
- `redistribution_plans` (incident_id, source_phc, destination_phc, sku, quantity, optimization_run_id, approval_status)

---

## 9. Deployment Model

- Node density: 2-3 nodes per PHC catchment (~20-30k population), sited on major community drains downstream of dense settlement, upstream of any treatment infrastructure.
- Redundancy rationale: a single drain's flow is not fully representative (dilution, blockages, industrial/greywater contamination) — multi-node coverage plus per-node baseline calibration is the mitigation, not a single "trust the sensor" assumption.
- Rollout sequencing: pilot in 1-2 catchments within a state that already ran COVID-era wastewater surveillance (lower institutional friction, existing familiarity with the concept), before wider rollout.

---

## 10. Hackathon Demo Scope (honest built-vs-roadmap split)

**Built and demonstrated live:**
- Stage 1 hardware: physicochemical sensing + fluidics + on-device anomaly detection, running on real prototype hardware.
- Full cloud/AI pipeline: ingestion → BigQuery → Vertex AI forecast → Google ADK multi-agent workflow → dashboard, using live Stage-1 data plus injected synthetic Stage-2/historical OPD data.
- Agentic workflow: Sentinel Orchestrator → Sensor Intelligence → Epidemiology → Supply Chain → Risk & Validation, with structured tool calls and explainable evidence.
- Deterministic redistribution optimization using simulated PHC inventory data, with a human-approval step before the recommendation is considered actionable.

**Simulated, clearly labeled as simulated:**
- Stage 2 LAMP bioassay readout — represented via a colorimetric reagent mimicking the LAMP pH-shift signal, explicitly labeled in the demo narrative as a simulated positive/negative readout.

**Explicitly scoped as roadmap, not claimed as built:**
- Wet-lab validation of the LAMP primer panel and field cross-reactivity testing.
- Regulatory engagement for field biosensor deployment.

This scoping is a deliberate product decision, not a limitation to hide — it directly targets the "Deployability & Scalability" judging criterion, which rewards teams who demonstrate they understand exactly what is validated versus what remains R&D risk.

---

## 11. Revenue Model

### 11.1 Structure
- **Recurring revenue:** reagent cartridge resupply (consumable, razor/blade model) sold to the operating state health department or implementation partner.
- **Service revenue:** per-catchment monthly early-warning-as-a-service fee.
- **Pricing anchor:** priced against avoided cost — emergency procurement premiums, emergency staff deployment costs, and excess morbidity/mortality from unprepared stockouts during a surge — not cost-plus on hardware.

### 11.2 Buyer
State health departments, NGOs, or multilateral health funders (several of which have funded prior WBE programs) — not individual PHCs, which lack discretionary budget. This is a deliberate go-to-market decision: sell to the entity that controls the budget line item that this system reduces.

### 11.3 Path to scale
Start with pilot catchments in a state with prior institutional WBE experience, use documented lead-time and avoided-cost outcomes from the pilot as the evidence base for statewide and then multi-state expansion.

---

## 12. Differentiation

Existing wastewater surveillance in India (COVID-era municipal/IIT-run programs) and internationally (e.g., national wastewater surveillance systems) operate at sewage-treatment-plant inlet scale: city-aggregate signal, lab-based qPCR, multi-day turnaround. Sentinel Drain's specific, narrow, defensible claim is resolution and turnaround: pushing the same underlying science down to PHC-catchment scale with field-deployable turnaround fast enough to drive a specific redistribution decision, rather than a general "cases are rising somewhere in the city" signal.

---

## 13. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| LAMP assay false positives/cross-reactivity | Erodes trust in alerts | Position outputs as probabilistic triage signal, not diagnosis; require Stage 1 + Stage 2 agreement before high-confidence alert |
| Rainfall dilution masking real signal | False negatives | Flag low-conductivity samples as reduced-confidence rather than silently reporting clean |
| Connectivity gaps in rural catchments | Data loss, delayed alerts | Store-and-forward firmware design; dual LoRa/GSM backhaul |
| Reagent cold-chain / shelf-life in field conditions | Assay reliability degradation | Cartridge design with stabilized reagents; scheduled cartridge replacement cadence |
| Institutional sales cycle length (state health depts) | Slow revenue ramp | Target states with existing WBE familiarity first; NGO/multilateral co-funding for pilots |
| Regulatory ambiguity around field biosensing | Deployment delay | Explicit non-diagnostic framing; early engagement with state health authorities during pilot design |
| Agent/LLM hallucination or unsupported reasoning | Incorrect recommendation or loss of trust | Ground agents in structured tool outputs; deterministic optimization for quantities; evidence citations; confidence thresholds; human approval for high-impact actions |
| Conflicting agent conclusions | Delayed or inconsistent response | Sentinel Orchestrator uses explicit workflow/state transitions; Risk & Validation Agent can downgrade/escalate incidents; all decisions are logged |
| Excessive agent latency/cost | Slow or expensive response | Use Gemini 3.5 Flash for routine work; escalate only complex incidents; keep forecasting and optimization as dedicated services |

---

## 14. Success Metrics

- Lead time achieved: days between Stage 2 positive signal and actual PHC OPD surge onset (target 3-7 days).
- Alert precision/recall against confirmed subsequent outbreaks in pilot catchments.
- Stockout incidents avoided in catchments with active redistribution recommendations vs. control catchments.
- Node uptime / data completeness (target >90% of expected reporting intervals delivered).
- Cost avoided per catchment per year (basis for revenue-model validation).
- Agent recommendation validity: percentage of recommendations grounded in available sensor, forecast, and inventory evidence.
- Unsupported-action rate: percentage of agent outputs attempting to act without sufficient evidence or required approval.
- Human-approval acceptance rate for high-impact redistribution recommendations.
- Agent workflow latency and cost per incident.

---

## 15. Hackathon Submission Mapping

| Evaluation criterion | Weight | How Sentinel Drain addresses it |
|---|---|---|
| Problem-Solution Fit | 20% | Directly answers the brief's call for demand forecasting, early stockout warning, and cross-district redistribution |
| AI/Technical Execution | 25% | Genuine multi-modal Vertex AI forecasting model + Google ADK multi-agent decision layer using Gemini for evidence synthesis, validation, alerting, and tool-grounded redistribution reasoning |
| Depth & Reach Across India | 20% | Catchment-tier deployment model reuses existing PHC network topology, scales state-by-state |
| Impact Potential | 15% | Direct mortality/morbidity and stockout-avoidance story, quantifiable per catchment |
| Deployability & Scalability | 20% | Explicit built-vs-roadmap scoping; pilot-first go-to-market targeting states with prior WBE familiarity |

---

## 16. Open Questions / Next Steps

1. Validate LAMP primer panel selection against regional seasonal disease priors with a domain/public-health advisor.
2. Confirm LoRa gateway coverage assumptions for target pilot geography, or budget for GSM/NB-IoT as primary in low-LoRa-coverage areas.
3. Identify a pilot state with existing WBE institutional experience for outreach.
4. Define the exact historical OPD/stock dataset needed to train the initial Vertex AI forecasting model (real PHC data vs. synthetic for hackathon submission).
5. Scope the minimum viable reagent cartridge design for a credible hardware demo unit.
6. Implement the Google ADK multi-agent workflow with the Sentinel Orchestrator, Sensor Intelligence, Epidemiology, Supply Chain, and Risk & Validation agents.
7. Define structured tool interfaces for BigQuery evidence retrieval, Vertex AI forecasting, and OR-Tools-based redistribution optimization.
8. Define the human-approval gate and agent audit schema for high-impact recommendations.
