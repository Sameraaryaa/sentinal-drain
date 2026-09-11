# Sentinel Drain — Cloud Backend & AI Architecture

> **Navigation**: [🏠 Project Root](../README.md) | [🔬 Hardware & Firmware](../hardware/README.md) | [🖥️ Google Cloud Console](../frontend/README.md)

The Sentinel Drain backend is a high-performance Python/FastAPI service simulating the Cloud Run / Pub/Sub ingestion pipeline, Vertex AI forecasting model, Google OR-Tools optimization engine, and Google ADK Multi-Agent decision layer.

---

## 1. Directory Structure

```
backend/
├── README.md                   # This documentation
├── sentinel_drain.db           # BigQuery-compatible SQLite database
└── app/
    ├── main.py                 # FastAPI server & background live streamer
    ├── database.py             # BigQuery-compatible schema definitions
    ├── seed_data.py            # Gorakhpur district seed data generator
    ├── models.py               # Pydantic data schemas
    ├── firmware_emulator/      # Edge node simulation twins
    │   ├── edge_node.py        # ESP32-S3 logic digital twin
    │   └── simulator_service.py# Fleet coordinator & scenario engine
    ├── forecasting/            # Predictive ML models
    │   └── vertex_predictor.py # Calibrated Vertex AI outbreak model
    ├── optimization/           # Google OR-Tools LP solver
    │   └── ortools_allocator.py# Min-cost flow pharmaceutical allocator
    ├── agents/                 # Google ADK Multi-Agent System
    │   ├── base_agent.py       # Agent base class & Gemini LLM client
    │   ├── orchestrator_agent.py # Master workflow coordinator
    │   ├── sensor_intelligence_agent.py # Physicochemical validator
    │   ├── epidemiology_agent.py   # Outbreak risk & clinical assessor
    │   ├── supply_chain_agent.py   # Stockout calculator & OR-Tools runner
    │   └── risk_validation_agent.py# Adversarial devil's advocate auditor
    └── routes/                 # REST API endpoints
        ├── telemetry.py        # Sensor packet ingestion
        ├── incidents.py        # Multi-agent trace & incidents
        ├── forecasts.py        # Vertex AI surge prediction queries
        ├── supply_chain.py     # Inventory, plans, and approval gate
        ├── alerts.py           # Multilingual broadcast endpoints
        └── simulation.py       # Presets and background stream controls
```

---

## 2. API Endpoints Reference

### 2.1 Telemetry Ingestion (`/api/telemetry`)
- `POST /api/telemetry/stage1`: Ingests continuous physicochemical readings from edge nodes.
- `POST /api/telemetry/stage2`: Ingests Stage-2 LAMP optical readouts and classifications.
- `GET /api/telemetry/nodes`: Lists all 11 nodes, GPS coordinates, status, and battery/cartridge health.
- `GET /api/telemetry/history/{node_id}`: Returns 24-hour time-series for chart visualizers.

### 2.2 Vertex AI Forecasting (`/api/forecasts`)
- `GET /api/forecasts/catchment/{catchment_id}`: Computes calibrated outbreak surge probability, lead-time (3–7 days), and SHAP feature drivers.
- `GET /api/forecasts/all`: Computes surge risk across all 5 catchments in the pilot district.

### 2.3 Multi-Agent Incident Management (`/api/incidents`)
- `POST /api/incidents/trigger`: Triggers end-to-end multi-agent evaluation starting from a drain node anomaly.
- `GET /api/incidents/active`: Lists active and pending incidents.
- `GET /api/incidents/{incident_id}`: Returns full audit dossier: agent thoughts, evidence ledger, tool executions, and redistribution plans.

### 2.4 Supply Chain & Human Approval Gate (`/api/supply-chain`)
- `GET /api/supply-chain/inventory`: Real-time stock levels of ORS, IV fluids, antibiotics, zinc, and RDT kits across all PHCs.
- `POST /api/supply-chain/optimize`: Runs Google OR-Tools optimization on demand.
- `GET /api/supply-chain/plans`: Lists generated redistribution plans and approval statuses.
- `POST /api/supply-chain/approve`: **Human-in-the-Loop Action Gate** where the District Health Officer authorizes, modifies, or rejects orders, automatically updating the live operational inventory.

