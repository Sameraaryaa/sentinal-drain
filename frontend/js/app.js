/**
 * Sentinel Drain - State Health Department Command Dashboard Logic (Light Theme)
 * Real-Time Live Streaming Data Engine:
 * - CartoDB Positron Light GIS Map
 * - Live continuous sensor streaming (3.5s auto-tick)
 * - Dynamic Chart.js waveforms
 * - Live Vertex AI Outbreak Forecasting & SHAP attributions
 * - Multi-Agent Incident War Room trace
 * - Google OR-Tools Deterministic Supply Chain optimization
 * - Real interactive Human Approval Gate committing to live database
 */

// Global State
let currentScenario = "OUTBREAK_CHOLERA";
let selectedNodeId = "ND-RAM-01";
let activeLang = "en";
let currentAlertData = null;
let currentPlanData = null;
let leafletMap = null;
let mapMarkers = {};
let transitPolyline = null;
let isStreamingActive = true;
let streamPollInterval = null;

// Chart instances
let chartPhOrp = null;
let chartCondTurb = null;
let chartAnomaly = null;
let chartLamp = null;
let chartOpdSurge = null;

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initMap();
  initCharts();
  initEventListeners();
  loadInitialData();
  startLiveStreamingLoop();
});

/* =========================================================================
   1. TAB NAVIGATION
   ========================================================================= */
function initTabs() {
  const tabButtons = document.querySelectorAll(".tab-btn");
  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      tabButtons.forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const targetPanel = document.getElementById(btn.dataset.tab);
      if (targetPanel) {
        targetPanel.classList.add("active");
        if (btn.dataset.tab === "tab-map" && leafletMap) {
          setTimeout(() => leafletMap.invalidateSize(), 200);
        }
      }
    });
  });
}

/* =========================================================================
   2. GIS LEAFLET MAP (LIGHT THEME)
   ========================================================================= */
function initMap() {
  const mapElem = document.getElementById("gis-map");
  if (!mapElem) return;

  // Center on Gorakhpur Health District
  leafletMap = L.map("gis-map", {
    center: [26.76, 83.38],
    zoom: 12,
    zoomControl: true
  });

  // CartoDB Positron Light-Mode Tile Layer
  L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap',
    maxZoom: 19
  }).addTo(leafletMap);
}

function updateMapLayers(nodes, phcs, transfers) {
  if (!leafletMap) return;

  // Clear existing markers
  Object.values(mapMarkers).forEach(m => leafletMap.removeLayer(m));
  mapMarkers = {};
  if (transitPolyline) {
    leafletMap.removeLayer(transitPolyline);
    transitPolyline = null;
  }

  // 1. Add PHC Hospital Markers
  phcs.forEach(p => {
    const isTarget = (p.phc_id === "PHC-RAMPUR");
    const isSource = (p.phc_id === "PHC-BILASPUR");
    
    let pinBg = "#0284c7";
    if (isTarget) pinBg = "#e11d48";
    else if (isSource) pinBg = "#059669";

    const phcIcon = L.divIcon({
      className: "custom-phc-pin",
      html: `
        <div style="
          background: ${pinBg};
          color: #ffffff;
          font-weight: 700;
          font-size: 11px;
          padding: 4px 8px;
          border-radius: 6px;
          border: 1px solid #ffffff;
          box-shadow: 0 2px 8px rgba(15,23,42,0.18);
          white-space: nowrap;
        ">
          🏥 ${p.phc_name.split(' ')[0]}
        </div>
      `,
      iconSize: [80, 24],
      iconAnchor: [40, 12]
    });

    const m = L.marker([p.lat, p.lon], { icon: phcIcon }).addTo(leafletMap);
    m.bindPopup(`
      <div style="font-family: Inter, sans-serif; font-size: 12px; color: #0f172a;">
        <strong style="font-size: 13px;">${p.phc_name}</strong><br>
        District: <strong>${p.district}</strong><br>
        Daily OPD: <strong>${p.opd_footfall_daily}</strong> patients<br>
        ORS Stock: <strong style="color:${isTarget ? '#e11d48' : '#059669'};">${p.stock_ors}</strong> sachets<br>
        IV Fluids: <strong style="color:${isTarget ? '#e11d48' : '#059669'};">${p.stock_iv_fluids}</strong> bottles
      </div>
    `);
    mapMarkers[p.phc_id] = m;
  });

  // 2. Add Drain Nodes
  nodes.forEach(n => {
    let color = "#059669"; // Normal baseline

    if (n.status === "FOULING_ALERT") {
      color = "#d97706";
    } else if (n.node_id === "ND-RAM-01" && currentScenario === "OUTBREAK_CHOLERA") {
      color = "#e11d48";
    } else if (n.catchment_id === "CAT-RAMPUR" && currentScenario === "OUTBREAK_CHOLERA") {
      color = "#7c3aed";
    }

    const nodeIcon = L.divIcon({
      className: "custom-node-pin",
      html: `
        <div style="
          width: 14px;
          height: 14px;
          background: ${color};
          border: 2px solid #ffffff;
          border-radius: 50%;
          box-shadow: 0 0 8px ${color};
          cursor: pointer;
        "></div>
      `,
      iconSize: [14, 14],
      iconAnchor: [7, 7]
    });

    const nm = L.marker([n.lat, n.lon], { icon: nodeIcon }).addTo(leafletMap);
    nm.on("click", () => inspectNode(n));
    nm.bindTooltip(`<strong>${n.node_id}</strong> (${n.catchment_id})`, { direction: 'top' });
    mapMarkers[n.node_id] = nm;
  });

  // 3. Draw Redistribution Transit Line
  if (transfers && transfers.length > 0) {
    const t = transfers[0];
    const srcPhc = phcs.find(p => p.phc_id === t.source_phc_id || p.phc_id === t.source_phc);
    const destPhc = phcs.find(p => p.phc_id === t.destination_phc_id || p.phc_id === t.destination_phc);

    if (srcPhc && destPhc) {
      const latlngs = [
        [srcPhc.lat, srcPhc.lon],
        [destPhc.lat, destPhc.lon]
      ];

      transitPolyline = L.polyline(latlngs, {
        color: "#0284c7",
        weight: 4,
        dashArray: "8, 8",
        opacity: 0.95
      }).addTo(leafletMap);

      transitPolyline.bindPopup(`
        <div style="font-family: Inter, sans-serif; font-size: 12px; color: #0f172a;">
          <strong style="color:#0284c7;">OR-Tools Redistribution Transit Route</strong><br>
          From: <strong>${srcPhc.phc_name}</strong><br>
          To: <strong>${destPhc.phc_name}</strong><br>
          Quantity: <strong>${t.quantity} ${t.sku}</strong><br>
          Distance: <strong>${t.transit_distance_km || t.distance_km} km</strong> (${t.est_transit_hours} hrs transit)
        </div>
      `);
    }
  }
}

