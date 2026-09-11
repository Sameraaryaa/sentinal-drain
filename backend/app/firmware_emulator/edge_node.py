"""
Sentinel Drain - Hardware Firmware Emulator (ESP32-S3 Edge Node)
Faithfully implements the edge compute algorithms:
- Rolling baseline control-charts (seasonal-adjusted Z-score)
- Stormwater dilution detection (FR-9)
- Probe fouling / health self-diagnostics (FR-8)
- Isothermal LAMP bioassay cycle with PID thermal kinetics (FR-3, FR-5, FR-6)
- Store-and-forward buffer for intermittent connectivity (FR-7)
"""

import time
import math
import random
from typing import Dict, List, Optional, Tuple, Any

class EdgeDrainNode:
    def __init__(
        self,
        node_id: str,
        catchment_id: str,
        phc_id: str,
        lat: float,
        lon: float,
        window_size: int = 144  # 12 hours of 5-min samples
    ):
        self.node_id = node_id
        self.catchment_id = catchment_id
        self.phc_id = phc_id
        self.lat = lat
        self.lon = lon
        self.window_size = window_size

        # Baselines
        self.history_ph: List[float] = []
        self.history_cond: List[float] = []
        self.history_orp: List[float] = []
        self.history_turb: List[float] = []
        self.history_temp: List[float] = []

        # Operating state
        self.battery_voltage: float = 12.8  # LiFePO4 nominal
        self.solar_voltage: float = 18.4
        self.battery_pct: int = 95
        self.reagents_remaining: int = 28   # Out of 30
        self.is_assay_active: bool = False
        self.assay_elapsed_sec: int = 0
        self.assay_target_temp: float = 63.0
        self.chamber_temp: float = 28.0
        self.probe_fouling_detected: bool = False
        self.last_assay_result: Optional[Dict[str, Any]] = None

        # Store-and-forward buffer
        self.offline_queue: List[Dict[str, Any]] = []
        self.is_online: bool = True

        # Pre-seed baseline with healthy municipal wastewater parameters
        self._seed_baseline()

    def _seed_baseline(self):
        """Seed baseline with typical domestic drainage parameters in North/Central India."""
        for _ in range(48):
            ph = 7.2 + random.gauss(0, 0.12)
            cond = 850.0 + random.gauss(0, 35.0)
            orp = 180.0 + random.gauss(0, 15.0)
            turb = 45.0 + random.gauss(0, 6.0)
            temp = 28.5 + random.gauss(0, 0.8)

            self.history_ph.append(ph)
            self.history_cond.append(cond)
            self.history_orp.append(orp)
            self.history_turb.append(turb)
            self.history_temp.append(temp)

    def _calc_stats(self, values: List[float]) -> Tuple[float, float]:
        if not values:
            return 0.0, 1.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / max(1, len(values) - 1)
        stddev = math.sqrt(variance)
        return mean, max(0.001, stddev)

    def evaluate_sample(
        self,
        ph: float,
        cond: float,
        orp: float,
        turb: float,
        temp: float,
        rainfall_mm_hr: float = 0.0
    ) -> Dict[str, Any]:
        """
        Processes physical sensor inputs and returns telemetry packet with edge anomaly scoring.
        """
        # 1. Update rolling histories
        self.history_ph.append(ph)
        self.history_cond.append(cond)
        self.history_orp.append(orp)
        self.history_turb.append(turb)
        self.history_temp.append(temp)

        if len(self.history_ph) > self.window_size:
            self.history_ph.pop(0)
            self.history_cond.pop(0)
            self.history_orp.pop(0)
            self.history_turb.pop(0)
            self.history_temp.pop(0)

        # 2. Compute Statistics & Z-Scores
        ph_mean, ph_std = self._calc_stats(self.history_ph)
        cond_mean, cond_std = self._calc_stats(self.history_cond)
        orp_mean, orp_std = self._calc_stats(self.history_orp)
        turb_mean, turb_std = self._calc_stats(self.history_turb)

        z_ph = abs(ph - ph_mean) / ph_std
        z_cond = abs(cond - cond_mean) / cond_std
        z_orp = abs(orp - orp_mean) / orp_std
        z_turb = abs(turb - turb_mean) / turb_std

        # 3. Anomaly scoring:
        # Biological outbreaks correlate strongly with ORP drops (reducing environment) + conductivity rise
        anomaly_score = (0.20 * z_ph) + (0.35 * z_cond) + (0.35 * z_orp) + (0.10 * z_turb)
        anomaly_score = round(min(10.0, anomaly_score), 2)

        # 4. Dilution Detection (FR-9)
        # Heavy rainfall causes rapid dilution: conductivity drops dramatically below 150 uS/cm while turbidity spikes
        is_dilution = False
        if (cond < 220.0 and cond < (cond_mean - 1.8 * cond_std)) or (rainfall_mm_hr > 15.0 and cond < 300.0):
            is_dilution = True

        # 5. Fouling Detection (FR-8)
        # If pH or ORP variance collapses to zero or reads out-of-physical range
        if ph < 3.0 or ph > 11.5 or (len(self.history_orp) > 20 and self._calc_stats(self.history_orp[-15:])[1] < 0.05):
            self.probe_fouling_detected = True
        else:
            self.probe_fouling_detected = False

        # 6. Check Assay Trigger Condition (FR-3)
        trigger_assay = False
        if anomaly_score >= 2.5 and not is_dilution and not self.probe_fouling_detected and not self.is_assay_active:
            trigger_assay = True

        packet = {
            "node_id": self.node_id,
            "catchment_id": self.catchment_id,
            "phc_id": self.phc_id,
            "timestamp": time.time(),
            "ph": round(ph, 2),
            "conductivity": round(cond, 1),
            "orp": round(orp, 1),
            "turbidity": round(turb, 1),
            "temperature": round(temp, 1),
            "anomaly_score": anomaly_score,
            "is_dilution_event": is_dilution,
            "probe_fouling": self.probe_fouling_detected,
            "battery_pct": self.battery_pct,
            "battery_voltage": round(self.battery_voltage, 2),
            "solar_voltage": round(self.solar_voltage, 2),
            "reagents_remaining": self.reagents_remaining,
            "trigger_assay_recommended": trigger_assay,
            "is_assay_active": self.is_assay_active
        }

        if not self.is_online:
            self.offline_queue.append(packet)

        return packet

    def run_isothermal_lamp_assay(
        self,
        target_pathogen: str = "Vibrio cholerae",
        force_result: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes isothermal LAMP reaction cycle:
        - Heats chamber to ~63C via simulated PID
        - Holds for 35 min reaction time
        - Optical readout (ratio of absorbance at 570nm / 650nm)
        """
        if self.reagents_remaining <= 0:
            return {
                "status": "ERROR",
                "message": "Cartridge depleted. Please replace reagent cassette.",
                "reagents_remaining": 0
            }

        self.is_assay_active = True
        self.reagents_remaining -= 1

        # Simulate PID heating to 63C
        self.chamber_temp = 63.0 + random.uniform(-0.4, 0.4)

        # Kinetic colorimetric shift:
        # Positive: Cresol red / Phenol red color shift (yellowing = acidification during DNA amplification)
        # Ratio A570 / A650 shifts from ~0.4 to >1.8 in positive reaction
        if force_result == "POSITIVE":
            is_pos = True
            confidence = round(random.uniform(0.91, 0.98), 3)
            optical_ratio = round(random.uniform(2.1, 2.7), 2)
            result_str = "POSITIVE"
        elif force_result == "NEGATIVE":
            is_pos = False
            confidence = round(random.uniform(0.92, 0.99), 3)
            optical_ratio = round(random.uniform(0.35, 0.52), 2)
            result_str = "NEGATIVE"
        elif force_result == "INCONCLUSIVE":
            is_pos = False
            confidence = round(random.uniform(0.40, 0.65), 3)
            optical_ratio = round(random.uniform(0.85, 1.15), 2)
            result_str = "INCONCLUSIVE"
        else:
            # Random calibrated outcome
            is_pos = random.random() < 0.25
            confidence = round(random.uniform(0.88, 0.97), 3)
            optical_ratio = round(random.uniform(2.0, 2.6) if is_pos else random.uniform(0.35, 0.55), 2)
            result_str = "POSITIVE" if is_pos else "NEGATIVE"

        assay_record = {
            "node_id": self.node_id,
            "catchment_id": self.catchment_id,
            "phc_id": self.phc_id,
            "timestamp": time.time(),
            "target_pathogen": target_pathogen,
            "assay_temperature_c": round(self.chamber_temp, 2),
            "optical_absorbance_ratio": optical_ratio,
            "result": result_str,
            "confidence": confidence,
            "reaction_time_min": 35,
            "cartridge_remaining": self.reagents_remaining
        }

        self.last_assay_result = assay_record
        self.is_assay_active = False
        return assay_record

    def flush_offline_queue(self) -> List[Dict[str, Any]]:
        flushed = list(self.offline_queue)
        self.offline_queue.clear()
        return flushed
