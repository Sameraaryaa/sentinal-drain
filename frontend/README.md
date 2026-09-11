# Sentinel Drain — Google Cloud Enterprise Web Console

> **Navigation**: [🏠 Project Root](../README.md) | [🔬 Hardware & Firmware](../hardware/README.md) | [☁️ Cloud Backend & AI](../backend/README.md)

The Sentinel Drain frontend is an enterprise-grade operational dashboard designed to match the visual fidelity, interaction patterns, and design language of the **Google Cloud Console**. It provides public health authorities and epidemiologists with live biosurveillance maps, real-time edge telemetry feeds, Vertex AI outbreak forecasts, multi-agent AI incident logs, and a human-in-the-loop supply chain authorization gate.

---

## 1. Google Design Language & Design Tokens

The interface strictly conforms to Google's Material and Cloud Console design guidelines, prioritizing clarity, legibility, and high-density clinical data visualization.

### 1.1 Color Palette

| Token | Hex Value | GCP Semantic Usage |
|---|---|---|
| `--gcp-blue` | `#1a73e8` | Primary Google action color, active tab indicator, primary buttons |
| `--gcp-blue-hover` | `#1765cc` | Button hover state |
| `--gcp-blue-bg` | `#e8f0fe` | Selected item tint, primary chip background |
| `--gcp-green` | `#1e8e3e` | Operational status, normal baseline, approved state |
| `--gcp-green-bg` | `#e6f4ea` | Success chip & badge background |
| `--gcp-yellow` | `#f9ab00` | Warning, elevated microbial anomaly, pending review |
| `--gcp-yellow-bg` | `#fef7e0` | Warning chip & badge background |
| `--gcp-red` | `#d93025` | Critical outbreak alert, high surge risk, stockout imminent |
| `--gcp-red-bg` | `#fce8e6` | Critical alert banner & chip background |
| `--gcp-surface` | `#ffffff` | Content cards, data tables, modals |
| `--gcp-bg` | `#f8f9fa` | Application canvas background |
| `--gcp-border` | `#dadce0` | Hairline card borders, table dividers, header rules |
| `--gcp-text-primary` | `#202124` | Primary headers, KPI values, high-emphasis text |
| `--gcp-text-secondary` | `#5f6368` | Secondary labels, sub-headers, metadata timestamps |

### 1.2 Typography System

- **Brand & Headings**: `Google Sans`, `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `Roboto`, `sans-serif`
- **Body & Controls**: `Roboto`, `-apple-system`, `BlinkMacSystemFont`, `sans-serif`
- **Telemetry & Logs**: `Google Sans Mono`, `JetBrains Mono`, `Consolas`, `monospace`

---

## 2. Interface Layout & Navigation Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  [≡] [Google Cloud] Sentinel Drain  |  [Project: sentinel-drain-gorakhpur-pilot ▾]      │
│      [ 🔍 Search nodes, PHCs, incidents... (/) ]      [asia-south1] [?] [⚙] [👤]        │
├──────────────┬─────────────────────────────────────────────────────────────────────────┤
│ [Nav Rail]   │ [Breadcrumbs: Sentinel Drain > Fleet Overview]   [District: Gorakhpur ▾]│
│              ├─────────────────────────────────────────────────────────────────────────┤
│ 🗺️ GIS Map   │ [KPI 1: 11 Nodes Online]  [KPI 2: Normal 2.5σ]  [KPI 3: 4.8d Lead Time] │
│ 📈 Telemetry ├─────────────────────────────────────────────────────────────────────────┤
│ 🔮 Vertex AI │                                                                         │
│ 🤖 War Room  │                         Active Operational View                         │
│ 📦 Logistics │            (GIS Map / Telemetry Charts / Multi-Agent War Room)           │
│ 📢 Advisory  │                                                                         │
│              │                                                                         │
└──────────────┴─────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Top Application Bar
- **Hamburger Menu Toggle**: Expands or collapses the left navigation rail.
- **Google Cloud Brand Identity**: Google Cloud icon alongside product title `Sentinel Drain`.
- **Project Selector**: Displays active GCP project `sentinel-drain-gorakhpur-pilot` with project dropdown modal.
- **Global Search Bar**: Quick search filter for nodes, PHCs, alerts, and agent action IDs.
- **Region Badge**: `asia-south1 (Mumbai)` datacenter location chip.
- **Utility Action Icons**: Quick links for Documentation, System Health, and Administrator Profile.

### 2.2 Collapsible Navigation Rail
The left navigation rail provides instant switching between 6 primary operational surfaces:
1. **Fleet Overview & GIS Map (`#overview`)**: Spatial distribution of 11 drain nodes across 5 PHC catchments with CartoDB Positron light tiles.
2. **Live Telemetry (`#telemetry`)**: High-frequency dual-axis sensor graphs (pH, TDS/conductivity, ORP, turbidity, temperature).
3. **Vertex AI Forecaster (`#forecasting`)**: 7-day outbreak surge risk curves, lead-time indicators, and SHAP explainability attributions.
4. **Agent War Room (`#war-room`)**: Google ADK 5-agent real-time deliberation trace, reasoning dossier, and evidence ledger.
5. **Supply Chain & Approvals (`#supply-chain`)**: Projected stockout curves, Google OR-Tools redistribution schedule, and one-click authorization gate.
6. **Multilingual Advisory (`#alerts`)**: Public health advisory engine broadcasting in English, Hindi, Kannada, and Tamil.

---

## 3. Real-Time Streaming Architecture

The console operates under a strict **Zero Mock Data Policy**:
- **Continuous 3.5s Live Polling Engine**: Synchronizes live sensor readings from the backend edge-node emulator.
- **Chart.js Multi-Axis Waveforms**: Automatically pushes newly arrived physicochemical data points onto real-time rolling charts.
- **Leaflet Light Map (CartoDB Positron)**: Dynamically updates marker pulse states (green for normal, amber for elevated anomaly, red for active LAMP confirmation) based on live API responses.
- **Live Human Approval Gate**: When an anomaly is detected and OR-Tools creates a redistribution plan, the UI unlocks the **"Authorize Inter-PHC Stock Reallocation"** action in real-time, executing a state transition upon authorization.

---

## 4. Local Development & Deployment

The frontend consists of modern vanilla JavaScript (ES6+), HTML5 semantic markup, and vanilla CSS with CSS Custom Properties. No heavy build tools or npm bundling required.

```bash
# Served directly by the FastAPI backend
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` in any modern web browser.