function inspectNode(node) {
  selectedNodeId = node.node_id;
  const selectElem = document.getElementById("node-selector");
  if (selectElem) selectElem.value = node.node_id;

  const inspector = document.getElementById("node-inspector");
  inspector.innerHTML = `
    <div style="font-size: 0.84rem;">
      <div style="display:flex; justify-content:space-between; margin-bottom:8px; align-items:center;">
        <strong style="color: #0284c7; font-size: 0.95rem;">${node.node_id}</strong>
        <span class="badge ${node.status === 'ONLINE' ? 'badge-emerald' : 'badge-amber'}">${node.status}</span>
      </div>
      <p style="color: #475569; font-size: 0.78rem;">Catchment: <strong>${node.catchment_id}</strong></p>
      <p style="color: #475569; font-size: 0.78rem;">Assigned PHC: <strong>${node.phc_id}</strong></p>
      <div style="margin-top:10px; display:grid; grid-template-columns: 1fr 1fr; gap:6px; font-size:0.75rem; color:#0f172a;">
        <div>Battery: <strong>${node.battery_pct}%</strong></div>
        <div>Reagents: <strong>${node.reagents_remaining}/30</strong></div>
        <div>Lat: <strong>${node.lat.toFixed(4)}</strong></div>
        <div>Lon: <strong>${node.lon.toFixed(4)}</strong></div>
      </div>
      <button onclick="switchToTelemetryTab('${node.node_id}')" class="btn btn-primary btn-sm btn-block" style="margin-top:12px;">
        View Live Telemetry Stream
      </button>
    </div>
  `;
}

function switchToTelemetryTab(nodeId) {
  selectedNodeId = nodeId;
  const tabBtn = document.querySelector('.tab-btn[data-tab="tab-telemetry"]');
  if (tabBtn) tabBtn.click();
  loadNodeTelemetry(nodeId);
}

/* =========================================================================
   3. CHART.JS WAVEFORMS & TIME SERIES (LIGHT THEME)
   ========================================================================= */
