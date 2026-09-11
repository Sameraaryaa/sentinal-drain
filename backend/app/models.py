"""
Sentinel Drain - Pydantic Data Models
Defines schema structures for telemetry ingestion, forecasts,
agent events, OR-Tools optimization, and human approvals.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class Stage1ReadingModel(BaseModel):
    node_id: str
    catchment_id: str
    phc_id: str
    timestamp: float
    ph: float
    conductivity: float
    orp: float
    turbidity: float
    temperature: float
    anomaly_score: float
    is_dilution_event: bool = False
    probe_fouling: bool = False
    battery_pct: int = 100
    battery_voltage: float = 12.8
    solar_voltage: float = 18.0
    reagents_remaining: int = 30
    trigger_assay_recommended: bool = False
    is_assay_active: bool = False

class Stage2AssayModel(BaseModel):
    node_id: str
    catchment_id: str
    phc_id: str
    timestamp: float
    target_pathogen: str
    assay_temperature_c: float
    optical_absorbance_ratio: float
    result: str  # POSITIVE, NEGATIVE, INCONCLUSIVE
    confidence: float
    reaction_time_min: int = 35
    cartridge_remaining: int = 25

class ScenarioTriggerRequest(BaseModel):
    scenario: str = Field(..., description="BASELINE, OUTBREAK_CHOLERA, MONSOON_DILUTION, PROBE_FOULING, OUTBREAK_ROTAVIRUS")
    target_node: Optional[str] = None
    target_catchment: Optional[str] = None

class ForecastRequest(BaseModel):
    catchment_id: str
    target_pathogen: Optional[str] = "Vibrio cholerae"

class ForecastResponse(BaseModel):
    catchment_id: str
    phc_id: str
    timestamp: float
    surge_probability: float
    lead_time_days: float
    predicted_footfall_multiplier: float
    confidence: float
    model_version: str
    primary_drivers: List[Dict[str, Any]]
    opd_footfall_baseline: int
    predicted_opd_footfall: int

class RedistributionRequest(BaseModel):
    incident_id: str
    deficit_phc: str
    sku: str
    required_quantity: int

class HumanApprovalRequest(BaseModel):
    plan_id: str
    incident_id: str
    officer_name: str
    officer_role: str
    action: str  # APPROVED, REJECTED, MODIFIED
    comments: Optional[str] = None
    modified_quantity: Optional[int] = None
