"""
Sentinel Drain - Supply Chain Agent
Specialist Agent evaluating PHC inventory depletion under forecasted demand surge,
and invoking Google OR-Tools to calculate deterministic, feasible cross-district stock redistribution.
"""

import math
from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent
from ..optimization.ortools_allocator import ortools_optimizer

class SupplyChainAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="SupplyChainAgent",
            role_description="Evaluates stock depletion against epidemiological surge forecasts and computes optimal redistribution via Google OR-Tools."
        )

    def evaluate_and_optimize(
        self,
        incident_id: str,
        phc_info: Dict[str, Any],
        forecast_result: Dict[str, Any],
        phc_network: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculates inventory deficit and runs OR-Tools deterministic solver.
        """
        phc_id = phc_info["phc_id"]
        phc_name = phc_info["phc_name"]
        surge_prob = forecast_result.get("surge_probability", 0.0)
        lead_time = forecast_result.get("lead_time_days", 4.0)
        multiplier = forecast_result.get("predicted_footfall_multiplier", 1.0)
        daily_baseline = phc_info.get("opd_footfall_daily", 85)

        # 1. Project Consumption over a 7-day surge horizon
        daily_surge_patients = daily_baseline * multiplier
        excess_patients_per_day = max(0, daily_surge_patients - daily_baseline)
        surge_horizon_days = 7

        # Standard WHO / NHM treatment guidelines for acute watery diarrhea surge
        ors_per_patient = 3.5      # 3-4 packets per patient
        iv_per_patient = 0.55      # ~55% severe dehydration requiring IV RL / Saline
        abx_per_patient = 0.35     # ~35% requiring Azithromycin / Ciprofloxacin

        needed_ors_7d = int(daily_surge_patients * ors_per_patient * surge_horizon_days)
        needed_iv_7d = int(daily_surge_patients * iv_per_patient * surge_horizon_days)

        current_ors = phc_info.get("stock_ors", 0)
        current_iv = phc_info.get("stock_iv_fluids", 0)

        # Deficit calculation
        deficit_ors = max(0, needed_ors_7d - current_ors)
        deficit_iv = max(0, needed_iv_7d - current_iv)

        # Days of inventory remaining at surge rate
        daily_ors_burn = daily_surge_patients * ors_per_patient
        days_to_ors_stockout = round(current_ors / max(1.0, daily_ors_burn), 1)

        daily_iv_burn = daily_surge_patients * iv_per_patient
        days_to_iv_stockout = round(current_iv / max(1.0, daily_iv_burn), 1)

        is_stockout_imminent = (days_to_ors_stockout <= lead_time + 1.5 or days_to_iv_stockout <= lead_time + 1.5)

        optimization_results = []
        transfers_all = []

        if is_stockout_imminent and deficit_ors > 0:
            # Call Deterministic OR-Tools Solver for ORS
            ors_solution = ortools_optimizer.solve_stock_redistribution(
                deficit_phc_id=phc_id,
                sku="ORS Packets",
                required_quantity=deficit_ors,
                phc_network=phc_network,
                safety_stock_ratio=0.35
            )
            optimization_results.append(ors_solution)
            transfers_all.extend(ors_solution.get("transfers", []))

        if is_stockout_imminent and deficit_iv > 0:
            # Call Deterministic OR-Tools Solver for IV Fluids
            iv_solution = ortools_optimizer.solve_stock_redistribution(
                deficit_phc_id=phc_id,
                sku="IV Fluids (Ringer's Lactate)",
                required_quantity=deficit_iv,
                phc_network=phc_network,
                safety_stock_ratio=0.35
            )
            optimization_results.append(iv_solution)
            transfers_all.extend(iv_solution.get("transfers", []))

        # Build Explainable Rationale
        explanation_lines = [
            f"Supply Chain Risk Assessment for {phc_name} ({phc_id}):",
            f"- Projected surge footfall: {int(daily_surge_patients)} patients/day (normal: {daily_baseline}).",
            f"- ORS stock status: {current_ors} on hand. At surge velocity, stockout will occur in {days_to_ors_stockout} days.",
            f"- IV Fluid status: {current_iv} units on hand. Stockout in {days_to_iv_stockout} days.",
            f"- Early-warning lead time window of {lead_time} days allows pre-positioning before clinical presentations spike."
        ]

        if transfers_all:
            explanation_lines.append(f"- Invoked Google OR-Tools optimization (Run ID: {optimization_results[0].get('run_id')}):")
            for t in transfers_all:
                explanation_lines.append(
                    f"  * Transfer {t['quantity']} units of {t['sku']} from {t['source_phc_name']} "
                    f"({t['distance_km']} km away, est. {t['est_transit_hours']} hrs transit). "
                    f"Source safety stock preserved ({t['source_stock_after']} units remain)."
                )
        else:
            explanation_lines.append("- Current inventory buffer is adequate; no emergency transfer required at this time.")

        rationale = "\n".join(explanation_lines)

        evidence = self.create_evidence(
            incident_id=incident_id,
            evidence_type="SUPPLY_CHAIN_OPTIMIZATION",
            source="ORTools/LinearSolver",
            summary=f"Imminent Stockout Flag: {'CRITICAL' if is_stockout_imminent else 'NOMINAL'}",
            data={
                "days_to_ors_stockout": days_to_ors_stockout,
                "days_to_iv_stockout": days_to_iv_stockout,
                "deficit_ors": deficit_ors,
                "deficit_iv": deficit_iv,
                "is_stockout_imminent": is_stockout_imminent,
                "transfers": transfers_all
            },
            confidence=0.96
        )

        action = self.log_action(
            incident_id=incident_id,
            action_type="OR_TOOLS_OPTIMIZATION",
            tool_called="ORTools.solve_stock_redistribution",
            input_params={"deficit_phc": phc_id, "deficit_ors": deficit_ors, "deficit_iv": deficit_iv},
            output_result={"total_transfers": len(transfers_all), "optimization_runs": len(optimization_results)}
        )

        return {
            "is_stockout_imminent": is_stockout_imminent,
            "days_to_ors_stockout": days_to_ors_stockout,
            "days_to_iv_stockout": days_to_iv_stockout,
            "deficit_ors": deficit_ors,
            "deficit_iv": deficit_iv,
            "transfers": transfers_all,
            "optimization_runs": optimization_results,
            "rationale": rationale,
            "evidence": evidence,
            "action": action
        }