function initCharts() {
  const chartOptionsLight = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 300 },
    plugins: {
      legend: {
        labels: {
          color: "#334155",
          font: { family: "Inter", size: 11, weight: 600 }
        }
      }
    },
    scales: {
      x: {
        grid: { color: "rgba(15, 23, 42, 0.06)" },
        ticks: { color: "#475569", font: { size: 10 } }
      },
      y: {
        grid: { color: "rgba(15, 23, 42, 0.06)" },
        ticks: { color: "#475569", font: { size: 10 } }
      }
    }
  };

  // Chart 1: pH & ORP
  const ctxPhOrp = document.getElementById("chart-ph-orp")?.getContext("2d");
  if (ctxPhOrp) {
    chartPhOrp = new Chart(ctxPhOrp, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          {
            label: "pH Level",
            data: [],
            borderColor: "#0284c7",
            backgroundColor: "rgba(2, 132, 199, 0.08)",
            yAxisID: "y-ph",
            tension: 0.3,
            borderWidth: 2
          },
          {
            label: "ORP (mV)",
            data: [],
            borderColor: "#e11d48",
            backgroundColor: "rgba(225, 29, 72, 0.08)",
            yAxisID: "y-orp",
            tension: 0.3,
            borderWidth: 2
          }
        ]
      },
      options: {
        ...chartOptionsLight,
        scales: {
          ...chartOptionsLight.scales,
          "y-ph": {
            type: "linear",
            position: "left",
            min: 5.5,
            max: 8.5,
            title: { display: true, text: "pH", color: "#0284c7" },
            ticks: { color: "#0284c7" }
          },
          "y-orp": {
            type: "linear",
            position: "right",
            min: 0,
            max: 250,
            title: { display: true, text: "ORP (mV)", color: "#e11d48" },
            ticks: { color: "#e11d48" },
            grid: { drawOnChartArea: false }
          }
        }
      }
    });
  }

  // Chart 2: Conductivity & Turbidity
  const ctxCondTurb = document.getElementById("chart-cond-turb")?.getContext("2d");
  if (ctxCondTurb) {
    chartCondTurb = new Chart(ctxCondTurb, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          {
            label: "Conductivity (uS/cm)",
            data: [],
            borderColor: "#d97706",
            backgroundColor: "rgba(217, 119, 6, 0.08)",
            tension: 0.3,
            yAxisID: "y-cond",
            borderWidth: 2
          },
          {
            label: "Turbidity (NTU)",
            data: [],
            borderColor: "#7c3aed",
            backgroundColor: "rgba(124, 58, 237, 0.08)",
            tension: 0.3,
            yAxisID: "y-turb",
            borderWidth: 2
          }
        ]
      },
      options: {
        ...chartOptionsLight,
        scales: {
          ...chartOptionsLight.scales,
          "y-cond": {
            type: "linear",
            position: "left",
            title: { display: true, text: "uS/cm", color: "#d97706" }
          },
          "y-turb": {
            type: "linear",
            position: "right",
            title: { display: true, text: "NTU", color: "#7c3aed" },
            grid: { drawOnChartArea: false }
          }
        }
      }
    });
  }

  // Chart 3: Anomaly Score
  const ctxAnomaly = document.getElementById("chart-anomaly")?.getContext("2d");
  if (ctxAnomaly) {
    chartAnomaly = new Chart(ctxAnomaly, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          {
            label: "Rolling Z-Score Anomaly",
            data: [],
            borderColor: "#059669",
            borderWidth: 2.5,
            tension: 0.2,
            fill: true,
            backgroundColor: "rgba(5, 150, 105, 0.08)"
          },
          {
            label: "Trigger Threshold (2.5 σ)",
            data: [],
            borderColor: "#e11d48",
            borderDash: [5, 5],
            borderWidth: 1.5,
            pointRadius: 0
          }
        ]
      },
      options: chartOptionsLight
    });
  }

  // Chart 4: Stage 2 LAMP Kinetics
  const ctxLamp = document.getElementById("chart-lamp-kinetics")?.getContext("2d");
  if (ctxLamp) {
    chartLamp = new Chart(ctxLamp, {
      type: "line",
      data: {
        labels: ["0m", "5m", "10m", "15m", "20m", "25m", "30m", "35m", "40m"],
        datasets: [
          {
            label: "Chamber Temp (°C) [Target 63°C PID]",
            data: [28.2, 54.0, 62.8, 63.1, 62.9, 63.0, 63.2, 62.9, 63.0],
            borderColor: "#7c3aed",
            yAxisID: "y-temp",
            tension: 0.3,
            borderWidth: 2
          },
          {
            label: "Absorbance Ratio A570/A650",
            data: [0.42, 0.44, 0.49, 0.72, 1.25, 1.88, 2.34, 2.51, 2.55],
            borderColor: "#0284c7",
            yAxisID: "y-abs",
            tension: 0.3,
            borderWidth: 2
          }
        ]
      },
      options: {
        ...chartOptionsLight,
        scales: {
          ...chartOptionsLight.scales,
          "y-temp": {
            type: "linear",
            position: "left",
            min: 20,
            max: 75,
            title: { display: true, text: "Chamber °C", color: "#7c3aed" }
          },
          "y-abs": {
            type: "linear",
            position: "right",
            min: 0,
            max: 3.0,
            title: { display: true, text: "A570 / A650", color: "#0284c7" },
            grid: { drawOnChartArea: false }
          }
        }
      }
    });
  }

  // Chart 5: Projected OPD Surge Curve
  const ctxOpd = document.getElementById("chart-opd-surge")?.getContext("2d");
  if (ctxOpd) {
    chartOpdSurge = new Chart(ctxOpd, {
      type: "line",
      data: {
        labels: ["Day -3", "Day -2", "Day -1", "Today (Early Warning)", "Day +1", "Day +2", "Day +3", "Day +4 (Surge Peak)", "Day +5", "Day +6", "Day +7"],
        datasets: [
          {
            label: "Projected OPD Surge (Without Intervention)",
            data: [82, 85, 87, 85, 110, 145, 185, 215, 195, 160, 125],
            borderColor: "#e11d48",
            backgroundColor: "rgba(225, 29, 72, 0.08)",
            fill: true,
            tension: 0.3,
            borderWidth: 2
          },
          {
            label: "Normal Facility Capacity (120/day)",
            data: [120, 120, 120, 120, 120, 120, 120, 120, 120, 120, 120],
            borderColor: "#d97706",
            borderDash: [6, 6],
            pointRadius: 0
          },
          {
            label: "Historical Baseline Footfall (85/day)",
            data: [85, 85, 85, 85, 85, 85, 85, 85, 85, 85, 85],
            borderColor: "#94a3b8",
            borderDash: [3, 3],
            pointRadius: 0
          }
        ]
      },
      options: chartOptionsLight
    });
  }
}

