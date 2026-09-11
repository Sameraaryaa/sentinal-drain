"""
Sentinel Drain - Simulator Service
Coordinates fleet of edge drain nodes across 5 PHC catchments in the Gorakhpur health block.
Provides realistic streaming sensor telemetry and pre-packaged demonstration scenarios.
"""

import time
import random
from typing import Dict, List, Optional, Any
from .edge_node import EdgeDrainNode

class FleetSimulatorService:
    def __init__(self):
        self.nodes: Dict[str, EdgeDrainNode] = {}
        self.active_scenario: str = "BASELINE"
        self.scenario_start_time: float = time.time()
        self._init_fleet()

    def _init_fleet(self):
        # 5 PHCs in Gorakhpur pilot district
        node_configs = [
            # Catchment 1: Rampur PHC (High density peri-urban)
            {"node_id": "ND-RAM-01", "catchment": "CAT-RAMPUR", "phc": "PHC-RAMPUR", "lat": 26.7588, "lon": 83.3697},
            {"node_id": "ND-RAM-02", "catchment": "CAT-RAMPUR", "phc": "PHC-RAMPUR", "lat": 26.7610, "lon": 83.3750},
            {"node_id": "ND-RAM-03", "catchment": "CAT-RAMPUR", "phc": "PHC-RAMPUR", "lat": 26.7545, "lon": 83.3640},

            # Catchment 2: Sitapur PHC (Rural cluster)
            {"node_id": "ND-SIT-01", "catchment": "CAT-SITAPUR", "phc": "PHC-SITAPUR", "lat": 26.7820, "lon": 83.4100},
            {"node_id": "ND-SIT-02", "catchment": "CAT-SITAPUR", "phc": "PHC-SITAPUR", "lat": 26.7865, "lon": 83.4150},

            # Catchment 3: Bilaspur PHC (Well-stocked block PHC)
            {"node_id": "ND-BIL-01", "catchment": "CAT-BILASPUR", "phc": "PHC-BILASPUR", "lat": 26.7350, "lon": 83.3320},
            {"node_id": "ND-BIL-02", "catchment": "CAT-BILASPUR", "phc": "PHC-BILASPUR", "lat": 26.7390, "lon": 83.3380},

            # Catchment 4: Maharajganj Border PHC (Upstream drainage)
            {"node_id": "ND-MAH-01", "catchment": "CAT-MAHARAJ", "phc": "PHC-MAHARAJ", "lat": 26.8150, "lon": 83.3900},
            {"node_id": "ND-MAH-02", "catchment": "CAT-MAHARAJ", "phc": "PHC-MAHARAJ", "lat": 26.8190, "lon": 83.3950},

            # Catchment 5: Chauri Chaura PHC (Downstream delta)
            {"node_id": "ND-CHA-01", "catchment": "CAT-CHAURI", "phc": "PHC-CHAURI", "lat": 26.6850, "lon": 83.5850},
            {"node_id": "ND-CHA-02", "catchment": "CAT-CHAURI", "phc": "PHC-CHAURI", "lat": 26.6890, "lon": 83.5910},
        ]

        for cfg in node_configs:
            self.nodes[cfg["node_id"]] = EdgeDrainNode(
                node_id=cfg["node_id"],
                catchment_id=cfg["catchment"],
                phc_id=cfg["phc"],
                lat=cfg["lat"],
                lon=cfg["lon"]
            )

    def set_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """
        Switches current operating scenario:
        - 'BASELINE': Normal healthy baseline
        - 'OUTBREAK_CHOLERA': Sharp pathogen load in Catchment Rampur
        - 'MONSOON_DILUTION': Heavy rainfall, tests false alarm mitigation
        - 'PROBE_FOULING': Sensor fouling drift on ND-SIT-01
        - 'OUTBREAK_ROTAVIRUS': Rotavirus pediatric surge in Chauri Chaura
        """
        self.active_scenario = scenario_name.upper()
        self.scenario_start_time = time.time()
        return {
            "scenario": self.active_scenario,
            "message": f"Scenario switched to {self.active_scenario}",
            "timestamp": self.scenario_start_time
        }

    def generate_fleet_telemetry(self) -> List[Dict[str, Any]]:
        """Generates one round of Stage-1 telemetry for all nodes in the fleet based on scenario."""
        packets = []

        for node_id, node in self.nodes.items():
            # Default healthy baseline values
            ph = 7.20 + random.uniform(-0.10, 0.10)
            cond = 840.0 + random.uniform(-30.0, 30.0)
            orp = 185.0 + random.uniform(-10.0, 10.0)
            turb = 42.0 + random.uniform(-4.0, 4.0)
            temp = 28.5 + random.uniform(-0.4, 0.4)
            rain = 0.0

            # Apply Scenario Injections
            if self.active_scenario == "OUTBREAK_CHOLERA" and node.catchment_id == "CAT-RAMPUR":
                # Pre-symptomatic Vibrio shedding produces:
                # - ORP collapse to reducing state (from +185 mV down to +45 mV or lower)
                # - Conductivity elevation (electrolyte shedding from diarrhea up to 1350 uS/cm)
                # - Slight pH acidification (down to 6.45)
                # - Turbidity elevation (organic matter)
                orp = 55.0 + random.uniform(-8.0, 8.0)
                cond = 1320.0 + random.uniform(-40.0, 40.0)
                ph = 6.48 + random.uniform(-0.06, 0.06)
                turb = 95.0 + random.uniform(-8.0, 8.0)

            elif self.active_scenario == "MONSOON_DILUTION":
                # Heavy monsoon cloudburst across district:
                # - Conductivity plummets due to rainwater dilution (<180 uS/cm)
                # - Turbidity skyrockets due to mud/road runoff (>550 NTU)
                # - ORP remains neutral
                rain = 35.0 + random.uniform(-5.0, 5.0)
                cond = 165.0 + random.uniform(-20.0, 20.0)
                turb = 620.0 + random.uniform(-40.0, 40.0)
                ph = 6.95 + random.uniform(-0.15, 0.15)
                orp = 175.0 + random.uniform(-12.0, 12.0)

            elif self.active_scenario == "PROBE_FOULING" and node_id == "ND-SIT-01":
                # Glass membrane bio-fouling causing frozen flatline and out-of-spec pH
                ph = 2.45
                orp = 450.0
                cond = 810.0

            elif self.active_scenario == "OUTBREAK_ROTAVIRUS" and node.catchment_id == "CAT-CHAURI":
                # Pediatric rotavirus surge
                orp = 75.0 + random.uniform(-10.0, 10.0)
                cond = 1180.0 + random.uniform(-35.0, 35.0)
                ph = 6.62 + random.uniform(-0.08, 0.08)
                turb = 82.0 + random.uniform(-6.0, 6.0)

            pkt = node.evaluate_sample(
                ph=ph,
                cond=cond,
                orp=orp,
                turb=turb,
                temp=temp,
                rainfall_mm_hr=rain
            )
            packets.append(pkt)

        return packets

    def trigger_node_assay(
        self,
        node_id: str,
        target_pathogen: Optional[str] = None,
        force_result: Optional[str] = None
    ) -> Dict[str, Any]:
        """Manually or automatically trigger an isothermal LAMP bioassay on a node."""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found in fleet.")

        node = self.nodes[node_id]

        if target_pathogen is None:
            if "ROTAVIRUS" in self.active_scenario:
                target_pathogen = "Rotavirus Group A"
            else:
                target_pathogen = "Vibrio cholerae O1/O139"

        # Determine result based on scenario if not forced
        if force_result is None:
            if self.active_scenario == "OUTBREAK_CHOLERA" and node.catchment_id == "CAT-RAMPUR":
                force_result = "POSITIVE"
            elif self.active_scenario == "OUTBREAK_ROTAVIRUS" and node.catchment_id == "CAT-CHAURI":
                force_result = "POSITIVE"
            elif self.active_scenario == "MONSOON_DILUTION":
                force_result = "NEGATIVE"
            elif self.active_scenario == "PROBE_FOULING":
                force_result = "INCONCLUSIVE"
            else:
                force_result = "NEGATIVE"

        return node.run_isothermal_lamp_assay(
            target_pathogen=target_pathogen,
            force_result=force_result
        )

# Global fleet simulator singleton
fleet_simulator = FleetSimulatorService()
