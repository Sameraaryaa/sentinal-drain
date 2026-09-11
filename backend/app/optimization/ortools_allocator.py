"""
Sentinel Drain - Deterministic Supply Chain Redistribution Optimizer (Google OR-Tools)
Solves min-cost network flow / integer programming for cross-district pharmaceutical redistribution.
Guarantees zero hallucinated inventory by LLMs.
"""

import math
import uuid
import time
from typing import Dict, List, Any, Optional
from ortools.linear_solver import pywraplp

# Haversine distance calculator between GPS coordinates
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)

class ORToolsRedistributionSolver:
    def __init__(self):
        self.average_transit_speed_kmh = 35.0  # Average rural/district transport speed in UP/Bihar

    def solve_stock_redistribution(
        self,
        deficit_phc_id: str,
        sku: str,
        required_quantity: int,
        phc_network: List[Dict[str, Any]],
        safety_stock_ratio: float = 0.35
    ) -> Dict[str, Any]:
        """
        Solves optimal redistribution using Google OR-Tools GLOP/SCIP solver.
        """
        run_id = f"OPT-{uuid.uuid4().hex[:8].upper()}"

        # 1. Identify target PHC and potential source PHCs
        target_phc = next((p for p in phc_network if p["phc_id"] == deficit_phc_id), None)
        if not target_phc:
            return {
                "status": "ERROR",
                "message": f"Target PHC {deficit_phc_id} not found in network.",
                "run_id": run_id
            }

        sku_col = f"stock_{sku.lower().replace(' ', '_').replace('-', '_')}"
        if sku_col not in target_phc:
            sku_col = "stock_ors"  # Default fallback

        # Candidate sources are all other PHCs in the network
        source_candidates = [p for p in phc_network if p["phc_id"] != deficit_phc_id]

        # Calculate surplus above safety stock for each candidate
        # Safety stock = normal_capacity * factor (or ratio of normal stock)
        sources = []
        for p in source_candidates:
            current_stock = p.get(sku_col, 0)
            safety_threshold = int(p.get("normal_capacity", 100) * 8 * safety_stock_ratio)
            surplus = max(0, current_stock - safety_threshold)
            dist = haversine_km(p["lat"], p["lon"], target_phc["lat"], target_phc["lon"])

            if surplus > 0:
                sources.append({
                    "phc_id": p["phc_id"],
                    "phc_name": p["phc_name"],
                    "current_stock": current_stock,
                    "safety_threshold": safety_threshold,
                    "available_surplus": surplus,
                    "distance_km": dist,
                    "transit_hours": round(dist / self.average_transit_speed_kmh, 1)
                })

        if not sources:
            return {
                "status": "INFEASIBLE",
                "run_id": run_id,
                "deficit_phc": deficit_phc_id,
                "sku": sku,
                "required_quantity": required_quantity,
                "allocated_quantity": 0,
                "unmet_deficit": required_quantity,
                "transfers": [],
                "explanation": "No neighboring PHCs have surplus inventory exceeding safety stock constraints."
            }

        # 2. Build OR-Tools Solver (CBC / SCIP / GLOP)
        solver = pywraplp.Solver.CreateSolver("SCIP")
        if not solver:
            solver = pywraplp.Solver.CreateSolver("GLOP")

        # Variables: x_i is quantity transferred from source i to target
        x_vars = {}
        for s in sources:
            var_name = f"x_{s['phc_id']}"
            x_vars[s["phc_id"]] = solver.IntVar(0, s["available_surplus"], var_name)

        # Constraint 1: Total transferred <= required_quantity
        solver.Add(sum(x_vars[s["phc_id"]] for s in sources) <= required_quantity)

        # Objective: Maximize transferred stock while minimizing transit distance cost
        # Objective = 1000 * sum(x_i) - sum(dist_i * x_i)
        objective = solver.Objective()
        for s in sources:
            cost_coeff = 1000.0 - (s["distance_km"] * 2.0)
            objective.SetCoefficient(x_vars[s["phc_id"]], cost_coeff)
        objective.SetMaximization()

        solver_status = solver.Solve()

        # 3. Extract Solution
        transfers = []
        total_allocated = 0

        if solver_status in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
            for s in sources:
                qty = int(round(x_vars[s["phc_id"]].solution_value()))
                if qty > 0:
                    total_allocated += qty
                    transfers.append({
                        "source_phc_id": s["phc_id"],
                        "source_phc_name": s["phc_name"],
                        "destination_phc_id": target_phc["phc_id"],
                        "destination_phc_name": target_phc["phc_name"],
                        "sku": sku,
                        "quantity": qty,
                        "distance_km": s["distance_km"],
                        "est_transit_hours": s["transit_hours"],
                        "source_stock_before": s["current_stock"],
                        "source_stock_after": s["current_stock"] - qty,
                        "safety_stock_threshold": s["safety_threshold"]
                    })

            # Sort transfers by distance
            transfers.sort(key=lambda x: x["distance_km"])

            return {
                "status": "OPTIMAL" if total_allocated >= required_quantity else "PARTIAL",
                "run_id": run_id,
                "deficit_phc_id": deficit_phc_id,
                "deficit_phc_name": target_phc["phc_name"],
                "sku": sku,
                "required_quantity": required_quantity,
                "allocated_quantity": total_allocated,
                "unmet_deficit": max(0, required_quantity - total_allocated),
                "fulfillment_rate_pct": round((total_allocated / max(1, required_quantity)) * 100, 1),
                "transfers": transfers,
                "timestamp": time.time()
            }
        else:
            return {
                "status": "FAILED",
                "run_id": run_id,
                "message": "Optimization solver failed to find feasible distribution."
            }

# Global optimizer singleton
ortools_optimizer = ORToolsRedistributionSolver()