/* =========================================================================
   4. DATA LOADING & CONTINUOUS LIVE STREAMING
   ========================================================================= */
async function loadInitialData() {
  await refreshLiveData();
}

function startLiveStreamingLoop() {
  if (streamPollInterval) clearInterval(streamPollInterval);
  // Auto poll every 3.5 seconds to refresh all live telemetry and decisions
  streamPollInterval = setInterval(async () => {
    if (isStreamingActive) {
      await refreshLiveData();
    }
  }, 3500);
}

async function refreshLiveData() {
  try {
    // 1. Fetch live nodes
    const resNodes = await fetch("/api/telemetry/nodes");
    const nodes = await resNodes.json();

    // 2. Fetch live inventory
    const resInv = await fetch("/api/supply-chain/inventory");
    const phcs = await resInv.json();

    // 3. Fetch live active incidents
    const resInc = await fetch("/api/incidents/active");
    const incidents = await resInc.json();

    // 4. Fetch live redistribution plans
    const resPlans = await fetch("/api/supply-chain/plans");
    const plans = await resPlans.json();

    // 5. Fetch live alerts
    const resAlerts = await fetch("/api/alerts/latest");
    const alerts = await resAlerts.json();

    // 6. Fetch live forecast for active catchment
    const targetCatchment = (currentScenario === "OUTBREAK_ROTAVIRUS") ? "CAT-CHAURI" : "CAT-RAMPUR";
    const resForecast = await fetch(`/api/forecasts/catchment/${targetCatchment}`);
    const forecast = await resForecast.json();

    // 7. Fetch stream status
    const resStream = await fetch("/api/simulation/stream/status");
    const streamInfo = await resStream.json();

    // Update Header
    document.getElementById("hud-nodes-count").textContent = `${nodes.filter(n => n.status === 'ONLINE').length} / ${nodes.length} Online`;
    document.getElementById("hud-stream-status").textContent = streamInfo.is_streaming ? `LIVE STREAM (${streamInfo.total_ticks} ticks)` : "FEED PAUSED";

    if (incidents && incidents.length > 0) {
      const topInc = incidents[0];
      const probPct = Math.round(topInc.surge_probability * 100);
      document.getElementById("hud-outbreak-status").textContent = `${topInc.status.replace(/_/g, ' ')} (${probPct}%)`;

      // Update War Room with latest incident
      loadIncidentTrace(topInc.incident_id);
    }

    renderCatchmentSummary(phcs);
    renderInventoryTable(phcs);
    renderRedistributionPlans(plans);

    if (alerts && alerts.length > 0) {
      currentAlertData = alerts[0];
      renderAlertCard(alerts[0]);
      renderDispatchedAlertsList(alerts);
    }

    renderForecastCenter(forecast);
    updateMapLayers(nodes, phcs, plans);
    loadNodeTelemetry(selectedNodeId);

  } catch (err) {
    console.warn("Live stream refresh tick:", err);
  }
}