### 2.5 Multilingual Alerts (`/api/alerts`)
- `GET /api/alerts/latest`: Retrieves recent advisories in English, Hindi, Kannada, and Tamil.
- `POST /api/alerts/dispatch/{alert_id}`: Simulates gateway dispatch to WhatsApp and SMS.

### 2.6 Simulation & Live Stream Controls (`/api/simulation`)
- `GET /api/simulation/stream/status`: Returns streaming status, interval, and tick count.
- `POST /api/simulation/stream/toggle`: Pauses or resumes background auto-streaming.
- `POST /api/simulation/scenario`: Switches operational presets (Outbreak Surge, Monsoon Dilution, etc.).
- `POST /api/simulation/tick`: Advances the simulation by one time-step.
- `POST /api/simulation/reset`: Restores the database to pristine baseline state.

---

## 3. Vertex AI Outbreak Forecasting Model ([`vertex_predictor.py`](file:///d:/sentinal%20drain/backend/app/forecasting/vertex_predictor.py))

- **Algorithm**: Calibrated Gradient Boosting Classifier combined with a Lead-Time Regressor.
- **Input Feature Vector**:
  1. `stage1_anomaly_mean`: Rolling Z-score anomaly mean across catchment nodes.
  2. `stage1_orp_drop_rate`: Velocity of ORP plunge indicating microbial anaerobic reduction.
  3. `stage1_cond_ratio`: Conductivity ratio vs 24h baseline.
  4. `stage2_assay_positive`: Colorimetric binary detection ($1$ for Positive, $0$ for Negative).
  5. `stage2_optical_ratio`: Absorbance ratio $A_{570}/A_{650}$.
  6. `opd_7d_baseline`: Historical clinic OPD footfall.
  7. `opd_recent_slope`: Short-term clinical presentation slope.
  8. `monsoon_rainfall_mm`: Weather covariate for dilution correction.
  9. `seasonal_prior_index`: Monthly epidemiological prior for enteric pathogens in UP/Bihar.
- **Outputs**:
  - `surge_probability`: Calibrated probability ($0.0 - 1.0$).
  - `lead_time_days`: Projected lead time ($3.0 - 7.0$ days).
  - `predicted_footfall_multiplier`: Anticipated surge scale ($1.2x - 3.5x$).
  - `primary_drivers`: SHAP-style attribution breakdown.

---

## 4. Google OR-Tools Redistribution Optimizer ([`ortools_allocator.py`](file:///d:/sentinal%20drain/backend/app/optimization/ortools_allocator.py))

Formulated as an Integer Programming / Min-Cost Network Flow model:
- **Zero Hallucination**: Inventory quantities are computed mathematically; LLMs only explain the resulting plan.
- **Safety Stock Constraint**: A donor facility's surplus is bounded by:
  $$\text{Surplus}_i = \max(0, \text{CurrentStock}_i - \text{Capacity}_i \times 8 \times 0.35)$$
- **Distance Minimization**: Uses the Haversine formula to compute transit distances across district GPS coordinates and prioritizes the nearest available surplus hubs.

---

## 5. Google ADK Multi-Agent System ([`backend/app/agents/`](file:///d:/sentinal%20drain/backend/app/agents/))

Powered primarily by **Gemini 2.5 Flash** (via `google-genai` SDK) with deterministic fallback:
1. **Sentinel Orchestrator Agent**: Manages the state machine:
   $$\text{TRIAGE} \rightarrow \text{SENSOR\_INTEL} \rightarrow \text{EPIDEMIOLOGY} \rightarrow \text{SUPPLY\_CHAIN} \rightarrow \text{RISK\_AUDIT} \rightarrow \text{HUMAN\_GATE}$$
2. **Sensor Intelligence Agent**: Validates physical readings against neighbor nodes and detects dilution.
3. **Epidemiology Agent**: Integrates LAMP assay results and Vertex AI forecasts into clinical severity.
4. **Supply Chain Agent**: Calculates days-to-stockout and triggers OR-Tools.
5. **Risk & Validation Agent**: Adversarial devil's advocate challenging assumptions and enforcing safety gates.
6. **Multilingual Alert Generator**: Formats alerts in English, Hindi, Kannada, and Tamil.
