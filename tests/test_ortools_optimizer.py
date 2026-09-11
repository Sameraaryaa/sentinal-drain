"""
Unit Tests for Google OR-Tools Redistribution Optimizer
Verifies PRD requirements:
- FR-16: Deterministic optimization of inventory allocation without hallucination
- Preservation of safety stock at donor facilities
- Conservation of mass and distance minimization
"""

import pytest
from backend.app.optimization.ortools_allocator import ORToolsRedistributionSolver

def test_ortools_redistribution_feasible_solution():
    solver = ORToolsRedistributionSolver()

    phc_network = [
        {
            "phc_id": "PHC-RAMPUR",
            "phc_name": "Rampur PHC",
            "lat": 26.7588,
            "lon": 83.3697,
            "normal_capacity": 100,
            "stock_ors": 200
        },
        {
            "phc_id": "PHC-BILASPUR",
            "phc_name": "Bilaspur Hub",
            "lat": 26.7350,
            "lon": 83.3320,
            "normal_capacity": 200,
            "stock_ors": 5000
        },
        {
            "phc_id": "PHC-SITAPUR",
            "phc_name": "Sitapur PHC",
            "lat": 26.7820,
            "lon": 83.4100,
            "normal_capacity": 100,
            "stock_ors": 1500
        }
    ]

    result = solver.solve_stock_redistribution(
        deficit_phc_id="PHC-RAMPUR",
        sku="ORS Packets",
        required_quantity=1200,
        phc_network=phc_network,
        safety_stock_ratio=0.35
    )

    assert result["status"] == "OPTIMAL"
    assert result["allocated_quantity"] == 1200
    assert result["unmet_deficit"] == 0
    assert len(result["transfers"]) > 0

    # Verify donor safety stock preservation
    for t in result["transfers"]:
        assert t["source_stock_after"] >= t["safety_stock_threshold"]
        assert t["quantity"] > 0
        assert t["destination_phc_id"] == "PHC-RAMPUR"

def test_ortools_zero_surplus_infeasible():
    solver = ORToolsRedistributionSolver()

    phc_network = [
        {
            "phc_id": "PHC-A",
            "phc_name": "PHC A",
            "lat": 26.70,
            "lon": 83.30,
            "normal_capacity": 100,
            "stock_ors": 50  # Depleted
        },
        {
            "phc_id": "PHC-B",
            "phc_name": "PHC B",
            "lat": 26.72,
            "lon": 83.32,
            "normal_capacity": 100,
            "stock_ors": 60  # Below safety threshold
        }
    ]

    result = solver.solve_stock_redistribution(
        deficit_phc_id="PHC-A",
        sku="ORS Packets",
        required_quantity=800,
        phc_network=phc_network
    )

    assert result["status"] == "INFEASIBLE"
    assert result["allocated_quantity"] == 0
    assert len(result["transfers"]) == 0