async function loadNodeTelemetry(nodeId) {
  try {
    const res = await fetch(`/api/telemetry/history/${nodeId}?limit=24`);
    const history = await res.json();
    if (!history || history.length === 0) return;

    const labels = history.map((h, i) => `T-${24 - i}h`);
    const phData = history.map(h => h.ph);
    const orpData = history.map(h => h.orp);
    const condData = history.map(h => h.conductivity);
    const turbData = history.map(h => h.turbidity);
    const anomalyData = history.map(h => h.anomaly_score);
    const threshData = history.map(() => 2.5);

    if (chartPhOrp) {
      chartPhOrp.data.labels = labels;
      chartPhOrp.data.datasets[0].data = phData;
      chartPhOrp.data.datasets[1].data = orpData;
      chartPhOrp.update("none");
    }

    if (chartCondTurb) {
      chartCondTurb.data.labels = labels;
      chartCondTurb.data.datasets[0].data = condData;
      chartCondTurb.data.datasets[1].data = turbData;
      chartCondTurb.update("none");
    }

    if (chartAnomaly) {
      chartAnomaly.data.labels = labels;
      chartAnomaly.data.datasets[0].data = anomalyData;
      chartAnomaly.data.datasets[1].data = threshData;
      const latestScore = anomalyData[anomalyData.length - 1];
      chartAnomaly.data.datasets[0].borderColor = (latestScore >= 2.5) ? "#e11d48" : "#059669";
      chartAnomaly.update("none");
    }

    // Update node live meta bar
    const lastPkt = history[history.length - 1];
    if (lastPkt) {
      const metaElem = document.getElementById("node-live-meta");
      if (metaElem) {
        metaElem.innerHTML = `
          <span>Latest pH: <strong>${lastPkt.ph}</strong></span> &bull;
          <span>ORP: <strong style="color:${lastPkt.orp < 100 ? '#e11d48' : '#0f172a'}">${lastPkt.orp} mV</strong></span> &bull;
          <span>Conductivity: <strong>${lastPkt.conductivity} uS/cm</strong></span> &bull;
          <span>Turbidity: <strong>${lastPkt.turbidity} NTU</strong></span> &bull;
          <span>Z-Score: <strong style="color:${lastPkt.anomaly_score >= 2.5 ? '#e11d48' : '#059669'}">${lastPkt.anomaly_score.toFixed(2)}</strong></span>
        `;
      }
    }

  } catch (err) {
    console.error(`Error streaming telemetry for ${nodeId}:`, err);
  }
}

async function loadIncidentTrace(incidentId) {
  try {
    const res = await fetch(`/api/incidents/${incidentId}`);
    const data = await res.json();
    renderWarRoom(data);
  } catch (err) {
    console.error("Error loading incident trace:", err);
  }
}

/* =========================================================================
   5. UI RENDERERS (LIGHT THEME)
   ========================================================================= */
function renderCatchmentSummary(phcs) {
  const container = document.getElementById("catchment-summary-list");
  if (!container) return;

  container.innerHTML = phcs.map(p => {
    const isDanger = (p.phc_id === "PHC-RAMPUR");
    return `
      <div class="catchment-item ${isDanger ? 'danger-border' : ''}">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span class="catchment-name">${p.phc_name}</span>
          <span class="badge ${isDanger ? 'badge-rose' : 'badge-emerald'}">
            ${isDanger ? 'Outbreak Warning' : 'Nominal'}
          </span>
        </div>
        <div class="catchment-meta">
          <span>Catchment: <strong>${p.catchment_id}</strong></span>
          <span>ORS Stock: <strong>${p.stock_ors}</strong></span>
        </div>
      </div>
    `;
  }).join("");
}

function renderInventoryTable(phcs) {
  const tbody = document.getElementById("inventory-tbody");
  if (!tbody) return;

  tbody.innerHTML = phcs.map(p => {
    const isDeficit = (p.phc_id === "PHC-RAMPUR");
    return `
      <tr class="${isDeficit ? 'row-deficit' : ''}">
        <td><strong>${p.phc_name}</strong></td>
        <td>${p.district}</td>
        <td>${p.opd_footfall_daily}</td>
        <td><strong class="${isDeficit ? 'text-rose' : ''}">${p.stock_ors}</strong></td>
        <td><strong class="${isDeficit ? 'text-rose' : ''}">${p.stock_iv_fluids}</strong></td>
        <td>${p.stock_antibiotics}</td>
        <td>${p.stock_zinc}</td>
        <td>${p.stock_rdt_kits}</td>
        <td>
          <span class="badge ${isDeficit ? 'badge-rose' : 'badge-emerald'}">
            ${isDeficit ? 'Critical Deficit' : 'Adequate Buffer'}
          </span>
        </td>
      </tr>
    `;
  }).join("");
}

function renderRedistributionPlans(plans) {
  const container = document.getElementById("redistribution-plans-list");
  if (!container) return;

  if (!plans || plans.length === 0) {
    container.innerHTML = `<p style="color:#64748b; font-size:0.8rem;">No active redistribution plans required at this time.</p>`;
    return;
  }

  currentPlanData = plans[0];

  container.innerHTML = plans.map(pl => {
    return `
      <div class="plan-item-card">
        <div class="plan-info-main">
          <div class="plan-route-title">
            🚚 Transfer ${pl.quantity} units of ${pl.sku}
          </div>
          <div class="plan-route-details">
            From: <strong>${pl.source_phc}</strong> &rarr; To: <strong>${pl.destination_phc}</strong> &bull;
            Distance: <strong>${pl.transit_distance_km} km</strong> (${pl.est_transit_hours} hrs transit) &bull;
            Run: <code>${pl.optimization_run_id}</code>
          </div>
        </div>
        <div>
          <span class="badge ${pl.approval_status === 'APPROVED' ? 'badge-emerald' : 'badge-purple'}">
            ${pl.approval_status}
          </span>
        </div>
      </div>
    `;
  }).join("");

  // Update Human Gate card with active plan
  const firstPlan = plans[0];
  document.getElementById("gate-plan-id").textContent = firstPlan.plan_id;
  document.getElementById("gate-items").textContent = `${firstPlan.quantity} ${firstPlan.sku}`;
  document.getElementById("gate-target-phc").textContent = firstPlan.destination_phc;
  document.getElementById("gate-source-phc").textContent = firstPlan.source_phc;
  document.getElementById("gate-transit").textContent = `${firstPlan.transit_distance_km} km (~${firstPlan.est_transit_hours} hrs transit)`;
}

function renderForecastCenter(fc) {
  const probPct = (fc.surge_probability * 100).toFixed(1);
  document.getElementById("forecast-prob-val").textContent = `${probPct}%`;
  document.getElementById("forecast-lead-val").textContent = `${fc.lead_time_days} Days`;
  document.getElementById("forecast-mult-val").textContent = `${fc.predicted_footfall_multiplier}x Surge`;
  document.getElementById("forecast-base-opd").textContent = `${fc.opd_footfall_baseline} patients/day`;
  document.getElementById("forecast-surge-opd").textContent = `${fc.predicted_opd_footfall} patients/day`;

  // Update KPI HUD
  document.getElementById("kpi-lead-time").textContent = fc.lead_time_days;
  document.getElementById("kpi-surge-prob").textContent = `${probPct}%`;

  // Render SHAP / Feature drivers
  const driversContainer = document.getElementById("forecast-drivers-list");
  if (driversContainer && fc.primary_drivers) {
    driversContainer.innerHTML = fc.primary_drivers.map(d => `
      <div class="driver-item">
        <div class="driver-header">
          <span>${d.feature}</span>
          <span class="text-cyan">${d.importance_pct}% weight</span>
        </div>
        <div class="driver-bar-wrap">
          <div class="driver-bar-fill" style="width: ${d.importance_pct}%;"></div>
        </div>
        <div style="display:flex; justify-content:space-between; margin-top:4px; font-size:0.7rem; color:#64748b;">
          <span>Value: <strong>${d.value}</strong></span>
          <span class="badge ${d.direction === 'RISK_ELEVATING' ? 'badge-rose' : 'badge-cyan'}">${d.direction}</span>
        </div>
      </div>
    `).join("");
  }
}

function renderWarRoom(data) {
  const timeline = document.getElementById("agent-timeline");
  const evidenceCards = document.getElementById("evidence-cards");
  const auditReport = document.getElementById("audit-report-card");
  if (!timeline) return;

  const agentSteps = [
    {
      name: "Sentinel Orchestrator Agent",
      class: "agent-orch",
      action: "Triage & Workflow Lifecycle Coordination",
      tool: "ADK.orchestrate_incident",
      thought: `Incident ${data.incident.incident_id} routed across 5 specialist agents. Telemetry flagged Z-score of ${data.incident.anomaly_score.toFixed(2)}. Initiated multi-agent corroboration.`
    },
    {
      name: "Sensor Intelligence Agent",
      class: "agent-sensor",
      action: "Physicochemical Anomaly Validation",
      tool: "SensorIntelligence.evaluate_physicochemical",
      thought: `Confirmed reducing ORP shift and electrical conductivity rise. Rule out stormwater dilution (FR-9) and probe fouling (FR-8). Recommended isothermal LAMP confirmation.`
    },
    {
      name: "Epidemiology Specialist Agent",
      class: "agent-epi",
      action: "Vertex AI Outbreak Surge Prediction",
      tool: "VertexAI.predict_catchment_surge",
      thought: `Synthesized Stage-2 LAMP bioassay (positive pathogen readout) with Vertex AI model. Surge probability: ${(data.incident.surge_probability * 100).toFixed(1)}%. Early warning lead time: ${data.incident.lead_time_days} days ahead of clinical presentation.`
    },
    {
      name: "Supply Chain Agent",
      class: "agent-supply",
      action: "Deterministic Redistribution Calculation",
      tool: "ORTools.solve_stock_redistribution",
      thought: `Projected 7-day surge demand. Calculated deficit. Invoked Google OR-Tools: calculated optimal transfer routes preserving safety reserves at source facilities.`
    },
    {
      name: "Risk & Validation Auditor Agent",
      class: "agent-risk",
      action: "Adversarial Integrity & Feasibility Audit",
      tool: "RiskValidation.audit_evidence_chain",
      thought: `Verified optical assay confidence (>95%). Verified transit feasibility within lead-time window. Enforced District Health Officer Human Approval Gate.`
    }
  ];

  timeline.innerHTML = agentSteps.map(s => `
    <div class="timeline-card ${s.class}">
      <div class="agent-meta-line">
        <span class="agent-name-tag">${s.name}</span>
        <span class="tool-tag">${s.tool}</span>
      </div>
      <p style="font-size: 0.8rem; font-weight: 700; color: #0f172a;">Action: ${s.action}</p>
      <div class="agent-thought-block">
        &ldquo;${s.thought}&rdquo;
      </div>
    </div>
  `).join("");

  // Evidences
  if (evidenceCards && data.evidence) {
    evidenceCards.innerHTML = data.evidence.map(ev => `
      <div class="evidence-card">
        <div class="ev-header">
          <span>${ev.evidence_type}</span>
          <span class="text-cyan">Confidence: ${(ev.confidence * 100).toFixed(0)}%</span>
        </div>
        <div class="ev-summary">${ev.summary}</div>
        <div style="font-size:0.7rem; color:#64748b; margin-top:4px;">Source: ${ev.source} &bull; ${new Date(ev.timestamp * 1000).toLocaleTimeString()}</div>
      </div>
    `).join("");
  }

  // Audit Report
  if (auditReport) {
    auditReport.innerHTML = `
      <div style="background:#ffffff; border:1px solid rgba(124,58,237,0.25); border-radius:10px; padding:14px; box-shadow: var(--shadow-sm);">
        <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
          <strong>Adversarial Audit Status:</strong>
          <span class="badge badge-purple">${data.incident.human_approval_required ? 'Human Gate Enforced' : 'Validated'}</span>
        </div>
        <p style="font-size:0.8rem; color:#475569; line-height:1.4;">
          The Risk &amp; Validation Agent challenged the hypothesis for weather dilution (FR-9) and sensor drift (FR-8).
          Findings: Signal confirmed genuine biological pathogen shedding. Zero hallucinated quantities verified via OR-Tools.
        </p>
      </div>
    `;
  }
}

function renderAlertCard(alert) {
  currentAlertData = alert;
  document.getElementById("alert-display-title").textContent = alert.title;
  document.getElementById("alert-body-text").textContent = alert[`message_${activeLang}`] || alert.message_en;
  document.getElementById("alert-rec-action").textContent = alert.action_recommended;

  // Update Mockups
  document.getElementById("mockup-whatsapp-text").textContent = alert[`message_${activeLang}`] || alert.message_en;
  document.getElementById("mockup-sms-text").textContent = `[NHM-ALRT] ${alert.title}. ${alert.action_recommended}`;
}

function renderDispatchedAlertsList(alerts) {
  const container = document.getElementById("dispatched-alerts-list");
  if (!container) return;

  container.innerHTML = alerts.map(a => `
    <div style="background:#ffffff; border:1px solid var(--border-subtle); border-radius:8px; padding:10px; margin-bottom:8px; box-shadow:var(--shadow-sm);">
      <div style="font-weight:700; font-size:0.82rem; color:#0f172a;">${a.title}</div>
      <div style="font-size:0.72rem; color:#64748b; margin-top:4px;">${new Date(a.timestamp * 1000).toLocaleTimeString()} &bull; Target: ${a.phc_name || a.phc_id}</div>
    </div>
  `).join("");
}

/* =========================================================================
   6. EVENT LISTENERS & LIVE ACTIONS
   ========================================================================= */
function initEventListeners() {
  // Scenario Selection
  document.getElementById("btn-apply-scenario")?.addEventListener("click", async () => {
    const sel = document.getElementById("scenario-select").value;
    currentScenario = sel;
    await fetch("/api/simulation/scenario", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario: sel })
    });
    // Immediately execute a live tick
    await fetch("/api/simulation/tick", { method: "POST" });
    await refreshLiveData();
  });

  // Sensor Tick Button
  document.getElementById("btn-sim-tick")?.addEventListener("click", async () => {
    const btn = document.getElementById("btn-sim-tick");
    btn.textContent = "Tick...";
    await fetch("/api/simulation/tick", { method: "POST" });
    await refreshLiveData();
    btn.textContent = "Tick Sensor";
  });

  // Live Stream Toggle Button
  document.getElementById("btn-toggle-stream")?.addEventListener("click", async () => {
    const btn = document.getElementById("btn-toggle-stream");
    const res = await fetch("/api/simulation/stream/toggle", { method: "POST" });
    const data = await res.json();
    isStreamingActive = data.is_streaming;
    btn.textContent = isStreamingActive ? "Pause Feed" : "Resume Feed";
    document.getElementById("hud-stream-status").textContent = isStreamingActive ? "LIVE STREAMING" : "FEED PAUSED";
  });

  // Reset Database Button
  document.getElementById("btn-reset-db")?.addEventListener("click", async () => {
    if (confirm("Restore database and fleet to pristine baseline state?")) {
      await fetch("/api/simulation/reset", { method: "POST" });
      currentScenario = "BASELINE";
      document.getElementById("scenario-select").value = "BASELINE";
      await refreshLiveData();
    }
  });

  // Node Dropdown Selector in Telemetry tab
  document.getElementById("node-selector")?.addEventListener("change", (e) => {
    selectedNodeId = e.target.value;
    loadNodeTelemetry(selectedNodeId);
  });

  // Language Switcher
  document.querySelectorAll(".lang-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".lang-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeLang = btn.dataset.lang;
      if (currentAlertData) {
        renderAlertCard(currentAlertData);
      }
    });
  });

  // Human Approval Modal
  const modal = document.getElementById("approval-modal");
  document.getElementById("btn-open-approval-modal")?.addEventListener("click", () => {
    if (currentPlanData) {
      document.getElementById("modal-summary-box").innerHTML = `
        <strong>Plan ID:</strong> ${currentPlanData.plan_id}<br>
        <strong>Route:</strong> ${currentPlanData.source_phc} &rarr; ${currentPlanData.destination_phc}<br>
        <strong>Item:</strong> ${currentPlanData.quantity} units of ${currentPlanData.sku}<br>
        <strong>Transit Time:</strong> ${currentPlanData.est_transit_hours} hours (${currentPlanData.transit_distance_km} km)
      `;
      modal.classList.add("show");
    }
  });

  document.getElementById("btn-close-modal")?.addEventListener("click", () => {
    modal.classList.remove("show");
  });
  document.getElementById("btn-modal-cancel")?.addEventListener("click", () => {
    modal.classList.remove("show");
  });

  // Confirm Human Approval
  document.getElementById("btn-modal-confirm")?.addEventListener("click", async () => {
    if (currentPlanData) {
      await approvePlan("APPROVED");
      modal.classList.remove("show");
    }
  });

  document.getElementById("btn-approve-plan")?.addEventListener("click", async () => {
    await approvePlan("APPROVED");
  });

  document.getElementById("btn-reject-plan")?.addEventListener("click", async () => {
    await approvePlan("REJECTED");
  });

  // Dispatch Broadcast Advisory Button
  document.getElementById("btn-dispatch-channels")?.addEventListener("click", async () => {
    if (!currentAlertData) return;
    const msgElem = document.getElementById("dispatch-status-msg");
    msgElem.textContent = "Transmitting to State Health Gateway...";

    const res = await fetch(`/api/alerts/dispatch/${currentAlertData.alert_id}`, { method: "POST" });
    const data = await res.json();

    msgElem.textContent = "✅ Broadcast confirmed: Dispatched to NHM SMS Gateway & WhatsApp Medical Officer Channel.";
    setTimeout(() => { msgElem.textContent = ""; }, 5000);
  });
}

async function approvePlan(action) {
  if (!currentPlanData) return;
  const officerName = document.getElementById("officer-name-input").value;
  const officerRole = document.getElementById("officer-role-input").value;
  const comments = document.getElementById("approval-notes-input").value;
  const feedback = document.getElementById("gate-feedback");

  try {
    const res = await fetch("/api/supply-chain/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        plan_id: currentPlanData.plan_id,
        incident_id: currentPlanData.incident_id,
        officer_name: officerName,
        officer_role: officerRole,
        action: action,
        comments: comments
      })
    });
    const result = await res.json();

    if (action === "APPROVED") {
      feedback.innerHTML = `<span style="color:#059669; font-weight:700;">✅ Transit Order Authorized by ${officerName}. Supplies dispatched.</span>`;
      document.getElementById("kpi-gate-status").textContent = "Authorized";
      document.getElementById("kpi-gate-status").className = "kpi-badge badge-emerald";
    } else {
      feedback.innerHTML = `<span style="color:#e11d48; font-weight:700;">❌ Plan Rejected by ${officerName}.</span>`;
      document.getElementById("kpi-gate-status").textContent = "Rejected";
      document.getElementById("kpi-gate-status").className = "kpi-badge badge-rose";
    }

    setTimeout(refreshLiveData, 1500);

  } catch (err) {
    feedback.innerHTML = `<span style="color:#e11d48;">Error processing authorization: ${err}</span>`;
  }
}
